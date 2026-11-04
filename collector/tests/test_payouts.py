"""Payout parsing and checks. The statement and sums below come from a real Zomato cycle. Run from collector/:
    ./.venv/bin/python -m unittest tests.test_payouts
"""

import io
import os
import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from zomato.payouts import ReportFormatChanged, money, parse_cycle_dates, parse_cycle_row, parse_details, parse_payout_date, parse_report, reconcile, save  # noqa: E402


def section(sid, label, value, items=()):
    return {"id": sid, "data": {"label": {"value": label}, "content": {"value": value}},
            "expandedData": [{"label": {"value": k}, "content": {"value": v}} for k, v in items]}


DETAILS = {"status": "success", "cardConfig": [
    {"type": "payout_info_card", "data": {"summaryData": [{"id": "est_payout", "data": {"content": {"title": {"value": "₹10,643.24"}}}}]}},
    {"type": "summary_accordion_card", "data": {"summaryData": [section("total_orders", "Total orders", "2", [("Delivered orders", "2"), ("Rejected orders", "0")])]}},
    {"type": "summary_accordion_card", "data": {"summaryData": [
        section("total_order_value", "Net order value (A)", "₹15,561.89", [("Item subtotal", "₹17,874.00")]),
        section("additions", "Additions (B)", "₹0.00"),
        section("order_level_deductions", "Order level deductions (C)", "- ₹2,016.10"),
        section("tax_deductions", "Tax deductions (D)", "- ₹1,118.77"),
        section("investments_in_growth", "Investments in growth (E)", "- ₹739.86", [("Online ordering ads", "- ₹739.86")]),
        section("hyperpure_deductions", "Hyperpure spend (F)", "- ₹1,043.92"),
        section("estimated_net_payout", "Est. payout", "₹10,643.24"),
    ]}},
    {"type": "transaction_details_card", "data": {"summaryData": [
        {"id": "utr", "data": {"content": {"value": "UTR123"}}},
        {"id": "account_number", "data": {"content": {"title": {"value": "SECRET-ACCOUNT"}, "subtitle": {"value": "SECRET-BANK"}}}},
    ]}},
]}


def order(**over):
    base = dict(order_id="1", order_date=None, status="DELIVERED", payment_mode="ONLINE", discount_construct="", subtotal=D(0), packaging_charge=D(0),
                restaurant_discount=D(0), gst_collected=D(0), net_order_value=D("15561.89"), commissionable_value=D("1000"), base_fee_pct=D("10.8"), service_fee_pct=D("10.8"),
                service_fee=D("108"), payment_fee=D(0), fees_total=D(0), government_charges=D(0), other_deductions=D(0), net_deductions=D("3134.87"),
                net_additions=D(0), payout=D("12427.02"), settlement_status="settled", settlement_date=None, bank_utr="", unsettled_amount=D(0))
    return {**base, **over}


