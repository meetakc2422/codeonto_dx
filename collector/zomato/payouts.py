"""Zomato payouts -> payout_cycles and payout_orders, for every Zomato id mapped to a store.

For each store: lists its payout cycles, reads each cycle's statement, and once a cycle is paid downloads its order-level
report and checks the sums. A paid cycle that has been checked is not fetched again. Meant to run daily
(`run.py zomato payouts --daily-at 06:00`).

The statement's sum is:  orders' payouts  +  adjustments not tied to an order (ads, Hyperpure)  =  net payout

Bank account numbers and customer ids are in these responses; neither is stored.
"""

import io
import json
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from core import alerts, config as cfg, db, retry
from core.common import ConfigError, log, require_env

from .outlets import _cookies
from .reviews import ZOMATO_API, _headers

FINANCE_URL = cfg.text("ZOMATO_FINANCE_URL", f"{ZOMATO_API}/finance")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
LOOKBACK_DAYS = cfg.integer("PAYOUT_LOOKBACK_DAYS", 14)
MAX_REPORTS = cfg.integer("PAYOUT_MAX_REPORTS_PER_RUN", 300)  # the rest wait for the next run
WORKERS = cfg.integer("PAYOUT_WORKERS", 3)
PACE_SEC = cfg.numbers("PAYOUT_PACE_SEC", "0.8,1.8")
REPORT_POLLS = cfg.integer("PAYOUT_REPORT_POLLS", 15)
REPORT_POLL_SEC = cfg.integer("PAYOUT_REPORT_POLL_SEC", 3)

PAYOUT_TOLERANCE = Decimal("1.00")  # the platform rounds each line, so a rupee over a whole cycle is rounding, not a problem
ORDER_TOLERANCE = Decimal("0.05")

# statement sections the order rows already add up to; anything else is an adjustment not tied to an order
ORDER_LEVEL_SECTIONS = {"total_order_value", "order_level_deductions", "tax_deductions", "additions"}
NOT_MONEY_PREFIXES = ("total_orders", "estimated_net_payout")  # also estimated_net_payout_with_non_zero_md on carried forward cycles

MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1)}

# Zomato serves several report formats at once, so each field lists every column name it goes by (lower case, first line,
# [] written as ()); a report has one of them. Older formats have a base rate only, the newest a single 'service fees %'.
TEXT_COLUMNS = {"order_id": ("order id",), "order_date": ("order date",), "status": ("order status (delivered/ cancelled/ rejected)",),
                "payment_mode": ("mode of payment",), "discount_construct": ("discount construct",), "settlement_status": ("settlement status",),
                "settlement_date": ("settlement date",), "bank_utr": ("bank utr",)}
NUMBER_COLUMNS = {"subtotal": ("subtotal (items total)",), "packaging_charge": ("packaging charge",), "discount_promo": ("restaurant discount (promo)",),
                  "discount_other": ("restaurant discount (bogo, freebies, gold, brand pack & others)",), "gst_collected": ("total gst collected from customers",),
                  "net_order_value": ("net order value",), "commissionable_value": ("total commissionable value", "commissionable value (excludes customer gst)"),
                  "base_fee_pct": ("base service fee %", "service fees %"), "service_fee_pct": ("total service fee %", "service fees %", "base service fee %"),
                  "service_fee": ("total service fee", "service fee", "base service fee"), "payment_fee": ("payment mechanism fee",),
                  "fees_total": ("service fee & payment mechanism fee", "service fee & payment mechanism fees"), "government_charges": ("government charges",),
                  "other_deductions": ("other order-level deductions",), "net_deductions": ("net deductions",), "net_additions": ("net additions",),
                  "payout": ("order level payout",), "unsettled_amount": ("unsettled amount",)}
REQUIRED_FIELDS = ("order_id", "commissionable_value", "base_fee_pct", "service_fee_pct", "service_fee", "net_order_value", "net_deductions", "net_additions", "payout", "settlement_status")


class RateLimited(Exception):
    pass


class NoFinanceAccess(Exception):
    """This login can't see this store's payouts; other stores are unaffected."""


class ReportFormatChanged(Exception):
    """Zomato's report no longer looks as expected: don't guess at money."""


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def money(text) -> Decimal | None:
    """'- ₹1,238.49' -> Decimal('-1238.49'). None when there is no number."""
    if text is None:
        return None
    s = str(text)
    digits = re.sub(r"[^\d.]", "", s)
    if not digits:
        return None
    try:
        value = Decimal(digits)
    except InvalidOperation:
        return None
    return -value if "-" in s else value


