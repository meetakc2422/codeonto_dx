"""Zomato dining payouts -> dining_payout_transactions.

Zomato builds the dining payout statement as an Excel report and emails it, so this job has three steps:
  1. ask Zomato (merchant web login) to email the "Consolidated payout report" for some outlets and dates,
  2. wait for the email in the mailbox the report is sent to, and download the attachment,
  3. read its "Transactions summary" sheet and save one row per bill.

Run:  python run.py zomato dining_payouts --account paras --res-id 111,222 --start 2026-07-01 --end 2026-11-18
      A long range is split into windows of DINING_REPORT_DAYS (default 92, about a quarter), one email per window.
Load a report you already have, without asking Zomato again:
      python -m zomato.dining_payouts load path/to/Consolidated_payout_report.xlsx [--res-id 111,222]
      python -m zomato.dining_payouts fetch --minutes 60 --res-id 111,222     (reports already emailed, not asked again)

.env (collector):
    DINING_REPORT_EMAIL      the address the report is sent to (must be a mailbox this job can read)
    DINING_REPORT_PASSWORD   that mailbox's password (an app password if the provider offers one)
    DINING_REPORT_IMAP_HOST  default imap.secureserver.net
"""

import email
import imaplib
import os
import re
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from email.header import decode_header
from email.utils import parsedate_to_datetime

import requests

from core import config as cfg, db
from core.common import ConfigError, log, require_env

from .outlets import _cookies

SITE = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
GENERATE_URL = f"{SITE}/dining-gw/merchant/web/payouts/soa-report/multi-outlet/generate?service_type=dine_out"
SUBJECT = "Consolidated payout report"
WINDOW_DAYS = cfg.integer("DINING_REPORT_DAYS", 92)
SHEET = "Transactions summary"
HEADER_ROW = 7  # the column names sit on the 7th row of the sheet


def config(account: str) -> dict:
    return require_env("SOCIALSPORK_DATABASE_URL")


# ---- reading the Excel ------------------------------------------------------------------------------------------

def _num(v):
    if v is None or str(v).strip() in ("", "-"):
        return None
    try:
        return Decimal(str(v).replace(",", "").strip())
    except InvalidOperation:
        return None


def _str(v) -> str:
    s = "" if v is None else str(v).strip()
    return "" if s == "-" else s


def _id(v) -> str:
    s = _str(v)
    return s[:-2] if s.endswith(".0") else s


def _when(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(v).strip(), fmt)
        except ValueError:
            continue
    return None


def parse_report(path: str) -> list[dict]:
    """One dict per bill from the report's 'Transactions summary' sheet."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    if SHEET not in wb.sheetnames:
        raise ConfigError(f"{os.path.basename(path)} has no '{SHEET}' sheet (it has: {', '.join(wb.sheetnames)})")
    rows = wb[SHEET].iter_rows(values_only=True)
    names = None
    out = []
    for n, row in enumerate(rows, 1):
        if n < HEADER_ROW:
            continue
        if n == HEADER_ROW:
            names = [_str(c).lower() for c in row]
            continue
        r = dict(zip(names, row))
        tx, rid = _id(r.get("transaction id")), _id(r.get("res. id"))
        if not tx or not rid or r.get("s.no.") in (None, ""):
            continue
        out.append({
            "res_id": rid, "transaction_id": tx, "occurred_at": _when(r.get("date and time")),
            "transaction_type": _str(r.get("transaction type")), "kind": _str(r.get("type")),
            "bill_amount": _num(r.get("bill amount")), "cover_charge": _num(r.get("cover charge")),
            "discount_type": _str(r.get("discount type")), "instant_discount": _num(r.get("instant discount")),
            "promo_share": _num(r.get("promo share")), "commissionable_amount": _num(r.get("commissionable amount")),
            "commission_pct": _num(r.get("commission %")), "commission_amount": _num(r.get("commission amount")),
            "tax_on_commission": _num(r.get("tax on commission")), "tips": _num(r.get("tips")),
            "adjustment_type": _str(r.get("adjustment type")), "adjustment": _num(r.get("adjustment")),
            "net_receivable": _num(r.get("net receivable")), "settlement_status": _str(r.get("settlement status")),
            "settlement_date": (_when(r.get("settlement date")) or None) and _when(r.get("settlement date")).date(),
            "utr_number": _str(r.get("utr number / reference id")), "remarks": _str(r.get("remarks")),
        })
    wb.close()
    return out


ADS_SHEET, ADS_HEADER_ROW = "Additions & deductions", 4


def parse_ads(path: str) -> list[dict]:
    """Ad charges and credits from the report's 'Additions & deductions' sheet (empty list if the sheet is missing)."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    if ADS_SHEET not in wb.sheetnames:
        wb.close()
        return []
    out, names = [], None
    for n, row in enumerate(wb[ADS_SHEET].iter_rows(values_only=True), 1):
        if n < ADS_HEADER_ROW:
            continue
        if n == ADS_HEADER_ROW:
            names = [_str(c).lower() for c in row]
            continue
        r = dict(zip(names, row))
        rid, amount = _id(r.get("res id")), _num(r.get("amount"))
        if not rid or amount is None or r.get("s.no.") in (None, ""):
            continue
        when = _when(r.get("date"))
        out.append({"res_id": rid, "kind": _str(r.get("type")).upper(), "campaign_id": _id(r.get("campaign id")), "order_id": _str(r.get("order id")),
                    "line_date": when.date() if when else None, "settlement_status": _str(r.get("settlement status")),
                    "utr_number": _str(r.get("utr number / reference id")) or _str(r.get("utr number / reference")), "amount": amount})
    wb.close()
    return out


