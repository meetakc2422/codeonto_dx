"""Swiggy payout parsing and checks, with figures from a real payout. Run from collector/:
    ./.venv/bin/python -m unittest tests.test_swiggy_payouts
"""

import io
import sys
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from openpyxl import Workbook  # noqa: E402

from swiggy.payouts import ReportFormatChanged, parse_annexure, parse_cycle, parse_details, reconcile  # noqa: E402

HEADERS = ["Order ID", "Parent Order ID", "Order Date", "Order Settlement Date", "Order Status", "Order Category", "Order Payment Type", "Coupon type applied by customer",
           "Item Total", "Packaging Charges", "Restaurant Discount Share [3a+3b]", "GST Collected", "Total Customer Paid [4+5]", "Commission charged on", "Service Fees %",
           "Commission", "Payment Collection Charges", "Total Swiggy Fees", "Complaint & Cancellation Charges", "Total Taxes", "Net Payout for Order (after taxes)", "Customer Name"]
ROW = [251232728110718, "", "2026-10-18 00:22:08", "28-10-2026", "delivered", "Swiggy", "prepaid", "DELULU", 269.0, 30.0, 130.0, 8.46, 177.46, 169.0, "14.0%", 23.66, 0.0, 27.92, 0.0, 8.62, 140.91, "SECRET NAME"]


def annexure(headers=HEADERS, rows=(ROW,), sheet="Order Level"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(["Order Level Breakup"])
    ws.append(["intro"])
    ws.append(headers)
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


DETAIL = {"payoutId": 138260064, "payoutDate": 1793147170, "orderCount": 1, "payoutStatus": {"state": "PAID"}, "payoutUTRs": ["AXIS1"], "netPayout": 140.91,
          "attachments": {"annexure": "https://x.test/a.xlsx"},
          "payoutSummary": [{"header": "(A) Total Customer Paid", "amount": 177.46, "subHeaders": [{"text": "Item Total", "amount": 269}]},
                            {"header": "(E) Growth Investments in Ads", "amount": 0, "subHeaders": []}, {"header": "(F) Other Charges & Refunds", "amount": 0, "subHeaders": []}]}


class SwiggyPayouts(unittest.TestCase):
    def test_cycle_uses_india_dates_and_pending_means_to_be_paid(self):
        c = parse_cycle({"payoutId": -97629901, "netPayout": 68047.36, "week": {"startDate": 1792866600, "endDate": 1793471399}, "payoutStatus": {"state": "PENDING"}})
        self.assertEqual((c["start_date"], c["end_date"], c["status"], c["net_payout"]), (date(2026, 10, 25), date(2026, 10, 31), "TO BE PAID", D("68047.36")))
        self.assertIsNone(parse_cycle({"payoutId": 1, "week": {}}))

    def test_details(self):
        d = parse_details(DETAIL)
        self.assertEqual((d["utr"], d["order_count"], d["net_payout"], d["annexure"]), ("AXIS1", 1, D("140.91"), "https://x.test/a.xlsx"))
        self.assertEqual(d["breakdown"][0]["id"], "total_customer_paid")

    def test_annexure(self):
        o = parse_annexure(annexure())[0]
        self.assertEqual((o["order_id"], o["status"], o["service_fee_pct"], o["payout"], o["settlement_date"], o["net_deductions"]),
                         ("251232728110718", "DELIVERED", D("14.0"), D("140.91"), date(2026, 10, 28), D("36.54")))
        self.assertNotIn("SECRET", str(o))

    def test_changed_annexure_is_refused(self):
        with self.assertRaises(ReportFormatChanged):
            parse_annexure(annexure(sheet="Orders"))
        with self.assertRaises(ReportFormatChanged):
            parse_annexure(annexure(headers=["Order ID", "Commission"], rows=()))

    def test_sums(self):
        r = reconcile(parse_details(DETAIL), parse_annexure(annexure()))
        self.assertEqual((r["expected_payout"], r["discrepancy"], r["issues"]), (D("140.91"), D("0.00"), []))

    def test_ads_count_as_adjustments(self):
        d = parse_details({**DETAIL, "netPayout": 100.91, "payoutSummary": [{"header": "(E) Growth Investments in Ads", "amount": -40, "subHeaders": []}]})
        r = reconcile(d, parse_annexure(annexure()))
        self.assertEqual((r["adjustments"], r["discrepancy"], r["issues"]), (D("-40.00"), D("0.00"), []))

    def test_short_payment_and_missing_utr(self):
        r = reconcile(parse_details({**DETAIL, "netPayout": 100, "payoutUTRs": []}), parse_annexure(annexure()))
        self.assertIn("payout_mismatch", r["issues"])
        self.assertIn("paid_without_utr", r["issues"])

    def test_cancelled_order_with_no_commission_is_not_flagged(self):
        cancelled = [*ROW]
        cancelled[0], cancelled[4], cancelled[13], cancelled[15], cancelled[17], cancelled[19], cancelled[20] = 9, "cancelled", 118.0, 0.0, 0.0, 0.0, 0.0
        r = reconcile({**parse_details(DETAIL), "order_count": 2}, parse_annexure(annexure(rows=(ROW, cancelled))))
        self.assertEqual(r["issues"], [])

    def test_rounding_in_the_rate_is_not_a_change(self):
        near = [*ROW]
        near[0], near[14] = 8, "14.000000000000002%"
        nearer = [*ROW]
        nearer[0], nearer[14], nearer[15] = 7, "13.98%", 23.63
        r = reconcile({**parse_details(DETAIL), "order_count": 3, "net_payout": D("422.73")}, parse_annexure(annexure(rows=(ROW, near, nearer))))
        self.assertEqual(r["issues"], [])

    def test_toing_rate_is_compared_with_toing_orders_only(self):
        toing = [*ROW]
        toing[0], toing[5], toing[14], toing[15] = 2, "Toing", "10%", 16.9
        orders = parse_annexure(annexure(rows=(ROW, [1, *ROW[1:]], toing)))
        self.assertNotIn("fee_rate_changed", reconcile({**parse_details(DETAIL), "order_count": 3, "net_payout": D("422.73")}, orders)["issues"])
        odd = [*ROW]
        odd[0], odd[14], odd[15] = 3, "30%", 50.7
        orders = parse_annexure(annexure(rows=(ROW, [1, *ROW[1:]], odd)))
        self.assertIn("fee_rate_changed", reconcile({**parse_details(DETAIL), "order_count": 3, "net_payout": D("422.73")}, orders)["issues"])


if __name__ == "__main__":
    unittest.main()
