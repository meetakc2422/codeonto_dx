"""Estimated sales lost to being offline, from each platform's own daily Online % and the outlet's usual sales.

    GET /brands/<id>/uptime/loss?start=&end=&outlet_id=&platform=

For one outlet, one platform and one day, with f the share of opening hours it was offline: it would normally have sold E that day,
so about E * f was lost. E is the outlet's typical sales for that weekday (the median of its normal days on that weekday over the
last 6 weeks, a day counting as normal when it was online at least 95% of the time). Zomato's own app works out its "Est. lost
sales" the same way, which is why this one lands close to it. With too few same-weekday days, the median of all its normal days
stands in; with no history at all, a day that was mostly online is extrapolated from what it sold while up (S * f / (1 - f)).
Not every offline order is lost (some customers come back, some order from a rival), so the range runs from 60% of that
figure to all of it.

The platform's own Online % comes first (it covers every day, both platforms); our own monitor's uptime (Zomato only) fills in
for a day the platform gave nothing for. A day with neither is left out and counted, not guessed.
"""

from datetime import date, timedelta
from statistics import median

from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.billing.access import require_module
from apps.metrics.models import MetricDaily
from apps.metrics.report import SALES_SOURCES
from apps.outlets.access import get_brand, in_scope, outlet_ids

from .models import UptimeDaily

LOW_SHARE = 0.6  # at least this share of the offline sales is really lost
MIN_OFFLINE = 0.01  # under 1% of the day is noise
MIN_CHECKS = 20  # about 100 minutes of our 5-minute checks
BASELINE_DAYS = 42  # how far back an outlet's usual sales are taken from (six weeks)
MIN_SAMPLES = 3  # normal days needed before a median counts as the outlet's usual


def lost_for_day(sales: float | None, offline: float | None, expected: float | None) -> float | None:
    """Sales lost on one day, or None when there is no basis for an estimate. `expected` is the outlet's usual sales for that day."""
    if offline is None:
        return None
    if offline < MIN_OFFLINE:
        return 0.0
    offline = min(offline, 1.0)
    if expected:
        return max(0.0, expected * offline)
    if sales and offline <= 0.5:  # no history: scale up from what it sold while it was up
        return sales * offline / (1 - offline)
    return None


def usual_sales(day: date, rows: list[tuple[date, float, float]]) -> float | None:
    """What this outlet normally sells on `day`'s weekday: the median of its normal days (online >= 95%) that weekday, else of all normal days."""
    normal = [(d, s) for d, s, off in rows if off <= 0.05 and s and d != day]
    same = [s for d, s in normal if d.weekday() == day.weekday()]
    if len(same) >= MIN_SAMPLES:
        return median(same)
    return median([s for _, s in normal]) if len(normal) >= MIN_SAMPLES else None


@api_view(["GET"])
def offline_loss(request, brand_id):
    brand = get_brand(request.user, brand_id)
    require_module(request.user, brand, "store_uptime")
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today() - timedelta(days=1)
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)
    since = start - timedelta(days=BASELINE_DAYS)
    plats = [p for p, _ in SALES_SOURCES if not qp.get("platform") or qp["platform"] == p]
    ids = outlet_ids(qp.get("outlet_id"))

    def scoped(qs):
        qs = in_scope(qs, request.user)
        return qs.filter(outlet_id__in=ids) if ids else qs

    sales_codes = {p: c for p, c in SALES_SOURCES if p in plats}
    base = scoped(MetricDaily.objects.filter(outlet__brand_id=brand_id, metric_date__range=(since, end), platform_id__in=plats))
    sales: dict[tuple, float] = {}
    online: dict[tuple, float] = {}
    for r in base.filter(kpi__code__in=[*sales_codes.values(), "online_pct"]).values("outlet_id", "platform_id", "metric_date", "kpi__code", "value"):
        if r["value"] is None:
            continue
        k = (r["outlet_id"], r["platform_id"], r["metric_date"])
        if r["kpi__code"] == "online_pct":
            online[k] = float(r["value"])
        elif r["kpi__code"] == sales_codes.get(r["platform_id"]):
            sales[k] = float(r["value"])
    ours: dict[tuple, float] = {}  # our own monitor (Zomato), used only where the platform gave nothing
    if "zomato" in plats:
        for r in scoped(UptimeDaily.objects.filter(outlet__brand_id=brand_id, platform_id="zomato", day__range=(since, end), checks__gte=MIN_CHECKS)).values("outlet_id", "day", "online_checks", "checks"):
            ours[(r["outlet_id"], "zomato", r["day"])] = r["online_checks"] / r["checks"] * 100

    by_series: dict[tuple, list] = {}
    for k, s in sales.items():
        pct, src = online.get(k), "platform"
        if pct is None and k in ours:
            pct, src = ours[k], "monitor"
        if pct is not None:
            by_series.setdefault((k[0], k[1]), []).append((k[2], s, max(0.0, min(1.0, 1 - pct / 100)), src))

    outlets: dict[int, dict] = {}
    unestimated = used_monitor = 0
    for (oid, plat), rows in by_series.items():
        history = [(d, s, off) for d, s, off, _ in rows]
        o = outlets.setdefault(oid, {"outlet_id": oid, "central": 0.0, "offline_days": 0, "offline_sum": 0.0, "days": 0, "platforms": set(), "monitor_days": 0, "day_rows": []})
        for d, s, off, src in rows:
            if not (start <= d <= end):
                continue
            o["days"] += 1
            lost = lost_for_day(s, off, usual_sales(d, history))
            if lost is None:
                unestimated += 1
                continue
            if off >= MIN_OFFLINE:
                o["offline_days"] += 1
                o["offline_sum"] += off
                o["platforms"].add(plat)
                o["central"] += lost
                o["day_rows"].append({"date": d.isoformat(), "platform": plat, "offline_pct": round(off * 100, 1), "low": round(lost * LOW_SHARE), "high": round(lost),
                                      "source": "Zomato's own Online %" if src == "platform" and plat == "zomato" else "Swiggy's own Online %" if src == "platform" else "our monitor"})
                if src == "monitor":
                    o["monitor_days"] += 1
                    used_monitor += 1

    from apps.outlets.models import BrandOutlet
    info = {b.id: b for b in BrandOutlet.objects.filter(id__in=outlets)}
    rows = []
    for oid, o in outlets.items():
        if o["central"] <= 0:
            continue
        b = info.get(oid)
        rows.append({"outlet_id": oid, "name": (b.area or b.outlet_name) if b else str(oid), "city": b.city if b else "", "outlet_name": b.outlet_name if b else "",
                     "low": round(o["central"] * LOW_SHARE), "high": round(o["central"]), "offline_days": o["offline_days"],
                     "avg_offline_pct": round(o["offline_sum"] / o["offline_days"] * 100, 1) if o["offline_days"] else None,
                     "platforms": sorted(o["platforms"]), "from_monitor_days": o["monitor_days"], "days": sorted(o["day_rows"], key=lambda r: r["date"])})
    rows.sort(key=lambda r: -r["high"])
    return Response({"low": sum(r["low"] for r in rows), "high": sum(r["high"] for r in rows), "outlets": rows,
                     "outlet_days": sum(o["days"] for o in outlets.values()), "outlet_days_unestimated": unestimated, "outlet_days_from_monitor": used_monitor,
                     "period": {"start": start.isoformat(), "end": end.isoformat()},
                     "method": "The outlet's usual sales for that weekday, times the share of the day it was offline. Range: 60% to 100% of that, since some customers order later or elsewhere."})
