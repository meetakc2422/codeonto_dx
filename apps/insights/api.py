"""Insights that join several modules' data."""

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.complaints.models import Complaint
from apps.listings.models import OutletHours
from apps.outlets.access import get_brand, in_scope, outlet_ids
from apps.payouts.models import PayoutCycle, PayoutOrder
from apps.reviews.models import Review
from apps.stockouts.models import StockOut
from apps.uptime.models import OfflineEpisode

from .models import ItemSalesDaily

TZ = ZoneInfo(settings.TIME_ZONE)
# usual sales come from this many days of history before the period's end
HISTORY_DAYS = 28
# an outlet's own hour-by-hour pattern is used only with at least this many days of orders; below it, sales are spread
# evenly over its opening hours
MIN_PATTERN_DAYS = 14
DEFAULT_HOURS = range(11, 23)
LOST_ORDER_STATUSES = ["CANCELLED", "REJECTED"]


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


class SalesModel:
    """How much an outlet usually sells, and when in the day. Built from delivered payout orders (timestamps) and
    opening hours."""

    def __init__(self, outlet_ids: set[int], end: date):
        start = end - timedelta(days=HISTORY_DAYS)
        hourly, days, plat_total, plat_days = defaultdict(lambda: [0.0] * 24), defaultdict(set), defaultdict(float), defaultdict(set)
        rows = (PayoutOrder.objects.filter(cycle__outlet_id__in=outlet_ids, status="DELIVERED", order_date__date__range=(start, end))
                .values_list("cycle__outlet_id", "cycle__platform_id", "order_date", "subtotal"))
        for outlet_id, platform, at, subtotal in rows:
            at = at.astimezone(TZ)
            hourly[outlet_id][at.hour] += float(subtotal)
            days[outlet_id].add(at.date())
            plat_total[(outlet_id, platform)] += float(subtotal)
            plat_days[(outlet_id, platform)].add(at.date())
        open_hours = defaultdict(set)
        for o, s, e in OutletHours.objects.filter(outlet_id__in=outlet_ids, is_active=True, start_time__isnull=False).values_list("outlet_id", "start_time", "end_time"):
            h = s.hour
            for _ in range(24):
                open_hours[o].add(h)
                h = (h + 1) % 24
                if h == (e.hour if e.minute == 0 else e.hour + 1) % 24:
                    break
        self.shape, self.basis = {}, {}
        for o in outlet_ids:
            if len(days[o]) >= MIN_PATTERN_DAYS:
                total = sum(hourly[o]) or 1
                self.shape[o] = [v / total for v in hourly[o]]
                self.basis[o] = f"{len(days[o])} days of orders"
            else:
                hours = open_hours[o] or set(DEFAULT_HOURS)
                self.shape[o] = [1 / len(hours) if h in hours else 0 for h in range(24)]
                self.basis[o] = f"estimate: {len(days[o])} days of orders, spread over opening hours"
        self.daily = {k: v / len(plat_days[k]) for k, v in plat_total.items()}
        self.order_days = {k: len(v) for k, v in plat_days.items()}

    def share(self, outlet_id: int, start: datetime, end: datetime) -> float:
        """Share of a usual day's sales that falls between start and end (more than 1 when it spans several days)."""
        shape, t, total = self.shape[outlet_id], start.astimezone(TZ), 0.0
        end = end.astimezone(TZ)
        while t < end:
            slot_end = min(end, t.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            total += shape[t.hour] * (slot_end - t).total_seconds() / 3600
            t = slot_end
        return total


def _item_daily_sales(outlet_ids: set[int], end: date) -> dict:
    """(outlet_id, item name) -> usual ₹ sold per day: item revenue over the history window / days the outlet sold anything."""
    start = end - timedelta(days=HISTORY_DAYS)
    qs = ItemSalesDaily.objects.filter(outlet_id__in=outlet_ids, day__range=(start, end), unit_price__isnull=False)
    active_days = {r["outlet_id"]: r["n"] for r in qs.values("outlet_id").annotate(n=Count("day", distinct=True))}
    out = defaultdict(float)
    for r in qs.values("outlet_id", "item_name").annotate(v=Sum(F("quantity") * F("unit_price"))):
        out[(r["outlet_id"], _norm(r["item_name"]))] += float(r["v"] or 0) / active_days[r["outlet_id"]]
    return out


def stockout_losses(stockouts: list, end: date, since: datetime | None = None, until: datetime | None = None) -> list[tuple]:
    """[(stock-out, hours out, ₹ missed or None when the item has no sales history)], and the SalesModel used.
    since / until clip each episode to a period, so a stock-out that started before it only counts its hours inside."""
    if not stockouts:
        return [], None
    model = SalesModel({s.outlet_id for s in stockouts}, end)
    items = _item_daily_sales({s.outlet_id for s in stockouts}, end)
    out = []
    for s in stockouts:
        s_start, s_end = s.first_detected_at, s.restored_at or s.last_detected_at
        if since or until:
            s_start, s_end = max(s_start, since or s_start), min(s_end, until or s_end)
            minutes = max(0.0, (s_end - s_start).total_seconds() / 60)
        else:
            minutes = s.downtime_minutes if s.downtime_minutes is not None else (s_end - s_start).total_seconds() / 60
        daily = items.get((s.outlet_id, _norm(s.item_name)))
        loss = None if daily is None else (daily * model.share(s.outlet_id, s_start, s_end) if s_end > s_start else 0.0)
        out.append((s, minutes / 60, loss))
    return out, model


def _episode_end(e) -> datetime:
    return e.restored_at or (timezone.now() if e.is_active else e.last_detected_at)


@api_view(["GET"])
def money_leaked(request, brand_id):
    """₹ the brand lost in the period, by cause and by outlet, with the basis of every estimate."""
    get_brand(request.user, brand_id)
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)

    def scoped(qs, field="outlet_id"):
        qs = in_scope(qs, request.user, field)
        if outlet_ids(qp.get("outlet_id")):
            qs = qs.filter(**{f"{field}__in": outlet_ids(qp.get("outlet_id"))})
        if qp.get("platform"):
            qs = qs.filter(**{field.replace("outlet_id", "platform_id"): qp["platform"]})
        return qs

    by_outlet = defaultdict(lambda: defaultdict(float))

    complaints = scoped(Complaint.objects.filter(outlet__brand_id=brand_id, raised_at__date__range=(start, end)))
    for r in complaints.values("outlet_id").annotate(v=Sum("refund_amount"), n=Count("id", filter=Q(refund_amount__gt=0))):
        by_outlet[r["outlet_id"]]["refunds"] += float(r["v"] or 0)
        by_outlet[r["outlet_id"]]["refunds_n"] += r["n"]

    orders = scoped(PayoutOrder.objects.filter(cycle__outlet__brand_id=brand_id, status__in=LOST_ORDER_STATUSES,
                                               order_date__date__range=(start, end)), "cycle__outlet_id")
    for r in orders.values("cycle__outlet_id").annotate(v=Sum("subtotal"), n=Count("id")):
        by_outlet[r["cycle__outlet_id"]]["lost_orders"] += float(r["v"] or 0)
        by_outlet[r["cycle__outlet_id"]]["lost_orders_n"] += r["n"]

    cycles = scoped(PayoutCycle.objects.filter(outlet__brand_id=brand_id, discrepancy__lt=0, end_date__range=(start, end)))
    for r in cycles.values("outlet_id").annotate(v=Sum("discrepancy"), n=Count("id")):
        by_outlet[r["outlet_id"]]["payout_short"] += -float(r["v"])
        by_outlet[r["outlet_id"]]["payout_short_n"] += r["n"]

    episodes = list(scoped(OfflineEpisode.objects.filter(outlet__brand_id=brand_id, log_date__range=(start, end))))
    stockouts = list(scoped(StockOut.objects.filter(outlet__brand_id=brand_id, log_date__range=(start, end))))
    outlet_ids = {e.outlet_id for e in episodes} | {s.outlet_id for s in stockouts}
    model = SalesModel(outlet_ids, end) if outlet_ids else None

    for e in episodes:
        o = by_outlet[e.outlet_id]
        o["offline_minutes"] += e.downtime_minutes
        daily = model.daily.get((e.outlet_id, e.platform_id))
        if daily:
            o["offline"] += daily * model.share(e.outlet_id, e.first_detected_at, _episode_end(e))
        else:
            o["offline_unpriced_minutes"] += e.downtime_minutes

    for s, hours, loss in stockout_losses(stockouts, end)[0]:
        o = by_outlet[s.outlet_id]
        o["stockout_hours"] += hours
        o["stockouts_n"] += 1
        if loss is None:
            o["stockouts_unmatched"] += 1
        else:
            o["stockouts"] += loss

    money = ("refunds", "stockouts", "offline", "lost_orders", "payout_short")
    sums = defaultdict(float)
    for v in by_outlet.values():
        for k, x in v.items():
            sums[k] += x
    outlets = sorted(({"outlet_id": oid, "total": round(sum(v[k] for k in money)), **{k: round(x, 1) for k, x in v.items()},
                       "basis": model.basis.get(oid) if model else None}
                      for oid, v in by_outlet.items()), key=lambda o: (-o["total"], -o.get("stockout_hours", 0)))
    estimated = [o for o in outlet_ids if model and model.basis[o].startswith("estimate")]

    def notes(*parts):
        return "; ".join(p for p in parts if p)

    causes = [
        {"key": "refunds", "label": "Complaint refunds & coupons", "amount": round(sums["refunds"]), "count": int(sums["refunds_n"]),
         "unit": "complaints", "note": "requested or issued on Zomato / Swiggy, as the platform reports them", "estimate": False},
        {"key": "stockouts", "label": "Sales missed on stock-outs", "amount": round(sums["stockouts"]), "count": round(sums["stockout_hours"]),
         "unit": "item-hours out", "estimate": True,
         "note": notes(f"each item's usual daily Zomato sales (last {HISTORY_DAYS} days) × the share of the day it was out",
                       f"{int(sums['stockouts_unmatched'])} of {int(sums['stockouts_n'])} items had no sales history and are not counted" if sums["stockouts_unmatched"] else "")},
        {"key": "offline", "label": "Sales missed while offline", "amount": round(sums["offline"]), "count": round(sums["offline_minutes"] / 60, 1),
         "unit": "hours offline", "estimate": True,
         "note": notes(f"the outlet's usual daily sales on that platform × the share of the day it was offline",
                       f"{round(sums['offline_unpriced_minutes'] / 60, 1)} h not counted (no order history)" if sums["offline_unpriced_minutes"] else "")},
        {"key": "lost_orders", "label": "Cancelled / rejected orders", "amount": round(sums["lost_orders"]), "count": int(sums["lost_orders_n"]),
         "unit": "orders", "note": "order value; check the cancellation reason", "estimate": False},
        {"key": "payout_short", "label": "Payouts below expected", "amount": round(sums["payout_short"]), "count": int(sums["payout_short_n"]),
         "unit": "cycles", "note": "from reconciliation", "estimate": False},
    ]
    return Response({
        "start": start, "end": end, "total": round(sum(c["amount"] for c in causes)),
        "causes": sorted(causes, key=lambda c: -c["amount"]),
        "stockouts": {"item_hours": round(sums["stockout_hours"], 1), "count": int(sums["stockouts_n"])},
        "confidence": {"min_pattern_days": MIN_PATTERN_DAYS, "outlets": len(outlet_ids), "estimated_outlets": len(estimated)},
        "by_outlet": outlets[:30],
    })


