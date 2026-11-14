"""Which menu items count as out of stock."""

import unittest

from zomato.stockouts import out_items


def wrap(name, variants=None, **cat):
    return {"catalogue": {"name": name, "catalogueId": 1, **cat},
            "variantWrappers": [{"variant": {"inStock": v}} for v in (variants if variants is not None else [True])]}


class OutItems(unittest.TestCase):
    def names(self, *wrappers):
        return sorted(i["item_name"] for i in out_items({"catalogueWrappers": list(wrappers)}))

    def test_switched_off_as_a_whole_is_out(self):
        self.assertEqual(self.names(wrap("Burger", autoTurnOnTime="2026-11-13")), ["Burger"])

    def test_one_variant_out_leaves_the_item_orderable(self):
        self.assertEqual(self.names(wrap("Burger", [True, False, True])), [])

    def test_every_variant_out_is_out(self):
        self.assertEqual(self.names(wrap("Burger", [False, False])), ["Burger"])

    def test_a_name_listed_twice_is_out_only_when_both_are(self):
        self.assertEqual(self.names(wrap("Burger", [False]), wrap("Burger", [True])), [])
        self.assertEqual(self.names(wrap("Burger", [False]), wrap("Burger", [False])), ["Burger"])

    def test_an_item_with_no_variants_and_no_switch_is_in_stock(self):
        self.assertEqual(self.names(wrap("Burger", [])), [])


if __name__ == "__main__":
    unittest.main()
