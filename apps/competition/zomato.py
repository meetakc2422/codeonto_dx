"""Zomato's customer app API (api.zomato.com): find places and restaurants around an outlet and read a restaurant's
menu, offers and best sellers, for competitor comparison. Not an official API: it speaks as the app does, with the
headers of one logged-in app session saved in settings.ZOMATO_APP_SESSION_FILE. When Zomato starts rejecting it,
copy any app request to api.zomato.com as cURL and run `manage.py zomato_app_session <file>`.

Location headers (lat/lng, city) are set per call, so the saved session never carries anyone's real location."""

import base64
import json
import logging
import re
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from django.conf import settings
from django.utils import timezone

log = logging.getLogger(__name__)

HOST = "https://api.zomato.com"
BASE = f"{HOST}/gw"
TIMEOUT = 30

# set by each call from the outlet being looked at, never taken from the saved session
PER_CALL = {"x-request-id", "x-present-lat", "x-present-long", "x-user-defined-lat", "x-user-defined-long",
            "x-present-horizontal-accuracy", "x-city-id", "x-o2-city-id", "x-location-token", "content-length", "host"}


def _session_path() -> Path:
    return Path(settings.ZOMATO_APP_SESSION_FILE)


def configured() -> bool:
    return _session_path().exists()


class ZomatoAppError(Exception):
    pass


def import_curl(text: str) -> dict:
    """Pull every -H 'name: value' out of a copied cURL and save them as the app's headers."""
    headers = {}
    for quote, raw in re.findall(r"""-H\s+(['"])(.*?)\1""", text, re.S):
        name, _, value = raw.partition(":")
        name = name.strip().lower()
        if name and name not in PER_CALL:
            headers[name] = value.strip()
    if "x-zomato-access-token" not in headers and "x-access-token" not in headers:
        raise ZomatoAppError("No Zomato app token found in that cURL. Copy a request to api.zomato.com from the app.")
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"headers": headers, "updated_at": timezone.now().isoformat(timespec="seconds")}, indent=2))
    path.chmod(0o600)
    log.info("Saved %d Zomato app headers", len(headers))
    return headers


def _headers() -> dict:
    path = _session_path()
    if not path.exists():
        raise ZomatoAppError("Zomato isn't connected yet: an admin needs to run `manage.py zomato_app_session <curl file>` on the server.")
    return json.loads(path.read_text())["headers"]