ISSUE_KEYS = ["missing_items", "wrong_items", "quality", "quantity", "packaging", "other"]


def _flags(r: dict, avg_complaint_rate: float) -> list[str]:
    """Plain-language problems worth acting on; empty for a healthy item."""
    flags = []
    if r["complaints"] >= 5 and r["complaint_rate"] >= max(1.0, 2 * avg_complaint_rate):
        top = max(ISSUE_KEYS, key=lambda k: r["issues"].get(k, 0))
        flags.append(f"{r['complaint_rate']:.1f} complaints per 100 orders, {r['complaint_rate'] / avg_complaint_rate:.1f}× the brand's average"
                     + (f" (mostly {top.replace('_', ' ')})" if r["issues"].get(top) else "") if avg_complaint_rate else "High complaint rate")
    # out of stock long enough to matter for this item: over a day per outlet that sells it, or 3%+ of its sales
    per_outlet = r["stockout_hours"] / max(1, r["outlets"])
    if r["stockout_loss"] >= 1000 and (per_outlet >= 24 or r["stockout_loss"] >= 0.03 * r["revenue"]):
        flags.append(f"Out of stock {r['stockout_hours']:.0f} h ({r['stockouts']} times), ₹{r['stockout_loss']:,.0f} of sales missed")
    if r["rated"] >= 5 and r["bad_review_pct"] >= 30:
        flags.append(f"{r['bad_review_pct']:.0f}% of {r['rated']} item ratings are 1–2★")
    return flags


