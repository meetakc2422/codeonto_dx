"""Order history parsing. The rows below are made up (no customer data). Run from collector/:
    ./.venv/bin/python -m unittest tests.test_orders
"""

import sys
import unittest
from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zomato import orders  # noqa: E402

HEAD = "Restaurant ID,Order ID,Order Placed At,Order Status,Items in order,Bill subtotal,Total,Cancellation / Rejection reason,Customer ID,Customer Phone"
CSV = "\n".join([
    HEAD,
    '111,9001,"09:15 PM, November 10 2026",Delivered,"1 x Butter Chicken, 2 x Garlic Naan, 1 x Dal, Makhani (Large)",1530,1155,,555,9999999999',
    '111,9002,"06:26 PM, November 10 2026",Delivered,1 x Malai Tikka,640,545,,556,9999999998',
    '111,9003,"12:24 AM, November 10 2026",Rejected,2 x Malai Tikka,1280,1000,Restaurant is closed,557,9999999997',
    '222,9004,"07:00 PM, November 10 2026",Delivered,1 x Other Store Item,100,100,,558,9999999996',
    '111,9005,"not a time",Delivered,1 x Bad Row,100,100,,559,9999999995',
    '111,9006,"01:00 PM, November 10 2026",Delivered,,100,100,,560,9999999994',
])


class Parsing(unittest.TestCase):
    def test_items_and_quantities(self):
        self.assertEqual(orders.parse_items("1 x Butter Chicken, 2 x Garlic Naan"), [("Butter Chicken", 1), ("Garlic Naan", 2)])
        self.assertEqual(orders.parse_items("1 x Dal, Makhani (Large), 1 x Rice"), [("Dal, Makhani (Large)", 1), ("Rice", 1)])
        self.assertEqual(orders.parse_items("1 x Naan, 2 x Naan"), [("Naan", 3)])
        self.assertEqual(orders.parse_items(""), [])

    def test_time_is_india_time(self):
        t = orders.parse_time("09:15 PM, November 10 2026")
        self.assertEqual((t.hour, t.minute, t.utcoffset().total_seconds()), (21, 15, 19800))
        self.assertIsNone(orders.parse_time("nonsense"))

    def test_report_rows_keep_no_customer_fields(self):
        rows = orders.parse_report(CSV, {"111": 7})
        self.assertEqual({r["order_id"] for r in rows}, {"9001", "9002", "9003"})  # other store, bad time and empty items skipped
        for r in rows:
            self.assertFalse({"Customer ID", "Customer Phone", "customer", "phone"} & set(r))
            self.assertNotIn("9999999", " ".join(str(v) for v in r.values()))
        multi = [r for r in rows if r["order_id"] == "9001"]
        self.assertEqual([(r["item"], r["qty"], r["unit_price"]) for r in multi],
                         [("Butter Chicken", 1, None), ("Garlic Naan", 2, None), ("Dal, Makhani (Large)", 1, None)])
        single = next(r for r in rows if r["order_id"] == "9002")
        self.assertEqual((single["unit_price"], single["subtotal"], single["total"]), (D("640.00"), D("640"), D("545")))
        late = next(r for r in rows if r["order_id"] == "9003")
        self.assertEqual((late["status"], late["reason"], late["order_date"]), ("Rejected", "Restaurant is closed", date(2026, 11, 9)))
        self.assertEqual(late["unit_price"], D("640.00"))  # 1280 / 2

    def test_windows_cover_the_range_once(self):
        spans = orders.windows(date(2026, 11, 1), date(2026, 11, 16))
        self.assertEqual(spans[0][0], date(2026, 11, 1))
        self.assertEqual(spans[-1][1], date(2026, 11, 16))
        days = [(b - a).days + 1 for a, b in spans]
        self.assertEqual(sum(days), 16)
        self.assertTrue(all(d <= orders.CHUNK_DAYS for d in days))

    def test_user_ids(self):
        import os
        os.environ["ORDER_USER_IDS"] = "main:381, bad:x ,other:77"
        self.assertEqual(orders.user_ids(), {"main": "381", "other": "77"})
        os.environ.pop("ORDER_USER_IDS")


if __name__ == "__main__":
    unittest.main()
