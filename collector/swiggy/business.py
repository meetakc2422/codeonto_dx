"""Swiggy business report -> metric_daily, for every Swiggy id mapped to a store.

Swiggy builds the report as an Excel file: we ask for up to SWIGGY_REPORT_BATCH outlets over a short window, get a
download link, and read the sheet (one row per outlet and metric, one column per day). Each figure is stored under
the KPI named in mappings/swiggy_business_report.json; counts Swiggy only gives as a share are derived from orders.
The session is the one `run.py swiggy session` keeps (access_token); no login happens here.
"""

import os
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from io import BytesIO

from core import config as cfg, db, derive
from core.common import ConfigError, log, require_env

from zomato.business import parse  # '₹37137.02' -> 37137.02, '17.22 min' -> seconds, '77%' -> 77

REPORT_URL = cfg.text("SWIGGY_BUSINESS_REPORT_URL", "https://vhc-composer.swiggy.com/query?query=GenerateBusinessReport")
ORIGIN = cfg.text("SWIGGY_PARTNER_ORIGIN", "https://partner-self-client.swiggy.com")
BATCH = cfg.integer("SWIGGY_REPORT_BATCH", 50)  # outlets per report request
WINDOW_DAYS = cfg.integer("SWIGGY_REPORT_WINDOW_DAYS", 7)  # days per request
THROTTLE_WAIT = cfg.integer("SWIGGY_REPORT_THROTTLE_WAIT_SEC", 60)
POLLS = cfg.integer("SWIGGY_REPORT_POLLS", 5)
POLL_WAIT = cfg.integer("SWIGGY_REPORT_POLL_WAIT_SEC", 12)
QUERY = cfg.text("SWIGGY_BUSINESS_REPORT_QUERY", """query GenerateBusinessReport($input: GenerateBusinessReportInput!) {
  generateBusinessReport(input: $input) { reportUrl message { value } } }""")

_MAP = cfg.mapping("swiggy_business_report")  # mappings/swiggy_business_report.json
KPI_CODES = derive.kpi_codes(_MAP)
WANTED = derive.wanted(_MAP)


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _day(header) -> date | None:
    """'26th Oct 2026' -> date."""
    try:
        return datetime.strptime(re.sub(r"(\d+)(st|nd|rd|th)", r"\1", str(header)).strip(), "%d %b %Y").date()
    except ValueError:
        return None


