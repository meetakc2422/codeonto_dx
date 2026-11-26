"""The daily snapshot: yesterday at a glance, for the pop-up that opens on the Overview.

Sales (against the same weekday over the last weeks), each platform's share, the reviews that came in, and the money that leaked
(discounts, cancelled orders, ad spend). The figures come from the same tables as the rest of the dashboard; the sales line is
the same one the Export report uses (Zomato's "Sales" plus Swiggy's "Net Sales").
"""

from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, is_staff, outlet_ids
from apps.outlets.models import BrandOutlet
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


def _by_outlet(outlets, plats, day) -> dict:
    """Each outlet's sales (the same line as the headline figure) for one day."""
    out: dict[int, float] = {}
    for plat, code in SALES_SOURCES:
        if plat not in plats:
            continue
        rows = MetricDaily.objects.filter(outlet_id__in=outlets, platform_id=plat, kpi__code=code, metric_date=day).values("outlet_id").annotate(v=Sum("value"))
        for r in rows:
            out[r["outlet_id"]] = out.get(r["outlet_id"], 0.0) + float(r["v"] or 0)
    return out


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
    # the whole client: every active outlet of every active brand mapped to it (limited to what this login may see)
    # a client login: its own client. A SocialSpork admin login has no single client, so it is every client's outlets together
    scope = BrandOutlet.objects.filter(brand__is_active=True, brand__client__is_active=True, is_active=True).select_related("brand")
    if not is_staff(request.user):
        scope = scope.filter(brand__client_id=brand.client_id)
    scope_rows = list(in_scope(scope, request.user, "id"))
    outlets = {o.id for o in scope_rows}
    brand_names = sorted({o.brand.name for o in scope_rows})
    if outlet_ids(qp.get("outlet_id")):
        outlets &= set(outlet_ids(qp.get("outlet_id")))
    platform = qp.get("platform") or None
    plats = [p for p, _ in SALES_SOURCES if not platform or platform == p]

    def day_sales(d):
        return sum(_sales(outlets, p, d, d) for p in plats)

    # the day: yesterday, or the latest earlier day that has any sales
    day = date.today() - timedelta(days=1)
    for _ in range(45):
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

    # outlets: who gained and who dropped against the same weekday last week (in rupees, so a tiny outlet's big percentage doesn't crowd out the real movers)
    now_o, was_o = _by_outlet(outlets, plats, day), _by_outlet(outlets, plats, day - timedelta(days=7))
    moves = [(oid, now_o.get(oid, 0.0), was_o.get(oid, 0.0)) for oid in set(now_o) | set(was_o)]
    many = len(brand_names) > 1
    names = {o.id: " · ".join(x for x in ((o.brand.name if many else ""), o.outlet_name, o.area) if x) for o in scope_rows}
    row = lambda m: {"name": names.get(m[0], f"Outlet {m[0]}"), "sales": round(m[1], 2), "last_week": round(m[2], 2), "diff": round(m[1] - m[2], 2), "change": _pct(m[1], m[2])}
    ups = sorted((m for m in moves if m[1] - m[2] > 0), key=lambda m: m[2] - m[1])[:3]
    downs = sorted((m for m in moves if m[1] - m[2] < 0), key=lambda m: m[1] - m[2])[:3]
    outlet_card = {"count": len(outlets), "reporting": len(now_o), "up": [row(m) for m in ups], "down": [row(m) for m in downs], "compared": bool(was_o)}

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
        "empty": False, "client": "All clients" if is_staff(request.user) else brand.client.name, "brands": brand_names, "outlet_count": len(outlets), "date": day.isoformat(), "weekday": day.strftime("%A"),
        "sales": {"value": round(cur, 2), "last_week": round(prev, 2), "change": _pct(cur, prev), "usual": round(sum(usual) / len(usual), 2) if usual else None, "bars": bars},
        "orders": {"value": int(_kpi_sum(outlets, ["delivered_orders"], day, platform))},
        "platforms": by_platform, "outlets": outlet_card,
        "reviews": {**rv, "pending": pending.count()},
        "leakage": {**{k: round(v, 2) for k, v in leak.items()}, "total": round(sum(leak.values()), 2)},
    })
