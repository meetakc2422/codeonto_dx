"""Zomato store uptime -> offline_episodes and outlet_uptime_daily, for every Zomato id mapped to a store.

One call per account returns the live delivery status of every outlet it can access. A store offline during its opening
hours starts an episode, which ends when it is seen online again. Only opening hours count as downtime. Meant to run
every few minutes (`run.py zomato uptime --every 5`).

An outlet missing from the response is unknown, not offline: nothing is recorded for it. If the collector stops for a
while, the episode ends at the last check that saw the store offline, so the gap isn't counted as downtime.
"""

from datetime import datetime, timedelta, timezone

from core import alerts, config as cfg, db, hours, notify, retry
from core.common import ConfigError, log, require_env

from .outlets import _cookies
from .reviews import ZOMATO_API, _headers

STATUS_URL = cfg.text("ZOMATO_OUTLET_STATUS_URL", f"{ZOMATO_API}/restaurant/get-all-minimal-lite")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
MAX_GAP = timedelta(minutes=cfg.integer("UPTIME_MAX_GAP_MIN", 30))


class RateLimited(Exception):
    pass


class Blocked(Exception):
    """Zomato's firewall (Akamai) refused the request: an "Access Denied" page, not a logged-out session."""


class Unreliable(Exception):
    """Zomato answered, but not with statuses we can trust."""
    transient = True  # degraded mode usually clears in seconds: retried


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _fetch(cookies: dict) -> dict[str, bool]:
    """{res_id: online} for every outlet this login can access. Raises PermissionError when the session is dead."""
    import requests

    resp = requests.get(STATUS_URL, headers={**_headers(cookies), "user-agent": cfg.user_agent()},
                        timeout=cfg.integer("UPTIME_HTTP_TIMEOUT_SEC", 20))
    if resp.status_code == 403 and ("access denied" in resp.text[:2000].lower() or "akamai" in resp.text[:2000].lower()
                                    or "json" not in resp.headers.get("content-type", "")):
        raise Blocked("Zomato blocked the outlet-status request (403 Access Denied)")
    if resp.status_code in (401, 403):
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
    if resp.status_code == 429:
        raise RateLimited("Zomato rate limit (429) on outlet status")
    resp.raise_for_status()
    try:
        body = resp.json()
    except ValueError:
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
    if body.get("is_degraded_mode"):
        raise Unreliable("Zomato reports degraded mode")
    entities = body.get("entities") or []
    if not entities:
        raise Unreliable("Zomato returned no outlets")
    return {str(e["id"]): e["delivery_status"] == 1 for e in entities if e.get("id") and e.get("delivery_status") in (0, 1)}


def _downtime(first: datetime, until: datetime, slots) -> int:
    start, end = (t.astimezone(IST).replace(tzinfo=None) for t in (first, until))
    return max(1, round(hours.open_minutes(slots, start, end)))


def _close(cur, episode: dict, at: datetime, slots) -> int:
    minutes = _downtime(episode["first_detected_at"], at, slots)
    cur.execute("UPDATE offline_episodes SET is_active = false, restored_at = %s, downtime_minutes = %s WHERE id = %s",
                (at, minutes, episode["id"]))
    return minutes


