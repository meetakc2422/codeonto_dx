"""Google Places API (New): find listings by name or around a point, and read one listing's rating.
The only place in the app that talks to Google Maps."""

import math

import httpx
from django.conf import settings
from django.utils import timezone

from .models import Place

BASE = "https://places.googleapis.com/v1"
SERVICES = ["delivery", "dineIn", "takeout", "reservable", "servesVegetarianFood"]
FIELDS = ["id", "displayName", "formattedAddress", "location", "rating", "userRatingCount", "priceLevel", "primaryType",
          "priceRange", "businessStatus", "regularOpeningHours", *SERVICES]
# read live when someone opens a competitor, never stored: review text is the part Google is strictest about caching
DETAIL_FIELDS = ["id", "reviews", "reviewSummary", "generativeSummary"]


class PlacesError(Exception):
    pass


def configured() -> bool:
    return bool(settings.GOOGLE_API_KEY)


def _call(method: str, path: str, fields: list[str], body: dict | None = None) -> dict:
    if not configured():
        raise PlacesError("Google Places isn't set up yet: add GOOGLE_API_KEY to the server's .env.")
    headers = {"X-Goog-Api-Key": settings.GOOGLE_API_KEY, "X-Goog-FieldMask": ",".join(fields)}
    try:
        resp = httpx.request(method, f"{BASE}/{path}", headers=headers, json=body, timeout=20)
    except httpx.HTTPError as e:
        raise PlacesError(f"Couldn't reach Google Places: {e}") from e
    if resp.status_code != 200:
        msg = resp.json().get("error", {}).get("message", resp.text[:200]) if resp.content else resp.reason_phrase
        raise PlacesError(f"Google Places said: {msg}")
    return resp.json()


def _price(r: dict | None) -> str:
    if not r:
        return ""
    sym = {"INR": "₹", "USD": "$"}
    lo, hi = r.get("startPrice") or {}, r.get("endPrice") or {}
    cur = sym.get(lo.get("currencyCode") or hi.get("currencyCode"), "")
    if lo.get("units") and hi.get("units"):
        return f"{cur}{int(lo['units']):,}–{int(hi['units']):,}"
    return f"{cur}{int(lo['units']):,}+" if lo.get("units") else ""


def save(p: dict) -> Place:
    """Store what Google returned for one place and hand back the row."""
    loc = p.get("location") or {}
    place, _ = Place.objects.update_or_create(place_id=p["id"], defaults={
        "name": (p.get("displayName") or {}).get("text", ""), "address": p.get("formattedAddress", ""),
        "lat": loc.get("latitude"), "lng": loc.get("longitude"), "primary_type": p.get("primaryType", ""),
        "rating": p.get("rating"), "rating_count": p.get("userRatingCount"), "price_level": p.get("priceLevel", ""),
        "price_range": _price(p.get("priceRange")), "business_status": p.get("businessStatus", ""),
        "hours": p.get("regularOpeningHours"), "services": {k: p[k] for k in SERVICES if k in p},
        "refreshed_at": timezone.now()})
    return place


def _circle(lat: float, lng: float, radius: int) -> dict:
    return {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius)}}


def search_text(query: str, near: Place | None = None, radius: int = 3000) -> list[Place]:
    body = {"textQuery": query, "pageSize": 10}
    if near and near.lat is not None:
        body["locationBias"] = _circle(near.lat, near.lng, radius)
    data = _call("POST", "places:searchText", [f"places.{f}" for f in FIELDS], body)
    return [save(p) for p in data.get("places", [])]


def search_nearby(near: Place, radius: int = 2000) -> list[Place]:
    body = {"includedTypes": ["restaurant"], "maxResultCount": 20, "locationRestriction": _circle(near.lat, near.lng, radius)}
    data = _call("POST", "places:searchNearby", [f"places.{f}" for f in FIELDS], body)
    return [save(p) for p in data.get("places", []) if p.get("id") != near.place_id]


def refresh(place_id: str) -> Place:
    return save(_call("GET", f"places/{place_id}", FIELDS))


def details(place_id: str) -> dict:
    """A place's latest reviews and Google's summary of them, for the page to show and forget."""
    d = _call("GET", f"places/{place_id}", DETAIL_FIELDS)
    summary = ((d.get("reviewSummary") or {}).get("text") or {}).get("text") or \
        ((d.get("generativeSummary") or {}).get("overview") or {}).get("text")
    return {"summary": summary, "reviews": [{
        "rating": r.get("rating"), "text": (r.get("text") or r.get("originalText") or {}).get("text", ""),
        "when": r.get("relativePublishTimeDescription", ""), "author": (r.get("authorAttribution") or {}).get("displayName", ""),
        "author_uri": (r.get("authorAttribution") or {}).get("uri", "")} for r in d.get("reviews", [])]}


def today_hours(hours: dict | None, weekday: int) -> dict | None:
    """Opening and closing minutes after midnight for one day (Python weekday, Monday = 0). Past-midnight closes run past 1440."""
    if not hours or not hours.get("periods"):
        return None
    day = (weekday + 1) % 7  # Google counts Sunday as 0
    spans = []
    for p in hours["periods"]:
        o, c = p.get("open") or {}, p.get("close")
        if o.get("day") != day:
            continue
        if not c:  # open around the clock
            return {"open": 0, "close": 1440}
        close = c.get("hour", 0) * 60 + c.get("minute", 0) + (1440 if c.get("day") != day else 0)
        spans.append((o.get("hour", 0) * 60 + o.get("minute", 0), close))
    return {"open": min(s[0] for s in spans), "close": max(s[1] for s in spans)} if spans else {"open": None, "close": None}


def distance_m(a: Place, b: Place) -> int | None:
    if None in (a.lat, a.lng, b.lat, b.lng):
        return None
    dlat, dlng = math.radians(b.lat - a.lat), math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * math.sin(dlng / 2) ** 2
    return round(6371000 * 2 * math.asin(math.sqrt(h)))