def _whole(text) -> int:
    value = money(text)
    return int(value) if value is not None else 0


def parse_cycle_dates(label: str) -> tuple[date, date] | None:
    """"04 - 10 May'26", "28 Apr - 03 May'26" or "28 Dec'25 - 03 Jan'26"."""
    m = re.match(r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+(\w{3})'?(\d{2})", label or "")
    try:
        if m:
            d1, d2, mon, yr = m.groups()
            return date(2000 + int(yr), MONTHS[mon], int(d1)), date(2000 + int(yr), MONTHS[mon], int(d2))
        m = re.match(r"(\d{1,2})\s+(\w{3})(?:'?\d{2})?\s*[-–]\s*(\d{1,2})\s+(\w{3})'?(\d{2})", label or "")
        if m:
            d1, mon1, d2, mon2, yr = m.groups()
            end = date(2000 + int(yr), MONTHS[mon2], int(d2))
            start_year = end.year - 1 if MONTHS[mon1] > MONTHS[mon2] else end.year
            return date(start_year, MONTHS[mon1], int(d1)), end
    except (KeyError, ValueError):
        pass
    return None


def parse_payout_date(label: str) -> date | None:
    """"04 Nov'26", sometimes followed by ', by 9PM'."""
    m = re.match(r"(\d{1,2})\s+(\w{3})'?(\d{2})", label or "")
    try:
        return date(2000 + int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))) if m else None
    except (KeyError, ValueError):
        return None


def _value(cell):
    return cell.get("value") if isinstance(cell, dict) else cell


def parse_cycle_row(row: dict) -> dict | None:
    """One row of the past cycles table."""
    label = _value(row.get("payout_cycle"))
    dates = parse_cycle_dates(label)
    if not dates:
        if label:
            log.warning("zomato payouts: unreadable payout cycle %r", label)
        return None
    status = _value(row.get("status"))
    if isinstance(status, dict):
        status = _value(status.get("label"))
    utr = _value(row.get("utr"))
    utr = utr if isinstance(utr, str) else ""
    raw_date = _value(row.get("payout_date"))
    return {"start_date": dates[0], "end_date": dates[1], "payout_date_raw": raw_date, "payout_date": parse_payout_date(raw_date),
            "status": str(status or "").strip().upper(), "utr": "" if utr.strip() in ("", "-") else utr.strip(),
            "net_payout": money(_value(row.get("payout"))), "order_count": _whole(_value(row.get("orders")))}


def parse_details(body: dict) -> dict:
    """The cycle's statement. The bank account card is skipped on purpose."""
    out = {"net_payout": None, "utr": "", "order_count": 0, "delivered_orders": 0, "rejected_orders": 0, "breakdown": []}
    for card in body.get("cardConfig") or []:
        kind, summary = card.get("type"), (card.get("data") or {}).get("summaryData") or []
        for entry in summary:
            sid, data = entry.get("id", ""), entry.get("data") or {}
            content = data.get("content") or {}
            if kind == "payout_info_card" and sid == "est_payout":
                out["net_payout"] = money((content.get("title") or {}).get("value"))
            elif kind == "transaction_details_card" and sid == "utr":
                utr = str(content.get("value") or "").strip()
                out["utr"] = "" if utr == "-" else utr
            elif kind == "summary_accordion_card":
                value, extra = content.get("value"), entry.get("expandedData") or []
                if sid == "total_orders":
                    out["order_count"] = _whole(value)
                    for ex in extra:
                        label = ((ex.get("label") or {}).get("value") or "").lower()
                        count = _whole((ex.get("content") or {}).get("value"))
                        out["delivered_orders" if "delivered" in label else "rejected_orders"] += count if ("delivered" in label or "rejected" in label) else 0
                elif sid == "estimated_net_payout":
                    if out["net_payout"] is None:
                        out["net_payout"] = money(value)
                elif sid:
                    items = [{"label": ((ex.get("label") or {}).get("value") or "").strip(), "value": _float(money((ex.get("content") or {}).get("value")))}
                             for ex in extra if ((ex.get("label") or {}).get("value") or "").strip()]
                    out["breakdown"].append({"id": sid, "label": (data.get("label") or {}).get("value") or sid, "value": _float(money(value)), "items": items})
    return out


def _float(v):
    return float(v) if v is not None else None


