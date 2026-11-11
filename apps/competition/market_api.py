"""Competition on the delivery apps (Zomato, Swiggy): stand where an outlet is in the app, find restaurants or dishes
around it, open any restaurant's menu and offers, and keep a few to compare with. Every view takes the platform from
the URL; markets.py does the app-specific part. The apps are only called on demand, never on a schedule."""

import json
from datetime import date, timedelta

from django.http import Http404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import zomato
from .api import MAX_TRACKED, _outlet
from .markets import INDIA, MARKETS
from .models import MarketCompetitor, MarketRestaurant, MarketSnapshot, MarketSpot

MENU_FRESH = timedelta(hours=6)  # only spares a second read when Compare follows straight after opening


def _market(platform):
    if platform not in MARKETS:
        raise Http404("Unknown platform")
    return MARKETS[platform]


def _error(e):
    return Response({"detail": str(e)}, status=502)


def _area(outlet, m):
    a = MarketSpot.objects.filter(outlet=outlet, platform=m.code).first()
    return a and {**a.details, "lat": a.lat, "lng": a.lng, "city_id": a.city_id}


def _spot(request, outlet, m):
    """Where to look from: a temporary spot the page passes (?spot= or body "spot", from peek) or the outlet's own."""
    raw = request.data.get("spot") if request.method == "POST" else request.query_params.get("spot")
    if raw:
        spot = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(spot, dict) and {"lat", "lng", "city_id"} <= spot.keys():
            return {k: spot.get(k) for k in m.SPOT_KEYS}
    return _area(outlet, m)


def _insights(r: MarketRestaurant) -> dict:
    """Worked out from the stored menu each time, so menus read before a new insight existed still get it."""
    return zomato.menu_insights({"items": r.items}) if r.items else (r.insights or {})


def our_res_id(outlet, m, find: bool = False) -> tuple[str | None, str]:
    """(res_id, how): the outlet's own listing on this app. 'linked' when set up under Brands & Outlets; otherwise 'found'
    by searching the brand's name from the outlet's spot (find=True looks it up once and keeps it), or 'picked' when
    someone chose it. (None, '') when there is none or it was marked as not us."""
    if m.linked_id(outlet):
        return str(m.linked_id(outlet)), "linked"
    a = MarketSpot.objects.filter(outlet=outlet, platform=m.code).first()
    if not a:
        return None, ""
    d = a.details or {}
    if "our_res_id" in d:
        return d["our_res_id"] or None, d.get("our_how", "found") if d["our_res_id"] else ""
    if not find:
        return None, ""
    brand = set(outlet.brand.name.lower().split())
    try:
        names = m.names(_area(outlet, m), outlet.brand.name)
    except m.Error:
        return None, ""
    hit = next(((rid, n) for rid, n in names if brand <= set(n.lower().split()) and rid not in d.get("not_us", [])), None)
    a.details = {**d, "our_res_id": hit[0] if hit else "", "our_name": hit[1] if hit else "", "our_how": "found"}
    a.save(update_fields=["details", "updated_at"])
    return (hit[0], "found") if hit else (None, "")


def _summary(r: MarketRestaurant, comp: MarketCompetitor | None = None, tracked: bool = False) -> dict:
    ins = _insights(r)
    info = r.info or {}
    return {"res_id": r.res_id, "name": r.name, "rating": r.rating, "votes": r.votes, "offers": r.offers,
            "items": ins.get("items"), "avg_price": ins.get("avg_price"), "veg_pct": ins.get("veg_pct"), "photo_pct": ins.get("photo_pct"),
            "out_of_stock": len(ins.get("out_of_stock") or []), "top_sellers": (ins.get("top_sellers") or [])[:3],
            "no_photo": len(ins.get("no_photo") or []), "no_desc": len(ins.get("no_desc") or []), "desc_pct": ins.get("desc_pct"),
            "cost_for_two": info.get("cost_for_two", ""), "cuisines": info.get("cuisines") or [],
            "menu_refreshed_at": r.menu_refreshed_at, "tracked": tracked,
            "distance_km": comp.distance_km if comp and comp.distance_km is not None else info.get("distance_km"),
            "delivery_time": (comp.delivery_time if comp and comp.delivery_time else "") or info.get("delivery_time", "")}


def load_menu(m, res_id: str, place: dict, name: str = "", force: bool = False) -> MarketRestaurant:
    """The restaurant with its menu no older than MENU_FRESH, read from the app when it is stale."""
    r = MarketRestaurant.objects.filter(platform=m.code, res_id=res_id).first()
    if r and not force and r.menu_refreshed_at and timezone.now() - r.menu_refreshed_at < MENU_FRESH:
        return r
    mn = m.menu(place, res_id)
    ins = zomato.menu_insights(mn)
    r, _ = MarketRestaurant.objects.update_or_create(platform=m.code, res_id=res_id, defaults={
        "name": mn["name"] or name or (r.name if r else res_id), "rating": mn["rating"], "votes": mn["votes"], "offers": mn["offers"],
        "combos": mn["combos"], "items": mn["items"], "insights": ins, "info": mn.get("info") or {}, "menu_refreshed_at": timezone.now()})
    MarketSnapshot.objects.update_or_create(restaurant=r, day=date.today(), defaults={
        "rating": r.rating, "votes": r.votes, "items": ins["items"], "out_of_stock": len(ins["out_of_stock"]),
        "avg_price": ins["avg_price"], "offers": r.offers})
    return r


