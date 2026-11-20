"""Dining view of the Performance page: for the brand's Zomato dining ids, the latest reading of each offer and how many
slots were left, how that changed across the readings so far, and which 15-minute slots are still open."""

from collections import defaultdict
from datetime import date

from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, outlet_ids
from apps.outlets.models import BrandOutlet

from .models import DiningOfferSnapshot as Offer, DiningSlotSnapshot as Slot


def _dining_outlets(request, brand_id):
    qs = BrandOutlet.objects.filter(brand_id=brand_id, is_active=True, zomato__is_dining=True, zomato__is_active=True).select_related("zomato", "brand")
    qs = in_scope(qs, request.user, "id")
    ids = outlet_ids(request.query_params.get("outlet_id"))
    return qs.filter(id__in=ids) if ids else qs


@api_view(["GET"])
def brand_dining(request, brand_id):
    get_brand(request.user, brand_id)
    outlets = list(_dining_outlets(request, brand_id))
    if request.query_params.get("summary"):  # the sidebar only needs to know whether to show the link
        return Response({"has_dining": bool(outlets)})
    out = []
    today = date.today().isoformat()
    for bo in outlets:
        rid = bo.zomato_id
        times = list(Offer.objects.filter(res_id=rid).order_by("-taken_at").values_list("taken_at", flat=True).distinct()[:40])
        row = {"outlet_id": bo.id, "name": bo.display_name, "res_id": rid, "last_checked": times[0] if times else None, "readings": len(times), "days": []}
        if times:
            latest = times[0]
            history = defaultdict(list)  # (date, meal, offer) -> [(taken_at, slots_left)] oldest first
            for o in Offer.objects.filter(res_id=rid, taken_at__in=times).order_by("taken_at"):
                history[(o.for_date, o.meal_time, o.offer)].append((o.taken_at, o.slots_left))
            days = defaultdict(lambda: {"offers": [], "slots": []})
            for o in Offer.objects.filter(res_id=rid, taken_at=latest, for_date__gte=today).order_by("for_date", "meal_time"):
                h = [v for _, v in history[(o.for_date, o.meal_time, o.offer)] if v is not None]
                top = max(h) if h else None
                days[o.for_date.isoformat()]["offers"].append({
                    "meal": o.meal_time, "offer": o.offer, "discount_pct": o.discount_pct, "window": o.window, "slots_left": o.slots_left,
                    "cover_charge": float(o.cover_charge) if o.cover_charge is not None else None,
                    "booked_since_first": (top - o.slots_left) if top is not None and o.slots_left is not None else None, "trend": h[-12:]})
            seen = defaultdict(set)
            for s in Slot.objects.filter(res_id=rid, taken_at__in=times, for_date__gte=today).values("for_date", "slot_time"):
                seen[s["for_date"]].add(s["slot_time"])
            for s in Slot.objects.filter(res_id=rid, taken_at=latest, for_date__gte=today).order_by("for_date", "id"):
                days[s.for_date.isoformat()]["slots"].append({"time": s.slot_time, "meal": s.meal_time, "discount_pct": s.discount_pct})
            for d, v in sorted(days.items()):
                open_times = {s["time"] for s in v["slots"]}
                v["gone"] = sorted(seen[date.fromisoformat(d)] - open_times)  # was bookable earlier, not now: full or closed
                row["days"].append({"date": d, **v})
        out.append(row)
    return Response({"has_dining": bool(outlets), "outlets": out})
