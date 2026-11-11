"""Zomato item sales -> item_sales_daily, for every Zomato id mapped to a store.

owner-hub/reporting/download with report_view_type=item_sales_report answers with a CSV link straight away: one row
per store, item and metric, one column per day. Up to 50 res_ids per call, at most 31 days per call, and at most
CAP item-days per report: a report that reaches it is cut off, so that call is split (fewer stores, then fewer days)
and fetched again. Covers the last
ZOMATO_ITEM_SALES_DAYS days (default 35) up to yesterday, so a daily run also fills late corrections.
"""

import csv
import io
import time
import uuid
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta

from core import config as cfg, db
from core.common import ConfigError, log, require_env

from .outlets import _cookies

REPORT_URL = cfg.text("ZOMATO_REPORT_URL", "https://api.zomato.com/merchant-gw/web/owner-hub/reporting/download")
ZOMATO_ORIGIN = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
BATCH = 50
CAP = 5000  # the report silently stops at this many item-days
METRICS = {"Item quantity sold": "quantity", "Unit cost of item (₹)": "unit_price", "Orders with item": "orders", "Item rating": "rating"}


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _headers(cookies: dict) -> dict:
    return {
        "accept": "application/json, text/plain, */*", "content-type": "application/json",
        "origin": ZOMATO_ORIGIN, "referer": ZOMATO_ORIGIN + "/", "user-agent": cfg.user_agent(),
        "x-zomato-trace-id": str(uuid.uuid4()), "x-client-id": cfg.text("ZOMATO_CLIENT_ID", "zomato_web_merchant"),
        "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""), "x-zomato-csrft": cookies.get("csrf", ""),
        "x-zomato-source-identifier": cfg.text("ZOMATO_SOURCE_ID", "merchant-dashboard"),
        "x-zomato-app-version": cfg.text("ZOMATO_APP_VERSION", "2"),
    }


