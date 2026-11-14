"""Codeonto collector: every job that talks to an external platform.

    python run.py zomato session --account main
    python run.py swiggy session --account mn --account ggn
    python run.py swiggy outlets --account mn --account ggn   # accessible outlets -> swiggy_outlets
    python run.py all session                      # every account in ACCOUNTS
    python run.py all outlets                      # every account in ACCOUNTS
    python run.py all session --daily-at 06:00     # keep running, repeat daily
    python run.py all session --check              # validate .env only, no external calls
    python run.py worker                           # keep running: do login refreshes staff ask for on the Sessions page
    python run.py alerts send --every 15           # WhatsApp/email: low reviews, payout problems, ad spikes
    python run.py swiggy payouts --start 2026-10-01 --end 2026-11-09   # one-off: these dates instead of the usual window
    python run.py zomato business --res-id 22222916 --start 2026-06-01 # one-off: only these outlets
                                                   # (offline and stock-out alerts go out from those jobs)
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
_VENV = Path(__file__).resolve().parent / ".venv"
_VENV_PYTHON = _VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if _VENV_PYTHON.exists() and Path(sys.prefix).resolve() != _VENV.resolve():
    if os.name == "nt":  # Windows has no real exec: run the venv's python as a child and pass its exit code on
        import subprocess
        sys.exit(subprocess.call([str(_VENV_PYTHON), *sys.argv]))
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON), *sys.argv])

from core.common import ConfigError, log, session_path, setup_logging  # noqa: E402

# platform -> task -> module with config(account) and either run(account, headless) for
# per-account jobs or run_all(accounts, headless, force) for jobs that need every account
# at once (e.g. outlets, to know what disappeared). Add a job: one module + one line here.
TASKS = {
    "zomato": {"session": "zomato.session", "outlets": "zomato.outlets", "reviews": "zomato.reviews", "stockouts": "zomato.stockouts", "uptime": "zomato.uptime", "payouts": "zomato.payouts", "business": "zomato.business", "timings": "zomato.timings", "replies": "zomato.replies", "complaints": "zomato.complaints", "item_sales": "zomato.item_sales", "ratings": "zomato.ratings", "orders": "zomato.orders"},
    "swiggy": {"session": "swiggy.session", "outlets": "swiggy.outlets", "reviews": "swiggy.reviews", "stockouts": "swiggy.stockouts", "orders": "swiggy.orders", "business": "swiggy.business", "payouts": "swiggy.payouts", "complaints": "swiggy.complaints", "ratings": "swiggy.ratings"},
    "alerts": {"send": "core.notify"},
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


def _crash_alert(what: str, e: Exception) -> None:
    """Email ops that a job crashed (at most once an hour per job, via ALERT_OPS_EMAILS); never let the alert itself fail."""
    try:
        from core import alerts
        alerts.incident(f"{what} crashed", f"{type(e).__name__}: {str(e)[:400]}",
                        "Check this job's window or log on the collector server; it retries on its next cycle.")
    except Exception:
        log.exception("could not send the crash alert for %s", what)


class _ErrorWatch:
    """Collects the ERROR lines a job logs while it runs. Jobs catch most problems themselves (one store, one
    account) and carry on, so without this a job could fail every run and nobody would hear about it. On exit,
    if the job logged errors and did not already send its own alert, ops get one mail (once an hour per job)."""

    def __init__(self, what: str):
        import logging

        self.what, self.lines = what, []
        handler = logging.Handler(logging.ERROR)
        handler.emit = lambda record: self.lines.append(record.getMessage().splitlines()[0][:300])
        self.handler = handler

    def __enter__(self):
        from core import alerts

        self.before = alerts.incident_calls
        log.addHandler(self.handler)
        return self

    def __exit__(self, *exc):
        log.removeHandler(self.handler)
        try:
            from core import alerts

            if self.lines and alerts.incident_calls == self.before:
                shown = list(dict.fromkeys(self.lines))[:5]
                alerts.incident(f"{self.what} had errors", f"{len(self.lines)} error(s) this run: " + " | ".join(shown),
                                "Check this job's window or log on the collector server; it runs again on its next cycle.")
        except Exception:
            log.exception("could not send the error alert for %s", self.what)
        return False


def run_jobs(jobs: list[tuple[str, str]], task: str, headless: bool, force: bool = False) -> bool:
    ok = True
    for platform in dict.fromkeys(p for p, _ in jobs):
        with _ErrorWatch(f"{platform} {task}"):
            ok = _run_platform(platform, task, [a for p, a in jobs if p == platform], headless, force) and ok
    return ok


def _run_platform(platform: str, task: str, accounts: list[str], headless: bool, force: bool) -> bool:
    module = _module(platform, task)
    if hasattr(module, "run_all"):
        try:
            return module.run_all(accounts, headless=headless, force=force)
        except Exception as e:
            log.exception("%s %s crashed: %s", task, platform, e)
            _crash_alert(f"{platform} {task}", e)
            return False
    ok = True
    for account in accounts:
        try:
            ok = module.run(account, headless=headless) and ok
        except Exception as e:  # one account failing must not stop the rest
            log.exception("%s %s/%s crashed: %s", task, platform, account, e)
            _crash_alert(f"{platform} {task} ({account})", e)
            if isinstance(e, PermissionError) and "expired" in str(e).lower():
                from core.db import mark_session_expired_by_label
                mark_session_expired_by_label(platform, account, f"{platform} {task}: {e}")
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
    parser.add_argument("platform", choices=[*TASKS, "all", "worker"])
    parser.add_argument("task", nargs="?", default="session", choices=all_tasks, help="default: session")
    parser.add_argument("--account", action="append", help="Account name (repeatable), e.g. main, mn, ggn")
    parser.add_argument("--headless", action="store_true", help="Run browsers without a window (servers)")
    parser.add_argument("--daily-at", metavar="HH:MM", help="Run now, then every day at this time")
    parser.add_argument("--every", metavar="MINUTES", type=int, help="Run now, then repeat every N minutes (e.g. stockouts)")
    parser.add_argument("--once", action="store_true", help="stockouts, uptime: run a single pass instead of repeating every 5 minutes")
    parser.add_argument("--check", action="store_true", help="Validate configuration only; no external calls")
    parser.add_argument("--force", action="store_true",
                        help="outlets: allow deactivating more than 20%% of a catalog in one run")
    parser.add_argument("--start", "--from", dest="start", metavar="YYYY-MM-DD",
                        help="business, item_sales, complaints, payouts, swiggy reviews: start of the dates to fetch")
    parser.add_argument("--end", "--to", dest="end", metavar="YYYY-MM-DD", help="end of the dates to fetch (default: the job's usual end)")
    parser.add_argument("--res-id", action="append", help="only these outlets (repeatable or comma separated)")
    args = parser.parse_args()
    setup_logging()
    from datetime import date as _date

    for flag, value, env in (("--start", args.start, "BACKFILL_FROM"), ("--end", args.end, "BACKFILL_TO")):
        if value:
            try:
                _date.fromisoformat(value)
            except ValueError:
                parser.error(f"{flag} must be YYYY-MM-DD, got '{value}'")
            os.environ[env] = value
    if args.start and args.end and args.start > args.end:
        parser.error("--start is after --end")
    if args.res_id:
        os.environ["ONLY_RES_IDS"] = ",".join(x.strip() for v in args.res_id for x in v.split(",") if x.strip())

    if args.platform == "worker":  # long-running: picks up refresh requests from the site
        from core import worker
        return worker.main(headless=args.headless, once=args.once)

    try:
        if args.platform == "alerts":  # not tied to a platform login
            if args.task not in TASKS["alerts"]:
                parser.error("alerts has one task: send (e.g. `python run.py alerts send --every 15`)")
            jobs = [("alerts", "-")]
        elif args.platform == "all":
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
    try:
        ok = run_jobs(jobs, args.task, args.headless, args.force)
    except Exception as e:  # a repeating job must reach its loop even if the first pass crashes
        if not args.every:
            raise
        ok = False
        log.exception("%s run crashed, will retry next cycle: %s", args.task, e)
        _crash_alert(args.task, e)
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
            _crash_alert(args.task, e)
    if args.daily_at:
        run_daily(args.daily_at, jobs, args.task, args.headless)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
