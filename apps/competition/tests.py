import json
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from . import markets, swiggy

CARD = json.loads((Path(__file__).parent / "test_data" / "swiggy_restaurant_card.json").read_text())["574401"]
SPOT = {"lat": 28.6461, "lng": 77.3666, "city_id": "10459", "city": "Noida 1"}


def _rows(*names_ids):
    return [{"res_id": i, "name": n, "rating": 4.0, "distance_km": d, "delivery_time": "30-35 mins", "area": "A", "address": "", "ratings": "",
             "cost_for_two": "", "cuisines": [], "serviceable": True, "closed_note": "", "locality": "", "city_id": ""} for i, n, d in names_ids]


class SwiggySearchCard(SimpleTestCase):
    def test_reads_a_real_restaurant_card(self):
        r = swiggy.parse_restaurant_card(CARD)
        self.assertEqual(r["res_id"], "574401")
        self.assertEqual(r["name"], "Kake Da Hotel since 1931")
        self.assertEqual(r["area"], "Indirapuram")
        self.assertIn("windsor park", r["address"])
        self.assertEqual(r["rating"], 4.2)
        self.assertEqual(r["ratings"], "3.8K+")
        self.assertIn("North Indian", r["cuisines"])
        self.assertTrue(r["serviceable"])
        self.assertTrue(r["distance_km"])

    def test_garbage_is_skipped_not_raised(self):
        for bad in ("", "abc", "ﾋ\x06\x05", CARD[:40]):
            self.assertIsNone(swiggy.parse_restaurant_card(bad))


class SwiggyAdapter(SimpleTestCase):
    def test_names_puts_the_nearest_matching_branch_first(self):
        rows = _rows(("1", "Other Place", 0.5), ("395126", "Kake Da Hotel Since 1931", 17.5), ("574401", "Kake Da Hotel since 1931", 1.5))
        with mock.patch.object(swiggy, "search_restaurants", return_value=rows):
            self.assertEqual(markets.Swiggy.names(SPOT, "Kake Da Hotel")[0][0], "574401")

    def test_falls_back_to_suggest_when_search_fails(self):
        sug = [{"res_id": "395126", "name": "Kake Da Hotel", "rating": 4.1, "delivery_time": "", "area": ""}]
        with mock.patch.object(swiggy, "search_restaurants", side_effect=swiggy.SwiggyAppError("boom")), \
                mock.patch.object(swiggy, "suggest", return_value=sug):
            self.assertEqual(markets.Swiggy.names(SPOT, "Kake"), [("395126", "Kake Da Hotel")])
            q, total, rows = markets.Swiggy.search(SPOT, "Kake")
            self.assertEqual([r["res_id"] for r in rows], ["395126"])

    def test_falls_back_when_search_finds_nothing(self):
        sug = [{"res_id": "7", "name": "Biryani Blues", "rating": 4.2, "delivery_time": "", "area": ""}]
        with mock.patch.object(swiggy, "search_restaurants", return_value=[]), mock.patch.object(swiggy, "suggest", return_value=sug):
            self.assertEqual(markets.Swiggy.search(SPOT, "biryani")[2][0]["res_id"], "7")

    def test_search_caps_the_list(self):
        rows = _rows(*[(str(i), f"R{i}", 1.0) for i in range(100)])
        with mock.patch.object(swiggy, "search_restaurants", return_value=rows):
            self.assertEqual(len(markets.Swiggy.search(SPOT, "x")[2]), 40)
