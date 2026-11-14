"""Which Swiggy menu items count as out of stock."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swiggy.stockouts import out_items  # noqa: E402


def entry(name, in_stock, enabled=1, active=True, **extra):
    return {"main_category_name": "Burgers", "item": {"name": name, "in_stock": in_stock, "enabled": enabled, "active": active,
                                                       "availability": {"next_change_time_text": "Unavailable"}, **extra}}


class OutItems(unittest.TestCase):
    def names(self, *entries):
        return sorted(i["item_name"] for i in out_items({"items_vo": list(entries)}))

    def test_enabled_and_not_in_stock_is_out(self):
        self.assertEqual(self.names(entry("Burger", 0)), ["Burger"])

    def test_in_stock_is_not_out(self):
        self.assertEqual(self.names(entry("Burger", 1)), [])

    def test_switched_off_on_purpose_is_not_a_stock_out(self):
        self.assertEqual(self.names(entry("Burger", 0, enabled=0), entry("Wrap", 0, active=False)), [])

    def test_a_name_listed_twice_is_out_only_when_both_are(self):
        self.assertEqual(self.names(entry("Burger", 0), entry("Burger", 1)), [])
        self.assertEqual(self.names(entry("Burger", 0), entry("Burger", 0)), ["Burger"])

    def test_unavailable_has_no_back_time(self):
        self.assertEqual(out_items({"items_vo": [entry("Burger", 0)]})[0]["back_at"], "")


if __name__ == "__main__":
    unittest.main()