def workbook(headers=None, rows=None, sheet="Order Level"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for _ in range(6):
        ws.append(["intro"])
    headers = headers or ["S.no.", "Order ID", "Order date", "Order status (Delivered/ Cancelled/ Rejected)", "Mode of payment", "Subtotal\n(items total)",
                          "Restaurant discount (Promo)", "Restaurant discount (BOGO, Freebies, Gold, Brand pack & others)", "Net order value", "Total commissionable value", "Base service fee %",
                          "Total service fee %", "Total service fee", "Net Deductions", "Net Additions", "Order level Payout", "Settlement status",
                          "Settlement date", "Bank UTR", "Unsettled amount", "Customer ID"]
    ws.append(headers)
    ws.append(["#REF!", "#REF!", "#REF!"])
    for r in rows if rows is not None else [[1, 8794482796, "2026-11-01 00:34:48", "DELIVERED", "ONLINE", 445.0, 56.0, 0.0, 439.95, 419.0, 10.8, 10.8, 45.252, 84.3186, 0.0, 355.6314, "settled", "2026-11-04", "UTR123", 0.0, "CUST-SECRET"]]:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class Parsing(unittest.TestCase):
    def test_money(self):
        self.assertEqual(money("- ₹1,238.49"), D("-1238.49"))
        self.assertEqual(money("₹10,643.24"), D("10643.24"))
        self.assertIsNone(money(None))
        self.assertIsNone(money("-"))

    def test_cycle_dates(self):
        self.assertEqual(parse_cycle_dates("04 - 10 May'26"), (date(2026, 5, 4), date(2026, 5, 10)))
        self.assertEqual(parse_cycle_dates("28 Oct - 30 Oct'26"), (date(2026, 10, 28), date(2026, 10, 30)))
        self.assertEqual(parse_cycle_dates("28 Apr - 03 May'26"), (date(2026, 4, 28), date(2026, 5, 3)))
        self.assertEqual(parse_cycle_dates("29 Dec - 04 Jan'27"), (date(2026, 12, 29), date(2027, 1, 4)))
        self.assertIsNone(parse_cycle_dates("rubbish"))
        self.assertIsNone(parse_cycle_dates("40 - 41 Zzz'26"))

    def test_payout_date(self):
        self.assertEqual(parse_payout_date("04 Nov'26"), date(2026, 11, 4))
        self.assertEqual(parse_payout_date("04 Nov'26, by 9PM"), date(2026, 11, 4))
        self.assertIsNone(parse_payout_date(None))

    def test_cycle_row(self):
        c = parse_cycle_row({"payout_cycle": {"value": "27 Oct - 27 Oct'26"}, "payout_date": {"value": "30 Oct'26"}, "payout": {"value": "₹5,000.50"},
                             "orders": {"value": "17"}, "status": {"value": {"label": {"value": "Paid"}}}, "utr": {"value": "U1"}})
        self.assertEqual((c["status"], c["utr"], c["net_payout"], c["order_count"], c["payout_date_raw"]), ("PAID", "U1", D("5000.50"), 17, "30 Oct'26"))
        self.assertEqual(parse_cycle_row({"payout_cycle": {"value": "27 Oct - 27 Oct'26"}, "utr": {"value": "-"}})["utr"], "")

    def test_details_keep_the_statement_and_drop_the_bank_account(self):
        d = parse_details(DETAILS)
        self.assertEqual((d["net_payout"], d["utr"], d["order_count"], d["delivered_orders"]), (D("10643.24"), "UTR123", 2, 2))
        self.assertEqual([s["id"] for s in d["breakdown"]], ["total_order_value", "additions", "order_level_deductions", "tax_deductions", "investments_in_growth", "hyperpure_deductions"])
        self.assertNotIn("SECRET", str(d))

    def test_report(self):
        rows = parse_report(workbook())
        self.assertEqual(len(rows), 1)  # the #REF! line is skipped
        o = rows[0]
        self.assertEqual((o["order_id"], o["payout"], o["status"], o["bank_utr"], o["settlement_date"]), ("8794482796", D("355.6314"), "DELIVERED", "UTR123", date(2026, 11, 4)))
        self.assertEqual(o["restaurant_discount"], D("56.0"))
        self.assertEqual(o["order_date"].isoformat(), "2026-11-01T00:34:48+05:30")
        self.assertNotIn("SECRET", str(o))

    def test_report_na_and_missing_values(self):
        o = parse_report(workbook(rows=[[1, 5, "NA", "DELIVERED", "NA", None, 0, 0, 10, 0, 0, 0, 0, 1, 0, 9, "pending", "NA", "NA", 9, "x"]]))[0]
        self.assertEqual((o["order_date"], o["settlement_date"], o["bank_utr"], o["payment_mode"], o["subtotal"]), (None, None, "", "", D(0)))

    def test_newest_report_format(self):
        headers = ["Order ID", "Order date", "Order status (Delivered/ Cancelled/ Rejected)", "Restaurant discount [Promo]", "Restaurant discount [BOGO, Freebies, Gold, Brand pack & others]",
                   "Commissionable value (excludes customer GST)", "Service fees %", "Service fee", "Service fee & payment mechanism fees", "Net order value", "Net Deductions", "Net Additions", "Order level Payout", "Settlement status"]
        o = parse_report(workbook(headers=headers, rows=[[5, "2026-10-27 10:00:00", "DELIVERED", 5, 2, 100, 12, 12, 14, 100, 20, 0, 80, "settled"]]))[0]
        self.assertEqual((o["commissionable_value"], o["base_fee_pct"], o["service_fee_pct"], o["service_fee"], o["fees_total"], o["restaurant_discount"]), (D(100), D(12), D(12), D(12), D(14), D(7)))

    def test_older_report_without_distance_fee_columns(self):
        headers = ["Order ID", "Order date", "Order status (Delivered/ Cancelled/ Rejected)", "Total commissionable value", "Base service fee %", "Base service fee", "Net order value", "Net Deductions", "Net Additions", "Order level Payout", "Settlement status"]
        o = parse_report(workbook(headers=headers, rows=[[5, "2026-05-01 10:00:00", "DELIVERED", 100, 10.8, 10.8, 100, 20, 0, 80, "settled"]]))[0]
        self.assertEqual((o["base_fee_pct"], o["service_fee_pct"], o["service_fee"]), (D("10.8"), D("10.8"), D("10.8")))

    def test_changed_report_is_refused_not_guessed(self):
        with self.assertRaises(ReportFormatChanged):
            parse_report(workbook(sheet="Orders"))
        with self.assertRaises(ReportFormatChanged):
            parse_report(workbook(headers=["Order ID", "Net order value"], rows=[]))
        with self.assertRaises(ReportFormatChanged):
            parse_report(workbook(headers=["Something else"], rows=[]))


class Checks(unittest.TestCase):
    def statement(self, **over):
        return {**parse_details(DETAILS), "order_count": 1, **over}

    def test_real_cycle_matches_to_the_paisa(self):
        r = reconcile(self.statement(), [order()])
        self.assertEqual((r["orders_total"], r["adjustments"], r["expected_payout"], r["discrepancy"]), (D("12427.02"), D("-1783.78"), D("10643.24"), D("0.00")))
        self.assertEqual(r["issues"], [])

    def test_short_payment_is_flagged(self):
        r = reconcile(self.statement(net_payout=D("10000.00")), [order()])
        self.assertEqual(r["discrepancy"], D("-643.24"))
        self.assertIn("payout_mismatch", r["issues"])

    def test_rupee_of_rounding_is_fine(self):
        self.assertNotIn("payout_mismatch", reconcile(self.statement(net_payout=D("10643.90")), [order()])["issues"])

    def test_missing_order_is_flagged(self):
        self.assertIn("order_count_mismatch", reconcile(self.statement(order_count=2), [order()])["issues"])

    def test_order_payout_math(self):
        o = order(payout=D("12000"))
        self.assertIn("order_payout_math", reconcile(self.statement(), [o])["issues"])
        self.assertEqual(o["issues"], ["order_payout_math"])

    def test_order_fee_math(self):
        o = order(service_fee=D("200"))
        self.assertIn("order_fee_math", reconcile(self.statement(), [o])["issues"])

    def test_unusual_fee_rate_flags_only_the_odd_order(self):
        usual = [order(order_id=str(i), net_order_value=D(0), net_deductions=D(0), payout=D(0)) for i in range(3)]
        odd = order(order_id="9", base_fee_pct=D("25"), service_fee_pct=D("25"), service_fee=D("250"), net_order_value=D(0), net_deductions=D(0), payout=D(0))
        r = reconcile(self.statement(), [*usual, odd])
        self.assertIn("fee_rate_changed", r["issues"])
        self.assertEqual((usual[0]["issues"], odd["issues"]), ([], ["fee_rate_changed"]))

    def test_distance_fee_is_not_a_rate_change(self):
        far = order(order_id="2", service_fee_pct=D("13.8"), service_fee=D("138"), net_order_value=D(0), net_deductions=D(0), payout=D(0))
        self.assertEqual(reconcile(self.statement(order_count=2), [order(), far])["issues"], [])

    def test_cancelled_order_pays_only_its_refund(self):
        c = order(order_id="3", status="CANCELLED", net_order_value=D("478"), net_deductions=D(0), net_additions=D("372.97"), payout=D("372.97"), commissionable_value=D(0), base_fee_pct=D(0), service_fee_pct=D(0), service_fee=D(0))
        reconcile(self.statement(order_count=2), [order(), c])
        self.assertEqual(c["issues"], [])
        c = {**c, "payout": D("100")}
        reconcile(self.statement(order_count=2), [order(), c])
        self.assertEqual(c["issues"], ["order_payout_math"])

    def test_carried_forward_total_line_is_not_counted(self):
        s = self.statement()
        s["breakdown"] = [*s["breakdown"], {"id": "estimated_net_payout_with_non_zero_md", "label": "Est.", "value": -404.28, "items": []}, {"id": "miscellaneous_deductions", "label": "Misc", "value": -10.0, "items": []}]
        self.assertEqual(reconcile({**s, "net_payout": D("10633.24")}, [order()])["adjustments"], D("-1793.78"))

    def test_paid_with_money_but_no_utr_is_flagged(self):
        self.assertIn("paid_without_utr", reconcile(self.statement(utr=""), [order()])["issues"])
        zero = reconcile(self.statement(utr="", net_payout=D("0")), [order(net_order_value=D("1783.78"), net_deductions=D(0), payout=D("1783.78"))])
        self.assertNotIn("paid_without_utr", zero["issues"])
        self.assertEqual(zero["discrepancy"], D("0.00"))

    def test_rejected_order_with_no_commission_doesnt_set_the_rate(self):
        cancelled = order(order_id="8", commissionable_value=D(0), base_fee_pct=D(0), service_fee_pct=D(0), service_fee=D(0), net_order_value=D(0), net_deductions=D(0), payout=D(0))
        self.assertEqual(reconcile(self.statement(order_count=2), [order(), cancelled])["issues"], [])

    def test_paid_with_unsettled_orders(self):
        self.assertIn("unsettled_orders", reconcile(self.statement(), [order(unsettled_amount=D("100"))])["issues"])

    def test_additions_not_on_order_rows_count_as_adjustments(self):
        s = self.statement()
        s["breakdown"] = [{**b, "value": 50.0} if b["id"] == "additions" else b for b in s["breakdown"]]
        r = reconcile({**s, "net_payout": D("10693.24")}, [order()])
        self.assertEqual((r["adjustments"], r["discrepancy"]), (D("-1733.78"), D("0.00")))

    def test_missing_net_payout_is_flagged_not_assumed_fine(self):
        r = reconcile(self.statement(net_payout=None), [order()])
        self.assertIsNone(r["discrepancy"])
        self.assertIn("payout_mismatch", r["issues"])


class Saving(unittest.TestCase):
    """On the real database, in a transaction that is always rolled back."""

    def setUp(self):
        self.conn = psycopg.connect(os.environ["CODEONTO_DATABASE_URL"], row_factory=dict_row)
        self.addCleanup(self.conn.close)
        self.addCleanup(self.conn.rollback)
        self.cur = self.conn.cursor()
        self.cur.execute("SELECT id FROM industries LIMIT 1")
        industry = self.cur.fetchone()["id"]
        now = datetime.now(timezone.utc)
        self.now = now
        self.cur.execute("INSERT INTO clients (name, contact_name, contact_email, contact_phone, is_active, created_at, updated_at) VALUES ('zz payouts', '', '', '', true, %s, %s) RETURNING id", (now, now))
        client = self.cur.fetchone()["id"]
        self.cur.execute("INSERT INTO brands (client_id, name, logo_url, industry_id, is_active, created_at, updated_at) VALUES (%s, 'zz', '', %s, true, %s, %s) RETURNING id", (client, industry, now, now))
        brand = self.cur.fetchone()["id"]
        self.cur.execute("INSERT INTO brand_outlets (brand_id, outlet_name, area, city, address, is_active, created_at, updated_at) VALUES (%s, 'zz', '', '', '', true, %s, %s) RETURNING id", (brand, now, now))
        self.outlet = self.cur.fetchone()["id"]
        self.cycle = {"start_date": date(2026, 11, 1), "end_date": date(2026, 11, 1), "payout_date": date(2026, 11, 4), "payout_date_raw": "04 Nov'26",
                      "status": "TO BE PAID", "utr": "", "net_payout": D("10643.24"), "order_count": 1}
        self.statement = {**parse_details(DETAILS), "order_count": 1}

    def row(self):
        self.cur.execute("SELECT * FROM payout_cycles WHERE outlet_id = %s", (self.outlet,))
        rows = self.cur.fetchall()
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_unpaid_cycle_is_stored_unchecked_then_checked_once_paid(self):
        save(self.cur, self.outlet, self.cycle, self.statement, None, self.now)
        r = self.row()
        self.assertEqual((r["status"], r["net_payout"], r["expected_payout"], r["reconciled_at"]), ("TO BE PAID", D("10643.24"), None, None))
        cycle_id = save(self.cur, self.outlet, {**self.cycle, "status": "PAID"}, self.statement, [order()], self.now)
        r = self.row()
        self.assertEqual((r["status"], r["utr"], r["expected_payout"], r["discrepancy"], r["issues"]), ("PAID", "UTR123", D("10643.24"), D("0.00"), []))
        self.assertIsNotNone(r["reconciled_at"])
        self.cur.execute("SELECT order_id, payout, issues FROM payout_orders WHERE cycle_id = %s", (cycle_id,))
        self.assertEqual(self.cur.fetchall(), [{"order_id": "1", "payout": D("12427.0200"), "issues": []}])

    def test_saving_again_replaces_orders_without_duplicates(self):
        cycle_id = save(self.cur, self.outlet, {**self.cycle, "status": "PAID"}, self.statement, [order()], self.now)
        save(self.cur, self.outlet, {**self.cycle, "status": "PAID"}, self.statement, [order(order_id="2")], self.now)
        self.cur.execute("SELECT order_id FROM payout_orders WHERE cycle_id = %s", (cycle_id,))
        self.assertEqual([r["order_id"] for r in self.cur.fetchall()], ["2"])


if __name__ == "__main__":
    unittest.main()
