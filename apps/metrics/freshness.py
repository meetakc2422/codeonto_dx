"""When did each kind of data last arrive for this brand? The dashboard tags a module that has gone quiet."""
from datetime import datetime, time, timezone as dt_tz

from django.db.models import Max
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.insights.models import ItemSalesDaily
from apps.metrics.models import MetricDaily
from apps.orders.models import OrderLine
from apps.outlets.access import get_brand, in_scope
from apps.payouts.models import PayoutCycle
from apps.reviews.models import Review
from apps.stockouts.models import StockOut
from apps.uptime.models import UptimeDaily
from .http_cache import cached_get

# key, label, model, timestamp field, hours of silence before it counts as late, platforms to check
SOURCES = [
    ("sales", "Sales & KPIs", MetricDaily, "updated_at", 36, ("zomato", "swiggy")),
    ("orders", "Order history", OrderLine, "created_at", 36, ("zomato", "swiggy")),
    ("item_sales", "Item sales", ItemSalesDaily, "day", 60, ("zomato", "swiggy")),
    ("uptime", "Store uptime", UptimeDaily, "updated_at", 12, ("zomato",)),
    ("stock_outs", "Stock-outs", StockOut, "last_detected_at", 24, ("zomato", "swiggy")),
    ("reviews", "Reviews", Review, "created_at", 72, ("zomato", "swiggy")),
    ("payouts", "Payouts", PayoutCycle, "fetched_at", 48, ("zomato", "swiggy")),
]


def _aware(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.max, tzinfo=dt_tz.utc)  # a plain date: end of that day


@api_view(["GET"])
@cached_get(60)
def brand_freshness(request, brand_id):
    brand = get_brand(request.user, brand_id)
    now = timezone.now()
    out = []
    for key, label, model, field, limit_hours, platforms in SOURCES:
        # one grouped query per source (the latest of each platform), not one per source and platform: each reads the table once
        qs = in_scope(model.objects.filter(outlet__brand_id=brand.id, platform_id__in=platforms), request.user)
        latest = {r["platform_id"]: r["m"] for r in qs.order_by().values("platform_id").annotate(m=Max(field))}
        for platform in platforms:
            last = _aware(latest.get(platform))
            age = round((now - last).total_seconds() / 3600, 1) if last else None
            out.append({"key": key, "label": label, "platform": platform, "last_at": last, "age_hours": age,
                        "limit_hours": limit_hours,
                        "status": "none" if last is None else ("late" if age > limit_hours else "ok")})
    return Response({"sources": out})
