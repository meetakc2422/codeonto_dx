"""Login refresh worker: does what staff ask for on the site's Sessions page: log an account in again, or sync the outlets
that account can see (adds new ones to the catalog; it never deactivates any). It also runs "Sync past data" for a brand
(Brands & Outlets page): run_backfill.py for that brand's outlets, reviews + business reports + payouts, one backfill at a
time across all workers, in the background so a login request is never kept waiting behind it.

    python run.py worker              # keep running, check for requests every 30 seconds
    python run.py worker --once       # handle what is queued now, then exit

The site only queues a request (table session_refreshes). This worker claims one with FOR UPDATE SKIP LOCKED, so with
several machines running a worker each request still runs exactly once, then runs the normal login for that account
(zomato.session / swiggy.session: Playwright + the email OTP) and records done or failed with the reason. The new
session is saved where the account reads it from (the database for db:session accounts), which also clears its
"expired" flag. Nothing here listens on a port: the worker pulls, so the machine needs no inbound access."""

import importlib
import logging
import os
import platform as _host
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import db
from .common import log

BACKFILL_LOCK = 770125  # one backfill at a time across every worker: Zomato and Swiggy throttle bulk reading
BACKFILL_JOBS = "business,payouts,reviews"  # what a brand's "Sync past data" loads: history-capable jobs only
BACKFILL_STALE_MINUTES = 45  # same as BackfillRequest.STALE_RUNNING_MINUTES on the site
HERE = Path(__file__).resolve().parent.parent
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


# ---------- backfill: load a brand's past reviews, business reports and payouts (queued on the site's Brands & Outlets page) ----------

def claim_backfill() -> dict | None:
    """Take the oldest queued backfill, but only when none is running anywhere (an advisory lock keeps two workers from both deciding that)."""
    with db.transaction() as cur:
        cur.execute("SELECT pg_try_advisory_xact_lock(%s) AS ok", (BACKFILL_LOCK,))
        if not cur.fetchone()["ok"]:
            return None
        cur.execute(f"""UPDATE backfill_requests SET status = 'failed', finished_at = now(),
                          error = 'The collector stopped reporting. Sync again: what was already loaded is kept.'
                        WHERE status = 'running' AND updated_at < now() - interval '{BACKFILL_STALE_MINUTES} minutes'""")
        cur.execute("""SELECT r.id, r.brand_id, r.days, r.requested_by, b.name AS brand
                         FROM backfill_requests r JOIN brands b ON b.id = r.brand_id
                        WHERE r.status = 'queued' AND NOT EXISTS (SELECT 1 FROM backfill_requests x WHERE x.status = 'running')
                        ORDER BY r.requested_at LIMIT 1 FOR UPDATE OF r SKIP LOCKED""")
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE backfill_requests SET status = 'running', started_at = now(), updated_at = now(), worker = %s, progress = 'Starting…' WHERE id = %s",
                        (worker_name(), row["id"]))
        return row


def _backfill_ids(brand_id: int) -> dict[str, list[str]]:
    with db.transaction() as cur:
        cur.execute("SELECT zomato_res_id AS z, swiggy_id AS s FROM brand_outlets WHERE brand_id = %s AND is_active", (brand_id,))
        rows = cur.fetchall()
    return {"zomato": sorted({str(r["z"]) for r in rows if r["z"]}), "swiggy": sorted({str(r["s"]) for r in rows if r["s"]})}


def _backfill_update(request_id: int, **fields) -> None:
    """Write progress / status; with no fields it only says 'still alive' (updated_at)."""
    sets = "".join(f"{k} = %s, " for k in fields)
    with db.transaction() as cur:
        cur.execute(f"UPDATE backfill_requests SET {sets}updated_at = now() WHERE id = %s", (*fields.values(), request_id))


_STAMP = re.compile(r"^\[[^\]]*\]\s*")
_TOTAL = re.compile(r"(\d+) runs to do")
_RANS = re.compile(r"Backfill finished: (\d+)/(\d+) runs done, (\d+) failed, (\d+) stopped")


