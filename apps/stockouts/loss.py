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
EPISODES_SHOWN = 40     # stock-outs listed per dish in the breakdown panel
ITEMS_WITH_EPISODES = 12  # dishes that carry that list (the rest are totals only)
NEGLIGIBLE_PCT = 5      # a stock-out that loses under this % of a normal day's sales of the dish at that outlet is shown as negligible
CAP_DAYS = 3            # a stock-out counts for at most its first 3 days: beyond that the dish is more likely delisted than lost sales (same rule as the 'off 3+ days' group)
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


def best_sellers(outlet_ids, today: date, platform=None) -> dict[int, set[str]]:
    """{outlet: item names}: the items making up most of the outlet's units over the window (on one platform when given)."""
    since = today - timedelta(days=WINDOW_DAYS)
    by_outlet = defaultdict(list)
    qs = OrderLine.objects.filter(outlet_id__in=outlet_ids, status__in=SOLD, order_date__gte=since, order_date__lt=today)
    rows = (qs.filter(platform_id=platform) if platform else qs).values("outlet_id", "item_name").annotate(u=Sum("quantity"))
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


def meal_rates(outlet_id: int, item: str, today: date, out_days: set[date], platform=None) -> tuple[dict[str, float], int]:
    """({meal: units per in-stock day}, number of in-stock days) for one item, ignoring days it was out of stock."""
    since = today - timedelta(days=WINDOW_DAYS)
    days = {since + timedelta(days=i) for i in range((today - since).days)} - out_days
    if not days:
        return {}, 0
    units = defaultdict(float)
    lines = OrderLine.objects.filter(outlet_id=outlet_id, item_name=item, status__in=SOLD, order_date__in=days)
    for r in (lines.filter(platform_id=platform) if platform else lines).values("mealtime").annotate(u=Sum("quantity")):
        units[r["mealtime"]] += float(r["u"])
    return {m: u / len(days) for m, u in units.items()}, len(days)


def price_of(outlet_id: int, item: str, platform=None) -> float | None:
    """What the item sells for: the latest price in the item sales report, else the latest single-item order (on one platform when given)."""
    sales = ItemSalesDaily.objects.filter(outlet_id=outlet_id, item_name=item, unit_price__gt=0)
    p = (sales.filter(platform_id=platform) if platform else sales).order_by("-day").values_list("unit_price", flat=True).first()
    if p is None:
        lines = OrderLine.objects.filter(outlet_id=outlet_id, item_name=item, unit_price__gt=0)
        p = (lines.filter(platform_id=platform) if platform else lines).order_by("-placed_at").values_list("unit_price", flat=True).first()
    return float(p) if p is not None else None


def _top_sellers_out_one(active: list[StockOut], now: datetime, platform) -> dict:
    """The currently out items that are best sellers, with what they have cost so far today.
    -> {"items": [{item_name, outlets, since, units, low, high, price, enough_history}], "low": ₹, "high": ₹}"""
    if not active:
        return {"items": [], "low": 0, "high": 0, "by_meal": {}}
    today = service_day(now)
    top = best_sellers({s.outlet_id for s in active}, today, platform)
    since = today - timedelta(days=WINDOW_DAYS)
    episodes = defaultdict(set)  # (outlet, item) -> days it was out
    for e in StockOut.objects.filter(outlet_id__in=list(top), platform_id=platform, log_date__gte=since - timedelta(days=60)):
        end = (e.restored_at or now).astimezone(IST).date()
        d = max(e.log_date, since)
        while d <= end:
            episodes[(e.outlet_id, e.item_name)].add(d)
            d += timedelta(days=1)
    merged: dict[str, dict] = {}
    for s in active:
        if s.item_name not in top.get(s.outlet_id, ()):
            continue
        rate, n = meal_rates(s.outlet_id, s.item_name, today, episodes.get((s.outlet_id, s.item_name), set()), platform)
        price = price_of(s.outlet_id, s.item_name, platform)
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


def top_sellers_out(active: list[StockOut], now: datetime) -> dict:
    """Same, for stock-outs on several platforms: each is valued with its own platform's orders, then the dishes are added up by name."""
    by_platform = defaultdict(list)
    for s in active:
        by_platform[s.platform_id].append(s)
    parts = [_top_sellers_out_one(rows, now, plat) for plat, rows in by_platform.items()]
    merged: dict[str, dict] = {}
    for part in parts:
        for it in part["items"]:
            m = merged.get(it["item_name"])
            if not m:
                merged[it["item_name"]] = dict(it)
                continue
            m["outlets"] += it["outlets"]
            m["since"] = min(m["since"], it["since"])
            m["units"] += it["units"]
            m["low"] += it["low"]
            m["high"] += it["high"]
            m["enough_history"] = m["enough_history"] and it["enough_history"]
            m["price"] = m["price"] or it["price"]
    items = sorted(merged.values(), key=lambda x: -x["high"])
    return {"items": items, "low": sum(i["low"] for i in items), "high": sum(i["high"] for i in items)}


