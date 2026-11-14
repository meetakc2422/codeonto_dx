"""Swiggy order history -> order_lines, for every Swiggy id mapped to a store.

Reads each store's order history from Swiggy's partner dashboard (the same list its Orders page shows) and keeps one row
per item per order, in the same table and shape as the Zomato job (zomato/orders.py): the loss estimate on the Stock-outs
page learns what each outlet normally sells at every mealtime from it. Customer details (name, phone, address) are never
read. Runs once a day over the last ORDERS_DAYS days (default 2); saving is an upsert, so running twice is harmless. A
backfill: `run.py swiggy orders --start 2026-10-14 --end 2026-11-13 --once`.

Order times come in India time. Status is saved as Delivered or Cancelled (as Swiggy words it), and a cancelled order keeps
Swiggy's reason text, so orders turned away for stock can be counted.
"""

import random
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from core import alerts, config as cfg, db, retry
from core.common import ConfigError, log, require_env

BASE = cfg.text("SWIGGY_ORDER_HISTORY_URL", "https://rms.swiggy.com/orders/v1/history")
ORIGIN = cfg.text("SWIGGY_ORDERS_ORIGIN", "https://partner-self-client.swiggy.com")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
DAYS = cfg.integer("ORDERS_DAYS", 2)
PAGE = 50
MAX_PAGES = cfg.integer("SWIGGY_ORDERS_MAX_PAGES", 400)  # a safety stop: 20,000 orders for one store in one run
PACE_SEC = cfg.numbers("SWIGGY_ORDERS_PACE_SEC", "0.2,0.6")  # between pages and between stores


def config(account: str) -> dict:
    return require_env("SOCIALSPORK_DATABASE_URL")


def money(value) -> Decimal | None:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01")) if value not in (None, "") else None
    except InvalidOperation:
        return None


