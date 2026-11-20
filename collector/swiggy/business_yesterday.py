"""Swiggy business numbers for YESTERDAY -> metric_daily, for every Swiggy id mapped to a store.

The business report job (business.py) stops two days back because Swiggy has not built the newest days yet. The partner
dashboard's own outlet-wise metrics query (outletWiseMetricDetailsV4, period YESTERDAY) has yesterday, so this job fills
that one day. Its figures are named like the report's, so they go through the same mapping (mappings/swiggy_business_report.json)
and land in the same KPIs; two days later the report job overwrites the day with Swiggy's final figures (same key, upsert).

What it has: the sales figures (net sales, delivered orders, average order value, cancellations). What it does not: Swiggy
holds the operations, ads, discounts and menu figures of this query back by 48 hours too, and the conversion funnel is not in
it, so those stay two days behind, as the report job has them.

Safe by design: Swiggy words the day it answers for in the response title ("16th November"). A row is saved only when that
day is yesterday; anything else is skipped and logged. Dry run (nothing is saved, only a few outlets are asked, and what came
back is printed):  `python run.py swiggy business_yesterday --dry-run`
"""

import os
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from core import config as cfg, db, derive
from core.common import ConfigError, log, require_env

from swiggy.business import KPI_CODES, ORIGIN, _MAP, WANTED, config  # noqa: F401  (config: used by run.py --check)
from zomato.business import parse  # '₹37,137' -> 37137.0, '17.2 min' -> 1032.0 (seconds), '77%' -> 77.0

URL = cfg.text("SWIGGY_OUTLET_METRICS_URL", "https://vhc-composer.swiggy.com/query?query=outletWiseMetricDetailsV4")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
BATCH = cfg.integer("SWIGGY_OUTLET_METRICS_BATCH", 100)  # outlets per request page
PAGE_SIZE = 500
DRY_OUTLETS = cfg.integer("SWIGGY_T1_DRY_OUTLETS", 3)

# metricId -> the field Swiggy sorts that category by (the query needs one). Checked on 2026-11-17: only SALES_V2 has yesterday.
# Operations, ads, discounts and menu answer "Below metrics have a lag of 48 hours" (the day before yesterday's day before), so the
# report job (business.py) is the one that gets those. Put them back here if Swiggy ever drops that lag: the title-day check
# below would then let them through by itself.
CATEGORIES = {"SALES_V2": "NET_SALES"}
LAGGED = {"OPERATIONS_V2": "DELAYED_ORDERS_PERCENTAGE", "ADS_V2": "ADS_ORDERS", "DISCOUNTS_V2": "ORDERS_WITH_OFFERS", "MENU_V2": "MENU_SCORE_PERCENTAGE"}

# the query's metric name -> the report's (section, metric): the keys mappings/swiggy_business_report.json is written in
NAMES = {
    "NET_SALES": ("SALES", "Net Sales"), "DELIVERED_ORDERS": ("SALES", "Delivered Orders"), "NET_AOV": ("SALES", "Net AOV"),
    "CANCELLED_ORDER_LOSS": ("SALES", "Cancelled Order Loss"), "CANCELLED_ORDER": ("SALES", "Restaurant Cancelled Orders"),
    "ONLINE_PERCENTAGE": ("OPERATIONS", "Online Availability %"), "KITCHEN_PREPARATION_TIME": ("OPERATIONS", "Kitchen Prep Time"),
    "MFR_ACCURACY": ("OPERATIONS", "Food Ready Accuracy (MFR)"), "DELAYED_ORDERS_PERCENTAGE": ("OPERATIONS", "Delayed Orders (> 10 mins)"),
    "ADS_ORDERS": ("ADS_CPC", "CPC Orders"), "ADS_DRIVEN_SALES": ("ADS_CPC", "CPC Driven Sales"), "ADS_SPEND": ("ADS_CPC", "Total CPC Spends"),
    "CBA_ORDERS": ("ADS_CBA", "CBA Orders"), "CBA_DRIVEN_SALES": ("ADS_CBA", "CBA Driven Sales"), "ADS_SPEND_CBA": ("ADS_CBA", "Total CBA Spends"),
    "ADS_IMPRESSIONS_CBA": ("ADS_CBA", "Ad Impressions"),
    "DISCOUNT_ORDER_PERCENTAGE": ("DISCOUNTS", "Discounted Orders %"), "EFFECTIVE_DISCOUNT_GMV_PERCENTAGE": ("DISCOUNTS", "Discount GMV %"),
    "DISCOUNT_GIVEN": ("DISCOUNTS", "Discount Given by Restaurant(RDGMV)"), "REST_DISCOUNT_PER_ORDER": ("DISCOUNTS", "Restaurant Discount Per Order(RDPO)"),
    "MENU_SCORE_PERCENTAGE": ("MENU", "Menu Score(Out of 100)"), "ITEMS_WITH_IMAGES_PERCENTAGE": ("MENU", "Items with Photos"),
    "ITEMS_WITH_DESCRIPTION_PERCENTAGE": ("MENU", "Items with Descriptions"),
}