def rejected_for_stock(outlet_ids, start: date, end: date) -> dict:
    """Orders rejected or cancelled because an item was out of stock (Zomato's and Swiggy's reason mentions it), in the period: a measured loss, not an estimate."""
    rows = (OrderLine.objects.filter(outlet_id__in=outlet_ids, rejection_reason__icontains="out of stock", order_date__range=(start, end))
            .values("order_id", "order_subtotal").distinct())
    value = sum(float(r["order_subtotal"] or 0) for r in rows)
    return {"orders": len(rows), "value": round(value)}


def _outlet_label(o) -> str:
    """The outlet's name, with its area when the name alone does not tell outlets of a chain apart."""
    extra = o.area or o.city
    return f"{o.outlet_name} · {extra}" if extra and extra.lower() not in o.outlet_name.lower() else o.outlet_name


def _period_bounds(start: date, end: date, now: datetime) -> tuple[datetime, datetime]:
    """The service days start..end (5 am to 5 am), never past now."""
    lo = datetime.combine(start, datetime.min.time(), tzinfo=IST) + timedelta(hours=5)
    return lo, min(datetime.combine(end, datetime.min.time(), tzinfo=IST) + timedelta(days=1, hours=5), now)


def _units_by_meal(rate: dict[str, float], a: datetime, b: datetime) -> dict[str, float]:
    """Expected units over the hours a..b, per meal: each service day's meal windows that overlap it, at the normal rate per meal."""
    units, d = defaultdict(float), service_day(a)
    while d <= service_day(b):
        base = datetime.combine(d, datetime.min.time(), tzinfo=IST)
        for meal, (h1, h2) in MEALS.items():
            s, e = base + timedelta(hours=h1), base + timedelta(hours=h2)
            lo, hi = max(s, a), min(e, b)
            if hi > lo:
                units[meal] += rate.get(meal, 0.0) * ((hi - lo).total_seconds() / (e - s).total_seconds())
        d += timedelta(days=1)
    return units


