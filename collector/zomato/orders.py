"""Zomato order history -> order_lines, for every Zomato id mapped to a store.

Asks Zomato's merchant dashboard for each store's order-history report (the same download the Order history page offers),
reads the zip + CSV straight from memory (nothing is written to disk) and keeps one row per item per order. Customer
columns (name, id, phone) are never read. Runs once a day: it re-reads the last ORDERS_DAYS days (default 2), and saving
is an upsert, so running twice is harmless. The first run for an outlet can backfill: BACKFILL_FROM / BACKFILL_TO.

The report request carries the merchant user's id ("uuid"): set it per login in ORDER_USER_IDS=main:381317736,other:123.
"""

import csv
import io
import random
import re
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from core import alerts, config as cfg, db, retry
from core.common import ConfigError, log, require_env

from .item_sales import _headers
from .outlets import _cookies

BASE = cfg.text("ZOMATO_ORDER_HISTORY_URL", "https://api.zomato.com/merchant-gw/web/order/history/download")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
DAYS = cfg.integer("ORDERS_DAYS", 2)
CHUNK_DAYS = cfg.integer("ORDERS_CHUNK_DAYS", 7)
BATCH = cfg.integer("ORDERS_BATCH", 10)  # outlets per report (Zomato takes a comma-separated list of ids)
POLL_TRIES = cfg.integer("ORDERS_POLL_TRIES", 30)
POLL_SEC = cfg.integer("ORDERS_POLL_SEC", 3)
PACE_SEC = cfg.numbers("ORDERS_PACE_SEC", "2,4")  # pause between reports, so a long backfill stays under Zomato's limits
ITEM_SPLIT = re.compile(r",\s*(?=\d+\s*x\s)")
ITEM = re.compile(r"^\s*(\d+)\s*x\s*(.+?)\s*$", re.S)


def config(account: str) -> dict:
    return require_env("SOCIALSPORK_DATABASE_URL")


def user_ids() -> dict[str, str]:
    """ORDER_USER_IDS=main:381317736,paras:123 -> {'main': '381317736', 'paras': '123'}"""
    out = {}
    for part in cfg.text("ORDER_USER_IDS").split(","):
        label, _, uid = part.partition(":")
        if label.strip() and uid.strip().isdigit():
            out[label.strip()] = uid.strip()
    return out


def parse_items(text: str) -> list[tuple[str, int]]:
    """'1 x Butter Chicken, 2 x Garlic Naan' -> [('Butter Chicken', 1), ('Garlic Naan', 2)], the same item twice added up."""
    merged: dict[str, int] = {}
    for chunk in ITEM_SPLIT.split(text or ""):
        m = ITEM.match(chunk)
        if m:
            name = re.sub(r"\s+", " ", m.group(2)).strip()[:255]
            merged[name] = merged.get(name, 0) + int(m.group(1))
    return list(merged.items())


def parse_time(text: str) -> datetime | None:
    """'09:15 PM, November 10 2026' (India time) -> an aware datetime."""
    try:
        return datetime.strptime((text or "").strip(), "%I:%M %p, %B %d %Y").replace(tzinfo=IST)
    except ValueError:
        return None


def money(text) -> Decimal | None:
    try:
        return Decimal(str(text or "").replace("₹", "").replace(",", "").strip())
    except InvalidOperation:
        return None


def parse_report(text: str, outlets: dict[str, int]) -> list[dict]:
    """The report CSV -> one dict per item per order, for the stores in `outlets` ({res_id: outlet id}). Customer columns are not read."""
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        outlet = outlets.get(str(r.get("Restaurant ID") or "").strip())
        order_id = str(r.get("Order ID") or "").strip()
        placed = parse_time(r.get("Order Placed At"))
        items = parse_items(r.get("Items in order"))
        if outlet is None or not order_id or placed is None or not items:
            continue
        local = placed.astimezone(IST).replace(tzinfo=None)
        subtotal, total = money(r.get("Bill subtotal")), money(r.get("Total"))
        for name, qty in items:
            rows.append({"outlet": outlet, "order_id": order_id, "placed_at": placed, "order_date": cfg.business_date(local),
                         "mealtime": cfg.mealtime(local.hour), "status": (r.get("Order Status") or "").strip()[:40],
                         "reason": (r.get("Cancellation / Rejection reason") or "").strip()[:255], "item": name, "qty": qty,
                         "unit_price": (subtotal / qty).quantize(Decimal("0.01")) if subtotal is not None and len(items) == 1 and qty else None,
                         "subtotal": subtotal, "total": total})
    return rows


def _download(cookies: dict, user_id: str, res_id: str, start: date, end: date) -> str:
    """Ask for the report, wait for it, read it into memory. Nothing is saved to disk."""
    import requests

    headers = _headers(cookies)
    body = {"uuid": user_id, "start_date": start.isoformat(), "end_date": end.isoformat(), "res_id": str(res_id), "download_type": "all_orders"}
    resp = requests.post(f"{BASE}/query", headers=headers, cookies=cookies, json=body, timeout=cfg.http_timeout())
    if resp.status_code in (401, 403):
        raise PermissionError(f"Zomato refused the order history request ({resp.status_code}): check the login and ORDER_USER_IDS")
    resp.raise_for_status()
    answer = resp.json()
    link = answer.get("download_link")
    for _ in range(POLL_TRIES):
        if link:
            break
        if answer.get("download_status") in ("failed", "error"):
            raise RuntimeError("Zomato could not build the order report")
        time.sleep(POLL_SEC)
        resp = requests.get(f"{BASE}/status", headers=headers, cookies=cookies, timeout=cfg.http_timeout(),
                            params={"uuid": user_id, "query_id": answer.get("query_id", ""), "download_type": "all_orders"})
        if resp.status_code in (401, 403):
            raise PermissionError(f"Zomato refused the order history status check ({resp.status_code})")
        resp.raise_for_status()
        answer = {**answer, **resp.json()}
        link = answer.get("download_link")
    if not link:
        raise RuntimeError("Zomato's order report was not ready in time")
    content = requests.get(link, timeout=cfg.integer("PAYOUT_DOWNLOAD_TIMEOUT_SEC", 120)).content  # signed link: no cookies
    if content[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(content))
        content = z.read(z.namelist()[0])
    return content.decode("utf-8-sig", errors="replace")


