"""Swiggy order history parsing. The orders below are made up (no customer data). Run from collector/:
    ./.venv/bin/python -m unittest tests.test_swiggy_orders
"""

import sys
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swiggy import orders  # noqa: E402


def order(order_id, ordered, items, status="delivered", reason=None, bill=0):
    return {"order_id": order_id, "bill": bill, "status": {"order_status": status, "ordered_time": ordered, "cancel_reason": reason},
            "cart": {"items": items}, "customerInfo": {"name": "Not Read", "phoneNumber": "9999999999"}}


def item(name, qty, total, addons=None):
    return {"name": name, "quantity": qty, "total": total, "sub_total": total, "addons": addons or [], "variants": []}


OBJECTS = [
    order(1001, "2026-11-12 20:15:00", [item("Classic Chicken Burger", 2, 490), item("Hot Sauce", 1, 69)], bill=640),
    order(1002, "2026-11-13 01:30:00", [item("Double Cheese Burger", 1, 464, addons=[{"name": "Extra Patty"}])], bill=520),
    order(1003, "2026-11-12 13:05:00", [item("Fries", 1, 99), item("Fries", 2, 198)], status="cancelled", reason="Item out of stock", bill=300),
    {"order_id": 1004, "status": {"ordered_time": "bad", "order_status": "delivered"}, "cart": {"items": [item("X", 1, 10)]}},
]


class Parse(unittest.TestCase):
    def setUp(self):
        self.rows = orders.parse_orders(OBJECTS, outlet_id=7)

    def by(self, order_id, name):
        return next(r for r in self.rows if r["order_id"] == order_id and r["item"] == name)

    def test_one_row_per_item_with_the_dish_price(self):
        r = self.by("1001", "Classic Chicken Burger")
        self.assertEqual((r["qty"], r["unit_price"], r["status"], r["mealtime"]), (2, D("245.00"), "Delivered", "Dinner"))

    def test_the_order_subtotal_and_total(self):
        r = self.by("1001", "Hot Sauce")
        self.assertEqual((r["subtotal"], r["total"]), (D("559.00"), D("640.00")))

    def test_a_line_with_add_ons_has_no_unit_price(self):
        self.assertIsNone(self.by("1002", "Double Cheese Burger")["unit_price"])

    def test_after_midnight_belongs_to_the_previous_service_day(self):
        self.assertEqual(self.by("1002", "Double Cheese Burger")["order_date"], date(2026, 11, 12))

    def test_the_same_item_twice_is_added_up(self):
        r = self.by("1003", "Fries")
        self.assertEqual((r["qty"], r["subtotal"]), (3, D("297.00")))
        self.assertEqual(sum(1 for x in self.rows if x["order_id"] == "1003"), 1)

    def test_a_cancelled_order_keeps_swiggys_reason(self):
        r = self.by("1003", "Fries")
        self.assertEqual((r["status"], r["reason"]), ("Cancelled", "Item out of stock"))
        self.assertEqual(self.by("1001", "Hot Sauce")["reason"], "")

    def test_a_bad_row_is_skipped_and_nothing_about_the_customer_is_kept(self):
        self.assertFalse(any(r["order_id"] == "1004" for r in self.rows))
        self.assertNotIn("Not Read", str(self.rows))
        self.assertNotIn("9999999999", str(self.rows))


if __name__ == "__main__":
    unittest.main()
