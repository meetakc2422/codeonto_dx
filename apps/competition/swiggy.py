"""Swiggy's customer app API: find places and restaurants around an outlet and read a restaurant's menu, offers and
best sellers, for competitor comparison. Not an official API: it speaks as the Android app does, with the headers of
one logged-in app session saved in settings.SWIGGY_APP_SESSION_FILE. When Swiggy starts rejecting it, copy any app
request as cURL and run `manage.py swiggy_app_session <file>`. Keep it a different account from the partner sessions.

Location headers (latitude/longitude and the encoded location context) are set per call from the outlet."""

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

# Swiggy serves menu photos from its CDN by imageId
IMAGE_CDN = "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto,w_300/"

TIMEOUT = 30
BAD_ESCAPE = re.compile(r'\\(?!["\\/bfnrtu])')

# set by each call from the spot being looked at, never taken from the saved session
PER_CALL = {"latitude", "longitude", "current-latitude", "current-longitude", "encoded-location-context",
            "content-length", "host", "x-request-id"}


class SwiggyAppError(Exception):
    pass


def _session_path() -> Path:
    return Path(settings.SWIGGY_APP_SESSION_FILE)


def configured() -> bool:
    return _session_path().exists()


def import_curl(text: str) -> dict:
    """Pull every -H 'name: value' out of a copied cURL and save them as the app's headers."""
    headers = {}
    for quote, raw in re.findall(r"""-H\s+(['"])(.*?)\1""", text, re.S):
        name, _, value = raw.partition(":")
        name = name.strip().lower()
        if name and name not in PER_CALL:
            headers[name] = value.strip()
    if "tid" not in headers and "token" not in headers:
        raise SwiggyAppError("No Swiggy app session (tid / token) found in that cURL. Copy a request the Swiggy app makes.")
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"headers": headers, "updated_at": timezone.now().isoformat(timespec="seconds")}, indent=2))
    path.chmod(0o600)
    log.info("Saved %d Swiggy app headers", len(headers))
    return headers


def _headers() -> dict:
    path = _session_path()
    if not path.exists():
        raise SwiggyAppError("Swiggy isn't connected yet: an admin needs to run `manage.py swiggy_app_session <curl file>` on the server.")
    return json.loads(path.read_text())["headers"]


def _location_context(lat: float, lng: float, city_id: str = "", city: str = "") -> str:
    ctx = {"cityId": str(city_id or ""), "cityName": city or "", "latLng": {"latitude": lat, "longitude": lng}, "zoneId": "", "geoZoneIds": None}
    return base64.b64encode(json.dumps(ctx, separators=(",", ":")).encode()).decode()


