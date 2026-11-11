"""Zomato owner-hub business report -> metric_daily, for every Zomato id mapped to a store.

One report call per store per 10-day window returns daily sales, customer experience (rating, online %,
prep time, delays, rejections), the customer funnel, ads, offers and menu health. Each figure is stored
under the matching KPI. Counts the report only gives as a percentage (menu views, ad orders, orders with
offers ...) are derived from the day's orders or impressions, so they are close but not exact.
"""

import os
import random
import re
import time
from datetime import date, timedelta

from core import alerts, config as cfg, db, derive
from core.refusals import Refusals
from core.common import ConfigError, log, require_env

from .outlets import _cookies

SITE = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
URL = cfg.text("ZOMATO_BUSINESS_REPORT_URL", cfg.text("ZOMATO_API_BASE", "https://api.zomato.com/merchant-gw/web")
               + "/owner-hub/reporting/get-business-report?view=table&selected_res_id=0&time_filter=ist_day&page_type=owner_hub"
               "&start_date={s}&end_date={e}")
TIME_FILTER = cfg.text("ZOMATO_REPORT_TIME_FILTER", "ist_day")
CHUNK_DAYS = cfg.integer("ZOMATO_REPORT_CHUNK_DAYS", 10)  # the report accepts at most 10 days at a time
# One outlet never delivers this many orders in a day. When Zomato can't apply the outlet filter (the login doesn't see
# that outlet) it answers with the whole account's totals instead; a day above this means that happened.
MAX_DAILY_ORDERS = cfg.integer("ZOMATO_MAX_DAILY_ORDERS_PER_OUTLET", 2000)

_MAP = cfg.mapping("zomato_business_report")  # mappings/zomato_business_report.json
KPI_CODES = derive.kpi_codes(_MAP)
WANTED = derive.wanted(_MAP)


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def parse(raw) -> float | None:
    """'₹30,164' -> 30164, '3.4%' -> 3.4, '18 mins' -> 1080 (seconds), '7.11 k' -> 7110, '₹1.2 L' -> 120000, '-' -> None."""
    if raw is None:
        return None
    t = str(raw).strip().replace("₹", "").replace(",", "").replace("%", "").strip()
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(k|l|cr|mins?|hrs?)?", t, re.I)
    if not m:
        return None
    n, unit = float(m.group(1)), (m.group(2) or "").lower()
    return n * {"k": 1e3, "l": 1e5, "cr": 1e7, "min": 60, "mins": 60, "hr": 3600, "hrs": 3600}.get(unit, 1)


def _val(cell):
    return cell.get("value") if isinstance(cell, dict) else cell