def _download(cookies: dict, res_ids: list[str], start: date, end: date) -> str:
    import requests

    body = {"selected_tab": "tab_daily", "selected_time_period": "custom_days", "start_date": start.isoformat(),
            "end_date": end.isoformat(), "report_view_type": "item_sales_report", "selected_res_ids": ",".join(res_ids)}
    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = requests.post(REPORT_URL, headers=_headers(cookies), cookies=cookies, json=body, timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
        if resp.status_code != 429 and resp.status_code < 500:
            break
        log.warning("Zomato %s; backing off", resp.status_code)
    resp.raise_for_status()
    url = resp.json().get("presignedUrl")
    if not url:
        raise RuntimeError(f"Zomato item sales: no report link ({str(resp.json())[:200]})")
    content = requests.get(url, timeout=cfg.integer("PAYOUT_DOWNLOAD_TIMEOUT_SEC", 120)).content
    if content[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(content))
        content = z.read(z.namelist()[0])
    return content.decode("utf-8-sig", errors="replace")


def _number(text: str):
    text = (text or "").replace("₹", "").replace(",", "").replace("%", "").strip()
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _rows(text: str, outlets: dict[str, int]) -> list[dict]:
    """CSV (one row per item and metric, one column per day) -> one dict per store, item and day."""
    reader = csv.DictReader(io.StringIO(text))
    days = {}
    for col in reader.fieldnames or []:
        try:
            days[col] = datetime.strptime(col.strip(), "%d %b %Y").date()
        except ValueError:
            pass
    merged = defaultdict(dict)
    for r in reader:
        field = METRICS.get((r.get("Metric") or "").strip())
        outlet = outlets.get(str(r.get("Restaurant ID") or "").strip())
        if not field or outlet is None:
            continue
        name = (r.get("Item name") or "").strip()[:255]
        for col, day in days.items():
            value = _number(r.get(col))
            if value is not None:
                row = merged[(outlet, name, day)]
                row[field] = value
                row["category"] = (r.get("Item category") or "")[:255]
    return [{"outlet": o, "item": n, "day": d, "category": v.get("category", ""), "quantity": v.get("quantity") or 0,
             "unit_price": v.get("unit_price"), "orders": int(v.get("orders") or 0), "rating": v.get("rating") or None}
            for (o, n, d), v in merged.items() if v.get("quantity") or v.get("orders")]


def _fetch(cookies: dict, res_ids: list[str], start: date, end: date, outlets: dict[str, int]) -> list[dict]:
    rows = _rows(_download(cookies, res_ids, start, end), outlets)
    if len(rows) < CAP:
        return rows
    if len(res_ids) > 1:
        half = len(res_ids) // 2
        return _fetch(cookies, res_ids[:half], start, end, outlets) + _fetch(cookies, res_ids[half:], start, end, outlets)
    if start < end:
        mid = start + (end - start) // 2
        return _fetch(cookies, res_ids, start, mid, outlets) + _fetch(cookies, res_ids, mid + timedelta(days=1), end, outlets)
    log.warning("zomato item sales %s %s: report capped at %s items for one day", res_ids[0], start, CAP)
    return rows


def _save(cur, rows: list[dict]) -> None:
    for r in rows:
        cur.execute(
            """INSERT INTO item_sales_daily (outlet_id, platform, item_name, category, day, quantity, unit_price, orders, rating)
               VALUES (%(outlet)s, 'zomato', %(item)s, %(category)s, %(day)s, %(quantity)s, %(unit_price)s, %(orders)s, %(rating)s)
               ON CONFLICT (outlet_id, platform, item_name, day) DO UPDATE SET
                 category = EXCLUDED.category, quantity = EXCLUDED.quantity, unit_price = EXCLUDED.unit_price,
                 orders = EXCLUDED.orders, rating = EXCLUDED.rating""",
            r,
        )


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato item sales: %s", e)
        return False
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=cfg.integer("ZOMATO_ITEM_SALES_DAYS", 35) - 1)
    start, end = cfg.date_range(start, end)  # BACKFILL_FROM/TO
    windows, s = [], start
    while s <= end:
        windows.append((s, min(end, s + timedelta(days=30))))
        s += timedelta(days=31)

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       WHERE bo.is_active AND z.is_active""")
        stores = cur.fetchall()
        stores = cfg.keep_stores(stores)  # ONLY_RES_IDS (backfill)
    if not stores:
        log.info("zomato item sales: no Zomato ids are mapped to stores yet")
        return True
    by_id = {a["id"]: a for a in accs.values()}
    default = next(iter(by_id))
    groups: dict[int, dict[str, int]] = {}
    for s in stores:
        groups.setdefault(s["account_id"] if s["account_id"] in by_id else default, {})[str(s["res_id"])] = s["outlet_id"]

    ok, total = True, 0
    for acc_id, outlets in groups.items():
        cookies = _cookies(db.load_credentials(by_id[acc_id]))
        res_ids = list(outlets)
        refused = None
        for i in range(0, len(res_ids), BATCH):
            batch = res_ids[i:i + BATCH]
            for w_start, w_end in windows:
                try:
                    rows = _fetch(cookies, batch, w_start, w_end, outlets)
                    with db.transaction() as cur:
                        _save(cur, rows)
                    total += len(rows)
                    log.info("zomato item sales %s: %s stores, %s to %s: %s item-days", by_id[acc_id]["label"], len(batch), w_start, w_end, len(rows))
                except PermissionError as e:
                    log.error("zomato item sales %s: %s; skipping this login's stores", by_id[acc_id]["label"], e)
                    db.mark_session_expired(acc_id, f"zomato item sales: {e}")
                    ok = refused = False
                    break
                except Exception as e:
                    log.exception("zomato item sales %s failed: %s", by_id[acc_id]["label"], e)
                    ok = False
            if refused is False:
                break
    log.info("zomato item sales: %s item-days saved", total)
    return ok
