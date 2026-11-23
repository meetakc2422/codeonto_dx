"""One adapter per delivery app, so the competition pages work the same for Zomato and Swiggy. Each turns the app's
own calls into: find a spot to stand at, search around it, and read a restaurant's menu (all in the same shapes)."""

import re

from . import swiggy, zomato

INDIA = (20.5937, 78.9629)  # where to search from before an outlet has a spot or a Google listing


class Zomato:
    code, name = "zomato", "Zomato"
    Error = zomato.ZomatoAppError
    configured = staticmethod(zomato.configured)
    SPOT_KEYS = {"lat", "lng", "city_id", "entity_id", "entity_type", "delivery_subzone_id", "cell_id", "poi_id", "place_type"}

    @staticmethod
    def linked_id(outlet):
        return outlet.zomato_id

    @staticmethod
    def spot_from_pin(lat, lng, title="", address=""):
        raw = {"entity_latitude": lat, "entity_longitude": lng, "user_defined_latitude": lat, "user_defined_longitude": lng,
               "entity_id": 0, "entity_type": "", "location_type": "geocode", "entity_title": "", "entity_subtitle": "", "place": {}}
        return zomato.location_details({"raw": raw, "lat": lat, "lng": lng})

    @staticmethod
    def locations(q, lat, lng):
        return [{"title": f["title"], "address": f["address"], "distance": f["distance"], "pick": {"raw": f["raw"], "lat": f["lat"], "lng": f["lng"]}}
                for f in zomato.location_search(q, lat, lng)[:12]]

    @staticmethod
    def confirm(pick):
        return zomato.location_details(pick)

    @staticmethod
    def search(spot, q, kind=None):
        """kind: None works out what was typed; "restaurant", "dish" or "cuisine" asks for only that. Zomato's own suggestions tell them
        apart: a restaurant has a res_id, a dish is marked "Dish", and a cuisine or category is marked "See all restaurants"."""
        hints = zomato.suggest(spot, q)
        named = [{"res_id": h["res_id"], "name": h["name"].strip(), "rating": None, "offers": [], "is_ad": False,
                  "distance_km": None, "delivery_time": "", "area": ""} for h in hints if h["res_id"]]
        if kind == "restaurant":
            return q, None, named
        if kind in ("dish", "cuisine"):
            want = "Dish" if kind == "dish" else "See all restaurants"
            hit = next((h for h in hints if h["search"] and not h["res_id"] and (h.get("kind") or "").strip() == want), None)
            if not hit:
                return q, 0, []
            return hit["name"], None, zomato.search_restaurants(spot, q, search=hit["search"])["restaurants"]
        dish = next((h for h in hints if h["search"] and not h["res_id"]), None)
        listed = zomato.search_restaurants(spot, q, search=dish["search"]) if dish or not named else {"total": None, "restaurants": []}
        return (dish["name"] if dish else q), listed.get("total"), named + listed["restaurants"]

    @staticmethod
    def ranked(spot, q, pages=5):
        """What the app lists for a cuisine, in the app's order: (total, [{res_id, name, rating, distance_km, delivery_time, is_ad, offer}]). Up to `pages` pages of ~6; Zomato's
        paging needs the previous page's postback token."""
        dish = next((h for h in zomato.suggest(spot, q) if h["search"] and not h["res_id"]), None)
        if not dish:
            return None, []
        out, seen, total, pb = [], set(), None, None
        for page in range(1, pages + 1):
            got = zomato.search_restaurants(spot, q, page=page, search=dish["search"], postback=pb)
            total, pb = got.get("total"), got.get("postback")
            for r in got["restaurants"]:
                if r["res_id"] and r["res_id"] not in seen:
                    seen.add(r["res_id"])
                    out.append({"res_id": r["res_id"], "name": r["name"], "rating": r.get("rating"), "distance_km": r.get("distance_km"),
                                "delivery_time": r.get("delivery_time", ""), "is_ad": r.get("is_ad", False),
                                "offer": ((r.get("offers") or [{}])[0].get("text") or "")})
            if not got.get("has_more") or not pb:
                break
        return total, out

    @staticmethod
    def names(spot, text):
        return [(h["res_id"], h["name"].strip()) for h in zomato.suggest(spot, text) if h["res_id"]]

    @staticmethod
    def menu(spot, res_id):
        return {**zomato.menu(spot, res_id), "info": {}}

    @staticmethod
    def profile(spot, res_id):
        """Cuisines, price, address and opening hours from the restaurant's info page (one light call, no menu)."""
        return zomato.res_info(spot, res_id)


class Swiggy:
    code, name = "swiggy", "Swiggy"
    Error = swiggy.SwiggyAppError
    configured = staticmethod(swiggy.configured)
    SPOT_KEYS = {"lat", "lng", "city_id", "city"}

    @staticmethod
    def linked_id(outlet):
        return outlet.swiggy_id

    @staticmethod
    def spot_from_pin(lat, lng, title="", address=""):
        s = swiggy.spot(lat, lng)
        return {**s, "title": title or s["city"], "address": address, "serviceable": bool(s["city_id"])}

    @staticmethod
    def locations(q, lat, lng):
        return [{"title": f["title"], "address": f["address"], "distance": "", "pick": {"place_id": f["place_id"]}}
                for f in swiggy.location_search(q, lat, lng)[:12]]

    @staticmethod
    def confirm(pick):
        d = swiggy.place_details(pick["place_id"], *INDIA)
        s = swiggy.spot(d["lat"], d["lng"])
        return {**s, "title": d["title"], "address": d["address"], "serviceable": bool(s["city_id"])}

    @staticmethod
    def _nearby(spot, q):
        """What the app lists after pressing search (the branches that deliver to this spot); [] when that isn't readable."""
        try:
            return swiggy.search_restaurants(spot, q)
        except swiggy.SwiggyAppError:
            return []

    @staticmethod
    def search(spot, q, kind=None):  # Swiggy lists by one search; the type option is Zomato's
        listed = Swiggy._nearby(spot, q)
        if listed:
            rows = [{"res_id": r["res_id"], "name": r["name"], "rating": r["rating"], "offers": [], "is_ad": False,
                     "distance_km": r["distance_km"], "delivery_time": r["delivery_time"], "area": r["area"]} for r in listed]
            return q, None, rows[:40]
        rows = [{"res_id": h["res_id"], "name": h["name"], "rating": h["rating"], "offers": [], "is_ad": False, "distance_km": None,
                 "delivery_time": h["delivery_time"], "area": h["area"]} for h in swiggy.suggest(spot, q) if h["res_id"]]
        return q, None, rows

    @staticmethod
    def names(spot, text):
        listed = Swiggy._nearby(spot, text)
        if listed:  # nearest branch first, so "us" is the branch next to the spot, not the chain's default one
            want = set(re.findall(r"[a-z0-9]+", text.lower()))
            listed.sort(key=lambda r: (not want <= set(re.findall(r"[a-z0-9]+", r["name"].lower())),
                                       r["distance_km"] if r["distance_km"] is not None else 1e9))
            return [(r["res_id"], r["name"]) for r in listed]
        return [(h["res_id"], h["name"]) for h in swiggy.suggest(spot, text) if h["res_id"]]

    @staticmethod
    def menu(spot, res_id):
        mn = swiggy.menu(spot, res_id)
        return {**mn, "info": {k: mn.get(k) for k in ("cost_for_two", "area", "cuisines", "delivery_time", "distance_km", "is_open")}}


MARKETS = {m.code: m for m in (Zomato, Swiggy)}