AD_COLS = ["res_id", "kind", "campaign_id", "order_id", "line_date", "settlement_status", "utr_number", "amount"]


def save_ads(rows: list[dict], only: set[str] | None = None) -> int:
    if only:
        rows = [r for r in rows if r["res_id"] in only]
    unique = {(r["res_id"], r["kind"], r["campaign_id"], r["order_id"], r["line_date"], r["amount"]): r for r in rows}
    if not unique:
        return 0
    with db.transaction() as cur:
        cur.execute("SELECT zomato_res_id AS res_id, id FROM brand_outlets WHERE zomato_res_id IS NOT NULL")
        outlet = {str(x["res_id"]): x["id"] for x in cur.fetchall()}
        cur.executemany(f"""INSERT INTO dining_ad_lines (outlet_id, {', '.join(AD_COLS)}, updated_at) VALUES (%s, {', '.join(['%s'] * len(AD_COLS))}, now())
                            ON CONFLICT (res_id, kind, campaign_id, order_id, line_date, amount) DO UPDATE SET outlet_id = EXCLUDED.outlet_id,
                            settlement_status = EXCLUDED.settlement_status, utr_number = EXCLUDED.utr_number, updated_at = now()""",
                        [(outlet.get(r["res_id"]), *[r[c] for c in AD_COLS]) for r in unique.values()])
    return len(unique)


COLS = ["res_id", "transaction_id", "occurred_at", "transaction_type", "kind", "bill_amount", "cover_charge", "discount_type",
        "instant_discount", "promo_share", "commissionable_amount", "commission_pct", "commission_amount", "tax_on_commission",
        "tips", "adjustment_type", "adjustment", "net_receivable", "settlement_status", "settlement_date", "utr_number", "remarks"]


def save(rows: list[dict], only: set[str] | None = None) -> int:
    """Upsert rows (only for the wanted res ids when given). Returns how many were written."""
    if only:
        rows = [r for r in rows if r["res_id"] in only]
    unique = {(r["transaction_id"], r["res_id"]): r for r in rows}  # a report can repeat a line
    if not unique:
        return 0
    with db.transaction() as cur:
        cur.execute("SELECT zomato_res_id AS res_id, id FROM brand_outlets WHERE zomato_res_id IS NOT NULL")
        outlet = {str(x["res_id"]): x["id"] for x in cur.fetchall()}
        sql = f"""INSERT INTO dining_payout_transactions (outlet_id, {', '.join(COLS)}, updated_at)
                  VALUES (%s, {', '.join(['%s'] * len(COLS))}, now())
                  ON CONFLICT (transaction_id, res_id) DO UPDATE SET outlet_id = EXCLUDED.outlet_id,
                  {', '.join(f'{c} = EXCLUDED.{c}' for c in COLS if c not in ('transaction_id', 'res_id'))}, updated_at = now()"""
        cur.executemany(sql, [(outlet.get(r["res_id"]), *[r[c] for c in COLS]) for r in unique.values()])
    return len(unique)


# ---- asking Zomato for the report, and fetching it from the mailbox ---------------------------------------------

def _mailbox():
    user, pw = os.getenv("DINING_REPORT_EMAIL", "").strip(), os.getenv("DINING_REPORT_PASSWORD", "").strip()
    if not user or not pw:
        raise ConfigError("Set DINING_REPORT_EMAIL and DINING_REPORT_PASSWORD in the collector .env: the mailbox Zomato emails the report to")
    return user, pw, os.getenv("DINING_REPORT_IMAP_HOST", "imap.secureserver.net")


def trigger(cookies: dict, res_ids: list[str], start: str, end: str, recipient: str) -> bool:
    csrf = cookies.get("csrf", "")
    headers = {
        "Content-Type": "application/json", "Accept": "application/json, text/plain, */*", "Origin": SITE,
        "User-Agent": cfg.user_agent(), "x-zomato-app-version": "2", "x-client-id": "zomato_web_merchant",
        "x-zomato-csrft": csrf, "x-zomato-zdcsrf-token": cookies.get("__Host-zdcsrft", ""),
        "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
        "Referer": f"{SITE}/partners/go-out/dining/payouts/consolidated-statement?resId={res_ids[0]}",
    }
    body = {"res_ids": [str(r) for r in res_ids], "recipient_email_id": recipient, "start_date": start, "end_date": end, "res_id": int(res_ids[0])}
    resp = requests.post(GENERATE_URL, headers=headers, json=body, timeout=cfg.http_timeout())
    if resp.status_code in (401, 403):
        raise PermissionError("Zomato web login refused the dining report request; refresh this account's session")
    try:
        ok = resp.status_code == 200 and resp.json().get("status") == "success"
    except ValueError:
        ok = False
    if not ok:
        log.warning("zomato dining_payouts: Zomato did not accept the %s to %s report (%s %s)", start, end, resp.status_code, resp.text[:200])
    return ok


