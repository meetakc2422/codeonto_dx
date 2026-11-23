"""Estimated sales lost to being offline, from each platform's own daily Online % and that day's sales.

    GET /brands/<id>/uptime/loss?start=&end=&outlet_id=&platform=

For one outlet, one platform and one day: with f the share of opening hours it was offline and S the sales it made while online,
the day would have sold about S / (1 - f) if it had stayed up, so about S * f / (1 - f) was lost. When it was offline for most of
the day there is too little to extrapolate from, so the outlet's usual day (the median of its normal days) stands in instead.
Not every offline order is lost (some customers come back, some order from a rival), so the range runs from 60% of that figure
to all of it.

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
BASELINE_DAYS = 28  # how far back an outlet's usual day is taken from


def lost_for_day(sales: float, offline: float, baseline: float | None) -> float | None:
    """Sales lost on one day, or None when there is no basis for an estimate."""
    if sales is None or offline is None or offline < MIN_OFFLINE:
        return 0.0 if offline is not None and offline < MIN_OFFLINE else None
    offline = min(offline, 1.0)
    if offline <= 0.5:
        expected = sales / (1 - offline)
    elif baseline:
        expected = baseline
    else:
        return None
    return max(0.0, expected * offline)


def _usual_day(rows: list[tuple[date, float, float]]) -> float | None:
    """Median sales of the days the outlet was online nearly all day (online >= 95%), if it had at least 3."""
    good = [s for _, s, off in rows if off <= 0.05 and s]
    return median(good) if len(good) >= 3 else None


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
        baseline = _usual_day([(d, s, off) for d, s, off, _ in rows])
        o = outlets.setdefault(oid, {"outlet_id": oid, "central": 0.0, "offline_days": 0, "offline_sum": 0.0, "days": 0, "platforms": set(), "monitor_days": 0})
        for d, s, off, src in rows:
            if not (start <= d <= end):
                continue
            o["days"] += 1
            lost = lost_for_day(s, off, baseline)
            if lost is None:
                unestimated += 1
                continue
            if off >= MIN_OFFLINE:
                o["offline_days"] += 1
                o["offline_sum"] += off
                o["platforms"].add(plat)
                o["central"] += lost
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
        rows.append({"outlet_id": oid, "name": (b.area or b.outlet_name) if b else str(oid), "city": b.city if b else "",
                     "low": round(o["central"] * LOW_SHARE), "high": round(o["central"]), "offline_days": o["offline_days"],
                     "avg_offline_pct": round(o["offline_sum"] / o["offline_days"] * 100, 1) if o["offline_days"] else None,
                     "platforms": sorted(o["platforms"]), "from_monitor_days": o["monitor_days"]})
    rows.sort(key=lambda r: -r["high"])
    return Response({"low": sum(r["low"] for r in rows), "high": sum(r["high"] for r in rows), "outlets": rows,
                     "outlet_days": sum(o["days"] for o in outlets.values()), "outlet_days_unestimated": unestimated, "outlet_days_from_monitor": used_monitor,
                     "period": {"start": start.isoformat(), "end": end.isoformat()},
                     "method": "Sales while online ÷ share of the day online, times the share offline. Range: 60% to 100% of that, since some customers order later or elsewhere."})