def _date_or_none(text) -> date | None:
    if isinstance(text, datetime):
        return text.date()
    try:
        return datetime.strptime(str(text).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _order_time(text) -> datetime | None:
    if isinstance(text, datetime):
        return text.replace(tzinfo=IST)
    try:
        return datetime.strptime(str(text).strip()[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    except ValueError:
        return None


def _header(text) -> str:
    return re.sub(r"\s+", " ", str(text or "").split("\n")[0]).strip().lower().replace("[", "(").replace("]", ")")


def _number(cell) -> Decimal:
    if isinstance(cell, bool) or cell is None:
        return Decimal(0)
    try:
        return Decimal(str(cell))
    except InvalidOperation:
        return Decimal(0)


def parse_report(content: bytes) -> list[dict]:
    """The 'Order Level' sheet of the payout report. Raises ReportFormatChanged rather than guess."""
    from openpyxl import load_workbook

    book = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    if "Order Level" not in book.sheetnames:
        raise ReportFormatChanged("no 'Order Level' sheet")
    rows = list(book["Order Level"].iter_rows(values_only=True))
    index = next((i for i, r in enumerate(rows[:30]) if "order id" in {_header(c) for c in r}), None)
    if index is None:
        raise ReportFormatChanged("no 'Order ID' column")
    headers = {_header(c): j for j, c in enumerate(rows[index]) if c is not None}
    where = {field: next((headers[n] for n in names if n in headers), None) for field, names in (TEXT_COLUMNS | NUMBER_COLUMNS).items()}
    missing = [f for f in REQUIRED_FIELDS if where[f] is None]
    if missing:
        raise ReportFormatChanged(f"missing columns: {', '.join(missing)}")
    id_col = where["order_id"]
    orders = []
    for r in rows[index + 1:]:
        order_id = str(r[id_col] or "").strip().removesuffix(".0")
        if not order_id.isdigit():
            continue
        o = {field: (r[where[field]] if where[field] is not None else None) for field in TEXT_COLUMNS}
        o |= {field: (_number(r[where[field]]) if where[field] is not None else Decimal(0)) for field in NUMBER_COLUMNS}
        o["order_id"] = order_id
        o["order_date"] = _order_time(o["order_date"])
        o["settlement_date"] = _date_or_none(o["settlement_date"])
        for field in ("status", "payment_mode", "discount_construct", "settlement_status", "bank_utr"):
            text = str(o[field] or "").strip()
            o[field] = "" if text.upper() == "NA" else text
        o["restaurant_discount"] = o.pop("discount_promo") + o.pop("discount_other")
        orders.append(o)
    return orders


def reconcile(statement: dict, orders: list[dict]) -> dict:
    """Check a paid cycle's statement against its orders. Adds 'issues' to each order; returns the cycle's result."""
    # the base rate is the contract; the total also carries a distance fee that varies order by order
    usual_rate = Counter(o["base_fee_pct"] for o in orders if o["commissionable_value"]).most_common(1)
    usual_rate = usual_rate[0][0] if usual_rate else None
    found = set()
    for o in orders:
        o["issues"] = []
        # a cancelled order pays only its additions (the refund): its order value never reached the restaurant
        value = Decimal(0) if o["status"].upper() in ("CANCELLED", "REJECTED") else o["net_order_value"]
        if abs(value - o["net_deductions"] + o["net_additions"] - o["payout"]) > ORDER_TOLERANCE:
            o["issues"].append("order_payout_math")
        if abs(o["commissionable_value"] * o["service_fee_pct"] / 100 - o["service_fee"]) > ORDER_TOLERANCE:
            o["issues"].append("order_fee_math")
        if usual_rate is not None and o["commissionable_value"] and o["base_fee_pct"] != usual_rate:
            o["issues"].append("fee_rate_changed")
        found.update(o["issues"])

    orders_total = sum((o["payout"] for o in orders), Decimal(0))
    order_additions = sum((o["net_additions"] for o in orders), Decimal(0))
    adjustments = Decimal(0)
    for section in statement["breakdown"]:
        value = Decimal(str(section["value"])) if section["value"] is not None else Decimal(0)
        if section["id"] == "additions":
            adjustments += value - order_additions  # additions the order rows don't carry
        elif section["id"] not in ORDER_LEVEL_SECTIONS and not section["id"].startswith(NOT_MONEY_PREFIXES):
            adjustments += value
    cents = Decimal("0.01")
    expected = (orders_total + adjustments).quantize(cents, ROUND_HALF_UP)
    net = statement["net_payout"]
    discrepancy = (net - expected) if net is not None else None
    if discrepancy is None or abs(discrepancy) > PAYOUT_TOLERANCE:
        found.add("payout_mismatch")
    if statement["order_count"] and statement["order_count"] != len(orders):
        found.add("order_count_mismatch")
    if sum((o["unsettled_amount"] for o in orders), Decimal(0)) > ORDER_TOLERANCE:
        found.add("unsettled_orders")
    if net and net > 0 and not statement["utr"]:  # a zero payout has no bank transfer, so no UTR
        found.add("paid_without_utr")
    return {"orders_total": orders_total.quantize(cents, ROUND_HALF_UP), "adjustments": adjustments.quantize(cents, ROUND_HALF_UP),
            "expected_payout": expected, "discrepancy": discrepancy,
            "commissionable_total": sum((o["commissionable_value"] for o in orders), Decimal(0)).quantize(cents, ROUND_HALF_UP),
            "service_fee_total": sum((o["service_fee"] for o in orders), Decimal(0)).quantize(cents, ROUND_HALF_UP),
            "issues": sorted(found)}


_ORDER_FIELDS = ("order_id", "order_date", "status", "payment_mode", "discount_construct", "subtotal", "packaging_charge", "restaurant_discount",
                 "gst_collected", "net_order_value", "commissionable_value", "base_fee_pct", "service_fee_pct", "service_fee", "payment_fee", "fees_total",
                 "government_charges", "other_deductions", "net_deductions", "net_additions", "payout", "settlement_status", "settlement_date",
                 "bank_utr", "unsettled_amount")


def save(cur, outlet_id: int, cycle: dict, statement: dict, orders: list[dict] | None, now: datetime, platform: str = "zomato", result: dict | None = None) -> int:
    """Store a cycle and, when its report was read, its orders and the check's result. Returns the cycle's id."""
    from psycopg.types.json import Jsonb

    if orders is not None and result is None:
        result = reconcile(statement, orders)
    result = result or {}
    cur.execute("""INSERT INTO payout_cycles (outlet_id, platform, start_date, end_date, payout_date, status, utr, net_payout, order_count,
                       delivered_orders, rejected_orders, breakdown, issues, fetched_at, orders_total, adjustments, expected_payout, discrepancy,
                       commissionable_total, service_fee_total, reconciled_at)
                   VALUES (%(o)s, %(platform)s, %(start)s, %(end)s, %(pd)s, %(status)s, %(utr)s, %(net)s, %(count)s, %(deliv)s, %(rej)s, %(bd)s, %(issues)s, %(now)s,
                       %(ot)s, %(adj)s, %(exp)s, %(disc)s, %(comm)s, %(fee)s, %(rec)s)
                   ON CONFLICT (outlet_id, platform, start_date, end_date) DO UPDATE SET payout_date = EXCLUDED.payout_date, status = EXCLUDED.status,
                       utr = EXCLUDED.utr, net_payout = EXCLUDED.net_payout, order_count = EXCLUDED.order_count, delivered_orders = EXCLUDED.delivered_orders,
                       rejected_orders = EXCLUDED.rejected_orders, breakdown = EXCLUDED.breakdown, issues = EXCLUDED.issues, fetched_at = EXCLUDED.fetched_at,
                       orders_total = EXCLUDED.orders_total, adjustments = EXCLUDED.adjustments, expected_payout = EXCLUDED.expected_payout,
                       discrepancy = EXCLUDED.discrepancy, commissionable_total = EXCLUDED.commissionable_total,
                       service_fee_total = EXCLUDED.service_fee_total, reconciled_at = EXCLUDED.reconciled_at
                   RETURNING id""",
                {"o": outlet_id, "platform": platform, "start": cycle["start_date"], "end": cycle["end_date"], "pd": cycle["payout_date"], "status": cycle["status"],
                 "utr": statement["utr"] or cycle["utr"], "net": statement["net_payout"] if statement["net_payout"] is not None else cycle["net_payout"],
                 "count": statement["order_count"] or cycle["order_count"], "deliv": statement["delivered_orders"], "rej": statement["rejected_orders"],
                 "bd": Jsonb(statement["breakdown"]), "issues": Jsonb(result.get("issues", [])), "now": now, "ot": result.get("orders_total"),
                 "adj": result.get("adjustments"), "exp": result.get("expected_payout"), "disc": result.get("discrepancy"),
                 "comm": result.get("commissionable_total"), "fee": result.get("service_fee_total"), "rec": now if orders is not None else None})
    cycle_id = cur.fetchone()["id"]
    if orders is not None:
        cur.execute("DELETE FROM payout_orders WHERE cycle_id = %s", (cycle_id,))
        names = ", ".join(_ORDER_FIELDS)
        slots = ", ".join(f"%({f})s" for f in _ORDER_FIELDS)
        cur.executemany(f"INSERT INTO payout_orders (cycle_id, {names}, issues) VALUES (%(cycle)s, {slots}, %(issues)s)",
                        [{**o, "cycle": cycle_id, "issues": Jsonb(o["issues"])} for o in orders])
    return cycle_id


def _session_headers(cookies: dict) -> dict:
    return {**_headers(cookies), "content-type": "application/json", "user-agent": cfg.user_agent(), "x-zomato-source-identifier": "merchant_finance"}


def _post(path: str, cookies: dict, payload: dict) -> dict:
    """One finance call, retried on network errors, 5xx and rate limits."""
    return retry.call(lambda: _post_once(path, cookies, payload), f"zomato payouts {path}", slow=(RateLimited,))


def _post_once(path: str, cookies: dict, payload: dict) -> dict:
    import random

    import requests

    time.sleep(random.uniform(*PACE_SEC))
    resp = requests.post(f"{FINANCE_URL}/{path}", headers=_session_headers(cookies), json=payload, timeout=cfg.integer("PAYOUT_HTTP_TIMEOUT_SEC", 30))
    if resp.status_code == 401:
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
    if resp.status_code == 403:
        raise NoFinanceAccess()
    if resp.status_code == 429:
        raise RateLimited("Zomato rate limit (429) on finance")
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")


def fetch_cycles(cookies: dict, res_id: str, start: date, end: date) -> list[dict]:
    postback = {"start_date": "0001-01-01", "end_date": "0001-01-01", "config_postback_params": [{"entityType": "outlets", "entityIds": [str(res_id)]}],
                "entity_ids": [int(res_id)]}
    body = _post("payouts/get-payout-cycles", cookies, {"cycle": "past_cycle", "postbackParams": json.dumps(postback, separators=(",", ":")), "pageIndex": 1,
                                                        "rows": 10, "startDate": str(start), "endDate": str(end)})
    rows = ((body.get("data") or {}).get("tableData") or {}).get("tableRows") or []
    return [c for c in map(parse_cycle_row, rows) if c]


def _request_id(res_id: str, cycle: dict) -> str:
    return json.dumps({"start_date": str(cycle["start_date"]), "end_date": str(cycle["end_date"]), "entity_ids": [int(res_id)],
                       "payout_date": str(cycle["payout_date_raw"])}, separators=(",", ":"))


def fetch_statement(cookies: dict, res_id: str, cycle: dict) -> dict:
    return parse_details(_post("payouts/get-payout-details", cookies, {"postbackParams": _request_id(res_id, cycle), "itemId": ""}))


def _download(url: str):
    import requests

    resp = requests.get(url, timeout=cfg.integer("PAYOUT_DOWNLOAD_TIMEOUT_SEC", 120))
    resp.raise_for_status()
    return resp


def fetch_report(cookies: dict, res_id: str, cycle: dict) -> bytes | None:
    """Ask Zomato to prepare the report, wait for it, download it. None if it isn't ready in time."""
    import requests

    payload = {"requestId": _request_id(res_id, cycle), "type": "payouts"}
    for _ in range(REPORT_POLLS):
        data = _post("download-report", cookies, payload).get("data") or {}
        state, urls = data.get("downloadStatus"), data.get("downloadURLs") or []
        if state in ("COMPLETED", "READY") and urls:
            try:
                resp = retry.call(lambda: _download(urls[0]), f"zomato payouts {res_id} report download", quiet=True)
            except requests.RequestException as e:  # the message would carry the signed link: keep it out of the logs
                log.warning("zomato payouts %s %s: report download failed (%s)", res_id, cycle["end_date"], type(e).__name__)
                return None
            return resp.content
        if state == "FAILED":
            return None
        time.sleep(REPORT_POLL_SEC)
    return None


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato payouts: %s", e)
        return False

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND z.is_active ORDER BY bo.id""")
        stores = cur.fetchall()
        stores = cfg.keep_stores(stores)  # ONLY_RES_IDS (backfill)
        cur.execute("""SELECT outlet_id, start_date, end_date FROM payout_cycles
                       WHERE platform = 'zomato' AND reconciled_at IS NOT NULL AND upper(status) = 'PAID'""")
        finished = {(r["outlet_id"], r["start_date"], r["end_date"]) for r in cur.fetchall()}
    if not stores:
        log.info("zomato payouts: no Zomato ids are mapped to stores yet")
        return True

    by_id = {a["id"]: a for a in accs.values()}
    creds = {a["id"]: _cookies(db.load_credentials(a)) for a in accs.values()}
    default = next(iter(by_id))
    end = datetime.now(IST).date()
    start = end - timedelta(days=LOOKBACK_DAYS)
    start, end = cfg.date_range(start, end)  # BACKFILL_FROM/TO

    stop = threading.Event()
    lock = threading.Lock()
    tally = Counter()

    again = []  # stores that failed on something unexpected: one more go at the end

    def work(s, last=False):
        if stop.is_set():
            return
        res_id, cookies = str(s["res_id"]), creds[s["account_id"] if s["account_id"] in by_id else default]
        try:
            cycles = fetch_cycles(cookies, res_id, start, end)
            for cycle in cycles:
                if stop.is_set():
                    return
                if (s["outlet_id"], cycle["start_date"], cycle["end_date"]) in finished:
                    continue
                statement = fetch_statement(cookies, res_id, cycle)
                orders = None
                if cycle["status"] == "PAID":
                    with lock:
                        allowed = tally["reports"] < MAX_REPORTS
                        tally["reports"] += allowed
                    if allowed:
                        content = fetch_report(cookies, res_id, cycle)
                        if content is None:
                            log.warning("zomato payouts %s %s: report not ready; next run retries", res_id, cycle["end_date"])
                            tally["not_ready"] += 1
                        else:
                            orders = parse_report(content)
                    else:
                        tally["deferred"] += 1
                with db.transaction() as cur:
                    save(cur, s["outlet_id"], cycle, statement, orders, datetime.now(timezone.utc))
                tally["cycles"] += 1
                if orders is not None:
                    tally["reconciled"] += 1
                    tally["orders"] += len(orders)
                    log.info("zomato payouts %s · %s (%s) %s to %s: %s orders", s["brand"], s["outlet_name"], res_id, cycle["start_date"], cycle["end_date"], len(orders))
        except NoFinanceAccess:
            log.warning("zomato payouts %s · %s (%s): this login has no access to its payouts", s["brand"], s["outlet_name"], res_id)
            tally["no_access"] += 1
        except PermissionError as e:
            stop.set()
            log.error("zomato payouts: %s", e)
            alerts.incident("Zomato session expired", str(e), "Run `python run.py zomato session`, then run payouts again.")
            tally["failed"] += 1
        except RateLimited as e:
            stop.set()
            log.error("zomato payouts: %s; stopping this run, the next one continues", e)
            alerts.incident("Zomato rate limit (429)", str(e), "Payouts stopped for now and continue on the next run. If it keeps happening, lower PAYOUT_WORKERS.")
            tally["failed"] += 1
        except ReportFormatChanged as e:
            stop.set()
            log.error("zomato payouts: the report format changed (%s); nothing more is saved until the parser is updated", e)
            alerts.incident("Zomato payout report changed", str(e), "Update collector/zomato/payouts.py to the new report format.")
            tally["failed"] += 1
        except Exception as e:  # one store failing must not stop the rest
            if not last:
                log.warning("zomato payouts %s failed (%s: %s); trying it again at the end", res_id, type(e).__name__, str(e)[:160])
                with lock:
                    again.append(s)
                return
            log.exception("zomato payouts %s failed: %s", res_id, e)
            tally["failed"] += 1

    log.info("zomato payouts: checking %s stores, %s to %s", len(stores), start, end)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(work, stores))
    if again and not stop.is_set():  # finished cycles are skipped, so this only redoes what was missed
        log.info("zomato payouts: %s stores failed; trying them again one at a time in %ss", len(again), retry.ROUND_WAIT)
        time.sleep(retry.ROUND_WAIT)
        for s in again:
            work(s, last=True)
    log.info("zomato payouts: %s cycles saved, %s reconciled (%s orders), %s waiting for the next run, %s not ready, %s stores without access, %s failed",
             tally["cycles"], tally["reconciled"], tally["orders"], tally["deferred"], tally["not_ready"], tally["no_access"], tally["failed"])
    return not tally["failed"]
