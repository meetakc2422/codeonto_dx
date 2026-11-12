"""What top-selling items out of stock are costing, estimated from the outlet's own order history.

For an outlet's best sellers (the items that make up most of its units, from the last 30 days of orders) we learn how many
it normally sells in each mealtime, counting only days the item was in stock. An item that is out now is then valued for
the hours it has been out today: expected units for those hours x its price. The answer is a range: the low end assumes
some customers order something else instead. Items without enough history get no figure, never a guess."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Sum

from apps.insights.models import ItemSalesDaily
from apps.orders.models import OrderLine

from .models import StockOut

IST = ZoneInfo("Asia/Kolkata")
WINDOW_DAYS = 30        # how far back demand is learned from
TOP_SHARE = 0.8         # best sellers: the items that make up this share of the outlet's units...
TOP_MAX = 20            # ...but never more than this many
MIN_UNITS = 8           # an item needs this many sales in the window to count as a best seller
MIN_DAYS = 7            # and this many in-stock days before we put a rupee figure on it
LOW_FACTOR = 0.4        # low end of the range: share of the loss that is real if some customers choose something else
SOLD = ("Delivered", "Picked up")
MEALS = {"Breakfast": (5, 12), "Lunch": (12, 16), "Evening Snacks": (16, 19), "Dinner": (19, 23), "Late Night Dinner": (23, 29)}


def service_day(moment: datetime) -> date:
    """The service day (5 am to 5 am) a moment belongs to."""
    return (moment.astimezone(IST) - timedelta(hours=5)).date()


def expected_loss(rate: dict[str, float], out_since: datetime, now: datetime, price: float | None) -> dict:
    """Units (and ₹ range) an item would have sold in the hours it has been out so far this service day.
    rate: expected units per meal on a normal in-stock day."""
    day = service_day(now)
    base = datetime.combine(day, datetime.min.time(), tzinfo=IST)
    units = 0.0
    for meal, (h1, h2) in MEALS.items():
        start, end = base + timedelta(hours=h1), base + timedelta(hours=h2)
        lo, hi = max(start, out_since), min(end, now)
        if hi > lo:
            units += rate.get(meal, 0.0) * ((hi - lo).total_seconds() / (end - start).total_seconds())
    high = units * price if price else None
    return {"units": round(units, 1), "high": round(high) if high is not None else None,
            "low": round(high * LOW_FACTOR) if high is not None else None}


def best_sellers(outlet_ids, today: date) -> dict[int, set[str]]:
    """{outlet: item names}: the items making up most of the outlet's units over the window."""
    since = today - timedelta(days=WINDOW_DAYS)
    by_outlet = defaultdict(list)
    rows = (OrderLine.objects.filter(outlet_id__in=outlet_ids, status__in=SOLD, order_date__gte=since, order_date__lt=today)
            .values("outlet_id", "item_name").annotate(u=Sum("quantity")))
    for r in rows:
        by_outlet[r["outlet_id"]].append((r["item_name"], r["u"]))
    top = {}
    for oid, items in by_outlet.items():
        items.sort(key=lambda x: -x[1])
        total, cum, keep = sum(u for _, u in items), 0, set()
        for name, u in items:
            if u < MIN_UNITS or len(keep) >= TOP_MAX or (cum >= TOP_SHARE * total and keep):
                break
            keep.add(name)
            cum += u
        top[oid] = keep
    return top


def meal_rates(outlet_id: int, item: str, today: date, out_days: set[date]) -> tuple[dict[str, float], int]:
    """({meal: units per in-stock day}, number of in-stock days) for one item, ignoring days it was out of stock."""
    since = today - timedelta(days=WINDOW_DAYS)
    days = {since + timedelta(days=i) for i in range((today - since).days)} - out_days
    if not days:
        return {}, 0
    units = defaultdict(float)
    for r in (OrderLine.objects.filter(outlet_id=outlet_id, item_name=item, status__in=SOLD, order_date__in=days)
              .values("mealtime").annotate(u=Sum("quantity"))):
        units[r["mealtime"]] += float(r["u"])
    return {m: u / len(days) for m, u in units.items()}, len(days)


def price_of(outlet_id: int, item: str) -> float | None:
    """What the item sells for: the latest price in the item sales report, else the latest single-item order."""
    p = (ItemSalesDaily.objects.filter(outlet_id=outlet_id, item_name=item, unit_price__gt=0).order_by("-day")
         .values_list("unit_price", flat=True).first())
    if p is None:
        p = (OrderLine.objects.filter(outlet_id=outlet_id, item_name=item, unit_price__gt=0).order_by("-placed_at")
             .values_list("unit_price", flat=True).first())
    return float(p) if p is not None else None


def top_sellers_out(active: list[StockOut], now: datetime) -> dict:
    """The currently out items that are best sellers, with what they have cost so far today.
    -> {"items": [{item_name, outlets, since, units, low, high, price, enough_history}], "low": ₹, "high": ₹}"""
    if not active:
        return {"items": [], "low": 0, "high": 0}
    today = service_day(now)
    top = best_sellers({s.outlet_id for s in active}, today)
    since = today - timedelta(days=WINDOW_DAYS)
    episodes = defaultdict(set)  # (outlet, item) -> days it was out
    for e in StockOut.objects.filter(outlet_id__in=list(top), log_date__gte=since - timedelta(days=60)):
        end = (e.restored_at or now).astimezone(IST).date()
        d = max(e.log_date, since)
        while d <= end:
            episodes[(e.outlet_id, e.item_name)].add(d)
            d += timedelta(days=1)
    merged: dict[str, dict] = {}
    for s in active:
        if s.item_name not in top.get(s.outlet_id, ()):
            continue
        rate, n = meal_rates(s.outlet_id, s.item_name, today, episodes.get((s.outlet_id, s.item_name), set()))
        price = price_of(s.outlet_id, s.item_name)
        enough = n >= MIN_DAYS
        loss = expected_loss(rate, s.first_detected_at, now, price) if enough else {"units": None, "high": None, "low": None}
        m = merged.setdefault(s.item_name, {"item_name": s.item_name, "outlets": 0, "since": s.first_detected_at, "units": 0.0, "low": 0, "high": 0,
                                            "price": price, "enough_history": True})
        m["outlets"] += 1
        m["since"] = min(m["since"], s.first_detected_at)
        m["enough_history"] = m["enough_history"] and enough
        if loss["units"] is not None:
            m["units"] += loss["units"]
            m["low"] += loss["low"] or 0
            m["high"] += loss["high"] or 0
    items = sorted(merged.values(), key=lambda x: -x["high"])
    return {"items": items, "low": sum(i["low"] for i in items), "high": sum(i["high"] for i in items)}


def rejected_for_stock(outlet_ids, start: date, end: date) -> dict:
    """Orders the restaurant rejected because an item was out of stock, in the period: a measured loss, not an estimate."""
    rows = (OrderLine.objects.filter(outlet_id__in=outlet_ids, rejection_reason__iexact="Items out of stock", order_date__range=(start, end))
            .values("order_id", "order_subtotal").distinct())
    value = sum(float(r["order_subtotal"] or 0) for r in rows)
    return {"orders": len(rows), "value": round(value)}