@api_view(["GET"])
def item_scorecard(request, brand_id):
    """One row per menu item (by name, across the brand's outlets): sales, stock-outs, complaints and item ratings,
    with flags for the items that need action."""
    from apps.billing.access import require_module

    require_module(request.user, get_brand(request.user, brand_id), "items")
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)

    def scoped(qs):
        qs = in_scope(qs, request.user)
        return qs.filter(outlet_id__in=outlet_ids(qp.get("outlet_id"))) if outlet_ids(qp.get("outlet_id")) else qs

    rows = {}

    def row(name: str, category: str = "") -> dict:
        key = _norm(name)
        if key not in rows:
            rows[key] = {"name": name.strip(), "category": category, "units": 0.0, "revenue": 0.0, "orders": 0, "outlets": set(),
                         "stockouts": 0, "stockout_hours": 0.0, "stockout_loss": 0.0, "complaints": 0, "refunds": 0.0,
                         "issues": defaultdict(int), "rated": 0, "bad": 0, "rating_sum": 0.0}
        elif category and not rows[key]["category"]:
            rows[key]["category"] = category
        return rows[key]

    sales = scoped(ItemSalesDaily.objects.filter(outlet__brand_id=brand_id, day__range=(start, end)))
    for r in sales.values("item_name", "category", "outlet_id").annotate(q=Sum("quantity"), v=Sum(F("quantity") * F("unit_price")), o=Sum("orders")):
        x = row(r["item_name"], r["category"])
        x["units"] += float(r["q"] or 0)
        x["revenue"] += float(r["v"] or 0)
        x["orders"] += r["o"] or 0
        x["outlets"].add(r["outlet_id"])

    stockouts = list(scoped(StockOut.objects.filter(outlet__brand_id=brand_id, log_date__range=(start, end))))
    for s, hours, loss in stockout_losses(stockouts, end)[0]:
        x = row(s.item_name, s.category)
        x["stockouts"] += 1
        x["stockout_hours"] += hours
        x["stockout_loss"] += loss or 0

    # complaints name items as "1 x Name, 2 x Other": match them against the known item names, longest first, so a
    # comma inside a name ("Dumpling, Tom Yum Sauce") doesn't split it
    names = sorted(rows, key=len, reverse=True)
    for c in scoped(Complaint.objects.filter(outlet__brand_id=brand_id, raised_at__date__range=(start, end))).only("items", "refund_amount", "issue_type"):
        text, hit = _norm(c.items), []
        for n in names:
            if n and n in text:
                hit.append(n)
                text = text.replace(n, " ")
        for n in hit:
            x = rows[n]
            x["complaints"] += 1
            x["refunds"] += float(c.refund_amount or 0) / len(hit)
            x["issues"][c.issue_type or "other"] += 1

    for rv in scoped(Review.objects.filter(outlet__brand_id=brand_id, reviewed_at__date__range=(start, end), platform__in=["zomato", "swiggy"])).only("platform", "rating", "raw"):
        raw = rv.raw or {}
        if rv.platform_id == "zomato":
            rated = [(d.get("title"), float(d["rating"])) for d in raw.get("dish_feedbacks") or [] if d.get("title") and d.get("rating")]
        else:
            rated = [(i.get("name"), float(rv.rating)) for i in raw.get("itemsInfo") or [] if i.get("name") and rv.rating is not None]
        for name, stars in rated:
            if _norm(name) in rows:
                x = rows[_norm(name)]
                x["rated"] += 1
                x["rating_sum"] += stars
                x["bad"] += stars <= 2

    total_orders = sum(x["orders"] for x in rows.values())
    total_complaints = sum(x["complaints"] for x in rows.values())
    avg_rate = 100 * total_complaints / total_orders if total_orders else 0
    out = []
    for x in rows.values():
        r = {**x, "outlets": len(x["outlets"]), "issues": dict(x["issues"]),
             "complaint_rate": round(100 * x["complaints"] / x["orders"], 2) if x["orders"] else 0,
             "avg_item_rating": round(x["rating_sum"] / x["rated"], 2) if x["rated"] else None,
             "bad_review_pct": round(100 * x["bad"] / x["rated"]) if x["rated"] else 0}
        for k in ("units", "revenue", "stockout_hours", "stockout_loss", "refunds"):
            r[k] = round(r[k], 1)
        del r["rating_sum"]
        r["flags"] = _flags(r, avg_rate)
        r["money_lost"] = round(r["stockout_loss"] + r["refunds"])
        out.append(r)
    out.sort(key=lambda r: (-len(r["flags"]), -r["money_lost"], -r["revenue"]))
    return Response({
        "start": start, "end": end, "avg_complaint_rate": round(avg_rate, 2),
        "totals": {"items": sum(1 for r in out if r["units"]), "revenue": round(sum(r["revenue"] for r in out)),
                   "flagged": sum(1 for r in out if r["flags"]), "money_lost": round(sum(r["money_lost"] for r in out)),
                   "complaints_matched": total_complaints},
        "items": out[:int(qp.get("limit", 300))],
    })