def _yesterday() -> date:
    return datetime.now(IST).date() - timedelta(days=1)


def _title_day(title, year: int) -> date | None:
    """The day Swiggy says the answer is for: '16th November' -> that day (in the given year)."""
    text = (((title or {}).get("attribute_values") or {}).get("date") or {}).get("value", "") if isinstance(title, dict) else ""
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)", str(text))
    if not m:
        return None
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {year}", fmt).date()
        except ValueError:
            continue
    return None


def _fetch(token: str, rids: list[int], category: str, day: date) -> tuple[list[dict], object]:
    """([{rid, metrics}], title) for one category; pages through every outlet."""
    import requests

    start = datetime(day.year, day.month, day.day, tzinfo=IST)
    from_ms, to_ms = int(start.timestamp() * 1000), int((start + timedelta(days=1)).timestamp() * 1000) - 1
    headers = {"Content-Type": "application/json", "Accept": "application/graphql-response+json, application/json",
               "Origin": ORIGIN, "Referer": ORIGIN + "/", "User-Agent": cfg.user_agent(), "access_token": token}
    out, title, page = [], None, 1
    while True:
        query = ("query { outletWiseMetricDetailsV4(input: {rids: %s, period: YESTERDAY, fromDate: %d, toDate: %d, metricId: %s, "
                 "sort: HIGH_TO_LOW, metricSortField: \"%s\", pageNumber: %d, pageSize: %d, manageeIds: [\"\"]}) "
                 "{ title showSortFilter outletWiseMetricDetailsV4 { rid metrics } totalCount hasNextPage } }"
                 % ('[' + ','.join(f'"{r}"' for r in rids) + ']', from_ms, to_ms, category, CATEGORIES[category], page, PAGE_SIZE))
        resp = requests.post(URL, headers=headers, json={"query": query, "variables": {}}, timeout=max(cfg.http_timeout(), 45))
        if resp.status_code in (401, 403):
            raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            msg = str(payload["errors"][0].get("message", payload["errors"]))
            if "Invalid Session" in msg or "Unauthorized" in msg:
                raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
            raise RuntimeError(f"Swiggy {category}: {msg[:200]}")
        data = (payload.get("data") or {}).get("outletWiseMetricDetailsV4") or {}
        title = title or data.get("title")
        rows = data.get("outletWiseMetricDetailsV4") or []
        out.extend(rows)
        if not data.get("hasNextPage") or len(out) >= (data.get("totalCount") or 0) or not rows:
            return out, title
        page += 1
        time.sleep(0.5)


