from datetime import date, timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.billing.access import require_module
from apps.outlets.access import get_brand, in_scope, require_outlet_edit, outlet_ids
from apps.outlets.models import BrandOutlet

from . import places
from .models import Competitor, OutletPlace, PlaceSnapshot

MODULE = "competitors"
MAX_TRACKED = 10


def _place_json(p, distance=None, moves=None) -> dict:
    m = (moves or {}).get(p.place_id, {})
    return {"place_id": p.place_id, "name": p.name, "address": p.address, "lat": p.lat, "lng": p.lng, "rating": p.rating, "rating_count": p.rating_count,
            "price_level": p.price_level, "price_range": p.price_range, "type": p.primary_type, "distance_m": distance,
            "status": p.business_status, "services": p.services, "today": places.today_hours(p.hours, date.today().weekday()),
            "week": (p.hours or {}).get("weekdayDescriptions", []), "refreshed_at": p.refreshed_at,
            "rating_change": m.get("rating"), "new_ratings": m.get("count")}


def _moves(place_ids, days: int = 7) -> dict:
    """Per place: how its rating and rating count moved since the oldest snapshot in the last `days` days."""
    first = {}
    for s in PlaceSnapshot.objects.filter(place_id__in=place_ids, day__gte=date.today() - timedelta(days=days)).order_by("day"):
        first.setdefault(s.place_id, s)
    out = {}
    for pid, s in first.items():
        p = s.place
        out[pid] = {"rating": round(p.rating - s.rating, 2) if None not in (p.rating, s.rating) else None,
                    "count": p.rating_count - s.rating_count if None not in (p.rating_count, s.rating_count) else None}
    return out


def _outlet(request, brand_id, outlet_id, edit=False) -> BrandOutlet:
    brand = get_brand(request.user, brand_id)
    require_module(request.user, brand, MODULE)
    outlet = get_object_or_404(in_scope(BrandOutlet.objects.filter(brand=brand, is_active=True), request.user, "pk"), pk=outlet_id)
    if edit:
        require_outlet_edit(request.user, outlet.pk)
    return outlet


def _places_error(e):
    return Response({"detail": str(e)}, status=502)


@api_view(["GET"])
def competition(request, brand_id):
    """Every outlet (or ?outlet_id=) with its own Google listing, the competitors it tracks, and where it ranks among them."""
    brand = get_brand(request.user, brand_id)
    require_module(request.user, brand, MODULE)
    outlets = in_scope(BrandOutlet.objects.filter(brand=brand, is_active=True), request.user, "pk")
    if outlet_ids(request.query_params.get("outlet_id")):
        outlets = outlets.filter(pk__in=outlet_ids(request.query_params.get("outlet_id")))
    outlets = list(outlets.select_related("google_place__place").order_by("city", "area", "outlet_name"))
    tracked = {}
    for c in Competitor.objects.filter(outlet__in=outlets, is_tracked=True).select_related("place"):
        tracked.setdefault(c.outlet_id, []).append(c)
    own = {o.pk: o.google_place.place for o in outlets if hasattr(o, "google_place")}
    moves = _moves([p.place_id for p in own.values()] + [c.place_id for cs in tracked.values() for c in cs])
    rows = []
    for o in outlets:
        mine, comps = own.get(o.pk), tracked.get(o.pk, [])
        rated = [p.rating for p in [mine, *[c.place for c in comps]] if p and p.rating is not None]
        rank = None
        if mine and mine.rating is not None and comps:
            rank = 1 + sum(1 for c in comps if c.place.rating is not None and c.place.rating > mine.rating)
        comp_ratings = [c.place.rating for c in comps if c.place.rating is not None]
        rows.append({"outlet_id": o.pk, "name": o.area or o.outlet_name, "city": o.city,
                     "place": _place_json(mine, moves=moves) if mine else None,
                     "competitors": sorted([_place_json(c.place, c.distance_m, moves) for c in comps],
                                           key=lambda p: -(p["rating"] or 0)),
                     "rank": rank, "of": len(rated) if rank else None,
                     "competitor_avg": round(sum(comp_ratings) / len(comp_ratings), 2) if comp_ratings else None})
    return Response({"configured": places.configured(), "maps_key": settings.GOOGLE_MAPS_BROWSER_KEY,
                     "max_tracked": MAX_TRACKED, "outlets": rows})


