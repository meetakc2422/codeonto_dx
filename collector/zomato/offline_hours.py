"""Zomato's own "Offline hours" per outlet and day -> zomato_offline_hours, for every Zomato id mapped to a store.

The partner dashboard's owner-hub report (`multi-outlet-breakdown?filter=offline_hours&selected_date=...`) lists, for one
date, every outlet the login can see with the hours it was offline. We keep it beside our own uptime checks: it covers days
our monitor wasn't running. Runs once a day over the last OFFLINE_HOURS_DAYS days (default 3, since Zomato settles the day
late); saving is an upsert, so running twice is harmless. BACKFILL_FROM / BACKFILL_TO fetch other dates.
"""

import re
import time
from datetime import datetime, timedelta, timezone

from core import alerts, config as cfg, db, retry
from core.common import ConfigError, log, require_env

from .outlets import _cookies
from .reviews import ZOMATO_API, _headers

URL = cfg.text("ZOMATO_OFFLINE_HOURS_URL", f"{ZOMATO_API}/owner-hub/reporting/multi-outlet-breakdown")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
DAYS = cfg.integer("OFFLINE_HOURS_DAYS", 3)
PACE_SEC = cfg.numbers("OFFLINE_HOURS_PACE_SEC", "1,3")
ID = re.compile(r"ID:\s*(\d+)")


class RateLimited(Exception):
    pass


def config(account: str) -> dict:
    return require_env("SOCIALSPORK_DATABASE_URL")


def _text(cell) -> str:
    return (cell.get("text") if isinstance(cell, dict) else cell) or ""


def parse(body: dict) -> dict[str, float]:
    """{res_id: hours offline} from the report's rows ("Outlet name, ID: 12345" with the hours as a decimal number)."""
    out = {}
    for block in body.get("results") or []:
        for item in (block.get("multi_line_text_snippet_type_2") or {}).get("items") or []:
            m = ID.search(_text(item.get("title")))
            value = _text(item.get("subtitle")).strip()
            if m and re.fullmatch(r"\d+(\.\d+)?", value):
                out[m.group(1)] = float(value)
    return out


def _fetch(cookies: dict, day) -> dict[str, float]:
    import requests

    resp = requests.get(URL, params={"selected_tab": "tab_daily", "filter": "offline_hours", "selected_date": day.isoformat()},
                        headers={**_headers(cookies), "user-agent": cfg.user_agent()}, cookies=cookies, timeout=cfg.http_timeout())
    if resp.status_code in (401, 403):
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
    if resp.status_code == 429:
        raise RateLimited("Zomato rate limit (429) on the owner-hub report")
    resp.raise_for_status()
    return parse(resp.json())


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato offline_hours: %s", e)
        return False
    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id FROM brand_outlets bo
                       JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id WHERE bo.is_active AND z.is_active""")
        by_res = {str(r["res_id"]): r["outlet_id"] for r in cur.fetchall()}
    if not by_res:
        log.info("zomato offline_hours: no Zomato ids are mapped to stores yet")
        return True
    today = datetime.now(IST).date()
    start, end = cfg.date_range(today - timedelta(days=DAYS), today - timedelta(days=1))  # the day in progress is not settled
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    ok, saved = True, 0
    for name, account in accs.items():
        try:
            cookies = _cookies(db.load_credentials(account))
            for day in days:
                rows = retry.call(lambda: _fetch(cookies, day), f"zomato offline_hours {name} {day}", slow=(RateLimited,))
                mine = [(by_res[r], h) for r, h in rows.items() if r in by_res]
                with db.transaction() as cur:
                    for outlet_id, hrs in mine:
                        cur.execute("""INSERT INTO zomato_offline_hours (outlet_id, day, hours, fetched_at) VALUES (%s, %s, %s, now())
                                       ON CONFLICT (outlet_id, day) DO UPDATE SET hours = EXCLUDED.hours, fetched_at = now()""",
                                    (outlet_id, day, round(min(hrs, 24.0), 2)))
                saved += len(mine)
                log.info("zomato offline_hours %s %s: %s of our outlets in %s listed", name, day, len(mine), len(rows))
                time.sleep(__import__("random").uniform(*PACE_SEC))
        except PermissionError as e:
            log.error("zomato offline_hours %s: %s", name, e)
            db.mark_session_expired(account["id"], f"zomato offline_hours: {e}")
            alerts.incident(f"Zomato session expired: {name}", str(e), f"Use Log in again on the Sessions page, or run `python run.py zomato session --account {name}`.")
            ok = False
        except Exception as e:  # noqa: BLE001
            log.exception("zomato offline_hours %s failed: %s", name, e)
            ok = False
    log.info("zomato offline_hours: %s outlet-days saved", saved)
    return ok
