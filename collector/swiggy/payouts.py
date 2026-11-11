"""Swiggy payouts -> payout_cycles and payout_orders, for every Swiggy id mapped to a store.

For each store: lists its weekly payouts, reads each statement, and once a payout is paid downloads its annexure and
checks the sums. A paid payout that has been checked is not fetched again. Meant to run daily
(`run.py swiggy payouts --daily-at 06:30`).

The sum is:  orders' net payouts  +  ads and other charges not tied to an order  =  net payout
Customer details and bank accounts are in these responses; neither is stored.
"""

import io
import random
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from urllib.parse import urlparse

from core import alerts, config as cfg, db
from core.common import ConfigError, log, require_env

from zomato.payouts import ReportFormatChanged, RateLimited, _header, money, save

API = cfg.text("SWIGGY_COMPOSER_URL", "https://vhc-composer.swiggy.com/query")
ORIGIN = cfg.text("SWIGGY_FINANCE_ORIGIN", "https://partner.swiggy.com")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
LOOKBACK_DAYS = cfg.integer("PAYOUT_LOOKBACK_DAYS", 14)
MAX_REPORTS = cfg.integer("PAYOUT_MAX_REPORTS_PER_RUN", 300)
WORKERS = cfg.integer("PAYOUT_WORKERS", 3)
PACE_SEC = cfg.numbers("PAYOUT_PACE_SEC", "0.8,1.8")
PAGE = 10

PAYOUT_TOLERANCE = Decimal("1.00")
ORDER_TOLERANCE = Decimal("0.05")
RATE_TOLERANCE = Decimal("0.05")  # Swiggy derives the % per order, so 13.98 and 14.01 are rounding on a 14% contract

PAYOUTS_QUERY = """query { getFinanceRestaurantPastPayouts(input: {restaurantId: %d, toDate: "%s", fromDate: "%s", offset: %d, limit: %d}) {
  payouts { payoutId netPayout week { startDate endDate } payoutStatus { state message } } } }"""
DETAILS_QUERY = """query getRestaurantPayoutDetailsV3($restaurantIds: [Int64!]!, $payoutId: Int64, $panId: String, $from: Int64, $to: Int64) {
  getRestaurantPayoutDetailsV3(getRestaurantPayoutDetailsV3Input: {restaurantIds: $restaurantIds, payoutId: $payoutId, panId: $panId, from: $from, to: $to}) {
    data { payoutId week { startDate endDate } payoutDate orderCount payoutStatus { message state } payoutUTRs
           payoutSummary { header amount subHeaders { text amount } } netPayout attachments { annexure } } } }"""

TEXT_COLUMNS = {"order_id": ("order id",), "order_date": ("order date",), "status": ("order status",), "category": ("order category",),
                "payment_mode": ("order payment type",), "discount_construct": ("coupon type applied by customer",), "settlement_date": ("order settlement date",),
                "service_fee_pct": ("service fees %",)}
NUMBER_COLUMNS = {"subtotal": ("item total",), "packaging_charge": ("packaging charges",), "restaurant_discount": ("restaurant discount share (3a+3b)",),
                  "gst_collected": ("gst collected",), "net_order_value": ("total customer paid (4+5)",), "commissionable_value": ("commission charged on",),
                  "service_fee": ("commission",), "payment_fee": ("payment collection charges",), "fees_total": ("total swiggy fees",),
                  "other_deductions": ("complaint & cancellation charges",), "government_charges": ("total taxes",), "payout": ("net payout for order (after taxes)",)}
REQUIRED_FIELDS = ("order_id", "status", "service_fee_pct", "net_order_value", "commissionable_value", "service_fee", "fees_total", "other_deductions", "government_charges", "payout")


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _day(ts) -> date | None:
    """Swiggy's epoch seconds, as a date in India."""
    try:
        return datetime.fromtimestamp(int(ts), IST).date()
    except (TypeError, ValueError, OSError):
        return None


def _decimal(v) -> Decimal | None:
    try:
        return Decimal(str(v)) if v is not None else None
    except InvalidOperation:
        return None


def _number(cell) -> Decimal:
    return money(cell) or Decimal(0) if isinstance(cell, str) else (_decimal(cell) or Decimal(0))