def run_backfill(req: dict) -> None:
    """Run run_backfill.py for the brand's outlets and keep the request's progress current. It already works in date chunks, waits out rate
    limits, runs Zomato and Swiggy side by side and remembers finished chunks, so a second attempt carries on where the first stopped."""
    ids = _backfill_ids(req["brand_id"])
    name = f"{req['brand']} ({req['days']} days)"
    if not ids["zomato"] and not ids["swiggy"]:
        _backfill_update(req["id"], status="failed", finished_at=datetime.now(timezone.utc),
                         error="This brand has no outlet with a Zomato or Swiggy ID.")
        return
    cmd = [sys.executable, str(HERE / "run_backfill.py"), "--days", str(req["days"]), "--jobs", BACKFILL_JOBS]
    for platform in ("zomato", "swiggy"):
        if ids[platform]:
            cmd += [f"--{platform}", ",".join(ids[platform])]
    log.info("Backfill %s requested by %s: %s Zomato and %s Swiggy outlets", name, req["requested_by"], len(ids["zomato"]), len(ids["swiggy"]))
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    total = done = 0
    problems: list[str] = []
    finished = None
    stop_beat = threading.Event()

    def beat():  # the site fails a backfill whose worker goes quiet; a long step prints nothing, so a timer says "still alive", not the output
        while not stop_beat.wait(60):
            try:
                _backfill_update(req["id"])
            except Exception as e:  # noqa: BLE001  a database blip must not stop the sync
                log.warning("Backfill heartbeat failed: %s", e)

    threading.Thread(target=beat, name="backfill-heartbeat", daemon=True).start()
    try:
        proc = subprocess.Popen(cmd, cwd=HERE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for raw in proc.stdout:
            line = _STAMP.sub("", raw.strip())
            if m := _TOTAL.search(line):
                total = int(m.group(1))
            if line.startswith("▶"):
                what = line[1:].strip().split(" (try")[0]  # e.g. "zomato payouts 50 outlets 2026-10-27..2026-11-25"
                parts = what.split()
                label = f"{parts[0].capitalize()} · {parts[1].replace('_', ' ')}" if len(parts) > 1 else what
                _backfill_update(req["id"], progress=f"{label} ({done} of {total} runs done)"[:300])
            elif line.startswith("✅"):
                done += 1
            elif line.startswith(("❌", "✋")):
                problems.append(line[1:].strip()[:300])
            elif m := _RANS.search(line):
                finished = tuple(int(x) for x in m.groups())
        code = proc.wait()
    except Exception as e:  # noqa: BLE001
        log.exception("Backfill %s crashed: %s", name, e)
        code, problems = 1, [str(e) or e.__class__.__name__]
    finally:
        stop_beat.set()
    now = datetime.now(timezone.utc)
    if code == 0:
        result = f"{finished[0]} of {finished[1]} runs done" if finished else ("Nothing left to load: already synced" if not total else f"{done} of {total} runs done")
        _backfill_update(req["id"], status="done", finished_at=now, progress="", result=result[:300], error="")
    else:
        expired = [p for p in problems if "expired" in p.lower()]
        error = (expired[-1] if expired else (problems[-1] if problems else f"The backfill stopped (exit {code}); see the collector log on {_host.node()}"))
        _backfill_update(req["id"], status="failed", finished_at=now, progress="", result=(f"{finished[0]} of {finished[1]} runs done" if finished else f"{done} of {total} runs done")[:300],
                         error=(error + "\nWhat finished is kept; sync again to load the rest.")[:2000])
    log.info("Backfill %s %s", name, "done" if code == 0 else "failed")


def release_own_backfills() -> int:
    with db.transaction() as cur:
        cur.execute("""UPDATE backfill_requests SET status = 'failed', finished_at = now(),
                          error = 'The worker was restarted while syncing. Sync again: what was already loaded is kept.'
                        WHERE status = 'running' AND worker = %s""", (worker_name(),))
        return cur.rowcount


def main(headless: bool = False, once: bool = False) -> int:
    log.info("Login refresh worker started as %s (checks every %ss)", worker_name(), POLL_SECONDS)
    try:
        if n := release_own():
            log.info("Released %s login(s) this worker was running when it stopped", n)
        if n := release_own_backfills():
            log.info("Released %s backfill(s) this worker was running when it stopped", n)
    except Exception as e:  # noqa: BLE001
        log.warning("Couldn't release unfinished logins: %s", e)
    active: threading.Thread | None = None
    while True:
        try:
            req = claim()
            while req:  # drain the login queue before sleeping
                run_one(req, headless)
                req = claim()
            if active is not None and not active.is_alive():
                active = None
            if active is None:  # a long backfill must never hold up a login: it runs in its own thread
                bf = claim_backfill()
                if bf:
                    active = threading.Thread(target=run_backfill, args=(bf,), name="backfill", daemon=not once)
                    active.start()
                    if once:
                        active.join()
                        active = None
        except Exception as e:  # noqa: BLE001  database blips: log and try again next round
            log.exception("Worker round failed, retrying in %ss: %s", POLL_SECONDS, e)
        if once:
            return 0
        time.sleep(POLL_SECONDS)
