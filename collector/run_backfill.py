"""Backfill old data for some outlets (e.g. newly onboarded clients) without touching everyone else.

For each job that has history it runs the normal `run.py <platform> <job>` limited to the given res_ids and dates
(ONLY_RES_IDS, BACKFILL_FROM, BACKFILL_TO), in date chunks, newest first. If a run hits a rate limit (429 / "too many
requests" / refusals) it waits RATE_WAIT seconds (2 minutes) and runs that chunk again. Finished chunks are saved in
logs/backfill_state.json, so stopping and starting again carries on where it left off.

Zomato and Swiggy run in parallel (different logins); inside a platform chunks go one by one unless --parallel > 1.

    python run_backfill.py --zomato 22222916,22222917 --swiggy 123456 --from 2026-05-01 --to 2026-11-08
    python run_backfill.py --new-since 2026-11-01 --from 2026-05-01        # every outlet first seen since that day
    python run_backfill.py --zomato-file new_zomato.txt --days 180         # ids one per line (or comma separated)
    python run_backfill.py ... --jobs business,item_sales --parallel 2 --chunk-days 30
    python run_backfill.py ... --dry-run                                   # show the plan only

Background on Windows:   start "backfill" /min python run_backfill.py --new-since 2026-11-01 --days 180
Background on Linux/mac: nohup python run_backfill.py ... &
Progress: logs/backfill.log
"""

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGS = HERE / "logs"
STATE = LOGS / "backfill_state.json"
LOG = LOGS / "backfill.log"

# jobs with history, per platform. Zomato reviews only goes by pages (newest first), so it gets more pages instead.
JOBS = {
    "zomato": ["business", "item_sales", "complaints", "payouts", "reviews"],
    "swiggy": ["business", "complaints", "payouts", "reviews"],
}
NO_DATES = {("zomato", "reviews")}
RATE_LIMIT = re.compile(r"\b429\b|rate.?limit|too many requests|throttl|refus|akamai|access denied", re.I)
EXPIRED = re.compile(r"session expired|run `run\.py \w+ session`", re.I)

_lock = threading.Lock()