def _fetch(cookies: dict, res_id: str, start: date, end: date) -> dict[tuple, dict[date, float]]:
    """{(section, metric): {day: number}} for the window."""
    import requests

    s, e = start.isoformat(), end.isoformat()
    headers = {
        "Content-Type": "application/json", "User-Agent": cfg.user_agent(),
        "Origin": SITE, "x-client-id": cfg.text("ZOMATO_CLIENT_ID", "zomato_web_merchant"), "x-zomato-csrft": cookies.get("csrf", ""),
        "Referer": cfg.text("ZOMATO_REPORT_REFERER", f"{SITE}/webviews/mx-reporting/?mode=mx-dashboard&tab_type=page_daily&buisness_report_type=table&selected_res_id=0")
                   + f"&start_date={s}&end_date={e}",
        "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""), "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
    }
    body = {"filters": [
        {"category_name": "time_filter", "selected_values": [TIME_FILTER], "selected_values_meta_data": {TIME_FILTER: {"start_date": s, "end_date": e}}},
        {"category_name": "restaurant", "selected_values": [str(res_id)], "selected_values_meta_data": {}}]}
    for wait in cfg.retry_waits():
        time.sleep(wait + random.uniform(0, 1))
        resp = requests.post(URL.format(s=s, e=e), headers=headers, json=body, timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
        if resp.status_code == 429:
            log.warning("Zomato 429; waiting")
            continue
        resp.raise_for_status()
        break
    else:
        resp.raise_for_status()
    out: dict[tuple, dict[date, float]] = {}
    for sec in (resp.json().get("data") or {}).get("sections") or []:
        heading = sec.get("heading")
        heading = _val(heading)
        rows = []
        for row in sec.get("row_data") or []:
            rows.append(row)
            rows.extend(row.get("child_rows") or row.get("sub_rows") or [])
        for row in rows:
            metric = _val(row.get("metric"))
            key = (heading, metric)
            if key not in WANTED or key in out:  # first occurrence wins (e.g. two 'Total complaints')
                continue
            days = {}
            for k, cell in row.items():
                if k.isdigit() and len(k) == 8:
                    n = parse(_val(cell))
                    if n is not None:
                        days[date(int(k[:4]), int(k[4:6]), int(k[6:]))] = n
            out[key] = days
    return out


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato business: %s", e)
        return False
    days = cfg.integer("ZOMATO_REPORT_DAYS", CHUNK_DAYS)
    end = date.today() - timedelta(days=1)
    start, end = cfg.date_range(end - timedelta(days=days - 1), end)  # BACKFILL_FROM/TO
    days = (end - start).days + 1
    windows, cursor = [], end
    while cursor > end - timedelta(days=days):  # newest window first
        start = max(cursor - timedelta(days=CHUNK_DAYS - 1), end - timedelta(days=days - 1))
        windows.append((start, cursor))
        cursor = start - timedelta(days=1)

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       JOIN brands b ON b.id = bo.brand_id WHERE bo.is_active AND z.is_active""")
        stores = cur.fetchall()
        stores = cfg.keep_stores(stores)  # ONLY_RES_IDS (backfill)
        cur.execute("SELECT code, id FROM kpis WHERE code = ANY(%s)", (list(KPI_CODES),))
        kpi_id = {r["code"]: r["id"] for r in cur.fetchall()}
    if not stores:
        log.info("zomato business: no Zomato ids are mapped to stores yet")
        return True
    missing = KPI_CODES - set(kpi_id)
    if missing:
        log.error("zomato business: KPIs missing in the database (%s); run `manage.py migrate`", ", ".join(sorted(missing)))
        return False

    by_id = {a["id"]: a for a in accs.values()}
    creds = {a["id"]: _cookies(db.load_credentials(a)) for a in accs.values()}
    default = next(iter(by_id))
    ok = True
    unknown: list[str] = []
    refusals = Refusals("zomato business")
    for s in stores:
        if s["account_id"] is None:
            # no login is known to see this outlet: the first login is tried, and if it can't see the outlet Zomato
            # answers with that login's account totals; the MAX_DAILY_ORDERS check below refuses to save those
            unknown.append(f"{s['brand']} · {s['outlet_name']} ({s['res_id']})")
        acc_id = s["account_id"] if s["account_id"] in by_id else default
        cookies = creds[acc_id]
        if refusals.is_dead(acc_id):
            continue
        try:
            n = 0
            for start, stop in windows:
                rows = derive.kpi_rows(_fetch(cookies, s["res_id"], start, stop), _MAP)
                too_big = [(d, v) for code, d, v, _ in rows if code == "delivered_orders" and v > MAX_DAILY_ORDERS]
                if too_big:
                    d, v = max(too_big, key=lambda x: x[1])
                    log.error("zomato business %s · %s (%s): %s delivered orders on %s is not one outlet's day (account "
                              "totals?); this window was not saved", s["brand"], s["outlet_name"], s["res_id"], int(v), d)
                    alerts.incident(f"Zomato business report looks wrong: {s['brand']} · {s['outlet_name']}",
                                    f"Res {s['res_id']}: {int(v)} delivered orders on {d}, more than one outlet can do "
                                    f"(limit {MAX_DAILY_ORDERS}). Zomato probably sent the whole account's totals. Nothing was saved.",
                                    "Check this outlet's Zomato id and which login can see it (Brands & Outlets, Sessions).")
                    ok = False
                    continue
                with db.transaction() as cur:
                    for code, day, value, weight in rows:
                        cur.execute(
                            """INSERT INTO metric_daily (outlet_id, platform, kpi_id, metric_date, value, weight, updated_at)
                               VALUES (%s, 'zomato', %s, %s, %s, %s, now())
                               ON CONFLICT (outlet_id, platform, kpi_id, metric_date)
                               DO UPDATE SET value = EXCLUDED.value, weight = EXCLUDED.weight, updated_at = now()""",
                            (s["outlet_id"], kpi_id[code], day, value, weight))
                n += len(rows)
            log.info("zomato business %s · %s (%s): %s daily values", s["brand"], s["outlet_name"], s["res_id"], n)
            refusals.success(acc_id)
        except PermissionError as e:
            refusals.refused(acc_id, f"{s['brand']} · {s['outlet_name']} ({s['res_id']})", e)
            ok = False
        except Exception as e:
            log.exception("zomato business %s failed: %s", s["res_id"], e)
            ok = False
    refusals.summary()
    if unknown:
        log.warning("zomato business: %s store(s) have no known Zomato login (run `run.py zomato outlets`), the first "
                    "login was used: %s", len(unknown), "; ".join(unknown[:10]))
    return ok