def _save_area(outlet, m, d: dict, pick: dict | None = None) -> MarketSpot:
    pick = pick or {}
    keep = {k: v for k, v in (MarketSpot.objects.filter(outlet=outlet, platform=m.code).values_list("details", flat=True).first() or {}).items()
            if k in ("our_res_id", "our_name", "our_how", "not_us")}
    a, _ = MarketSpot.objects.update_or_create(outlet=outlet, platform=m.code, defaults={
        "title": d.get("title") or pick.get("title", ""), "address": d.get("address") or pick.get("address", ""),
        "lat": d["lat"], "lng": d["lng"], "city_id": str(d.get("city_id") or ""), "details": {**d, **keep}})
    return a


def _auto_area(outlet, m) -> MarketSpot | None:
    """Stand the outlet in the app at its Google pin, or failing that at the first match for its area and city.
    None when neither works; the page then asks for the spot."""
    gp = getattr(getattr(outlet, "google_place", None), "place", None)
    try:
        if gp and gp.lat is not None:
            d = m.spot_from_pin(gp.lat, gp.lng, gp.name, gp.address)
        else:
            q = " ".join(filter(None, [outlet.area or outlet.outlet_name, outlet.city]))
            found = m.locations(q, *INDIA) if q else []
            if not found:
                return None
            d = m.confirm(found[0]["pick"])
            d = {**d, "title": d.get("title") or found[0]["title"], "address": d.get("address") or found[0]["address"]}
    except m.Error:
        return None
    return _save_area(outlet, m, d) if d.get("serviceable") else None


@api_view(["GET"])
def overview(request, brand_id, outlet_id, platform):
    """The outlet's spot (set from its Google pin the first time), its own listing and its competitors on this app."""
    m = _market(platform)
    outlet = _outlet(request, brand_id, outlet_id)
    a = MarketSpot.objects.filter(outlet=outlet, platform=m.code).first()
    if not a and m.configured():
        a = _auto_area(outlet, m)
    comps = MarketCompetitor.objects.filter(outlet=outlet, restaurant__platform=m.code).select_related("restaurant").order_by("-restaurant__rating")
    ours, how = our_res_id(outlet, m, find=bool(a))
    if a:
        a.refresh_from_db()  # the lookup may have just stored what it found
    us = MarketRestaurant.objects.filter(platform=m.code, res_id=ours).first() if ours else None
    return Response({"platform": m.code, "platform_name": m.name, "configured": m.configured(), "max_tracked": MAX_TRACKED,
                     "our_res_id": ours, "our_how": how, "our_name": us.name if us else ((a.details or {}).get("our_name") if a else ""),
                     "area": {"title": a.title, "address": a.address} if a else None,
                     "us": _summary(us) if us else None,
                     "competitors": [_summary(c.restaurant, c, True) for c in comps]})


@api_view(["POST"])
def locations(request, brand_id, outlet_id, platform):
    """{q}: the app's own address search, from near the outlet when we know where it is."""
    m = _market(platform)
    outlet = _outlet(request, brand_id, outlet_id)
    q = (request.data.get("q") or "").strip()
    if not q:
        return Response({"detail": "Type an area or address."}, status=400)
    gp = getattr(getattr(outlet, "google_place", None), "place", None)
    near = _area(outlet, m) or (gp and gp.lat is not None and {"lat": gp.lat, "lng": gp.lng}) or {"lat": INDIA[0], "lng": INDIA[1]}
    try:
        return Response(m.locations(q, near["lat"], near["lng"]))
    except m.Error as e:
        return _error(e)


def _confirm(m, request):
    pick = request.data.get("pick") or {}
    if not (pick.get("pick") or pick):
        return None, Response({"detail": "Pick a location from the search."}, status=400)
    try:
        d = m.confirm(pick.get("pick") or pick)
    except m.Error as e:
        return None, _error(e)
    if not d.get("serviceable"):
        return None, Response({"detail": f"{m.name} doesn't deliver to that spot. Pick another."}, status=400)
    return {**d, "title": d.get("title") or pick.get("title", ""), "address": d.get("address") or pick.get("address", "")}, None


@api_view(["POST"])
def set_area(request, brand_id, outlet_id, platform):
    """{pick}: one of the locations results; confirmed with the app and kept as the outlet's spot."""
    m = _market(platform)
    outlet = _outlet(request, brand_id, outlet_id, edit=True)
    d, bad = _confirm(m, request)
    if bad:
        return bad
    a = _save_area(outlet, m, d)
    return Response({"title": a.title, "address": a.address})


