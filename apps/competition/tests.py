import json
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from . import markets, swiggy, zomato

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


class ZomatoResInfo(SimpleTestCase):
    """The restaurant info page: cuisines and the weekly timings, as the app lays them out for display."""

    ANSWER = {"results": [
        {"v4_image_text_snippet_type_3": {"items": [{"title": {"text": "Test Kitchen"}, "subtitle1": {"text": "Mughlai · Chinese · Beverages · ₹350 for one"},
                                                       "subtitle2": {"text": "Lane 3, Saket, New Delhi"}}]}},
        {"accordion_snippet_type_14": {"title": {"text": "<regular-300|{green-500|Open now}> • Closes 11:59 pm"}, "expanded_state": {"subtitle_list": [
            {"subtitle1": {"text": "Monday"}, "subtitle2": {"text": "12:00 am - 1:00 am"}},
            {"subtitle1": {"text": " "}, "subtitle2": {"text": "11:30 am - 11:59 pm"}},
            {"subtitle1": {"text": "Tuesday"}, "subtitle2": {"text": "11:30 am - 11:59 pm"}}]}}},
        {"v4_image_text_snippet_type_3": {"items": [{"top_title": {"text": "Provides both delivery & dining"}}]}},
        {"text_snippet_type_5": {"title": {"text": "GST Number"}, "subtitle1": {"text": "07XXXXXXXXXX1ZH"}}}]}

    def test_cuisines_price_and_address(self):
        r = zomato.parse_res_info(self.ANSWER)
        self.assertEqual((r["name"], r["cuisines"], r["cost_text"]), ("Test Kitchen", ["Mughlai", "Chinese", "Beverages"], "₹350 for one"))
        self.assertEqual(r["address"], "Lane 3, Saket, New Delhi")
        self.assertTrue(r["delivery_and_dining"])

    def test_open_status_has_no_markup(self):
        self.assertEqual(zomato.parse_res_info(self.ANSWER)["open_text"], "Open now • Closes 11:59 pm")

    def test_a_second_slot_belongs_to_the_day_above(self):
        t = zomato.parse_res_info(self.ANSWER)["timings"]
        self.assertEqual(t, [{"day": "Monday", "slots": ["12:00 am - 1:00 am", "11:30 am - 11:59 pm"]}, {"day": "Tuesday", "slots": ["11:30 am - 11:59 pm"]}])

    def test_legal_and_tax_details_are_not_kept(self):
        self.assertNotIn("07XXXXXXXXXX1ZH", str(zomato.parse_res_info(self.ANSWER)))

    def test_an_empty_answer_gives_empty_fields(self):
        r = zomato.parse_res_info({})
        self.assertEqual((r["cuisines"], r["timings"], r["open_text"]), ([], [], ""))
