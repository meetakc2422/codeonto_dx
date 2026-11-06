from datetime import date, timedelta

from django.db.models import Avg, F, Max, Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import brands_for, get_brand, in_scope, outlet_ids
from apps.billing.access import require_module

from .models import OfflineEpisode, UptimeDaily


def _pct(online, checks):
    return round(online / checks * 100, 2) if checks else None


def _filtered(request, brand_id):
    """(episodes that started in the period or are still going, uptime days in the period), limited to this login's outlets."""
    require_module(request.user, get_brand(request.user, brand_id), "store_uptime")
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)
    episodes = in_scope(OfflineEpisode.objects.filter(outlet__brand_id=brand_id), request.user).filter(
        Q(log_date__range=(start, end)) | Q(is_active=True))
    days = in_scope(UptimeDaily.objects.filter(outlet__brand_id=brand_id, day__range=(start, end)), request.user)
    if outlet_ids(qp.get("outlet_id")):
        ids = outlet_ids(qp.get("outlet_id"))
        episodes, days = episodes.filter(outlet_id__in=ids), days.filter(outlet_id__in=ids)
    if qp.get("platform"):
        episodes, days = episodes.filter(platform_id=qp["platform"]), days.filter(platform_id=qp["platform"])
    return episodes, days, qp


@api_view(["GET"])
def uptime_summary(request, brand_id):
    episodes, days, _ = _filtered(request, brand_id)
    totals = days.aggregate(checks=Sum("checks"), online=Sum("online_checks"), last=Max("updated_at"))
    ended = episodes.filter(is_active=False).aggregate(avg=Avg("downtime_minutes"))["avg"]
    fields = ("outlet_id", "outlet__outlet_name", "outlet__area", "outlet__city", "outlet__zomato_id")
    # the area tells stores apart: many have the brand as their name, and a few share an area, so the id goes along
    entry = lambda r: {"id": r["outlet_id"], "name": r["outlet__area"] or r["outlet__outlet_name"], "city": r["outlet__city"],
                       "zomato_id": r["outlet__zomato_id"], "uptime_pct": None, "events": 0, "downtime_minutes": 0, "offline_since": None}
    by_outlet = {}
    for r in days.values(*fields).annotate(checks=Sum("checks"), online=Sum("online_checks")):
        by_outlet[r["outlet_id"]] = {**entry(r), "uptime_pct": _pct(r["online"], r["checks"])}
    for r in episodes.values(*fields, "is_active", "first_detected_at", "downtime_minutes"):
        o = by_outlet.setdefault(r["outlet_id"], entry(r))
        o["events"] += 1
        o["downtime_minutes"] += r["downtime_minutes"]
        if r["is_active"]:
            o["offline_since"] = r["first_detected_at"]
    outlets = sorted(by_outlet.values(), key=lambda o: (o["offline_since"] is None, o["uptime_pct"] is None, o["uptime_pct"] or 0, o["name"]))
    return Response({
        "uptime_pct": _pct(totals["online"] or 0, totals["checks"] or 0),
        "last_checked_at": totals["last"],
        "offline_now": episodes.filter(is_active=True).count(),
        "events": episodes.count(),
        "avg_downtime": round(ended) if ended is not None else None,
        "total_downtime": episodes.aggregate(n=Sum("downtime_minutes"))["n"] or 0,
        "trend": [{"date": r["day"], "value": _pct(r["online"], r["checks"])}
                  for r in days.values("day").annotate(checks=Sum("checks"), online=Sum("online_checks")).order_by("day")],
        "outlets": outlets,
    })


@api_view(["GET"])
def offline_episodes(request, brand_id):
    episodes, _, qp = _filtered(request, brand_id)
    if qp.get("status") == "active":
        episodes = episodes.filter(is_active=True)
    elif qp.get("status") == "restored":
        episodes = episodes.filter(is_active=False)
    offset, limit = int(qp.get("offset", 0)), min(int(qp.get("limit", 50)), 500)
    return Response([{"id": e.id, "outlet_id": e.outlet_id, "outlet_name": e.outlet.display_name, "zomato_id": e.outlet.zomato_id, "platform": e.platform_id,
                      "is_active": e.is_active, "first_detected_at": e.first_detected_at, "restored_at": e.restored_at,
                      "downtime_minutes": e.downtime_minutes}
                     for e in episodes.select_related("outlet__brand")[offset:offset + limit]])


@api_view(["GET"])
def uptime_changes(request):
    """Outlets offline right now, and those back online in the last 2 hours, across the brands this login can see
    (?brand_id= for one brand). Drives the corner popups."""
    brands = brands_for(request.user)
    if request.query_params.get("brand_id"):
        brands = brands.filter(pk=request.query_params["brand_id"])
    episodes = in_scope(OfflineEpisode.objects.filter(outlet__is_active=True, outlet__brand__in=brands), request.user)
    episodes = episodes.select_related("outlet__brand", "platform")
    row = lambda e: {"id": e.id, "outlet_id": e.outlet_id, "brand_id": e.outlet.brand_id, "brand": e.outlet.brand.name,
                     "outlet": e.outlet.area or e.outlet.outlet_name, "city": e.outlet.city, "platform": e.platform.name,
                     "since": e.first_detected_at, "restored_at": e.restored_at, "downtime_minutes": e.downtime_minutes}
    # an episode closed at its last offline check ended because the collector stopped: nobody saw the store come back
    back = (episodes.filter(is_active=False, restored_at__gte=timezone.now() - timedelta(hours=2))
            .exclude(restored_at=F("last_detected_at")).order_by("-restored_at")[:200])
    return Response({"offline": [row(e) for e in episodes.filter(is_active=True).order_by("-first_detected_at")[:200]],
                     "back": [row(e) for e in back]})