def _report(rows: list[dict], day: date) -> dict[int, dict]:
    """{outlet id: {(section, metric): {day: number}}} from one category's rows."""
    out: dict[int, dict] = defaultdict(dict)
    for row in rows:
        try:
            rid = int(row.get("rid"))
        except (TypeError, ValueError):
            continue
        for name, cell in (row.get("metrics") or {}).items():
            key = NAMES.get(name)
            n = parse(cell.get("value") if isinstance(cell, dict) else cell)
            if key and key in WANTED and n is not None:
                out[rid][key] = {day: n}
    return out


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("swiggy business_yesterday: %s", e)
        return False
    dry = os.getenv("SWIGGY_T1_DRY_RUN", "").strip() == "1"
    day = _yesterday()

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "swiggy", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.swiggy_id AS res_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id
                       JOIN brands b ON b.id = bo.brand_id WHERE bo.is_active AND s.is_active""")
        stores = cfg.keep_stores(cur.fetchall())  # ONLY_RES_IDS
        cur.execute("SELECT code, id FROM kpis WHERE code = ANY(%s)", (list(KPI_CODES),))
        kpi_id = {r["code"]: r["id"] for r in cur.fetchall()}
    missing = KPI_CODES - set(kpi_id)
    if missing:
        log.error("swiggy business_yesterday: KPIs missing in the database (%s); run `manage.py migrate`", ", ".join(sorted(missing)))
        return False

    ok, saved = True, 0
    for label, account in accs.items():
        try:
            creds = db.load_credentials(account)
        except ConfigError as e:
            log.error("swiggy business_yesterday: %s", e)
            return False
        token = creds.get("access_token")
        if not token:
            log.error("swiggy business_yesterday: account %s has no access_token; run `run.py swiggy session --account %s`", label, label)
            return False
        listed = {str(o.get("rest_id") if isinstance(o, dict) else o) for o in creds.get("outlets") or []}
        mine = [s for s in stores if s["res_id"] in listed]  # only outlets this login can see
        if not mine:
            log.info("swiggy business_yesterday: account %s has no mapped stores", label)
            continue
        if dry:
            mine = mine[:DRY_OUTLETS]
        by_rid = {int(s["res_id"]): s for s in mine}
        rids = list(by_rid)
        log.info("swiggy business_yesterday: account %s, %s stores, day %s%s", label, len(rids), day, " (DRY RUN, nothing saved)" if dry else "")
        report: dict[int, dict] = defaultdict(dict)
        try:
            for category in CATEGORIES:
                for i in range(0, len(rids), BATCH):
                    rows, title = _fetch(token, rids[i:i + BATCH], category, day)
                    answered = _title_day(title, day.year)
                    if dry:
                        print(f"[{category}] Swiggy says the day is: {title!r} -> {answered}; asked for {day}; {len(rows)} outlets answered")
                    if answered != day:
                        log.warning("swiggy business_yesterday %s: Swiggy answered for %s, not %s; skipped", category, answered, day)
                        continue
                    for rid, series in _report(rows, day).items():
                        report[rid].update(series)
                time.sleep(1)
            with db.transaction() as cur:
                for rid, data in report.items():
                    rows = derive.kpi_rows(data, _MAP)
                    if dry:
                        print(f"  {by_rid[rid]['brand']} · {by_rid[rid]['outlet_name']} ({rid}): {len(rows)} KPI values")
                        for code, d, value, weight in sorted(rows):
                            print(f"      {code:24} {d}  {value:>14,.2f}  (weight {weight})")
                        continue
                    for code, d, value, weight in rows:
                        if d != day:
                            continue
                        cur.execute(
                            """INSERT INTO metric_daily (outlet_id, platform, kpi_id, metric_date, value, weight, updated_at)
                               VALUES (%s, 'swiggy', %s, %s, %s, %s, now())
                               ON CONFLICT (outlet_id, platform, kpi_id, metric_date)
                               DO UPDATE SET value = EXCLUDED.value, weight = EXCLUDED.weight, updated_at = now()""",
                            (by_rid[rid]["outlet_id"], kpi_id[code], d, value, weight))
                        saved += 1
        except PermissionError as e:
            log.error("swiggy business_yesterday: %s", e)
            return False
        except Exception as e:
            log.exception("swiggy business_yesterday account %s failed: %s", label, e)
            ok = False
    log.info("swiggy business_yesterday: %s values saved for %s%s", saved, day, " (dry run: none)" if dry else "")
    return ok
