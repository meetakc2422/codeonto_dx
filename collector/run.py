"""Codeonto collector: every job that talks to an external platform.

    python run.py zomato session --account main
    python run.py swiggy session --account mn --account ggn
    python run.py swiggy outlets --account mn --account ggn   # accessible outlets -> swiggy_outlets
    python run.py all session                      # every account in ACCOUNTS
    python run.py all outlets                      # every account in ACCOUNTS
    python run.py all session --daily-at 06:00     # keep running, repeat daily
    python run.py all session --check              # validate .env only, no external calls
"""

import argparse
import importlib
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Always run inside the collector's own virtualenv (it has Playwright, Google auth, psycopg),
# even when started with some other `python`.
_VENV_PYTHON = Path(__file__).resolve().parent / ".venv" / "bin" / "python"
if _VENV_PYTHON.exists() and Path(sys.prefix).resolve() != _VENV_PYTHON.parent.parent.resolve():
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON), *sys.argv])

from core.common import ConfigError, log, session_path, setup_logging  # noqa: E402

# platform -> task -> module with config(account) and either run(account, headless) for
# per-account jobs or run_all(accounts, headless, force) for jobs that need every account
# at once (e.g. outlets, to know what disappeared). Add a job: one module + one line here.
TASKS = {
    "zomato": {"session": "zomato.session", "outlets": "zomato.outlets", "reviews": "zomato.reviews", "stockouts": "zomato.stockouts", "uptime": "zomato.uptime", "payouts": "zomato.payouts", "business": "zomato.business", "timings": "zomato.timings", "complaints": "zomato.complaints", "item_sales": "zomato.item_sales", "ratings": "zomato.ratings"},
    "swiggy": {"session": "swiggy.session", "outlets": "swiggy.outlets", "reviews": "swiggy.reviews", "business": "swiggy.business", "payouts": "swiggy.payouts", "complaints": "swiggy.complaints", "ratings": "swiggy.ratings"},
    "google": {"session": "google_business.session", "outlets": "google_business.outlets", "reviews": "google_business.reviews", "performance": "google_business.performance", "profile": "google_business.profile"},
}


def configured_accounts() -> list[tuple[str, str]]:
    """ACCOUNTS=zomato:main,swiggy:mn,swiggy:ggn,google:agency
    A star takes every active account of that platform from the database (google:* includes clients who connected
    Google from the dashboard)."""
    pairs = []
    for item in os.getenv("ACCOUNTS", "").split(","):
        if ":" in item:
            platform, account = (s.strip() for s in item.split(":", 1))
            if platform not in TASKS:
                raise ConfigError(f"Unknown platform '{platform}' in ACCOUNTS")
            if account == "*":
                from core import db
                with db.transaction() as cur:
                    cur.execute("SELECT label FROM platform_accounts WHERE platform_id = %s AND is_active ORDER BY label", (platform,))
                    pairs += [(platform, r["label"]) for r in cur.fetchall()]
            else:
                pairs.append((platform, account))
    if not pairs:
        raise ConfigError("ACCOUNTS is empty, e.g. ACCOUNTS=zomato:main,swiggy:mn")
    return list(dict.fromkeys(pairs))


def _module(platform: str, task: str):
    return importlib.import_module(TASKS[platform][task])


def run_jobs(jobs: list[tuple[str, str]], task: str, headless: bool, force: bool = False) -> bool:
    ok = True
    for platform in dict.fromkeys(p for p, _ in jobs):
        module = _module(platform, task)
        accounts = [a for p, a in jobs if p == platform]
        if hasattr(module, "run_all"):
            try:
                ok = module.run_all(accounts, headless=headless, force=force) and ok
            except Exception as e:
                log.exception("%s %s crashed: %s", task, platform, e)
                ok = False
            continue
        for account in accounts:
            try:
                ok = module.run(account, headless=headless) and ok
            except Exception as e:  # one account failing must not stop the rest
                log.exception("%s %s/%s crashed: %s", task, platform, account, e)
                ok = False
    return ok


def check(jobs: list[tuple[str, str]], task: str) -> bool:
    ok = True
    for platform, account in jobs:
        try:
            _module(platform, task).config(account)
            path = session_path(platform, account)
            age = (f"session refreshed {datetime.fromtimestamp(path.stat().st_mtime):%Y-%m-%d %H:%M}"
                   if path.exists() else "no session file yet")
            log.info("OK  %s %s/%s (%s)", task, platform, account, age)
        except ConfigError as e:
            log.error("BAD %s %s/%s: %s", task, platform, account, e)
            ok = False
    return ok


def run_daily(at: str, jobs, task: str, headless: bool) -> None:
    hour, minute = (int(x) for x in at.split(":"))
    while True:
        now = datetime.now()
        nxt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        log.info("Next %s run at %s", task, nxt.strftime("%Y-%m-%d %H:%M"))
        time.sleep((nxt - now).total_seconds())
        run_jobs(jobs, task, headless)


def main() -> int:
    all_tasks = sorted({t for tasks in TASKS.values() for t in tasks})
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("platform", choices=[*TASKS, "all"])
    parser.add_argument("task", nargs="?", default="session", choices=all_tasks, help="default: session")
    parser.add_argument("--account", action="append", help="Account name (repeatable), e.g. main, mn, ggn")
    parser.add_argument("--headless", action="store_true", help="Run browsers without a window (servers)")
    parser.add_argument("--daily-at", metavar="HH:MM", help="Run now, then every day at this time")
    parser.add_argument("--every", metavar="MINUTES", type=int, help="Run now, then repeat every N minutes (e.g. stockouts)")
    parser.add_argument("--once", action="store_true", help="stockouts, uptime: run a single pass instead of repeating every 5 minutes")
    parser.add_argument("--check", action="store_true", help="Validate configuration only; no external calls")
    parser.add_argument("--force", action="store_true",
                        help="outlets: allow deactivating more than 20%% of a catalog in one run")
    args = parser.parse_args()
    setup_logging()

    try:
        if args.platform == "all":
            jobs = [(p, a) for p, a in configured_accounts() if args.task in TASKS[p]]
        else:
            if args.task not in TASKS[args.platform]:
                parser.error(f"{args.platform} has no '{args.task}' task (has: {', '.join(TASKS[args.platform])})")
            accounts = args.account or [a for p, a in configured_accounts() if p == args.platform]
            if not accounts:
                parser.error(f"No {args.platform} account: pass --account or add {args.platform}:<name> to ACCOUNTS")
            jobs = [(args.platform, a) for a in accounts]
    except ConfigError as e:
        log.error("%s", e)
        return 2

    if args.check:
        return 0 if check(jobs, args.task) else 1
    if args.task in ("stockouts", "uptime") and not args.every and not args.once:
        args.every = 5  # live monitors: repeat unless told otherwise
    started = time.time()
    ok = run_jobs(jobs, args.task, args.headless, args.force)
    while args.every:
        # fixed cadence: wait out the rest of the interval, so a slow pass does not push the next one later
        wait = max(5.0, args.every * 60 - (time.time() - started))
        log.info("Next %s run in %.1f min", args.task, wait / 60)
        time.sleep(wait)
        started = time.time()
        try:
            run_jobs(jobs, args.task, args.headless, args.force)
        except Exception as e:
            log.exception("%s run crashed, will retry next cycle: %s", args.task, e)
    if args.daily_at:
        run_daily(args.daily_at, jobs, args.task, args.headless)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