@api_view(["POST"])
def peek(request, brand_id, outlet_id, platform):
    """{pick}: a spot to look from for a while, not saved. The page sends it back as `spot` with searches and menus;
    tracked competitors, the outlet's own row and exports stay on the outlet's spot."""
    m = _market(platform)
    _outlet(request, brand_id, outlet_id)
    d, bad = _confirm(m, request)
    if bad:
        return bad
    return Response({"title": d["title"], "address": d["address"], "spot": {k: d.get(k) for k in m.SPOT_KEYS}})


@api_view(["POST"])
def search(request, brand_id, outlet_id, platform):
    """{q}: a restaurant name gives those restaurants; a dish or cuisine gives what the app lists for it here."""
    m = _market(platform)
    outlet = _outlet(request, brand_id, outlet_id)
    place = _spot(request, outlet, m)
    if not place:
        return Response({"detail": f"Set the outlet's {m.name} location first."}, status=400)
    q = (request.data.get("q") or "").strip()
    if not q:
        return Response({"detail": "Type a restaurant, dish or cuisine."}, status=400)
    try:
        query, total, found = m.search(place, q)
    except m.Error as e:
        return _error(e)
    tracked = set(MarketCompetitor.objects.filter(outlet=outlet, restaurant__platform=m.code).values_list("restaurant__res_id", flat=True))
    ours = our_res_id(outlet, m)[0]
    rows = []
    for r in found:
        if r["res_id"] and r["res_id"] not in {x["res_id"] for x in rows}:
            rows.append({**r, "tracked": r["res_id"] in tracked, "is_us": r["res_id"] == ours})
    return Response({"query": query, "total": total, "results": rows})


@api_view(["GET"])
def restaurant(request, brand_id, outlet_id, platform, res_id):
    """A restaurant's menu, offers, combos and best sellers, read fresh every time it is opened or refreshed."""
    m = _market(platform)
    outlet = _outlet(request, brand_id, outlet_id)
    place = _spot(request, outlet, m)
    if not place:
        return Response({"detail": f"Set the outlet's {m.name} location first."}, status=400)
    try:
        r = load_menu(m, res_id, place, force=True)
    except m.Error as e:
        return _error(e)
    comp = MarketCompetitor.objects.filter(outlet=outlet, restaurant=r).first()
    ours = our_res_id(outlet, m, find=True)[0]
    return Response({**_summary(r, comp, bool(comp)), "combos": r.combos, "insights": _insights(r), "is_us": res_id == ours, "has_us": bool(ours),
                     "items": sorted(r.items, key=lambda i: (i["category"], -(i.get("popularity") or i.get("reorder_score") or 0)))})


@api_view(["POST"])
def track(request, brand_id, outlet_id, platform):
    """{res_id, tracked, distance_km?, delivery_time?}: start or stop comparing with a restaurant on this app."""
    m = _market(platform)
    outlet = _outlet(request, brand_id, outlet_id, edit=True)
    res_id, on = str(request.data.get("res_id") or ""), bool(request.data.get("tracked", True))
    if not res_id:
        return Response({"detail": "res_id is required"}, status=400)
    mine = MarketCompetitor.objects.filter(outlet=outlet, restaurant__platform=m.code)
    if not on:
        mine.filter(restaurant__res_id=res_id).delete()
        return Response({"tracked": False})
    if mine.exclude(restaurant__res_id=res_id).count() >= MAX_TRACKED:
        return Response({"detail": f"You can compare up to {MAX_TRACKED} {m.name} restaurants per outlet. Remove one first."}, status=400)
    place = _spot(request, outlet, m)  # the spot the search was run from, so what was found can be opened
    if not place:
        return Response({"detail": f"Set the outlet's {m.name} location first."}, status=400)
    try:
        r = load_menu(m, res_id, place, request.data.get("name", ""))
    except m.Error as e:
        return _error(e)
    MarketCompetitor.objects.update_or_create(outlet=outlet, restaurant=r, defaults={
        "distance_km": request.data.get("distance_km"), "delivery_time": request.data.get("delivery_time") or ""})
    return Response({"tracked": True})


@api_view(["POST"])
def set_us(request, brand_id, outlet_id, platform):
    """{res_id}: this restaurant is the outlet itself; {res_id: null}: what was found is not us.
    Only for outlets not linked to this app under Brands & Outlets, where the link itself lives."""
    m = _market(platform)
    outlet = _outlet(request, brand_id, outlet_id, edit=True)
    if m.linked_id(outlet):
        return Response({"detail": f"This outlet is linked to its {m.name} listing under Brands & Outlets. Change it there."}, status=400)
    a = MarketSpot.objects.filter(outlet=outlet, platform=m.code).first()
    if not a:
        return Response({"detail": f"Set the outlet's {m.name} location first."}, status=400)
    d = a.details or {}
    rid = request.data.get("res_id")
    if rid:
        MarketCompetitor.objects.filter(outlet=outlet, restaurant__platform=m.code, restaurant__res_id=str(rid)).delete()
        d = {**d, "our_res_id": str(rid), "our_how": "picked"}
    else:
        d = {**d, "our_res_id": "", "not_us": list({*d.get("not_us", []), *([d["our_res_id"]] if d.get("our_res_id") else [])})}
    a.details = d
    a.save(update_fields=["details", "updated_at"])
    return Response({"our_res_id": d["our_res_id"] or None})
