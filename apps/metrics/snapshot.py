"""The daily snapshot: yesterday at a glance, for the pop-up that opens on the Overview.

Sales (against the same weekday over the last weeks), each platform's share, the reviews that came in, and the money that leaked
(discounts, cancelled orders, ad spend). The figures come from the same tables as the rest of the dashboard; the sales line is
the same one the Export report uses (Zomato's "Sales" plus Swiggy's "Net Sales").
"""

from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, outlet_ids
from apps.reviews.models import Review

from .models import MetricDaily
from .report import SALES_SOURCES

WEEKS = 5  # the bars: the day itself and the same weekday over the four weeks before it


def _sales(outlets, plat, s, e) -> float:
    code = dict(SALES_SOURCES).get(plat)
    if not code:
        return 0.0
    v = MetricDaily.objects.filter(outlet_id__in=outlets, platform_id=plat, kpi__code=code, metric_date__range=(s, e)).aggregate(v=Sum("value"))["v"]
    return float(v or 0)


def _kpi_sum(outlets, codes, day, platform=None) -> float:
    q = MetricDaily.objects.filter(outlet_id__in=outlets, kpi__code__in=codes, metric_date=day)
    if platform:
        q = q.filter(platform_id=platform)
    return float(q.aggregate(v=Sum("value"))["v"] or 0)


def _pct(cur, prev):
    return None if not prev else round((cur - prev) / prev * 100, 1)


@api_view(["GET"])
def brand_snapshot(request, brand_id):
    brand = get_brand(request.user, brand_id)
    qp = request.query_params
    outlets = {o.id for o in in_scope(brand.outlets.filter(is_active=True), request.user, "id")}
    if outlet_ids(qp.get("outlet_id")):
        outlets &= set(outlet_ids(qp.get("outlet_id")))
    platform = qp.get("platform") or None
    plats = [p for p, _ in SALES_SOURCES if not platform or platform == p]

    def day_sales(d):
        return sum(_sales(outlets, p, d, d) for p in plats)

    # the day: yesterday, or the latest earlier day that has any sales
    day = date.today() - timedelta(days=1)
    for _ in range(14):
        if day_sales(day) > 0:
            break
        day -= timedelta(days=1)
    else:
        return Response({"empty": True})

    bars = [{"date": (day - timedelta(days=7 * i)).isoformat(), "sales": round(day_sales(day - timedelta(days=7 * i)), 2)} for i in reversed(range(WEEKS))]
    cur, prev = bars[-1]["sales"], bars[-2]["sales"]
    usual = [b["sales"] for b in bars[:-1] if b["sales"] > 0]
    by_platform = []
    for p in plats:
        c, w = _sales(outlets, p, day, day), _sales(outlets, p, day - timedelta(days=7), day - timedelta(days=7))
        if c or w:
            by_platform.append({"platform": p, "sales": round(c, 2), "last_week": round(w, 2), "change": _pct(c, w)})
    by_platform.sort(key=lambda r: -r["sales"])

    reviews = Review.objects.filter(outlet_id__in=outlets, reviewed_at__date=day)
    if platform:
        reviews = reviews.filter(platform_id=platform)
    rv = reviews.aggregate(total=Count("id"), positive=Count("id", filter=Q(rating__gte=4)), negative=Count("id", filter=Q(rating__lte=2)))
    pending = Review.objects.filter(outlet_id__in=outlets, reply_status="pending")
    if platform:
        pending = pending.filter(platform_id=platform)

    leak = {"discounts": _kpi_sum(outlets, ["discount_given"], day, platform), "cancelled": _kpi_sum(outlets, ["cancellation_loss"], day, platform),
            "ads": _kpi_sum(outlets, ["ad_spend"], day, platform)}
    return Response({
        "empty": False, "date": day.isoformat(), "weekday": day.strftime("%A"),
        "sales": {"value": round(cur, 2), "last_week": round(prev, 2), "change": _pct(cur, prev), "usual": round(sum(usual) / len(usual), 2) if usual else None, "bars": bars},
        "orders": {"value": int(_kpi_sum(outlets, ["delivered_orders"], day, platform))},
        "platforms": by_platform,
        "reviews": {**rv, "pending": pending.count()},
        "leakage": {**{k: round(v, 2) for k, v in leak.items()}, "total": round(sum(leak.values()), 2)},
    })