def fetch_reports(since: datetime, expected: int, wait_sec: int = 30, tries: int = 20) -> list[str]:
    """Download the report attachments that arrived after `since`. Returns file paths."""
    user, pw, host = _mailbox()
    saved, seen = [], set()
    for attempt in range(1, tries + 1):
        try:
            imap = imaplib.IMAP4_SSL(host, 993)
            imap.login(user, pw)
            imap.select("INBOX")
            _, found = imap.search(None, f'(SINCE "{(since - timedelta(days=1)).strftime("%d-%b-%Y")}" SUBJECT "{SUBJECT}")')
            for eid in reversed(found[0].split()):
                if eid in seen:
                    continue
                _, data = imap.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                sent = parsedate_to_datetime(msg.get("Date"))
                if sent.timestamp() < since.timestamp() - 120:
                    continue
                seen.add(eid)
                for part in msg.walk():
                    name = part.get_filename()
                    if not name:
                        continue
                    raw, enc = decode_header(name)[0]
                    name = raw.decode(enc or "utf-8") if isinstance(raw, bytes) else raw
                    if name.lower().endswith((".xlsx", ".xls")):
                        path = os.path.join(tempfile.mkdtemp(prefix="dining_report_"), re.sub(r"[^\w.\-]", "_", name))
                        with open(path, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        saved.append(path)
            imap.logout()
        except Exception as e:
            log.warning("zomato dining_payouts: mailbox check %s/%s failed: %s", attempt, tries, e)
        if len(saved) >= expected:
            return saved
        time.sleep(wait_sec)
    return saved


def windows(start: date, end: date) -> list[tuple[str, str]]:
    out, s = [], start
    while s <= end:
        e = min(end, s + timedelta(days=WINDOW_DAYS - 1))
        out.append((s.isoformat(), e.isoformat()))
        s = e + timedelta(days=1)
    return out


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    require_env("SOCIALSPORK_DATABASE_URL")
    only = cfg.only_res_ids()
    if not only:
        log.error("zomato dining_payouts: pass --res-id with the dining outlets (this report is per outlet)")
        return False
    start, end = cfg.date_range(date.today() - timedelta(days=150), date.today() - timedelta(days=1))
    user, _, _ = _mailbox()
    with db.transaction() as cur:
        acc = db.get_account(cur, "zomato", accounts[0])
    cookies = _cookies(db.load_credentials(acc))
    started, expected = datetime.now().astimezone(), 0
    for s, e in windows(start, end):
        if trigger(cookies, sorted(only), s, e, user):
            expected += 1
            log.info("zomato dining_payouts: asked Zomato for %s to %s (%d outlets)", s, e, len(only))
        time.sleep(10)
    if not expected:
        return False
    files = fetch_reports(started, expected)
    saved = 0
    for f in files:
        rows = parse_report(f)
        n = save(rows, only)
        ads = save_ads(parse_ads(f), only)
        saved += n
        log.info("zomato dining_payouts: %s: %d of its %d bills and %d ad lines are for these outlets", os.path.basename(f), n, len(rows), ads)
    log.info("zomato dining_payouts: %d reports of %d expected, %d bills saved", len(files), expected, saved)
    return len(files) >= expected


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "fetch":  # collect reports already emailed in the last N minutes, without asking Zomato again
        minutes = int(sys.argv[sys.argv.index("--minutes") + 1]) if "--minutes" in sys.argv else 60
        only = {x.strip() for x in sys.argv[sys.argv.index("--res-id") + 1].split(",") if x.strip()} if "--res-id" in sys.argv else set()
        files = fetch_reports(datetime.now().astimezone() - timedelta(minutes=minutes), expected=1, tries=3)
        total = 0
        for f in files:
            n = save(parse_report(f), only or None)
            ads = save_ads(parse_ads(f), only or None)
            total += n
            print(f"{os.path.basename(f)}: saved {n} bills and {ads} ad lines")
        print(f"{len(files)} reports found, {total} bills saved")
    elif len(sys.argv) >= 3 and sys.argv[1] == "load":
        only = set()
        if "--res-id" in sys.argv:
            only = {x.strip() for x in sys.argv[sys.argv.index("--res-id") + 1].split(",") if x.strip()}
        rows = parse_report(sys.argv[2])
        print(f"{len(rows)} lines in the report; saved {save(rows, only or None)} bills and {save_ads(parse_ads(sys.argv[2]), only or None)} ad lines" + (f" for {len(only)} outlets" if only else ""))
    else:
        print("usage: python -m zomato.dining_payouts load <report.xlsx> [--res-id 111,222]")