def call(method: str, url: str, lat: float, lng: float, city_id: str = "", city: str = "", params: dict | None = None,
         body: dict | None = None) -> dict:
    """One call to the app API, placed at (lat, lng) as if the phone were standing there."""
    h = {**_headers(), "latitude": str(lat), "longitude": str(lng), "current-latitude": str(lat), "current-longitude": str(lng),
         "encoded-location-context": _location_context(lat, lng, city_id, city)}
    try:
        resp = httpx.request(method, url, headers=h, params=params, json=body, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise SwiggyAppError(f"Couldn't reach Swiggy: {e}") from e
    if resp.status_code in (401, 403):
        raise SwiggyAppError(f"Swiggy rejected the app session ({resp.status_code}). Refresh it with `manage.py swiggy_app_session`.")
    if resp.status_code != 200:
        raise SwiggyAppError(f"Swiggy answered {resp.status_code}")
    try:
        return resp.json()
    except ValueError:
        pass
    try:  # some answers embed protobuf text with escapes JSON doesn't allow (\a, \v): keep those backslashes literal
        return json.loads(BAD_ESCAPE.sub(r"\\\\", resp.text))
    except ValueError as e:
        raise SwiggyAppError("Swiggy sent something that isn't JSON (it may be blocking this server)") from e


def location_search(text: str, lat: float, lng: float) -> list[dict]:
    """Swiggy's address search, as typed into the app's location box: [{title, address, place_id}].
    The place_id is a Google Maps place id; turning it into coordinates is a separate call."""
    r = call("GET", "https://maps.swiggy.com/place/autocomplete", lat, lng,
             params={"input": text, "location": f"{lat:.4f},{lng:.4f}", "radius": 15000})
    return [{"title": (p.get("structured_formatting") or {}).get("main_text") or p.get("description", ""),
             "address": (p.get("structured_formatting") or {}).get("secondary_text", ""), "place_id": p.get("place_id")}
            for p in r.get("data") or [] if p.get("place_id")]


def place_details(place_id: str, near_lat: float, near_lng: float) -> dict:
    """A location_search result as a spot to look from: {title, address, lat, lng, city}."""
    r = call("GET", "https://maps.swiggy.com/address/recommend", near_lat, near_lng,
             params={"place_id": place_id, "enrich_poi_components": "true"})
    d = (r.get("data") or [{}])[0]
    loc = ((d.get("geometry") or {}).get("location")) or {}
    if loc.get("lat") is None:
        raise SwiggyAppError("Swiggy couldn't place that location")
    parts = {t: c.get("long_name") for c in d.get("address_components") or [] for t in c.get("types") or []}
    return {"title": parts.get("locality") or d.get("formatted_address", "").split(",")[0], "address": d.get("formatted_address", ""),
            "lat": loc["lat"], "lng": loc["lng"], "city": parts.get("city", "")}


def spot(lat: float, lng: float) -> dict:
    """Where to look from in Swiggy: {lat, lng, city_id, city}. Swiggy's own city id goes into every later call's
    location header, as the app does after picking a location."""
    r = call("GET", "https://disc.swiggy.com/api/v1/location_based_features", lat, lng,
             params=[("lat", lat), ("lng", lng), ("features", "CITY_INFO")])
    info = ((r.get("data") or {}).get("CITY_INFO")) or {}
    return {"lat": lat, "lng": lng, "city_id": str(info.get("city_id") or ""), "city": info.get("city_name", "")}


def _cards(o):
    """Every {type_url, value} widget in an answer, however deeply it is grouped."""
    if isinstance(o, dict):
        if "type_url" in o and "value" in o:
            yield o
        for v in o.values():
            yield from _cards(v)
    elif isinstance(o, list):
        for v in o:
            yield from _cards(v)


def suggest(place: dict, text: str) -> list[dict]:
    """What the app suggests while typing: restaurants and dishes.
    [{name, type (RESTAURANT / DISH / ...), res_id, brand_id, area, rating, delivery_time, query, metadata}].
    The widgets are protobuf inside JSON; the readable parts are the deeplink (with its metadata JSON) and a few labels."""
    r = call("POST", "https://disc.swiggy.com/api/v1/auto-suggest/", place["lat"], place["lng"], place.get("city_id", ""), place.get("city", ""),
             params={"lat": place["lat"], "lng": place["lng"]},
             body={"categoryPage": "FOOD", "marketplaces": [{"businessLineId": "FOOD", "marketplaceId": "SWIGGY"}],
                   "query": text, "trackingId": str(uuid.uuid4())})
    out = []
    for c in _cards(r):
        if not c["type_url"].endswith("GlobalAutoSuggestion"):
            continue
        v = c["value"]
        link = re.search(r"swiggy://explore\?[^\s\x00-\x1f\"\\]+", v)
        if not link:
            continue
        q = {k: x[0] for k, x in parse_qs(urlparse(link.group(0)).query).items()}
        try:
            meta = json.loads(q.get("metadata", "{}"))
        except ValueError:
            meta = {}
        data = meta.get("data") or {}
        rating = re.search(r"Z\x03([1-5]\.\d)", v)
        area = next((v[m.end():m.end() + ord(m.group(1))] for m in re.finditer(r"R([\x02-\x3f])", v)
                     if v[m.end() + ord(m.group(1)):m.end() + ord(m.group(1)) + 1] == "Z"), "")
        out.append({"name": q.get("query", ""), "type": meta.get("type", ""), "label": meta.get("displayLabel", ""),
                    "res_id": str(data.get("primaryRestaurantId") or "") or None, "brand_id": data.get("brandId") or data.get("parentId"),
                    "area": area, "rating": float(rating.group(1)) if rating else None,
                    "delivery_time": (m.group(0) if (m := re.search(r"\d+-\d+ mins", v)) else ""), "query": q.get("query", ""), "metadata": meta})
    return out


# app-made sections that repeat real menu items for this user
PERSONAL_SECTIONS = ("recommended", "combos for", "your", "previously ordered", "top picks")


def _count(text) -> int | None:
    """'10364 ratings' -> 10364; '10.4K+' -> 10400."""
    m = re.search(r"([\d.]+)\s*([KkLl])?", str(text or "").replace(",", ""))
    if not m:
        return None
    n = float(m.group(1)) * {"k": 1_000, "l": 100_000}.get((m.group(2) or "").lower(), 1)
    return int(n)


def _menu_items(cards):
    """(section, category, item info) for every dish card, through nested categories."""
    for c in cards:
        cc = (c.get("card") or {}).get("card") or {}
        section = cc.get("title") or ""
        for ic in cc.get("itemCards") or []:
            yield section, section, (ic.get("card") or {}).get("info") or {}
        for sub in cc.get("categories") or []:
            for ic in sub.get("itemCards") or []:
                yield section, sub.get("title") or section, (ic.get("card") or {}).get("info") or {}


def menu_once(place: dict, res_id: str) -> dict:
    r = call("POST", f"https://disc.swiggy.com/api/v2/menu/{res_id}", place["lat"], place["lng"], place.get("city_id", ""), place.get("city", ""),
             params={"complete-menu": "true", "lat": place["lat"], "lng": place["lng"]},
             body={"source": "SEARCH", "submitAction": "DEEPLINK", "takeaway": 0, "isSld": 0, "qrEnabled": "false", "request_contexts": []})
    cards = (r.get("success") or {}).get("cards") or []
    header = next(((c.get("card") or {}).get("card") or {} for c in cards
                   if ((c.get("card") or {}).get("card") or {}).get("@type", "").endswith("CompactMenuHeader")), {})
    info = (header.get("info") or {}).get("info") or {}
    offers = [{"text": " ".join(filter(None, [(o.get("info") or {}).get("header"), (o.get("info") or {}).get("description")])),
               "code": re.sub(r"^USE\s+", "", (o.get("info") or {}).get("couponCode") or "")}
              for o in (header.get("offers") or {}).get("offers") or []]
    regular = next((((c.get("groupedCard") or {}).get("cardGroupMap") or {}).get("REGULAR") or {} for c in cards if c.get("groupedCard")), {})
    items = {}
    for section, category, it in _menu_items(regular.get("cards") or []):
        if not it.get("id"):
            continue
        personal = section.lower().startswith(PERSONAL_SECTIONS)
        if it["id"] in items and (personal or not items[it["id"]]["_personal"]):
            continue
        rupees = lambda p: round(p / 100) if p else None
        price = rupees(it.get("price") or it.get("defaultPrice") or it.get("finalPrice"))
        variant_prices = [rupees(v.get("price")) for g in ((it.get("variantsV2") or {}).get("pricingModels") or []) for v in [g] if v.get("price")]
        agg = ((it.get("ratings") or {}).get("aggregatedRating")) or {}
        tags = [t for t in [(it.get("ribbon") or {}).get("text"), "Bestseller" if it.get("isBestseller") else None] if t]
        items[it["id"]] = {"id": it["id"], "name": it.get("name", ""), "section": section, "category": it.get("category") or category,
                           "price": price, "min_price": min([price, *variant_prices]) if price else None, "max_price": max([price, *variant_prices]) if price else None,
                           "veg": (it.get("itemAttribute") or {}).get("vegClassifier") == "VEG" or it.get("isVeg") == 1,
                           "tags": list(dict.fromkeys(tags)), "reorder_score": None,
                           "item_rating": float(agg["rating"]) if agg.get("rating") else None, "popularity": _count(agg.get("ratingCount")),
                           "in_stock": bool(it.get("inStock", 1)), "has_photo": bool(it.get("imageId")),
                           "image": f"{IMAGE_CDN}{it['imageId']}" if it.get("imageId") else "",
                           "desc": re.sub(r"\s*\[Energy:.*?\]", "", it.get("description") or "").strip(), "alias": "", "_personal": personal}
    for i in items.values():
        i.pop("_personal")
    sla = info.get("sla") or {}
    return {"res_id": str(res_id), "name": info.get("name", ""), "rating": info.get("avgRating"), "votes": (info.get("totalRatingsString") or "").replace(" ratings", ""),
            "offers": offers, "combos": [], "items": list(items.values()), "cost_for_two": info.get("costForTwoMessage", ""),
            "area": info.get("areaName", ""), "cuisines": info.get("cuisines") or [],
            "delivery_time": f"{sla['minDeliveryTime']}-{sla['maxDeliveryTime']} mins" if sla.get("minDeliveryTime") else "",
            "distance_km": sla.get("lastMileTravel"), "is_open": info.get("isOpen")}


def menu(place: dict, res_id: str, tries: int = 3, min_items: int = 15) -> dict:
    """menu_once, retried a couple of times while it comes back thin; keeps the fullest answer."""
    best = None
    for attempt in range(1, tries + 1):
        got = menu_once(place, res_id)
        if not best or len(got["items"]) > len(best["items"]):
            best = got
        if len(got["items"]) >= min_items:
            break
        if attempt < tries:
            time.sleep(2 * attempt)
    best["tries"] = attempt
    return best