def say(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    with _lock:
        print(line, flush=True)
        LOGS.mkdir(exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def load_state() -> set[str]:
    try:
        return set(json.loads(STATE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def mark_done(done: set[str], key: str) -> None:
    with _lock:
        done.add(key)
        LOGS.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(sorted(done), indent=0), encoding="utf-8")


def ids_from(value: str | None, file: str | None) -> list[str]:
    raw = (value or "") + "," + (Path(file).read_text(encoding="utf-8") if file else "")
    return list(dict.fromkeys(x.strip() for x in re.split(r"[,\s]+", raw) if x.strip()))


def new_since(day: date) -> dict[str, list[str]]:
    """res_ids first seen on or after `day` and mapped to an active store."""
    sys.path.insert(0, str(HERE))
    from core import db

    with db.transaction() as cur:
        cur.execute("""SELECT z.res_id FROM zomato_outlets z JOIN brand_outlets bo ON bo.zomato_res_id = z.res_id
                       WHERE z.is_active AND bo.is_active AND z.first_seen_at >= %s""", (day,))
        zom = [str(r["res_id"]) for r in cur.fetchall()]
        cur.execute("""SELECT s.swiggy_id FROM swiggy_outlets s JOIN brand_outlets bo ON bo.swiggy_id = s.swiggy_id
                       WHERE s.is_active AND bo.is_active AND s.first_seen_at >= %s""", (day,))
        swg = [str(r["swiggy_id"]) for r in cur.fetchall()]
    return {"zomato": zom, "swiggy": swg}


def chunks(start: date, end: date, size: int) -> list[tuple[date, date]]:
    out, cur = [], end
    while cur >= start:  # newest first, so recent data lands soonest
        s = max(start, cur - timedelta(days=size - 1))
        out.append((s, cur))
        cur = s - timedelta(days=1)
    return out


def run_once(platform: str, job: str, ids: list[str], window, pages: int, timeout: int) -> tuple[int, str]:
    env = {**os.environ, "ONLY_RES_IDS": ",".join(ids), "PYTHONIOENCODING": "utf-8"}
    if window:
        env["BACKFILL_FROM"], env["BACKFILL_TO"] = window[0].isoformat(), window[1].isoformat()
    else:
        env.pop("BACKFILL_FROM", None), env.pop("BACKFILL_TO", None)
        env["ZOMATO_REVIEW_PAGES"] = str(pages)
    cmd = [sys.executable, str(HERE / "run.py"), platform, job, "--headless"]
    try:
        p = subprocess.run(cmd, env=env, cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        return 124, f"timed out after {timeout}s\n{e.stdout or ''}{e.stderr or ''}"


def do_task(task: dict, args, done: set[str]) -> str:
    platform, job, ids, window, key = task["platform"], task["job"], task["ids"], task["window"], task["key"]
    what = f"{platform} {job} {len(ids)} outlets " + (f"{window[0]}..{window[1]}" if window else f"{args.review_pages} pages")
    for attempt in range(1, args.max_retries + 2):
        say(f"▶ {what} (try {attempt})")
        code, out = run_once(platform, job, ids, window, args.review_pages, args.timeout)
        errors = [ln for ln in out.splitlines() if "[ERROR]" in ln or "Traceback" in ln]
        if EXPIRED.search(out):
            say(f"✋ {what}: login session expired; refresh it on the Sessions page, then run this again. Last: {(errors or [''])[-1][-200:]}")
            return "expired"
        if code == 0 and not errors:
            mark_done(done, key)
            say(f"✅ {what}")
            return "ok"
        if RATE_LIMIT.search(out) and attempt <= args.max_retries:
            say(f"⏳ {what}: rate limited; waiting {args.rate_wait}s, then trying again")
            time.sleep(args.rate_wait)
            continue
        say(f"❌ {what}: exit {code}. Last: {(errors or out.strip().splitlines()[-1:] or [''])[-1][-300:]}")
        return "failed"
    say(f"❌ {what}: still rate limited after {args.max_retries} waits; run again later (finished chunks are kept)")
    return "failed"


def main():
    ap = argparse.ArgumentParser(description="Backfill old data for some outlets", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--zomato", help="Zomato res_ids, comma separated")
    ap.add_argument("--swiggy", help="Swiggy res_ids, comma separated")
    ap.add_argument("--zomato-file"), ap.add_argument("--swiggy-file")
    ap.add_argument("--new-since", metavar="YYYY-MM-DD", help="every mapped outlet first seen on/after this day")
    ap.add_argument("--from", dest="start", metavar="YYYY-MM-DD")
    ap.add_argument("--to", dest="end", metavar="YYYY-MM-DD", help="default: yesterday")
    ap.add_argument("--days", type=int, default=180, help="when --from isn't given: this many days back (default 180)")
    ap.add_argument("--jobs", help="comma separated subset, e.g. business,item_sales (default: all with history)")
    ap.add_argument("--chunk-days", type=int, default=30, help="days per run (default 30)")
    ap.add_argument("--batch", type=int, default=50, help="outlets per run (default 50)")
    ap.add_argument("--parallel", type=int, default=1, help="runs at once per platform (default 1 = one by one)")
    ap.add_argument("--rate-wait", type=int, default=120, help="seconds to wait after a rate limit (default 120)")
    ap.add_argument("--max-retries", type=int, default=10, help="rate-limit waits per chunk before giving up (default 10)")
    ap.add_argument("--review-pages", type=int, default=200, help="Zomato review pages per outlet (default 200)")
    ap.add_argument("--timeout", type=int, default=3 * 3600, help="seconds one run may take (default 3h)")
    ap.add_argument("--redo", action="store_true", help="ignore logs/backfill_state.json and run every chunk again")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    end = date.fromisoformat(args.end) if args.end else date.today() - timedelta(days=1)
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=args.days - 1)
    if start > end:
        ap.error("--from is after --to")

    ids = {"zomato": ids_from(args.zomato, args.zomato_file), "swiggy": ids_from(args.swiggy, args.swiggy_file)}
    if args.new_since:
        for p, found in new_since(date.fromisoformat(args.new_since)).items():
            ids[p] = list(dict.fromkeys(ids[p] + found))
    if not any(ids.values()):
        ap.error("no outlets: pass --zomato / --swiggy / --zomato-file / --swiggy-file / --new-since")
    wanted = {j.strip() for j in (args.jobs or "").split(",") if j.strip()}

    done = set() if args.redo else load_state()
    plan: dict[str, list[dict]] = {}
    for platform, platform_ids in ids.items():
        for job in JOBS[platform]:
            if wanted and job not in wanted:
                continue
            for b in range(0, len(platform_ids), args.batch):
                batch = platform_ids[b:b + args.batch]
                windows = [None] if (platform, job) in NO_DATES else chunks(start, end, args.chunk_days)
                for w in windows:
                    key = f"{platform}|{job}|{','.join(sorted(batch))}|" + (f"{w[0]}|{w[1]}" if w else "pages")
                    if key not in done:
                        plan.setdefault(platform, []).append({"platform": platform, "job": job, "ids": batch, "window": w, "key": key})

    total = sum(len(v) for v in plan.values())
    say(f"Backfill {start}..{end}: zomato {len(ids['zomato'])} outlets, swiggy {len(ids['swiggy'])} outlets, {total} runs to do"
        + (f" ({len(done)} already done)" if done else ""))
    if args.dry_run or not total:
        for tasks in plan.values():
            for t in tasks:
                say(f"  would run {t['platform']} {t['job']} {len(t['ids'])} outlets " + (f"{t['window'][0]}..{t['window'][1]}" if t["window"] else "by pages"))
        return

    def run_platform(tasks: list[dict]) -> list[str]:
        results, stop = [], threading.Event()

        def one(t):
            if stop.is_set():
                return "skipped"
            r = do_task(t, args, done)
            if r == "expired":
                stop.set()  # the login is dead: no point running the rest of this platform
            return r

        with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
            results = list(pool.map(one, tasks))
        return results

    with ThreadPoolExecutor(max_workers=len(plan)) as pool:
        results = [r for rs in pool.map(run_platform, plan.values()) for r in rs]
    ok = results.count("ok")
    say(f"Backfill finished: {ok}/{len(results)} runs done, {results.count('failed')} failed, "
        f"{results.count('expired') + results.count('skipped')} stopped by an expired login. Run the same command again to retry what's left.")
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
