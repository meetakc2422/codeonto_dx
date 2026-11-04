"""Alert rules. Each rule looks at one store and returns (severity, title, detail) when something needs
attention, or None. evaluate() keeps the alerts table in step: it opens, refreshes and resolves rows."""

from datetime import date, timedelta

from django.db import connection
from django.utils import timezone

from apps.listings.models import ListingProfile
from apps.outlets.models import BrandOutlet
from apps.reviews.models import Review

from .models import Alert


def _sum(outlet_id: int, kpis: list[str], start: date, end: date) -> float:
    with connection.cursor() as cur:
        cur.execute("""SELECT COALESCE(SUM(m.value), 0) FROM metric_daily m JOIN kpis k ON k.id = m.kpi_id
                       WHERE m.outlet_id = %s AND k.code = ANY(%s) AND m.metric_date BETWEEN %s AND %s""",
                    (outlet_id, kpis, start, end))
        return float(cur.fetchone()[0])


def views_drop(o):
    end = date.today() - timedelta(days=3)  # Google data lags; compare two complete weeks
    now_w, prev_w = _sum(o.id, ["profile_views"], end - timedelta(days=6), end), _sum(o.id, ["profile_views"], end - timedelta(days=13), end - timedelta(days=7))
    if prev_w >= 50 and now_w <= prev_w * 0.7:
        drop = round((1 - now_w / prev_w) * 100)
        return ("critical" if drop >= 50 else "warning", f"Google views down {drop}%", f"{int(now_w)} profile views last week vs {int(prev_w)} the week before.")


def actions_drop(o):
    end = date.today() - timedelta(days=3)
    kpis = ["call_clicks", "direction_requests", "website_clicks"]
    now_w, prev_w = _sum(o.id, kpis, end - timedelta(days=6), end), _sum(o.id, kpis, end - timedelta(days=13), end - timedelta(days=7))
    if prev_w >= 10 and now_w <= prev_w * 0.6:
        return ("warning", f"Customer actions down {round((1 - now_w / prev_w) * 100)}%",
                f"{int(now_w)} calls, directions and website clicks last week vs {int(prev_w)} before.")


def rating_drop(o):
    now = timezone.now()
    recent = Review.objects.filter(outlet=o, reviewed_at__gte=now - timedelta(days=14), rating__isnull=False)
    before = Review.objects.filter(outlet=o, reviewed_at__gte=now - timedelta(days=28), reviewed_at__lt=now - timedelta(days=14), rating__isnull=False)
    r, b = list(recent.values_list("rating", flat=True)), list(before.values_list("rating", flat=True))
    if len(r) >= 5 and len(b) >= 5:
        ra, ba = sum(r) / len(r), sum(b) / len(b)
        if ba - ra >= 0.3:
            return ("warning", f"Rating dropped {ba - ra:.1f}★", f"Average {float(ra):.2f}★ over the last 14 days vs {float(ba):.2f}★ in the 14 days before.")


def negative_spike(o):
    n = Review.objects.filter(outlet=o, reviewed_at__gte=timezone.now() - timedelta(days=3), rating__lte=2).count()
    if n >= 3:
        return ("critical", f"{n} negative reviews in 3 days", "Three or more 1–2★ reviews arrived in the last three days.")


def reply_backlog(o):
    n = Review.objects.filter(outlet=o, reply_status="pending", reviewed_at__lte=timezone.now() - timedelta(days=3)).count()
    if n >= 5:
        return ("warning", f"{n} reviews waiting over 3 days", "Reviews older than three days still have no reply.")


def listing_problem(o):
    p = ListingProfile.objects.filter(outlet=o, platform_id="google").first()
    if not p:
        return None
    if p.open_status and p.open_status != "OPEN":
        return ("critical", "Google listing is not open", f"Listing status: {p.open_status.replace('_', ' ').title()}.")
    if p.health_score < 60:
        return ("warning", f"Listing health {p.health_score}/100", "Fix: " + "; ".join(i["label"] for i in p.issues[:3]))


def heavy_stockouts(o):
    from apps.stockouts.models import StockOut
    n = StockOut.objects.filter(outlet=o, is_active=True).count()
    if n >= 40:
        return ("warning", f"{n} items out of stock", "The menu is badly thinned out; customers may be seeing little to order.")


def store_offline(o):
    from apps.uptime.models import OfflineEpisode
    e = OfflineEpisode.objects.filter(outlet=o, is_active=True, downtime_minutes__gte=15).select_related("platform").first()
    if e:
        m = e.downtime_minutes
        length = f"{m // 60}h {m % 60}m" if m >= 60 else f"{m} min"
        return ("critical", f"Offline on {e.platform.name} for {length}", "The store is not taking orders during its opening hours.")


RULES = {"views_drop": views_drop, "actions_drop": actions_drop, "rating_drop": rating_drop,
         "negative_spike": negative_spike, "reply_backlog": reply_backlog, "listing_problem": listing_problem,
         "heavy_stockouts": heavy_stockouts, "store_offline": store_offline}


def evaluate() -> dict:
    """Run every rule on every active store. Returns counts and the alerts opened this run."""
    opened, resolved, refreshed = [], 0, 0
    for o in BrandOutlet.objects.filter(is_active=True).select_related("brand"):
        for kind, rule in RULES.items():
            hit = rule(o)
            current = Alert.objects.filter(outlet=o, kind=kind, is_open=True).first()
            if hit:
                severity, title, detail = hit
                if current:
                    current.severity, current.title, current.detail = severity, title, detail
                    current.save(update_fields=["severity", "title", "detail", "last_seen_at"])
                    refreshed += 1
                else:
                    opened.append(Alert.objects.create(outlet=o, kind=kind, severity=severity, title=title, detail=detail))
            elif current:
                current.is_open, current.resolved_at = False, timezone.now()
                current.save(update_fields=["is_open", "resolved_at", "last_seen_at"])
                resolved += 1
    return {"opened": opened, "refreshed": refreshed, "resolved": resolved}