def parse_time(text) -> datetime | None:
    """'2026-11-13 03:35:39' (India time) -> an aware datetime."""
    try:
        return datetime.strptime((text or "").strip()[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    except ValueError:
        return None


def parse_orders(objects: list[dict], outlet_id: int) -> list[dict]:
    """The history answer -> one dict per item per order. Same item twice in an order (two variants) is added up, because a
    row is unique per order and item name. Only the fields below are read: nothing about the customer."""
    rows = []
    for order in objects or []:
        status = order.get("status") or {}
        order_id = str(order.get("order_id") or "").strip()
        placed = parse_time(status.get("ordered_time"))
        items = (order.get("cart") or {}).get("items") or []
        if not order_id or placed is None or not items:
            continue
        local = placed.astimezone(IST).replace(tzinfo=None)
        raw_status = str(status.get("order_status") or "").strip()
        cancelled = raw_status.lower() == "cancelled"
        merged: dict[str, dict] = {}
        for it in items:
            name = " ".join(str(it.get("name") or "").split())[:255]
            if not name:
                continue
            qty = int(it.get("quantity") or 1)
            total = money(it.get("total", it.get("sub_total"))) or Decimal("0")
            m = merged.setdefault(name, {"qty": 0, "total": Decimal("0"), "addons": False})
            m["qty"] += qty
            m["total"] += total
            m["addons"] = m["addons"] or bool(it.get("addons"))
        subtotal = sum((m["total"] for m in merged.values()), Decimal("0"))
        for name, m in merged.items():
            rows.append({"outlet": outlet_id, "order_id": order_id, "placed_at": placed, "order_date": cfg.business_date(local),
                         "mealtime": cfg.mealtime(local.hour), "status": raw_status.title()[:40],
                         "reason": (str(status.get("cancel_reason") or "").strip()[:255] if cancelled else ""), "item": name, "qty": m["qty"],
                         # the dish's own price: skipped when add-ons are in the line, since the line total then includes them
                         "unit_price": (m["total"] / m["qty"]).quantize(Decimal("0.01")) if m["qty"] and m["total"] and not m["addons"] else None,
                         "subtotal": subtotal, "total": money(order.get("bill"))})
    return rows


CHUNK_DAYS = cfg.integer("SWIGGY_ORDERS_CHUNK_DAYS", 1)  # the partner site asks for one day at a time (a wider range returned only the newest 50 orders)


def fetch_history(token: str, swiggy_id: str, start, end) -> list[dict]:
    """Every order of one store between two dates (inclusive), fetched in windows of CHUNK_DAYS because Swiggy limits the span.
    Raises PermissionError when the login is dead."""
    out, a = [], start - timedelta(days=1)  # one extra day before, so the late-night orders of the day before the first service day are not cut off
    while a <= end:
        b = min(end, a + timedelta(days=CHUNK_DAYS - 1))
        out.extend(_fetch_window(token, swiggy_id, a, b))
        a = b + timedelta(days=1)
        if a <= end:
            time.sleep(random.uniform(*PACE_SEC))
    seen, unique = set(), []  # windows overlap by a day, so an order can come back twice
    for o in out:
        k = str(o.get("order_id") or id(o))
        if k not in seen:
            seen.add(k)
            unique.append(o)
    return unique


def _fetch_window(token: str, swiggy_id: str, start, end) -> list[dict]:
    """One window of orders (inclusive dates), newest first, page by page."""
    import requests

    if not token:
        raise PermissionError("Swiggy login has no access token; run `run.py swiggy session` for this account")
    headers = {"accept": "*/*", "accesstoken": token, "access_token": token, "content-type": "application/json",
               "origin": ORIGIN, "referer": ORIGIN + "/", "user-agent": cfg.user_agent()}
    a, b = start.isoformat(), end.isoformat()
    out, offset = [], 0
    for _ in range(MAX_PAGES):
        resp = requests.get(BASE, headers=headers, timeout=cfg.http_timeout(),
                            params={"limit": PAGE, "offset": offset, "ordered_time__gte": a, "ordered_time__lte": b,
                                    "restaurant_id": str(swiggy_id)})
        if resp.status_code in (401, 403):
            raise PermissionError(f"Swiggy session expired ({resp.status_code}); run `run.py swiggy session` for this account")
        resp.raise_for_status()
        body = resp.json() or {}
        if body.get("statusCode") not in (0, None) and any(w in str(body.get("statusMessage") or "").lower() for w in ("token", "unauthor", "login", "expired")):
            raise PermissionError(f"Swiggy session expired ({body.get('statusMessage')}); run `run.py swiggy session` for this account")
        data = ((body.get("data") or [{}])[0].get("data")) or {}
        objects = data.get("objects") or []
        out.extend(objects)
        offset += len(objects)  # Swiggy may return fewer than PAGE rows per page, so move on by what came back
        total = int((data.get("meta") or {}).get("total_count") or 0)
        if not objects or (total and offset >= total):  # total_count may be missing or 0: then only an empty page ends it
            break
        time.sleep(random.uniform(*PACE_SEC))
    return out


SAVE = """INSERT INTO order_lines (outlet_id, platform, order_id, placed_at, order_date, mealtime, status, rejection_reason, item_name,
                                 quantity, unit_price, order_subtotal, order_total, created_at)
         VALUES (%(outlet)s, 'swiggy', %(order_id)s, %(placed_at)s, %(order_date)s, %(mealtime)s, %(status)s, %(reason)s, %(item)s,
                 %(qty)s, %(unit_price)s, %(subtotal)s, %(total)s, now())
         ON CONFLICT (platform, order_id, item_name) DO UPDATE SET status = EXCLUDED.status, rejection_reason = EXCLUDED.rejection_reason,
             quantity = EXCLUDED.quantity, unit_price = EXCLUDED.unit_price, order_subtotal = EXCLUDED.order_subtotal,
             order_total = EXCLUDED.order_total"""


def save(rows: list[dict]) -> int:
    if rows:
        with db.transaction() as cur:
            cur.executemany(SAVE, rows)
    return len(rows)


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("swiggy orders: %s", e)
        return False
    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "swiggy", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.swiggy_id AS res_id, s.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id
                       JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND s.is_active ORDER BY bo.id""")
        stores = cfg.keep_stores(cur.fetchall())
    if not stores:
        log.info("swiggy orders: no Swiggy ids are mapped to stores yet")
        return True
    by_id = {a["id"]: a for a in accs.values()}
    default = next(iter(by_id))
    tokens = {i: db.load_credentials(a).get("access_token") for i, a in by_id.items()}
    today = datetime.now(IST).date()
    start, end = cfg.date_range(today - timedelta(days=DAYS - 1), today)

    ok, dead, saved_total, failures, first = True, set(), 0, [], True
    for s in stores:
        acc_id = s["account_id"] if s["account_id"] in by_id else default
        label = by_id[acc_id]["label"]
        if acc_id in dead:
            continue
        if not first:
            time.sleep(random.uniform(*PACE_SEC))
        first = False
        try:
            objects = retry.call(lambda: fetch_history(tokens[acc_id], s["res_id"], start, end), f"swiggy orders {s['res_id']}", quiet=True)
            saved = save(parse_orders(objects, s["outlet_id"]))
        except PermissionError as e:
            dead.add(acc_id)
            ok = False
            log.error("swiggy orders: login '%s' was refused (%s); its stores are skipped this run", label, e)
            db.mark_session_expired(acc_id, f"swiggy orders: {e}")
            alerts.incident(f"Swiggy session expired: {label}", str(e), f"Use Log in again on the Sessions page, or run `python run.py swiggy session --account {label}`.")
            continue
        except Exception as e:  # noqa: BLE001
            ok = False
            failures.append(f"{type(e).__name__}: {str(e)[:160]}")
            log.warning("swiggy orders %s · %s (%s) failed: %s: %s", s["brand"], s["outlet_name"], s["res_id"], type(e).__name__, str(e)[:220])
            continue
        saved_total += saved
        if saved:
            log.info("swiggy orders %s · %s (%s): %s order lines, %s to %s", s["brand"], s["outlet_name"], s["res_id"], saved, start, end)
    if len(failures) >= max(3, len(stores) // 5):
        alerts.incident("Swiggy order history failing", f"{len(failures)} of {len(stores)} stores failed. Example: {failures[0]}",
                        "Check the collector window and the Swiggy login. Order history for those stores is not up to date.")
    log.info("swiggy orders: %s order lines saved across %s stores (%s to %s)", saved_total, len(stores), start, end)
    return ok