def _period_loss_one(platform, episodes: list[StockOut], start: date, end: date, now: datetime, long_cutoff: datetime) -> dict:
    """What best sellers cost over the period: every stock-out of a best seller, valued for the hours it was out
    (expected units for those hours x price), as a low-high range. Each stock-out counts for at most CAP_DAYS, and items
    still out past long_cutoff are left out: beyond that they are most likely delisted, not lost sales.
    -> {"items": [{item_name, outlets, units, low, high, price}], "low": ₹, "high": ₹}"""
    lo_t, hi_t = _period_bounds(start, end, now)
    eps = [e for e in episodes if not (e.is_active and e.first_detected_at < long_cutoff)]
    if not eps:
        return {"items": [], "low": 0, "high": 0, "by_meal": {}}
    today = service_day(now)
    top = best_sellers({e.outlet_id for e in eps}, today, platform)
    eps = [e for e in eps if e.item_name in top.get(e.outlet_id, ())]
    if not eps:
        return {"items": [], "low": 0, "high": 0, "by_meal": {}}
    pairs = {(e.outlet_id, e.item_name) for e in eps}
    outlets = {o for o, _ in pairs}
    since = today - timedelta(days=WINDOW_DAYS)
    window = {since + timedelta(days=i) for i in range((today - since).days)}

    out_days = defaultdict(set)  # days each item was out in the learning window: not normal demand
    for e in StockOut.objects.filter(outlet_id__in=outlets, platform_id=platform, log_date__gte=since - timedelta(days=60)):
        if (e.outlet_id, e.item_name) in pairs:
            d, last = max(e.log_date, since), (e.restored_at or now).astimezone(IST).date()
            while d <= last:
                out_days[(e.outlet_id, e.item_name)].add(d)
                d += timedelta(days=1)
    sold = defaultdict(list)  # (outlet, item) -> [(meal, day, units)]
    for r in (OrderLine.objects.filter(outlet_id__in=outlets, platform_id=platform, status__in=SOLD, order_date__gte=since, order_date__lt=today)
              .values("outlet_id", "item_name", "mealtime", "order_date").annotate(u=Sum("quantity"))):
        if (r["outlet_id"], r["item_name"]) in pairs:
            sold[(r["outlet_id"], r["item_name"])].append((r["mealtime"], r["order_date"], float(r["u"])))
    price = {}
    for o, i, p in (OrderLine.objects.filter(outlet_id__in=outlets, platform_id=platform, unit_price__gt=0, order_date__gte=since).order_by("-placed_at")
                    .values_list("outlet_id", "item_name", "unit_price")):
        if (o, i) in pairs and (o, i) not in price:
            price[(o, i)] = float(p)
    for o, i in pairs - set(price):  # no priced order lately: the item sales report has it
        p = price_of(o, i, platform)
        if p is not None:
            price[(o, i)] = p

    rates = {}
    for key in pairs:
        days = window - out_days[key]
        if len(days) >= MIN_DAYS:
            per = defaultdict(float)
            for meal, day, u in sold[key]:
                if day in days:
                    per[meal] += u
            rates[key] = {m: u / len(days) for m, u in per.items()}
    merged: dict[str, dict] = {}
    by_meal = defaultdict(float)
    for e in eps:
        key = (e.outlet_id, e.item_name)
        first = e.first_detected_at.astimezone(IST)
        a, real_end = max(first, lo_t), min((e.restored_at or now).astimezone(IST), hi_t)
        b = min(real_end, first + timedelta(days=CAP_DAYS))
        if key not in rates or key not in price or b <= a:
            continue
        by_meal_units = _units_by_meal(rates[key], a, b)
        per_meal = {m: u * price[key] for m, u in by_meal_units.items()}  # ₹ (high end) per meal
        high = sum(per_meal.values())
        daily = sum(rates[key].values())  # what the dish normally sells here on a day
        m = merged.setdefault(e.item_name, {"item_name": e.item_name, "outlet_set": set(), "high": 0.0, "price": price[key], "episodes": []})
        m["outlet_set"].add(e.outlet_id)
        m["high"] += high
        for meal, v in per_meal.items():
            by_meal[meal] += v
        m["episodes"].append({"outlet": _outlet_label(e.outlet), "from": first.isoformat(), "back": e.restored_at.isoformat() if e.restored_at else None,
                              "hours": round((real_end - a).total_seconds() / 3600, 1), "counted_hours": round((b - a).total_seconds() / 3600, 1),
                              "negligible": sum(by_meal_units.values()) < daily * NEGLIGIBLE_PCT / 100, "daily_units": round(daily, 1), "high": round(high), "low": round(high * LOW_FACTOR),
                              "meals": {k: [round(v * LOW_FACTOR), round(v)] for k, v in per_meal.items() if v >= 1}})
    items = sorted(({"item_name": m["item_name"], "outlets": len(m["outlet_set"]), "price": m["price"], "high": round(m["high"]),
                     "low": round(m["high"] * LOW_FACTOR), "episode_count": len(m["episodes"]),
                     "episodes": sorted((x for x in m["episodes"] if x["high"] >= 1), key=lambda x: -x["high"])[:EPISODES_SHOWN]}
                    for m in merged.values() if m["high"] >= 1), key=lambda x: -x["high"])
    return {"items": items, "low": sum(i["low"] for i in items), "high": sum(i["high"] for i in items),
            "by_meal": {k: {"low": round(v * LOW_FACTOR), "high": round(v)} for k, v in by_meal.items()}}


def period_loss(episodes: list[StockOut], start: date, end: date, now: datetime, long_cutoff: datetime) -> dict:
    """The same across platforms: each platform's stock-outs are valued with that platform's own orders (a Zomato stock-out
    never borrows Swiggy's sales), then dishes, mealtimes and totals are added up."""
    by_platform = defaultdict(list)
    for e in episodes:
        by_platform[e.platform_id].append(e)
    merged: dict[str, dict] = {}
    by_meal = defaultdict(lambda: {"low": 0, "high": 0})
    for plat, rows in by_platform.items():
        part = _period_loss_one(plat, rows, start, end, now, long_cutoff)
        for meal, v in part["by_meal"].items():
            by_meal[meal]["low"] += v["low"]
            by_meal[meal]["high"] += v["high"]
        for it in part["items"]:
            m = merged.get(it["item_name"])
            if not m:
                merged[it["item_name"]] = {**it, "episodes": list(it["episodes"])}
                continue
            m["outlets"] += it["outlets"]
            m["high"] += it["high"]
            m["low"] += it["low"]
            m["episode_count"] += it["episode_count"]
            m["episodes"] += it["episodes"]
            m["price"] = m["price"] or it["price"]
    items = sorted(merged.values(), key=lambda x: -x["high"])
    for i, it in enumerate(items):
        it["episodes"] = sorted(it["episodes"], key=lambda x: -x["high"])[:EPISODES_SHOWN] if i < ITEMS_WITH_EPISODES else []
    return {"items": items, "low": sum(i["low"] for i in items), "high": sum(i["high"] for i in items), "by_meal": dict(by_meal)}