def _slug(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", re.sub(r"^\(\w\)\s*", "", (header or "").lower())).strip("_")


def parse_cycle(p: dict) -> dict | None:
    week = p.get("week") or {}
    start, end = _day(week.get("startDate")), _day(week.get("endDate"))
    if not start or not end or p.get("payoutId") is None:
        return None
    state = str((p.get("payoutStatus") or {}).get("state") or "").strip().upper()
    return {"start_date": start, "end_date": end, "payout_date": None, "status": "TO BE PAID" if state == "PENDING" else state, "utr": "",
            "net_payout": _decimal(p.get("netPayout")), "order_count": 0, "payout_id": int(p["payoutId"]), "from_ts": int(week["startDate"]), "to_ts": int(week["endDate"])}


def parse_details(d: dict) -> dict:
    """The statement, in the same shape the shared save() takes. Also returns the annexure link and payout date."""
    breakdown = [{"id": _slug(s.get("header")), "label": s.get("header") or "", "value": float(s["amount"]) if s.get("amount") is not None else None,
                  "items": [{"label": (u.get("text") or "").strip(), "value": float(u["amount"]) if u.get("amount") is not None else None} for u in s.get("subHeaders") or []]}
                 for s in d.get("payoutSummary") or []]
    return {"net_payout": _decimal(d.get("netPayout")), "utr": ", ".join(d.get("payoutUTRs") or []), "order_count": int(d.get("orderCount") or 0),
            "delivered_orders": 0, "rejected_orders": 0, "breakdown": breakdown, "payout_date": _day(d.get("payoutDate")),
            "annexure": (d.get("attachments") or {}).get("annexure") or ""}


def _order_time(text):
    if isinstance(text, datetime):
        return text.replace(tzinfo=IST)
    try:
        return datetime.strptime(str(text).strip()[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    except ValueError:
        return None


def _settled_on(text):
    if isinstance(text, datetime):
        return text.date()
    try:
        return datetime.strptime(str(text).strip()[:10], "%d-%m-%Y").date()
    except ValueError:
        return None


def parse_annexure(content: bytes) -> list[dict]:
    """The 'Order Level' sheet. Raises ReportFormatChanged rather than guess."""
    from openpyxl import load_workbook

    book = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    if "Order Level" not in book.sheetnames:
        raise ReportFormatChanged("no 'Order Level' sheet")
    rows = list(book["Order Level"].iter_rows(values_only=True))
    index = next((i for i, r in enumerate(rows[:30]) if "order id" in {_header(c) for c in r}), None)
    if index is None:
        raise ReportFormatChanged("no 'Order ID' column")
    headers: dict[str, int] = {}
    for j, c in enumerate(rows[index]):
        if c is not None:
            headers.setdefault(_header(c), j)
    where = {field: next((headers[n] for n in names if n in headers), None) for field, names in (TEXT_COLUMNS | NUMBER_COLUMNS).items()}
    missing = [f for f in REQUIRED_FIELDS if where[f] is None]
    if missing:
        raise ReportFormatChanged(f"missing columns: {', '.join(missing)}")
    orders = []
    for r in rows[index + 1:]:
        order_id = str(r[where["order_id"]] or "").strip().removesuffix(".0")
        if not order_id.isdigit():
            continue
        o = {f: (r[where[f]] if where[f] is not None else None) for f in TEXT_COLUMNS}
        o |= {f: (_number(r[where[f]]) if where[f] is not None else Decimal(0)) for f in NUMBER_COLUMNS}
        pct = money(o["service_fee_pct"]) or Decimal(0)
        settled = _settled_on(o["settlement_date"])
        fees, other, taxes = o["fees_total"], o["other_deductions"], o["government_charges"]
        o |= {"order_id": order_id, "order_date": _order_time(o["order_date"]), "settlement_date": settled, "service_fee_pct": pct, "base_fee_pct": pct,
              "status": str(o["status"] or "").strip().upper(), "category": str(o["category"] or "").strip(), "payment_mode": str(o["payment_mode"] or "").strip(),
              "discount_construct": str(o["discount_construct"] or "").strip(), "settlement_status": "settled" if settled else "", "bank_utr": "",
              "net_deductions": abs(fees) + abs(other) + abs(taxes), "net_additions": Decimal(0), "unsettled_amount": Decimal(0)}
        orders.append(o)
    return orders


def check_orders(orders: list[dict]) -> None:
    """Swiggy's own order-level checks; save() then adds the cycle totals. Rates differ between Swiggy and Toing orders, so each compares with its own."""
    delivered = [o for o in orders if o["status"] == "DELIVERED" and o["commissionable_value"]]
    usual = {cat: Counter(o["base_fee_pct"].quantize(Decimal("0.1")) for o in delivered if o["category"] == cat).most_common(1)
             for cat in {o["category"] for o in orders}}
    for o in orders:
        o["checks"] = []
        if o["status"] != "DELIVERED":  # a cancelled order shows a commission base but is charged none
            continue
        if abs(o["net_order_value"] - o["net_deductions"] - o["payout"]) > ORDER_TOLERANCE:
            o["checks"].append("order_payout_math")
        if abs(o["commissionable_value"] * o["service_fee_pct"] / 100 - o["service_fee"]) > ORDER_TOLERANCE:
            o["checks"].append("order_fee_math")
        rate = usual[o["category"]]
        if rate and o["commissionable_value"] and abs(o["base_fee_pct"] - rate[0][0]) > RATE_TOLERANCE:
            o["checks"].append("fee_rate_changed")


def reconcile(statement: dict, orders: list[dict]) -> dict:
    check_orders(orders)
    found = set()
    for o in orders:
        o["issues"] = o.pop("checks")
        found.update(o["issues"])
    cents = Decimal("0.01")
    orders_total = sum((o["payout"] for o in orders), Decimal(0))
    adjustments = sum((Decimal(str(s["value"])) for s in statement["breakdown"]
                       if s["value"] is not None and s["label"].startswith(("(E)", "(F)"))), Decimal(0))
    expected = (orders_total + adjustments).quantize(cents, ROUND_HALF_UP)
    net = statement["net_payout"]
    discrepancy = (net - expected) if net is not None else None
    if discrepancy is None or abs(discrepancy) > PAYOUT_TOLERANCE:
        found.add("payout_mismatch")
    if statement["order_count"] and statement["order_count"] != len(orders):
        found.add("order_count_mismatch")
    if net and net > 0 and not statement["utr"]:
        found.add("paid_without_utr")
    return {"orders_total": orders_total.quantize(cents, ROUND_HALF_UP), "adjustments": adjustments.quantize(cents, ROUND_HALF_UP), "expected_payout": expected,
            "discrepancy": discrepancy, "commissionable_total": sum((o["commissionable_value"] for o in orders), Decimal(0)).quantize(cents, ROUND_HALF_UP),
            "service_fee_total": sum((o["service_fee"] for o in orders), Decimal(0)).quantize(cents, ROUND_HALF_UP), "issues": sorted(found)}


def _post(name: str, token: str, body: dict) -> dict:
    import requests

    time.sleep(random.uniform(*PACE_SEC))
    resp = requests.post(f"{API}?query={name}", json=body, timeout=cfg.integer("PAYOUT_HTTP_TIMEOUT_SEC", 30),
                         headers={"Content-Type": "application/json", "Accept": "application/graphql-response+json, application/json", "access_token": token,
                                  "Origin": ORIGIN, "Referer": ORIGIN + "/", "User-Agent": cfg.user_agent()})
    if resp.status_code in (401, 403):
        raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
    if resp.status_code == 429:
        raise RateLimited("Swiggy rate limit (429) on payouts")
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        log.warning("swiggy payouts %s: %s", name, str(data["errors"][0].get("message"))[:200])
    return data.get("data") or {}


def fetch_cycles(token: str, res_id: int, start: date, end: date) -> list[dict]:
    payouts, offset = [], 0
    while True:
        batch = (_post("getFinanceRestaurantPastPayouts", token, {"query": PAYOUTS_QUERY % (res_id, end, start, offset, PAGE), "variables": {}})
                 .get("getFinanceRestaurantPastPayouts") or {}).get("payouts") or []
        payouts += batch
        if len(batch) < PAGE:
            return [c for c in map(parse_cycle, payouts) if c]
        offset += PAGE


def fetch_statement(token: str, res_id: int, cycle: dict) -> dict | None:
    items = (_post("getRestaurantPayoutDetailsV3", token, {"query": DETAILS_QUERY, "operationName": "getRestaurantPayoutDetailsV3", "variables": {
        "restaurantIds": [res_id], "payoutId": cycle["payout_id"], "panId": None, "from": cycle["from_ts"], "to": cycle["to_ts"]}})
             .get("getRestaurantPayoutDetailsV3") or {}).get("data") or []
    return parse_details(items[0]) if items else None


def fetch_annexure(url: str, token: str) -> bytes | None:
    import requests

    host = urlparse(url).hostname or ""
    headers = {"access_token": token} if host == "swiggy.com" or host.endswith(".swiggy.com") else {}  # the login never goes to another host
    try:
        resp = requests.get(url, headers=headers, timeout=cfg.integer("PAYOUT_DOWNLOAD_TIMEOUT_SEC", 120))
        resp.raise_for_status()
    except requests.RequestException as e:  # the message would carry the signed link: keep it out of the logs
        log.warning("swiggy payouts: annexure download failed (%s)", type(e).__name__)
        return None
    return resp.content


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("swiggy payouts: %s", e)
        return False

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "swiggy", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.swiggy_id AS res_id, s.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND s.is_active ORDER BY bo.id""")
        stores = cur.fetchall()
        stores = cfg.keep_stores(stores)  # ONLY_RES_IDS (backfill)
        cur.execute("""SELECT outlet_id, start_date, end_date FROM payout_cycles
                       WHERE platform = 'swiggy' AND reconciled_at IS NOT NULL AND upper(status) = 'PAID'""")
        finished = {(r["outlet_id"], r["start_date"], r["end_date"]) for r in cur.fetchall()}
    tokens = {a["id"]: db.load_credentials(a).get("access_token") for a in accs.values()}
    stores = [s for s in stores if tokens.get(s["account_id"])]
    if not stores:
        log.info("swiggy payouts: no Swiggy ids are mapped to these accounts")
        return True

    end = datetime.now(IST).date()
    start = end - timedelta(days=LOOKBACK_DAYS)
    start, end = cfg.date_range(start, end)  # BACKFILL_FROM/TO
    stop, lock, tally = threading.Event(), threading.Lock(), Counter()

    def work(s):
        if stop.is_set():
            return
        res_id, token = int(s["res_id"]), tokens[s["account_id"]]
        try:
            for cycle in fetch_cycles(token, res_id, start, end):
                if stop.is_set():
                    return
                if (s["outlet_id"], cycle["start_date"], cycle["end_date"]) in finished:
                    continue
                statement = fetch_statement(token, res_id, cycle)
                if statement is None:
                    continue
                cycle["payout_date"] = statement["payout_date"]
                orders = None
                if cycle["status"] == "PAID" and statement["annexure"]:
                    with lock:
                        allowed = tally["reports"] < MAX_REPORTS
                        tally["reports"] += allowed
                    if allowed:
                        content = fetch_annexure(statement["annexure"], token)
                        if content is None:
                            tally["not_ready"] += 1
                        else:
                            orders = parse_annexure(content)
                    else:
                        tally["deferred"] += 1
                result = reconcile(statement, orders) if orders is not None else None
                with db.transaction() as cur:
                    save(cur, s["outlet_id"], cycle, statement, orders, datetime.now(timezone.utc), platform="swiggy", result=result)
                tally["cycles"] += 1
                if orders is not None:
                    tally["reconciled"] += 1
                    tally["orders"] += len(orders)
        except PermissionError as e:
            stop.set()
            log.error("swiggy payouts: %s", e)
            alerts.incident("Swiggy session expired", str(e), "Run `python run.py swiggy session`, then run payouts again.")
            tally["failed"] += 1
        except RateLimited as e:
            stop.set()
            log.error("swiggy payouts: %s; stopping this run, the next one continues", e)
            alerts.incident("Swiggy rate limit (429)", str(e), "Payouts stopped for now and continue on the next run.")
            tally["failed"] += 1
        except ReportFormatChanged as e:
            stop.set()
            log.error("swiggy payouts: the annexure format changed (%s); nothing more is saved until the parser is updated", e)
            alerts.incident("Swiggy payout annexure changed", str(e), "Update collector/swiggy/payouts.py to the new format.")
            tally["failed"] += 1
        except Exception as e:  # one store failing must not stop the rest
            log.exception("swiggy payouts %s failed: %s", res_id, e)
            tally["failed"] += 1

    log.info("swiggy payouts: checking %s stores, %s to %s", len(stores), start, end)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(work, stores))
    log.info("swiggy payouts: %s cycles saved, %s reconciled (%s orders), %s waiting for the next run, %s not ready, %s failed",
             tally["cycles"], tally["reconciled"], tally["orders"], tally["deferred"], tally["not_ready"], tally["failed"])
    return not tally["failed"]