SAVE = """INSERT INTO order_lines (outlet_id, platform, order_id, placed_at, order_date, mealtime, status, rejection_reason, item_name,
                                 quantity, unit_price, order_subtotal, order_total, created_at)
         VALUES (%(outlet)s, 'zomato', %(order_id)s, %(placed_at)s, %(order_date)s, %(mealtime)s, %(status)s, %(reason)s, %(item)s,
                 %(qty)s, %(unit_price)s, %(subtotal)s, %(total)s, now())
         ON CONFLICT (platform, order_id, item_name) DO UPDATE SET status = EXCLUDED.status, rejection_reason = EXCLUDED.rejection_reason,
             quantity = EXCLUDED.quantity, unit_price = EXCLUDED.unit_price, order_subtotal = EXCLUDED.order_subtotal,
             order_total = EXCLUDED.order_total"""


def save(rows: list[dict]) -> int:
    if rows:
        with db.transaction() as cur:
            cur.executemany(SAVE, rows)
    return len(rows)


def windows(start: date, end: date) -> list[tuple[date, date]]:
    out, cur = [], start
    while cur <= end:
        stop = min(cur + timedelta(days=CHUNK_DAYS - 1), end)
        out.append((cur, stop))
        cur = stop + timedelta(days=1)
    return out


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato orders: %s", e)
        return False
    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND z.is_active ORDER BY bo.id""")
        stores = cfg.keep_stores(cur.fetchall())
    if not stores:
        log.info("zomato orders: no Zomato ids are mapped to stores yet")
        return True
    by_id = {a["id"]: a for a in accs.values()}
    creds = {a["id"]: _cookies(db.load_credentials(a)) for a in accs.values()}
    default = next(iter(by_id))
    uids = user_ids()
    today = datetime.now(IST).date()
    start, end = cfg.date_range(today - timedelta(days=DAYS - 1), today)
    spans = windows(start, end)
    ok, dead, skipped, saved_total, failures = True, set(), set(), 0, []
    by_login: dict[int, list] = {}
    for s in stores:
        acc_id = s["account_id"] if s["account_id"] in by_id else default
        label = by_id[acc_id]["label"]
        if label not in uids:
            if label not in skipped:
                skipped.add(label)
                log.warning("zomato orders: no user id for login '%s' (set ORDER_USER_IDS=%s:<id>); its stores are skipped", label, label)
            ok = False
            continue
        by_login.setdefault(acc_id, []).append(s)

    def fetch(acc_id: int, group: list) -> int:
        """One report per date window for these stores; saved as it arrives. Returns the order lines saved."""
        label, n = by_id[acc_id]["label"], 0
        outlets = {str(s["res_id"]): s["outlet_id"] for s in group}
        for a, b in spans:
            text = retry.call(lambda: _download(creds[acc_id], uids[label], ",".join(outlets), a, b),
                              f"zomato orders {len(group)} stores", quiet=True)
            n += save(parse_report(text, outlets))
        return n

    first = True
    for acc_id, mine in by_login.items():
        label = by_id[acc_id]["label"]
        for i in range(0, len(mine), max(1, BATCH)):
            group = mine[i:i + max(1, BATCH)]
            if acc_id in dead:
                break
            if not first:
                time.sleep(random.uniform(*PACE_SEC))
            first = False
            try:
                saved = fetch(acc_id, group)
            except PermissionError as e:
                dead.add(acc_id)
                ok = False
                log.error("zomato orders: login '%s' was refused (%s); its stores are skipped this run", label, e)
                db.mark_session_expired(acc_id, f"zomato orders: {e}")
                alerts.incident(f"Zomato session expired: {label}", str(e), f"Use Log in again on the Sessions page, or run `python run.py zomato session --account {label}`.")
                break
            except Exception as e:  # noqa: BLE001
                # one bad store must not hold up the rest of its batch: try the stores one at a time
                log.warning("zomato orders: a batch of %s stores failed (%s); trying them one by one", len(group), type(e).__name__)
                saved = 0
                for s in group:
                    try:
                        saved += fetch(acc_id, [s])
                    except PermissionError as pe:
                        dead.add(acc_id)
                        ok = False
                        log.error("zomato orders: login '%s' was refused (%s); its stores are skipped this run", label, pe)
                        db.mark_session_expired(acc_id, f"zomato orders: {pe}")
                        break
                    except Exception as se:  # noqa: BLE001
                        ok = False
                        failures.append(f"{type(se).__name__}: {str(se)[:160]}")
                        log.warning("zomato orders %s · %s (%s) failed: %s", s["brand"], s["outlet_name"], s["res_id"], type(se).__name__)
            saved_total += saved
            log.info("zomato orders (%s): %s stores, %s order lines, %s to %s", label, len(group), saved, start, end)
    if len(failures) >= max(3, len(stores) // 5):
        alerts.incident("Zomato order history failing", f"{len(failures)} of {len(stores)} stores failed. Example: {failures[0]}",
                        "Check the collector window and the Zomato login. Order history for those stores is not up to date.")
    log.info("zomato orders: %s order lines saved across %s stores (%s to %s)", saved_total, len(stores), start, end)
    return ok
