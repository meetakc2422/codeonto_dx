"""Login refresh worker: does what staff ask for on the site's Sessions page: log an account in again, or sync the outlets
that account can see (adds new ones to the catalog; it never deactivates any).

    python run.py worker              # keep running, check for requests every 30 seconds
    python run.py worker --once       # handle what is queued now, then exit

The site only queues a request (table session_refreshes). This worker claims one with FOR UPDATE SKIP LOCKED, so with
several machines running a worker each request still runs exactly once, then runs the normal login for that account
(zomato.session / swiggy.session: Playwright + the email OTP) and records done or failed with the reason. The new
session is saved where the account reads it from (the database for db:session accounts), which also clears its
"expired" flag. Nothing here listens on a port: the worker pulls, so the machine needs no inbound access."""

import importlib
import logging
import platform as _host
import time

from . import db
from .common import log

POLL_SECONDS = 30
STALE_MINUTES = 15  # same as SessionRefresh.STALE_MINUTES on the site
SUPPORTED = ("zomato", "swiggy")


def worker_name() -> str:
    return f"collector@{_host.node()}"[:150]


def claim() -> dict | None:
    """Fail stale requests, then take the oldest queued one for a platform this worker can log in to."""
    with db.transaction() as cur:
        cur.execute(f"""UPDATE session_refreshes SET status = 'failed', finished_at = now(),
                          error = 'No collector picked this up in {STALE_MINUTES} minutes. Is the Windows worker running?'
                        WHERE status = 'queued' AND requested_at < now() - interval '{STALE_MINUTES} minutes'""")
        cur.execute(f"""UPDATE session_refreshes SET status = 'failed', finished_at = now(),
                          error = 'The login didn''t finish in {STALE_MINUTES} minutes; the worker may have stopped.'
                        WHERE status = 'running' AND started_at < now() - interval '{STALE_MINUTES} minutes'""")
        cur.execute("""SELECT r.id, r.requested_by, r.kind, a.label, a.platform_id AS platform
                         FROM session_refreshes r JOIN platform_accounts a ON a.id = r.account_id
                        WHERE r.status = 'queued' AND a.platform_id = ANY(%s)
                        ORDER BY r.requested_at LIMIT 1
                        FOR UPDATE OF r SKIP LOCKED""", (list(SUPPORTED),))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE session_refreshes SET status = 'running', started_at = now(), worker = %s WHERE id = %s",
                        (worker_name(), row["id"]))
        return row


def finish(request_id: int, ok: bool, error: str = "", result: str = "") -> None:
    with db.transaction() as cur:
        cur.execute("UPDATE session_refreshes SET status = %s, finished_at = now(), error = %s, result = %s WHERE id = %s",
                    ("done" if ok else "failed", error[:2000], result[:300], request_id))


class _LastError(logging.Handler):
    """Keeps the last error the login logged, so a failed request says why on the site."""

    def __init__(self):
        super().__init__(logging.ERROR)
        self.message = ""

    def emit(self, record):
        self.message = record.getMessage()


def run_outlet_sync(req: dict, headless: bool) -> None:
    """Ask the platform which outlets this login can access and update the catalog (add and refresh only: other logins
    weren't read, so nothing is deactivated). Reports what it found on the site, e.g. '24 outlets, 3 new'."""
    from . import outlets as shared

    name = f"{req['platform']}/{req['label']}"
    log.info("Outlet sync %s requested by %s", name, req["requested_by"])
    catcher = _LastError()
    log.addHandler(catcher)
    result = ""
    try:
        ok = importlib.import_module(f"{req['platform']}.outlets").run_all([req["label"]], headless=headless)
        stats = shared.LAST.get(req["label"])
        if ok and stats:
            result = f"{stats.get('outlets', 0)} outlets, {stats.get('new', 0)} new"
        error = "" if ok else (catcher.message or f"Outlet sync failed; see the collector log on {_host.node()}")
    except Exception as e:  # noqa: BLE001
        log.exception("Outlet sync %s crashed: %s", name, e)
        ok, error = False, str(e) or e.__class__.__name__
    finally:
        log.removeHandler(catcher)
    finish(req["id"], ok, error, result)
    log.info("Outlet sync %s %s%s", name, "done" if ok else "failed", f": {error or result}")


def run_one(req: dict, headless: bool) -> None:
    if req.get("kind") == "outlets":
        return run_outlet_sync(req, headless)
    name = f"{req['platform']}/{req['label']}"
    log.info("Refresh %s requested by %s: logging in", name, req["requested_by"])
    catcher = _LastError()
    log.addHandler(catcher)
    try:
        ok = importlib.import_module(f"{req['platform']}.session").run(req["label"], headless=headless)
        error = "" if ok else (catcher.message or f"Login failed; see the collector log on {_host.node()}")
    except Exception as e:  # noqa: BLE001  one failed login must not stop the worker
        log.exception("Refresh %s crashed: %s", name, e)
        ok, error = False, str(e) or e.__class__.__name__
    finally:
        log.removeHandler(catcher)
    finish(req["id"], ok, error)
    log.info("Refresh %s %s%s", name, "done" if ok else "failed", f": {error}" if error else "")


def release_own() -> int:
    """A worker that was stopped mid-login leaves its request 'running'. On start, fail those at once (instead of
    after the 15-minute timeout) so the button on the site unlocks."""
    with db.transaction() as cur:
        cur.execute("""UPDATE session_refreshes SET status = 'failed', finished_at = now(),
                          error = 'The worker was restarted while running this. Click the button again.'
                        WHERE status = 'running' AND worker = %s""", (worker_name(),))
        return cur.rowcount


def main(headless: bool = False, once: bool = False) -> int:
    log.info("Login refresh worker started as %s (checks every %ss)", worker_name(), POLL_SECONDS)
    try:
        if n := release_own():
            log.info("Released %s login(s) this worker was running when it stopped", n)
    except Exception as e:  # noqa: BLE001
        log.warning("Couldn't release unfinished logins: %s", e)
    while True:
        try:
            req = claim()
            while req:  # drain the queue before sleeping
                run_one(req, headless)
                req = claim()
        except Exception as e:  # noqa: BLE001  database blips: log and try again next round
            log.exception("Worker round failed, retrying in %ss: %s", POLL_SECONDS, e)
        if once:
            return 0
        time.sleep(POLL_SECONDS)