def _request(token: str, rids: list[int], start: date, end: date) -> str:
    """Report download link; polls while Swiggy builds it and waits out its 'try again in 5 minutes' throttle."""
    import requests

    headers = {"Content-Type": "application/json", "Accept": "*/*", "Origin": ORIGIN, "Referer": ORIGIN + "/",
               "User-Agent": cfg.user_agent(), "access_token": token}
    body = {"query": QUERY, "operationName": "GenerateBusinessReport", "variables": {"input": {
        "rids": rids, "aggregation": "DAILY", "duration": "CUSTOM",
        "startDate": start.isoformat(), "endDate": end.isoformat(), "entityDetailsType": "RX"}}}
    throttled = False
    for attempt in range(POLLS):
        resp = requests.post(REPORT_URL, headers=headers, json=body, timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
        resp.raise_for_status()
        payload = resp.json()
        report = (payload.get("data") or {}).get("generateBusinessReport") or {}
        if report.get("reportUrl"):
            return report["reportUrl"]
        errors = payload.get("errors") or []
        msg = (errors[0].get("message") if errors else (report.get("message") or {}).get("value")) or "no message"
        if "Invalid Session" in msg or "Unauthorized" in msg:
            raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
        if "5 minutes" in msg and not throttled:
            log.warning("Swiggy throttled the report request; waiting %ss", THROTTLE_WAIT)
            throttled = True
            time.sleep(THROTTLE_WAIT)
            continue
        log.info("Swiggy report not ready (%s); polling %s/%s", msg, attempt + 1, POLLS)
        time.sleep(POLL_WAIT)
    raise RuntimeError("Swiggy did not return a report link")


def _read(link: str) -> dict[int, dict[tuple, dict[date, float]]]:
    """{outlet id: {(overview, metric): {day: number}}}"""
    import openpyxl
    import requests

    resp = requests.get(link, timeout=max(cfg.http_timeout(), 60))
    resp.raise_for_status()
    out: dict[int, dict] = defaultdict(dict)
    wb = openpyxl.load_workbook(BytesIO(resp.content), read_only=True, data_only=True)
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        header = next(rows, None)
        if not header or "Metric" not in header or "Restaurant ID" not in header:
            continue
        i_id, i_ov, i_m = header.index("Restaurant ID"), header.index("Overview"), header.index("Metric")
        days = {i: _day(h) for i, h in enumerate(header) if i > i_m and _day(h)}
        for row in rows:
            key = (row[i_ov], row[i_m])
            if row[i_id] is None or key not in WANTED:
                continue
            series = out[int(row[i_id])].setdefault(key, {})  # first occurrence wins
            if series:
                continue
            for i, day in days.items():
                n = parse(row[i])
                if n is not None:
                    series[day] = n
    return out


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("swiggy business: %s", e)
        return False
    days = cfg.integer("SWIGGY_REPORT_DAYS", WINDOW_DAYS)
    end = date.today() - timedelta(days=cfg.integer("SWIGGY_REPORT_LAG_DAYS", 2))  # the newest days are not ready yet
    windows, cursor = [], end
    while cursor > end - timedelta(days=days):
        start = max(cursor - timedelta(days=WINDOW_DAYS - 1), end - timedelta(days=days - 1))
        windows.append((start, cursor))
        cursor = start - timedelta(days=1)

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "swiggy", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.swiggy_id AS res_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id
                       JOIN brands b ON b.id = bo.brand_id WHERE bo.is_active AND s.is_active""")
        stores = cur.fetchall()
        cur.execute("SELECT code, id FROM kpis WHERE code = ANY(%s)", (list(KPI_CODES),))
        kpi_id = {r["code"]: r["id"] for r in cur.fetchall()}
    missing = KPI_CODES - set(kpi_id)
    if missing:
        log.error("swiggy business: KPIs missing in the database (%s); run `manage.py migrate`", ", ".join(sorted(missing)))
        return False
    only = {x.strip() for x in os.getenv("ONLY_RES_IDS", "").split(",") if x.strip()}
    if only:
        stores = [s for s in stores if s["res_id"] in only]

    ok, done = True, 0
    for label, account in accs.items():
        try:
            creds = db.load_credentials(account)
        except ConfigError as e:
            log.error("swiggy business: %s", e)
            return False
        token = creds.get("access_token")
        if not token:
            log.error("swiggy business: account %s has no access_token; run `run.py swiggy session --account %s`", label, label)
            return False
        listed = {str(o.get("rest_id") if isinstance(o, dict) else o) for o in creds.get("outlets") or []}
        mine = [s for s in stores if s["res_id"] in listed]  # only outlets this login can see
        if not mine:
            log.info("swiggy business: account %s has no mapped stores", label)
            continue
        by_rid = {int(s["res_id"]): s for s in mine}
        rids = list(by_rid)
        log.info("swiggy business: account %s, %s stores, %s windows", label, len(rids), len(windows))
        try:
            for start, stop in windows:
                for i in range(0, len(rids), BATCH):
                    batch = rids[i:i + BATCH]
                    report = _read(_request(token, batch, start, stop))
                    with db.transaction() as cur:
                        for rid in batch:
                            rows = derive.kpi_rows(report.get(rid, {}), _MAP)
                            for code, day, value, weight in rows:
                                cur.execute(
                                    """INSERT INTO metric_daily (outlet_id, platform, kpi_id, metric_date, value, weight, updated_at)
                                       VALUES (%s, 'swiggy', %s, %s, %s, %s, now())
                                       ON CONFLICT (outlet_id, platform, kpi_id, metric_date)
                                       DO UPDATE SET value = EXCLUDED.value, weight = EXCLUDED.weight, updated_at = now()""",
                                    (by_rid[rid]["outlet_id"], kpi_id[code], day, value, weight))
                            done += len(rows)
                    log.info("swiggy business %s: %s to %s, %s outlets saved", label, start, stop, len(batch))
                    time.sleep(cfg.integer("SWIGGY_REPORT_BATCH_PAUSE_SEC", 5))
        except PermissionError as e:
            log.error("swiggy business: %s", e)
            return False
        except Exception as e:
            log.exception("swiggy business account %s failed: %s", label, e)
            ok = False
    log.info("swiggy business: %s daily values saved", done)
    return ok
