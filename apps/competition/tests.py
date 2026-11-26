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
        self.assertIn("RX_THUMBNAIL/IMAGES/VENDOR/2026/2/7/ce422778-4ed6-4729-a3e3-e7925d94feb9_574401.JPG", r["image"])
        self.assertTrue(r["image"].startswith("https://media-assets.swiggy.com/"))

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


class UpstreamErrorTests(SimpleTestCase):
    def test_a_platform_failure_shows_one_plain_sentence_and_no_internals(self):
        from .errors import FRIENDLY, upstream_error

        res = upstream_error(Exception("HTTPSConnectionPool(host='api.zomato.com', port=443): Max retries exceeded; set GOOGLE_API_KEY in .env"))
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.data["detail"], FRIENDLY)
        self.assertNotIn("zomato.com", str(res.data))
        self.assertNotIn(".env", str(res.data))


import httpx  # noqa: E402

from . import errors  # noqa: E402


def _resp(status, text="{}", headers=None):
    return httpx.Response(status, text=text, headers=headers or {}, request=httpx.Request("POST", "https://example.test"))


class ZomatoCallIsRobust(SimpleTestCase):
    """Zomato's answers change without warning: none of these may crash a page."""

    def setUp(self):
        patcher = mock.patch.object(zomato, "_headers", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)
        slept = mock.patch.object(errors.time, "sleep")
        slept.start()
        self.addCleanup(slept.stop)

    def post(self):
        return zomato.post("x", {}, 28.6, 77.3)

    def test_an_answer_that_is_not_json_is_our_error_not_a_crash(self):
        with mock.patch.object(zomato.httpx, "post", return_value=_resp(200, "<html>Access Denied</html>")):
            with self.assertRaises(zomato.ZomatoAppError):
                self.post()

    def test_one_network_failure_is_retried(self):
        calls = [httpx.ConnectTimeout("slow"), _resp(200, '{"ok": 1}')]
        with mock.patch.object(zomato.httpx, "post", side_effect=calls) as post:
            self.assertEqual(self.post(), {"ok": 1})
        self.assertEqual(post.call_count, 2)

    def test_a_busy_answer_is_retried_once_then_reported(self):
        with mock.patch.object(zomato.httpx, "post", return_value=_resp(503)) as post:
            with self.assertRaises(zomato.ZomatoAppError):
                self.post()
        self.assertEqual(post.call_count, 2)

    def test_a_refused_session_is_not_retried(self):
        with mock.patch.object(zomato.httpx, "post", return_value=_resp(401)) as post:
            with self.assertRaises(zomato.ZomatoAppError):
                self.post()
        self.assertEqual(post.call_count, 1)

    def test_two_network_failures_give_our_error(self):
        with mock.patch.object(zomato.httpx, "post", side_effect=httpx.ConnectTimeout("slow")):
            with self.assertRaises(zomato.ZomatoAppError):
                self.post()


class UnexpectedFailuresOnCompetitionPages(SimpleTestCase):
    """Anything unexpected on a competition page is a plain 502 and is logged in full; the rest of the API behaves as before."""

    class Req:
        def __init__(self, path):
            self.path, self.method = path, "GET"

    def test_an_unexpected_error_on_a_competition_page_is_a_plain_502(self):
        from config.exception_handler import handler

        with self.assertLogs("config.exception_handler", level="ERROR") as logs:
            res = handler(KeyError("name"), {"request": self.Req("/api/brands/1/competition/2/zomato/cuisines")})
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.data["detail"], errors.FRIENDLY)
        self.assertIn("competition request failed", logs.output[0])

    def test_other_pages_keep_djangos_normal_behaviour(self):
        from config.exception_handler import handler

        self.assertIsNone(handler(KeyError("name"), {"request": self.Req("/api/brands/1/kpis")}))

    def test_login_and_not_found_answers_pass_through(self):
        from django.http import Http404

        from config.exception_handler import handler

        res = handler(Http404("nope"), {"request": self.Req("/api/brands/1/competition/2/zomato/cuisines")})
        self.assertEqual(res.status_code, 404)

    def test_it_is_wired_in(self):
        from django.conf import settings

        self.assertEqual(settings.REST_FRAMEWORK["EXCEPTION_HANDLER"], "config.exception_handler.handler")


class SuggestedCompetitorsTests(__import__("django.test", fromlist=["SimpleTestCase"]).SimpleTestCase):
    """Which nearby restaurants are suggested as competitors."""

    @staticmethod
    def _r(rid, name, rating=4.2, km=1.0):
        return {"res_id": rid, "name": name, "rating": rating, "distance_km": km, "delivery_time": "30 min", "offer": ""}

    def test_most_cuisines_in_common_comes_first_then_closest(self):
        from .market_api import pick_suggestions
        found = {"Biryani": [self._r("1", "A", km=3), self._r("2", "B", km=1), self._r("3", "C", km=2)],
                 "Mughlai": [self._r("3", "C", km=2), self._r("2", "B", km=1)]}
        got = pick_suggestions(found, ours=None, tracked=set())
        self.assertEqual([c["name"] for c in got], ["B", "C", "A"])  # B and C serve both; B is closer
        self.assertEqual(got[0]["cuisines"], ["Biryani", "Mughlai"])

    def test_leaves_out_ourselves_tracked_ones_and_poorly_rated(self):
        from .market_api import pick_suggestions
        found = {"Burger": [self._r("us", "Us"), self._r("t", "Tracked"), self._r("bad", "Bad", rating=2.1), self._r("ok", "Fine"), self._r("n", "Unrated", rating=None)]}
        got = pick_suggestions(found, ours="us", tracked={"t"})
        self.assertEqual(sorted(c["name"] for c in got), ["Fine", "Unrated"])

    def test_at_most_four(self):
        from .market_api import pick_suggestions
        found = {"Pizza": [self._r(str(i), f"R{i}", km=i) for i in range(1, 9)]}
        self.assertEqual([c["name"] for c in pick_suggestions(found, None, set())], ["R1", "R2", "R3", "R4"])

    def test_nearby_beats_far_even_with_fewer_cuisines_in_common(self):
        from .market_api import pick_suggestions
        found = {"Chinese": [self._r("far", "Far", km=6.9), self._r("near", "Near", km=2.7)], "Asian": [self._r("far", "Far", km=6.9)]}
        self.assertEqual([c["name"] for c in pick_suggestions(found, None, set())], ["Near", "Far"])  # Far matches two, but is over 5 km


class UpstreamErrorForStaffTests(SimpleTestCase):
    def test_clients_get_the_plain_sentence_and_staff_also_get_the_reason(self):
        from .errors import FRIENDLY, upstream_error

        e = zomato.ZomatoAppError("Zomato blocked this server's IP (403 Access Denied).")
        self.assertEqual(upstream_error(e).data["detail"], FRIENDLY)
        staff = upstream_error(e, staff=True)
        self.assertEqual(staff.status_code, 502)
        self.assertTrue(staff.data["detail"].startswith(FRIENDLY))
        self.assertIn("Zomato blocked this server's IP", staff.data["detail"])