def sync(cur, outlet_id: int, online: bool, now: datetime, slots=None) -> str | None:
    """Store one check of one store. Returns 'offline' or 'online' when this check changed its state."""
    local = now.astimezone(IST)
    is_open = hours.is_open(slots, local.replace(tzinfo=None))
    day = cfg.business_date(local)
    if is_open:  # closed hours say nothing about uptime
        cur.execute("""INSERT INTO outlet_uptime_daily (outlet_id, platform, day, checks, online_checks, updated_at)
                       VALUES (%s, 'zomato', %s, 1, %s, %s)
                       ON CONFLICT (outlet_id, platform, day) DO UPDATE SET checks = outlet_uptime_daily.checks + 1,
                         online_checks = outlet_uptime_daily.online_checks + EXCLUDED.online_checks, updated_at = EXCLUDED.updated_at""",
                    (outlet_id, day, int(online), now))
    cur.execute("""SELECT id, first_detected_at, last_detected_at FROM offline_episodes
                   WHERE outlet_id = %s AND platform = 'zomato' AND is_active""", (outlet_id,))
    episode = cur.fetchone()
    if episode and now - episode["last_detected_at"] > MAX_GAP:
        _close(cur, episode, episode["last_detected_at"], slots)  # we weren't watching: don't count the gap as downtime
        episode = None
    if online:
        if not episode:
            return None
        _close(cur, episode, now, slots)
        return "online"
    if episode:
        cur.execute("UPDATE offline_episodes SET last_detected_at = %s, downtime_minutes = %s WHERE id = %s",
                    (now, _downtime(episode["first_detected_at"], now, slots), episode["id"]))
        return None
    if not is_open:  # offline while closed is expected
        return None
    cur.execute("""INSERT INTO offline_episodes (outlet_id, platform, is_active, log_date, first_detected_at, last_detected_at, downtime_minutes)
                   VALUES (%s, 'zomato', true, %s, %s, %s, 0)""", (outlet_id, day, now, now))
    return "offline"


def _save(outlet_id, online, now, slots):
    with db.transaction() as cur:
        return sync(cur, outlet_id, online, now, slots)


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato uptime: %s", e)
        return False

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND z.is_active""")
        stores = cur.fetchall()
    if not stores:
        log.info("zomato uptime: no Zomato ids are mapped to stores yet")
        return True

    statuses: dict[str, bool] = {}
    ok = True
    for name, account in accs.items():
        try:
            cookies = _cookies(db.load_credentials(account))
            statuses |= retry.call(lambda: _fetch(cookies), f"zomato uptime {name}", slow=(RateLimited, Blocked))
        except PermissionError as e:
            log.error("zomato uptime %s: %s", name, e)
            db.mark_session_expired(account["id"], f"zomato uptime: {e}")
            alerts.incident(f"Zomato session expired: {name}", str(e), f"Use Log in again on the Sessions page, or run `python run.py zomato session --account {name}`.")
            ok = False
        except RateLimited as e:
            log.error("zomato uptime %s: %s; next cycle retries", name, e)
            alerts.incident("Zomato rate limit (429)", str(e), "The uptime job retried and backed off, then gave up until the next cycle. If it keeps happening, raise the interval (--every 10).")
            ok = False
        except Blocked as e:
            log.error("zomato uptime %s: %s; next cycle retries", name, e)
            alerts.incident("Zomato blocked the uptime checks (403)", str(e),
                            "This is usually Zomato's firewall refusing the server, not the login. Slow the job down "
                            "(--every 10); if it keeps happening, log in again on the Sessions page.")
            ok = False
        except Exception as e:  # nothing is recorded for this account's stores: unknown, not offline
            log.error("zomato uptime %s: %s", name, e)
            alerts.incident(f"Zomato uptime checks failing: {name}", f"{type(e).__name__}: {str(e)[:300]}",
                            "Outlet online/offline status is not being recorded for this login's stores. "
                            "Check the uptime window on the Windows server.")
            ok = False

    store_hours = hours.load("zomato", cfg.text("UPTIME_HOURS_SERVICE", "delivery"))
    now = datetime.now(timezone.utc)
    checked, offline, went_off, came_back = 0, 0, 0, 0
    for s in stores:
        online = statuses.get(str(s["res_id"]))
        if online is None:
            continue
        try:
            change = retry.call(lambda: _save(s["outlet_id"], online, now, store_hours.get(s["outlet_id"])),
                                f"zomato uptime save {s['res_id']}")
        except Exception as e:
            log.exception("zomato uptime %s save failed: %s", s["res_id"], e)
            ok = False
            continue
        checked += 1
        offline += not online
        went_off += change == "offline"
        came_back += change == "online"
        if change:
            log.info("zomato uptime %s · %s (%s): went %s", s["brand"], s["outlet_name"], s["res_id"], change)
    log.info("zomato uptime: checked %s of %s stores, %s offline (%s went offline, %s came back)",
             checked, len(stores), offline, went_off, came_back)
    notify.send(("offline", "online"))  # WhatsApp / email to the people who asked for them (Alerts settings)
    return ok