def post(path: str, body: dict, lat: float, lng: float, city_id: int | None = None, location_token: str | None = None,
         form: bool = False, params: dict | None = None) -> dict:
    """One call to the app API, placed at (lat, lng) as if the phone were standing there. form=True sends the body
    url-encoded, as the menu endpoint expects."""
    h = {**_headers(), "x-request-id": str(uuid.uuid4()), "content-type": "application/json; charset=UTF-8",
         "x-present-lat": str(lat), "x-present-long": str(lng), "x-user-defined-lat": str(lat), "x-user-defined-long": str(lng),
         "x-present-horizontal-accuracy": "15"}
    if city_id:
        h["x-city-id"] = h["x-o2-city-id"] = str(city_id)
    if location_token:
        h["x-location-token"] = location_token
    url = path if path.startswith("http") else f"{HOST}/{path}" if path.startswith("gateway/") else f"{BASE}/{path}"
    try:
        if form:
            h["content-type"] = "application/x-www-form-urlencoded"
            resp = httpx.post(url, headers=h, params=params, data=body, timeout=TIMEOUT)
        else:
            resp = httpx.post(url, headers=h, params=params, json=body, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise ZomatoAppError(f"Couldn't reach Zomato: {e}") from e
    if resp.status_code in (401, 403):
        raise ZomatoAppError(f"Zomato rejected the app session ({resp.status_code}). Refresh it with `manage.py zomato_app_session`.")
    if resp.status_code != 200:
        raise ZomatoAppError(f"Zomato answered {resp.status_code}")
    return resp.json()


def _snippets(resp: dict):
    """The app answers with a list of UI snippets; yield (snippet type, snippet body) for each."""
    for item in (resp.get("response") or {}).get("results", []):
        kind = (item.get("layout_config") or {}).get("snippet_type")
        if kind and kind in item:
            yield kind, item[kind]


def location_search(text: str, lat: float, lng: float, city_id: int | None = None) -> list[dict]:
    """Zomato's own location search, as typed into the app's address box: [{title, address, lat, lng, distance, raw}].
    raw is the app's location object, which the restaurant search later needs as-is."""
    body = {"search_text": text, "source": "delivery_home", "lang": "en", "postback_params": "{}", "recent_locations": [],
            "device_location": {"latitude": lat, "longitude": lng, "accuracy": 15},
            "location_permissions": {"device_location_on": True, "location_permission_available": True,
                                     "precise_location_permission_available": True}}
    if city_id:
        body["city_id"] = str(city_id)
    out = []
    for kind, snip in _snippets(post("user/location/search", body, lat, lng, city_id)):
        loc = ((snip.get("click_action") or {}).get("update_location_result") or {}).get("location")
        if kind.startswith("location_text") and loc and loc.get("entity_latitude") is not None:
            out.append({"title": loc.get("entity_title", ""), "address": loc.get("entity_subtitle", ""),
                        "lat": loc["entity_latitude"], "lng": loc["entity_longitude"],
                        "distance": loc.get("distance_text", ""), "raw": loc})
    return out


def location_details(picked: dict) -> dict:
    """Confirm a location picked from location_search, as the app does on tap. Returns what later calls are placed
    with: {lat, lng, city_id, entity_id, entity_type, poi_id, delivery_subzone_id, serviceable, title, address}."""
    loc = picked["raw"]
    r = post("user/location/details", {"location": loc, "source": "delivery_home", "lang": "en"}, picked["lat"], picked["lng"])
    L = (r.get("response") or {}).get("location") or {}
    place = L.get("place") or {}
    return {"lat": L.get("entity_latitude", picked["lat"]), "lng": L.get("entity_longitude", picked["lng"]),
            "city_id": L.get("city_id"), "entity_id": L.get("entity_id"), "entity_type": L.get("entity_type"),
            "poi_id": L.get("current_poi_id"), "delivery_subzone_id": place.get("delivery_subzone_id"),
            "serviceable": place.get("o2_serviceablity"), "cell_id": place.get("cell_id"),
            "place_type": place.get("place_type", "DSZ"), "title": L.get("entity_title", ""), "address": L.get("entity_subtitle", "")}


def set_location(text: str, lat: float, lng: float) -> dict:
    """Search for a place near (lat, lng) and confirm the closest match: one step to stand the app at an outlet."""
    found = location_search(text, lat, lng)
    if not found:
        raise ZomatoAppError(f"Zomato found no location for '{text}'")
    return location_details(found[0])


def _text(o) -> str:
    return o.get("text", "") if isinstance(o, dict) else (o or "")


def _tracking(snip: dict) -> list[dict]:
    out = []
    for t in snip.get("tracking_data") or []:
        raw = t.get("payload") if isinstance(t, dict) else None
        try:
            out.append(json.loads(raw) if isinstance(raw, str) else (raw or {}))
        except ValueError:
            pass
    return out


def _offers(tracking: list[dict]) -> list[dict]:
    for t in tracking:
        if "var3" in t:
            try:
                return [{"text": o.get("offer_text", ""), "code": o.get("offer_code", "")}
                        for o in (json.loads(x) for x in json.loads(t["var3"] or "[]"))]
            except ValueError:
                return []
    return []


def _restaurant(snip: dict) -> dict:
    """One search result card as plain fields."""
    tracking = _tracking(snip)
    meta = next((t["metadata"] for t in tracking if isinstance(t.get("metadata"), dict)), {})
    num = lambda v: round(float(v), 2) if v not in (None, "") else None
    subtitle_rows = (snip.get("animating_vertical_subtitles") or {}).get("vertical_subtitles") or []
    first_row = [_text(x) for x in (subtitle_rows[0].get("horizontal_subtitles") or [])] if subtitle_rows else []
    return {"res_id": str(snip.get("id")), "name": _text(snip.get("title")),
            "rating": num(meta.get("rating")), "rating_for_you": num(meta.get("personalised_rating")),
            "distance_km": num(meta.get("display_dist")), "delivery_time": first_row[0] if first_row else "",
            "is_ad": meta.get("is_ad") == "true", "rank": int(meta["final_res_rank"]) if meta.get("final_res_rank") else None,
            "offers": _offers(tracking) or [{"text": _text(x), "code": ""} for x in snip.get("bottom_horizontal_subtitles") or []],
            "tags": [_text(x.get("title")) for x in snip.get("bottom_horizontal_carousel_titles") or []],
            "dishes": [{"name": _text(m["top_right_container"].get("title")),
                        "price": _text(m["top_right_container"].get("right_title")).replace("·", "").strip()}
                       for m in snip.get("media_carousel") or [] if m.get("top_right_container")],
            "image": (((snip.get("media_carousel") or [{}])[0].get("media_content") or {}).get("image") or {}).get("url", "")}


def _spot(place: dict) -> dict:
    """The location ids searches and menus are placed with. place_id is always the delivery subzone (type DSZ), even
    when Zomato reported the spot as a GOOGLE_PLACE; a spot with no point of interest goes as POI 0."""
    return {"entity_type": place.get("entity_type") or "subzone", "entity_id": place["entity_id"], "place_type": "DSZ",
            "place_id": place["delivery_subzone_id"], "cell_id": place.get("cell_id") or "", "city_id": place["city_id"],
            "poi_id": place.get("poi_id") or 0}


def _search_location(place: dict) -> dict:
    p = _spot(place)
    return {"entity_type": p["entity_type"], "entity_id": str(p["entity_id"]), "place_type": p["place_type"],
            "place_id": str(p["place_id"]), "cell_id": str(p["cell_id"]), "city_id": str(p["city_id"]),
            "address_id": "0", "current_poi_id": str(p["poi_id"]), "poi_status": "User"}


def suggest(place: dict, text: str) -> list[dict]:
    """What the app suggests while typing: dishes, cuisines and restaurants, each with what search needs to open it.
    [{name, kind, entity_type, entity_id, res_id (restaurants), search: {as_entity_name, deeplink_filters, tracking_params, previous_search_id}}]"""
    body = {"search_key": text, "keyword": text, "page_type": "delivery_home", "is_map": False, "location": _search_location(place),
            "boost_ac_entity": False, "postback_params": "{}", "post_filters": [json.dumps({"category_context": "delivery_home"})],
            "search_id": uuid.uuid4().hex.upper()}
    r = post("gateway/search/v1/get_suggestions", body, place["lat"], place["lng"], place["city_id"])
    out = []
    for item in r.get("results", []):
        card = item.get(item.get("type", "")) or {}
        url = (((card.get("click_action") or {}).get("deeplink")) or {}).get("url", "")
        if not url:
            continue
        meta = next((t for t in _tracking(card) if "entity_type" in t), {})
        u = urlparse(url)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        res_id = u.path.strip("/") if u.netloc in ("order", "restaurant", "res") else None
        out.append({"name": _text(card.get("name")), "kind": _text(card.get("subtext")), "entity_type": meta.get("entity_type", ""),
                    "entity_id": meta.get("entity_id", ""), "res_id": res_id or (meta.get("entity_id") if meta.get("entity_type") == "restaurant" else None),
                    "search": q if u.netloc == "search" else None})
    return out


def search_restaurants(place: dict, query: str, count: int = 10, page: int = 1, search: dict | None = None) -> dict:
    """Restaurants Zomato shows at a confirmed location (from location_details). Pass a suggestion's `search`
    to get exactly what the app shows for that dish or cuisine; without it Zomato ignores the keyword.
    Returns {total, has_more, restaurants: [...]}; ads are kept and flagged, as they hold real places too."""
    search = search or {}
    filters = search.get("deeplink_filters") or base64.b64encode(json.dumps([json.dumps({"context": "delivery"})]).encode()).decode()
    name = search.get("as_entity_name") or query
    body = {"as_input_query": query, "keyword": name, "as_entity_name": name, "request_type": "initial" if page == 1 else "load_more",
            "count": count, "page_index": str(page), "deeplink_filters": filters, "load_more": True, "is_gold_mode_on": False,
            "deeplink_flags": "as_load_more_flow,as_leader_state", "location": _search_location(place)}
    if search.get("tracking_params"):
        body["tracking_params"] = search["tracking_params"]
    if search.get("previous_search_id"):
        body["autosuggest_search_id"] = search["previous_search_id"]
    r = post("gateway/search/v1/get_search_results", body, place["lat"], place["lng"], place["city_id"])
    found = [_restaurant(item[kind]) for item in r.get("results", [])
             for kind in [(item.get("layout_config") or {}).get("snippet_type", "")] if kind.startswith("v2_res_snippet") and kind in item]
    return {"total": r.get("total_results"), "has_more": r.get("has_more"), "restaurants": found}


def _place_params(place: dict) -> dict:
    p = _spot(place)
    return {"entity_type": p["entity_type"], "entity_id": p["entity_id"], "place_type": p["place_type"],
            "place_id": p["place_id"], "delivery_subzone_id": p["place_id"], "cell_id": p["cell_id"],
            "city_id": p["city_id"], "current_poi_id": p["poi_id"], "poi_status": "User", "location_type": "poi",
            "is_order_location": 1, "user_defined_latitude": place["lat"], "user_defined_longitude": place["lng"], "lang": "en"}


def menu_raw(place: dict, res_id: str) -> dict:
    """The restaurant page as the app loads it: header (rating, offers) and full menu."""
    q = _place_params(place)
    return post(f"menu/{res_id}", {**q, "resID": res_id, "mode": "delivery", "type": "all", "tabId": "menu"},
                place["lat"], place["lng"], place["city_id"], form=True, params=q)


# app-made sections that repeat real menu items for this user; the real categories come after them
PERSONAL_SECTIONS = ("your orders", "recommended for you", "most ordered together", "items starting at", "pair with")


def _texts(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "text" and isinstance(v, str):
                yield v
            else:
                yield from _texts(v)
    elif isinstance(o, list):
        for v in o:
            yield from _texts(v)


def _overall_rating(top_snippets) -> tuple[float | None, str]:
    """(4.4, '2.9K+'): the number right after the 'Overall rating (2.9K+)' label (the one before it is 'for you')."""
    texts = list(_texts(top_snippets))
    for i, t in enumerate(texts):
        if t.startswith("Overall rating"):
            num = next((x for x in texts[i + 1:i + 4] if re.fullmatch(r"\d\.\d", x)), None)
            votes = re.search(r"\(([^)]+)\)", t)
            return (float(num) if num else None, votes.group(1) if votes else "")
    return None, ""


def _menu_offers(promo) -> list[dict]:
    """[{text, code}]: each full offer line, with the 'Use code X' that follows it."""
    out = []
    for t in dict.fromkeys(_texts(promo)):
        if re.match(r"(Flat ₹[\d,]+ OFF above|\d+% OFF up to|Items starting at)", t):
            out.append({"text": t, "code": ""})
        elif (m := re.match(r"Use code (\w+)", t)) and out and not out[-1]["code"]:
            out[-1]["code"] = m.group(1)
    return out


# the first load sometimes comes back with only the personalised rails; retry until the menu looks complete
MENU_TRIES = 4
MENU_MIN_ITEMS = 20


def menu(place: dict, res_id: str, tries: int = MENU_TRIES, min_items: int = MENU_MIN_ITEMS) -> dict:
    """menu_once, retried up to `tries` times (2s, 4s, 6s apart) while it returns fewer than `min_items` items.
    Keeps the fullest answer, so a small restaurant whose whole menu is under min_items still comes back."""
    best = None
    for attempt in range(1, tries + 1):
        got = menu_once(place, res_id)
        if not best or len(got["items"]) > len(best["items"]):
            best = got
        if len(got["items"]) >= min_items:
            break
        if attempt < tries:
            log.info("Zomato menu %s: %d items on try %d, retrying", res_id, len(got["items"]), attempt)
            time.sleep(2 * attempt)
    best["tries"] = attempt
    return best


def menu_once(place: dict, res_id: str) -> dict:
    """A restaurant's page as plain data: {res_id, name, rating, votes, offers, combos, items}. Each item:
    {id, name, category, section, price, min_price, max_price, veg, tags, reorder_score, popularity, in_stock, has_photo, desc}.
    reorder_score is Zomato's 'highly reordered' bar (0-1); popularity is its in-menu search score: the two best
    public proxies for what sells, since order counts aren't shown."""
    r = menu_raw(place, res_id)
    m = r.get("menu") or {}
    tag_names = {t["slug"]: (t.get("title") or (t.get("pill_object") or {}).get("title") or {}).get("text") for t in m.get("tags", [])}
    rating, votes = _overall_rating(r.get("top_snippets"))
    items, combos = {}, []
    for sec in m.get("menus", []):
        sm = sec.get("menu") or {}
        section = sm.get("name", "")
        personal = section.lower().startswith(PERSONAL_SECTIONS)
        for c in sm.get("categories", []):
            cat = c.get("category") or {}
            dc = cat.get("display_config_data") or {}
            if section.lower().startswith("most ordered together") and dc:
                combos.append({"name": re.sub(r"<[^|]*\|\{[^|]*\|([^}]*)\}>", r"\1", _text(dc.get("title"))),
                               "price": _text((dc.get("bottom_container") or {}).get("left_title")),
                               "ordered_by": _text((dc.get("tag") or {}).get("title"))})
            for wrap in cat.get("items", []):
                it = wrap.get("item") or {}
                if not it.get("id") or (personal and it["id"] in items):
                    continue
                if it["id"] in items and not items[it["id"]]["_personal"]:
                    continue
                rt = it.get("rating") or {}
                items[it["id"]] = {"id": it["id"], "name": it.get("name", ""), "section": section, "category": cat.get("name") or section,
                    "price": it.get("display_price", it.get("price")), "min_price": it.get("min_price"), "max_price": it.get("max_price"),
                    "veg": "veg" in (it.get("dietary_slugs") or []), "tags": [tag_names[t] for t in it.get("tag_slugs", []) if tag_names.get(t)]
                    + (["High repeat"] if "high-repeat" in it.get("tag_slugs", []) else []),
                    "reorder_score": rt.get("progress_value") if rt.get("rating_identifier") == "highly_reordered" else None,
                    "popularity": it.get("search_popularity_score"), "in_stock": it.get("item_state") == "available",
                    "has_photo": bool(it.get("item_image_url")), "desc": it.get("desc", ""), "alias": it.get("search_alias", ""),
                    "_personal": personal}
    for i in items.values():
        i.pop("_personal")
    return {"res_id": res_id, "name": (r.get("meta_data") or {}).get("name", ""), "rating": rating, "votes": votes,
            "offers": _menu_offers(r.get("promo")), "combos": combos, "items": list(items.values())}


def menu_insights(mn: dict) -> dict:
    """What the menu says about how this restaurant sells."""
    items = mn["items"]
    by_cat = {}
    for i in items:
        by_cat.setdefault(i["category"], []).append(i)
    prices = lambda xs: sorted(x["price"] for x in xs if x["price"])
    top = sorted(items, key=lambda i: (-(i["reorder_score"] or 0), -(i["popularity"] or 0)))[:10]
    n = len(items) or 1
    return {"items": len(items), "categories": len(by_cat),
            "by_category": {c: {"items": len(xs), "avg_price": round(sum(prices(xs)) / len(prices(xs))) if prices(xs) else None,
                                "min": prices(xs)[0] if prices(xs) else None, "max": prices(xs)[-1] if prices(xs) else None}
                            for c, xs in sorted(by_cat.items(), key=lambda kv: -len(kv[1]))},
            "avg_price": round(sum(prices(items)) / len(prices(items))) if prices(items) else None,
            "veg_pct": round(100 * sum(i["veg"] for i in items) / n), "photo_pct": round(100 * sum(i["has_photo"] for i in items) / n),
            "no_photo": [i["name"] for i in items if not i["has_photo"]],
            "no_desc": [i["name"] for i in items if len((i.get("desc") or "").strip()) < 15],
            "desc_pct": round(100 * sum(len((i.get("desc") or "").strip()) >= 15 for i in items) / n),
            "out_of_stock": [i["name"] for i in items if not i["in_stock"]],
            "bestsellers": [i["name"] for i in items if "Bestseller" in i["tags"] or "Most Ordered" in i["tags"]],
            "top_sellers": [{"name": i["name"], "price": i["price"], "reorder": i["reorder_score"], "popularity": i["popularity"]} for i in top]}