@api_view(["POST"])
def locate(request, brand_id, outlet_id):
    """No place_id: search Google for this outlet's own listing. With place_id: save it as the outlet's listing."""
    outlet = _outlet(request, brand_id, outlet_id, edit=True)
    try:
        if request.data.get("place_id"):
            place = places.refresh(request.data["place_id"])
            OutletPlace.objects.update_or_create(outlet=outlet, defaults={"place": place})
            return Response(_place_json(place))
        query = request.data.get("q") or " ".join(filter(None, [outlet.brand.name, outlet.outlet_name, outlet.area, outlet.city]))
        return Response({"query": query, "results": [_place_json(p) for p in places.search_text(query)]})
    except places.PlacesError as e:
        return _places_error(e)


def _anchor(outlet):
    op = OutletPlace.objects.filter(outlet=outlet).select_related("place").first()
    return op.place if op else None


@api_view(["POST"])
def suggest(request, brand_id, outlet_id):
    """Restaurants around the outlet's listing, nearest first, each saved as an untracked suggestion."""
    outlet = _outlet(request, brand_id, outlet_id, edit=True)
    mine = _anchor(outlet)
    if not mine or mine.lat is None:
        return Response({"detail": "Find this outlet on Google first."}, status=400)
    radius = min(max(int(request.data.get("radius") or 2000), 300), 10000)
    try:
        found = places.search_nearby(mine, radius)
    except places.PlacesError as e:
        return _places_error(e)
    tracked = set(Competitor.objects.filter(outlet=outlet, is_tracked=True).values_list("place_id", flat=True))
    out = []
    for p in found:
        d = places.distance_m(mine, p)
        Competitor.objects.update_or_create(outlet=outlet, place=p, defaults={"distance_m": d})
        out.append({**_place_json(p, d), "tracked": p.place_id in tracked})
    out.sort(key=lambda p: p["distance_m"] if p["distance_m"] is not None else 1e9)
    return Response(out)


@api_view(["POST"])
def search(request, brand_id, outlet_id):
    """Find a competitor by name, near this outlet when we know where it is."""
    outlet = _outlet(request, brand_id, outlet_id, edit=True)
    q = (request.data.get("q") or "").strip()
    if not q:
        return Response({"detail": "Type a name to search for."}, status=400)
    mine = _anchor(outlet)
    try:
        found = places.search_text(q, near=mine)
    except places.PlacesError as e:
        return _places_error(e)
    tracked = set(Competitor.objects.filter(outlet=outlet, is_tracked=True).values_list("place_id", flat=True))
    return Response([{**_place_json(p, places.distance_m(mine, p) if mine else None), "tracked": p.place_id in tracked}
                     for p in found if not mine or p.place_id != mine.place_id])


@api_view(["POST"])
def track(request, brand_id, outlet_id):
    """{place_id, tracked}: start or stop comparing this outlet with a place."""
    outlet = _outlet(request, brand_id, outlet_id, edit=True)
    pid, on = request.data.get("place_id"), bool(request.data.get("tracked", True))
    if not pid:
        return Response({"detail": "place_id is required"}, status=400)
    if on and Competitor.objects.filter(outlet=outlet, is_tracked=True).exclude(place_id=pid).count() >= MAX_TRACKED:
        return Response({"detail": f"You can compare up to {MAX_TRACKED} competitors per outlet. Remove one first."}, status=400)
    comp = Competitor.objects.filter(outlet=outlet, place_id=pid).first()
    if not comp:
        if not on:
            return Response({"tracked": False})
        try:
            place = places.refresh(pid)
        except places.PlacesError as e:
            return _places_error(e)
        mine = _anchor(outlet)
        comp = Competitor.objects.create(outlet=outlet, place=place, distance_m=places.distance_m(mine, place) if mine else None)
    comp.is_tracked = on
    comp.save(update_fields=["is_tracked", "updated_at"])
    return Response({"tracked": on})


@api_view(["GET"])
def place_reviews(request, brand_id, outlet_id, place_id):
    """A tracked competitor's (or the outlet's own) latest Google reviews and Google's summary of them, read live."""
    outlet = _outlet(request, brand_id, outlet_id)
    mine = _anchor(outlet)
    if not Competitor.objects.filter(outlet=outlet, place_id=place_id).exists() and not (mine and mine.place_id == place_id):
        return Response({"detail": "Not a place this outlet compares with"}, status=404)
    try:
        return Response(places.details(place_id))
    except places.PlacesError as e:
        return _places_error(e)
