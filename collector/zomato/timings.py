"""Zomato opening hours -> outlet_hours, for every Zomato id mapped to a store.

Reads the delivery (and any other service in SERVICE_TYPES) timings the merchant portal shows and replaces the
store's saved hours. Used by the stock-out job to skip closed stores and to leave closed hours out of downtime.
"""

import time
from datetime import time as clock

from core import config as cfg, db
from core.common import ConfigError, log, require_env

from .outlets import _cookies

SITE = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
URL = cfg.text("ZOMATO_TIMINGS_URL", f"{SITE}/merchant-api/restaurant/fetch-timings")
REFERER = cfg.text("ZOMATO_TIMINGS_REFERER", f"{SITE}/partners/o2-business/outletInfo/outlet-timings")
SERVICE_TYPES = [t.strip() for t in cfg.text("ZOMATO_TIMING_SERVICES", "delivery").split(",") if t.strip()]


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _fetch(cookies: dict, res_id: str, service: str) -> list[tuple]:
    """[(service, day, active, start, end)] for one store."""
    import os

    import requests

    headers = {"accept": "application/json, text/plain, */*", "user-agent": cfg.user_agent(), "referer": REFERER,
               "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
               "x-zomato-app-version": cfg.text("ZOMATO_APP_VERSION", "2"), "x-client-id": cfg.text("ZOMATO_CLIENT_ID", "zomato_web_merchant"),
               "x-zomato-csrft": cookies.get("csrf", ""), "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""),
               "x-zomato-trace-id": "web" + os.urandom(16).hex()}
    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = requests.get(URL, params={"res_id": res_id, "service_type": service}, headers=headers, timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
        if resp.status_code == 429:
            log.warning("Zomato 429; waiting")
            continue
        resp.raise_for_status()
        break
    else:
        resp.raise_for_status()
    body = resp.json()
    if body.get("status") != "success":
        return []
    rows = []
    for timing in (body.get("data") or {}).get("timings") or []:
        for day in timing.get("days") or []:
            slots = day.get("time_slots") or []
            for slot in slots:
                rows.append((timing.get("type") or service, (day.get("display_slug") or "").lower(), bool(day.get("active")),
                             _t(slot.get("start")), _t(slot.get("end"))))
            if not slots:  # a closed day, or active with no slots
                rows.append((timing.get("type") or service, (day.get("display_slug") or "").lower(), bool(day.get("active")), None, None))
    return rows


def _t(text):
    if not text:
        return None
    h, m, *s = (int(x) for x in text.split(":"))
    return clock(h % 24, m, s[0] if s else 0)


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato timings: %s", e)
        return False
    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       JOIN brands b ON b.id = bo.brand_id WHERE bo.is_active AND z.is_active""")
        stores = cur.fetchall()
    by_id = {a["id"]: a for a in accs.values()}
    creds = {a["id"]: _cookies(db.load_credentials(a)) for a in accs.values()}
    default = next(iter(by_id))
    ok, refused = True, 0  # a store this login may not read is skipped; several refusals in a row mean the session is dead
    for s in stores:
        cookies = creds[s["account_id"] if s["account_id"] in by_id else default]
        try:
            rows = [r for service in SERVICE_TYPES for r in _fetch(cookies, s["res_id"], service)]
            if not rows:
                log.info("zomato timings %s · %s: no hours returned, keeping what is saved", s["brand"], s["outlet_name"])
                continue
            services = sorted({r[0] for r in rows})
            with db.transaction() as cur:
                cur.execute("DELETE FROM outlet_hours WHERE outlet_id = %s AND platform = 'zomato' AND service_type = ANY(%s)",
                            (s["outlet_id"], services))
                for service, day, active, start, end in rows:
                    cur.execute("""INSERT INTO outlet_hours (outlet_id, platform, service_type, day, is_active, start_time, end_time, updated_at)
                                   VALUES (%s, 'zomato', %s, %s, %s, %s, %s, now())""", (s["outlet_id"], service, day, active, start, end))
            log.info("zomato timings %s · %s: %s slots", s["brand"], s["outlet_name"], len(rows))
            refused = 0
        except PermissionError as e:
            refused += 1
            log.warning("zomato timings %s · %s (%s): refused (%s)", s["brand"], s["outlet_name"], s["res_id"], e)
            ok = False
            if refused >= cfg.integer("ZOMATO_REFUSALS_BEFORE_STOP", 3):
                log.error("zomato timings: %s refusals in a row; session probably expired", refused)
                return False
        except Exception as e:
            log.exception("zomato timings %s failed: %s", s["res_id"], e)
            ok = False
    return ok
