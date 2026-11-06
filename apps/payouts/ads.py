"""Ads & discounts performance, read from the platforms' own payout statements (PayoutCycle.breakdown).

Per cycle: ad spend (Zomato "Investments in growth", Swiggy "Growth investments in ads" + display ads), restaurant
discounts, order value, orders and net payout.

Per outlet, a weekly model separates what ads did from everything else that moves orders:
    orders a day = base + ads + discounts + season + trend [+ store uptime] [+ stock-outs]
one row per payout period (Zomato pays daily, Swiggy weekly). season is how busy the brand's other outlets were in the
same period (festivals, weather, weekdays and salary days hit them all at once);
trend is the outlet's slow growth or decline; uptime and stock-outs join once there are about 3 months of them.
It is still statistics on past weeks, not an experiment, so each result carries a confidence.
"""

from collections import defaultdict
from datetime import date, timedelta

from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.billing.access import require_module
from apps.outlets.access import get_brand, in_scope, outlet_ids
from apps.stockouts.models import StockOut
from apps.uptime.models import UptimeDaily

from .lines import norm
from .models import PayoutCycle, PayoutLineType

AD_SECTIONS = {"investments_in_growth", "growth_investments_in_ads"}
ORDER_VALUE_SECTIONS = {"total_order_value", "total_customer_paid"}
LIFT_DAYS = 365  # history the per-outlet model learns from, whatever range is on screen
MIN_CONTROL_DAYS = 90  # uptime / stock-outs join the model once an outlet has about this many days of them


def _num(v) -> float:
    try:
        return abs(float(v or 0))
    except (TypeError, ValueError):
        return 0.0


def _ad_lines() -> set:
    """Statement lines reviewed as ad spend outside the usual ad sections (e.g. a new ad product)."""
    from .lines import AD_SECTIONS
    return {(p, sec, label) for p, sec, label in PayoutLineType.objects.filter(kind="ad", reviewed=True)
            .exclude(section__in=AD_SECTIONS).values_list("platform", "section", "label")}


def cycle_numbers(c: PayoutCycle, ad_lines: set = frozenset()) -> dict:
    ads = discounts = order_value = 0.0
    for s in c.breakdown or []:
        sid, items = s.get("id"), s.get("items") or []
        if sid in AD_SECTIONS:
            ads += _num(s.get("value")) or sum(_num(i.get("value")) for i in items)
        if sid in ORDER_VALUE_SECTIONS:
            item_total = next((_num(i.get("value")) for i in items if (i.get("label") or "").lower() == "item total"), None)
            order_value += item_total if item_total is not None else _num(s.get("value"))
            discounts += sum(_num(i.get("value")) for i in items if "discount" in (i.get("label") or "").lower())
        if sid not in AD_SECTIONS:
            ads += sum(_num(i.get("value")) for i in items if (c.platform_id, sid, norm(i.get("label"))) in ad_lines
                       or (sid == "other_charges_refunds" and "display ads" in (i.get("label") or "").lower()))
    return {"ads": ads, "discounts": discounts, "order_value": order_value,
            "orders": c.delivered_orders or c.order_count or 0, "net_payout": float(c.net_payout or 0)}


def _totals(rows: list[dict]) -> dict:
    t = {k: sum(r[k] for r in rows) for k in ("ads", "discounts", "order_value", "orders", "net_payout")}
    ov = t["order_value"]
    t["ad_pct"] = round(100 * t["ads"] / ov, 1) if ov else None
    t["growth_pct"] = round(100 * (t["ads"] + t["discounts"]) / ov, 1) if ov else None
    t["ad_per_order"] = round(t["ads"] / t["orders"]) if t["orders"] else None
    t["roas"] = round(ov / t["ads"], 1) if t["ads"] else None
    return t


def _week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _days(c: dict) -> int:
    return (c["end_date"] - c["start_date"]).days + 1


def _lift(cycles: list[dict]) -> dict:
    """Plain averages: orders a week in periods with ads vs periods without (Zomato pays daily, Swiggy weekly)."""
    on = [c for c in cycles if c["ads"] > 0]
    off = [c for c in cycles if c["ads"] == 0]
    per_week = lambda cs: 7 * sum(c["orders"] for c in cs) / max(1, sum(_days(c) for c in cs))
    return {"with_ads": round(per_week(on), 1) if len(on) >= 2 else None,
            "without_ads": round(per_week(off), 1) if len(off) >= 2 else None}


def _season(brand_id: int, platform: str, since: date, end: date) -> dict:
    """{period end date: {outlet_id: orders a day then ÷ that outlet's usual orders a day}} across the brand on one platform.
    Festivals, weather, weekdays and salary days lift or sink all outlets together; this captures that."""
    per = defaultdict(dict)
    for oid, s0, e0, delivered, total in PayoutCycle.objects.filter(outlet__brand_id=brand_id, platform_id=platform, end_date__range=(since, end)) \
            .values_list("outlet_id", "start_date", "end_date", "delivered_orders", "order_count"):
        per[oid][e0] = (delivered or total or 0) / ((e0 - s0).days + 1)
    out = defaultdict(dict)
    for oid, days in per.items():
        usual = sum(days.values()) / len(days) if days else 0
        if usual > 0.2:
            for e0, v in days.items():
                out[e0][oid] = v / usual
    return out


def _daily_uptime(outlet_ids, platform: str, since: date) -> dict:
    """{(outlet_id, day): share of checks the store was online}"""
    return {(oid, d): on / n for oid, d, n, on in UptimeDaily.objects.filter(outlet_id__in=outlet_ids, platform_id=platform, day__gte=since)
            .values_list("outlet_id", "day", "checks", "online_checks") if n}


def _daily_stockouts(outlet_ids, platform: str, since: date) -> dict:
    """{(outlet_id, day): distinct items out of stock that day}"""
    seen = defaultdict(set)
    for oid, d, name in StockOut.objects.filter(outlet_id__in=outlet_ids, platform_id=platform, log_date__gte=since) \
            .values_list("outlet_id", "log_date", "item_name"):
        seen[(oid, d)].add(name)
    return {k: len(v) for k, v in seen.items()}


def _confidence(t: float) -> str:
    return "confident" if t >= 2.5 else "likely" if t >= 1.5 else "unclear"


def _model(oid: int, cycles: list[dict], season: dict, uptime: dict, stock: dict) -> dict:
    """Fit orders a day on ads, discounts, season and trend (+ uptime, stock-outs once there are enough days of them),
    one row per payout period. Returns what an extra order from ads (and from discounts) cost, and how sure we are."""
    import numpy as np

    cs = sorted(cycles, key=lambda c: c["end_date"])
    n = len(cs)
    days = np.array([_days(c) for c in cs], dtype=float)
    ads = np.array([c["ads"] for c in cs]) / days / 1000        # ₹1,000s of ads a day
    disc = np.array([c["discounts"] for c in cs]) / days / 1000
    y = np.array([c["orders"] for c in cs]) / days               # orders a day
    avg_order = sum(c["order_value"] for c in cs) / max(1, sum(c["orders"] for c in cs))
    base = {"periods": n, "avg_order": round(avg_order), "controls": [], "extra_orders": None, "cost_per_extra": None,
            "confidence": None, "disc_cost_per_extra": None, "disc_confidence": None}
    if not ads.any():
        return {**base, "verdict": "no_ads"}
    if ads.std() < 0.1 * ads.mean():
        return {**base, "verdict": "always_on"}  # the same spend every period: nothing to compare against

    first, last = cs[0]["end_date"], cs[-1]["end_date"]
    cols, names = [np.ones(n), ads], []
    if disc.std() > 0:
        cols.append(disc)
        names.append("discounts")
    cols.append(np.array([(c["end_date"] - first).days for c in cs]) / max(1, (last - first).days))
    names.append("trend")
    others = [[v for o, v in season.get(c["end_date"], {}).items() if o != oid] for c in cs]
    if sum(len(o) >= 2 for o in others) >= 0.8 * n:
        cols.append(np.array([sum(o) / len(o) if len(o) >= 2 else 1.0 for o in others]))
        names.append("season")
    for key, table in (("uptime", uptime), ("stock-outs", stock)):
        vals = []
        for c in cs:
            got = [table[(oid, c["start_date"] + timedelta(days=i))] for i in range(_days(c)) if (oid, c["start_date"] + timedelta(days=i)) in table]
            vals.append(sum(got) / len(got) if got else None)
        have = [v for v in vals if v is not None]
        covered = sum(_days(c) for c, v in zip(cs, vals) if v is not None)
        if covered >= MIN_CONTROL_DAYS and np.std(have) > 0:
            mean = sum(have) / len(have)
            cols.append(np.array([mean if v is None else v for v in vals], dtype=float))
            names.append(key)
    X = np.column_stack(cols)
    k = X.shape[1]
    if n < k + 8:
        return {**base, "controls": names, "verdict": "too_little"}

    w = np.sqrt(days)  # a 7-day period counts for more than a 1-day one
    b, *_ = np.linalg.lstsq(X * w[:, None], y * w, rcond=None)
    resid = (y - X @ b) * w
    s2 = float(resid @ resid) / (n - k)
    se = np.sqrt(np.clip(np.diag(s2 * np.linalg.pinv((X * w[:, None]).T @ (X * w[:, None]))), 0, None))

    def effect(i):
        coef = float(b[i])
        return coef, (coef / se[i] if se[i] > 0 else 0.0), (round(1000 / coef) if coef > 0.01 else None)

    a_coef, a_t, a_cost = effect(1)
    out = {**base, "controls": names, "confidence": _confidence(a_t), "cost_per_extra": a_cost,
           "extra_orders": round(7 * a_coef * float(ads[ads > 0].mean()), 1)}
    if "discounts" in names:
        _, d_t, d_cost = effect(2)
        out.update({"disc_cost_per_extra": d_cost, "disc_confidence": _confidence(d_t)})
    if a_cost is None:
        out["verdict"] = "no_lift"
    elif out["confidence"] == "unclear":
        out["verdict"] = "unclear"
    elif a_cost <= 0.35 * avg_order:
        out["verdict"] = "works"
    elif a_cost <= 0.7 * avg_order:
        out["verdict"] = "ok"
    else:
        out["verdict"] = "costly"
    return out


@api_view(["GET"])
def ads_performance(request, brand_id):
    brand = get_brand(request.user, brand_id)
    require_module(request.user, brand, "marketplace_ads")
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=89)
    span = (end - start).days + 1
    earliest = min(start - timedelta(days=span), end - timedelta(days=LIFT_DAYS))

    qs = in_scope(PayoutCycle.objects.filter(outlet__brand_id=brand_id, end_date__range=(earliest, end)), request.user)
    if outlet_ids(qp.get("outlet_id")):
        qs = qs.filter(outlet_id__in=outlet_ids(qp.get("outlet_id")))
    if qp.get("platform"):
        qs = qs.filter(platform_id=qp["platform"])

    rows, ad_lines = [], _ad_lines()
    for c in qs.exclude(breakdown=[]).select_related("outlet").order_by("end_date"):
        rows.append({**cycle_numbers(c, ad_lines), "start_date": c.start_date, "end_date": c.end_date, "platform": c.platform_id, "outlet_id": c.outlet_id,
                     "outlet": c.outlet.area or c.outlet.outlet_name, "city": c.outlet.city})
    current = [r for r in rows if start <= r["end_date"] <= end]
    previous = [r for r in rows if start - timedelta(days=span) <= r["end_date"] < start]

    # every Monday-to-Sunday payout week that overlaps the chosen dates, whole, plus the week before for the change
    by_week = defaultdict(list)
    for r in rows:
        by_week[_week(r["end_date"])].append(r)
    first, last = _week(start), _week(end)
    weekly, prev = [], _totals(by_week.get(first - timedelta(days=7), []))
    w = first
    while w <= last:
        t = _totals(by_week.get(w, []))
        empty = not t["orders"] and not t["ads"]
        weekly.append({"week": w, "week_end": w + timedelta(days=6), **t, "partial": w + timedelta(days=6) > end,
                       "orders_change": None if empty else _pct(t["orders"], prev["orders"]),
                       "ads_change": None if empty else _pct(t["ads"], prev["ads"]),
                       "discounts_change": None if empty else _pct(t["discounts"], prev["discounts"]), "note": _week_note(t, prev)})
        prev, w = t, w + timedelta(days=7)
    by_day = defaultdict(list)
    for r in current:
        by_day[r["end_date"]].append(r)
    daily = [{"day": d, **_totals(rs)} for d, rs in sorted(by_day.items())]
    trend = [x for x in weekly if x["orders"] or x["ads"]]

    by_outlet = defaultdict(list)
    for r in rows:
        if r["end_date"] >= end - timedelta(days=LIFT_DAYS):
            by_outlet[(r["outlet_id"], r["platform"])].append(r)
    since = end - timedelta(days=LIFT_DAYS)
    ids = {oid for oid, _ in by_outlet}
    seasons, uptimes, stocks = {}, {}, {}
    for plat in {p for _, p in by_outlet}:
        seasons[plat] = _season(brand_id, plat, since, end)
        uptimes[plat] = _daily_uptime(ids, plat, since)
        stocks[plat] = _daily_stockouts(ids, plat, since)
    outlets = []
    for (oid, plat), rs in by_outlet.items():
        now = [r for r in rs if start <= r["end_date"] <= end]
        if not now:
            continue
        outlets.append({"outlet_id": oid, "outlet": rs[0]["outlet"], "city": rs[0]["city"], "platform": plat,
                        **_totals(now), "lift": _lift(rs), "model": _model(oid, rs, seasons[plat], uptimes[plat], stocks[plat])})
    outlets.sort(key=lambda o: -o["ads"])

    return Response({"start": start, "end": end, "totals": _totals(current), "previous": _totals(previous),
                     "trend": trend, "weekly": weekly, "daily": daily, "outlets": outlets, "insights": _insights(outlets)})


def _pct(now: float, before: float) -> int | None:
    return round(100 * (now - before) / before) if before else None


def _week_note(t: dict, p: dict) -> str:
    """One line on how the week went against the one before."""
    if not t["orders"] and not t["ads"]:
        return "No payouts yet"
    o, a, d = _pct(t["orders"], p["orders"]), _pct(t["ads"], p["ads"]), _pct(t["discounts"], p["discounts"])
    if o is None:
        return "First week with payouts"
    up = lambda v: v is not None and v >= 8
    down = lambda v: v is not None and v <= -8
    if up(o) and (up(d) and not up(a)):
        return "Orders up with bigger discounts"
    if up(o) and up(a):
        return "Orders up as ad spend rose"
    if up(o):
        return "Orders up without extra spend"
    if down(o) and (up(a) or up(d)):
        return "Spent more, but orders fell"
    if down(o) and (down(a) or down(d)):
        return "Orders fell as spend was cut"
    if down(o):
        return "Orders fell with the same spend"
    if (down(a) or down(d)) and not (up(a) or up(d)):
        return "Similar orders on less spend"
    if up(a) or up(d):
        return "More spend, orders flat"
    return "Steady week"


def _insights(outlets: list[dict]) -> list[dict]:
    """Plain-language findings from the per-outlet model, most useful first. Only 'likely' or 'confident' results."""
    out = []
    def sure(m):
        return m["confidence"] in ("likely", "confident")
    spenders = [o for o in outlets if o["ads"] > 0]
    works = sorted([o for o in spenders if o["model"]["verdict"] == "works"], key=lambda o: o["model"]["cost_per_extra"])
    costly = sorted([o for o in spenders if o["model"]["verdict"] == "costly"], key=lambda o: -o["ads"])
    flat = sorted([o for o in spenders if o["model"]["verdict"] in ("no_lift", "unclear")], key=lambda o: -o["ads"])
    if works:
        o, m = works[0], works[0]["model"]
        out.append({"tone": "good", "title": f"Ads pay off best at {o['outlet']}",
                    "text": f"After allowing for discounts, season and trend, ads add about {m['extra_orders']:g} orders a week at roughly "
                            f"₹{m['cost_per_extra']:,} each, against a ₹{m['avg_order']:,} average order ({m['confidence']})."})
    for o in costly[:2]:
        m = o["model"]
        text = (f"Each extra order from ads costs roughly ₹{m['cost_per_extra']:,} against a ₹{m['avg_order']:,} average order."
                if m["cost_per_extra"] else "Once discounts, season and trend are allowed for, ads show no clear effect on orders.")
        out.append({"tone": "bad", "title": f"Ads at {o['outlet']} likely aren't paying back", "text": text + " Try cutting or moving this budget."})
    if flat:
        names = ", ".join(o["outlet"] for o in flat[:3]) + (f" and {len(flat) - 3} more" if len(flat) > 3 else "")
        out.append({"tone": "warn", "title": f"No measurable effect from ads at {names}",
                    "text": "Once discounts, season and trend are allowed for, orders don't move with ad spend. "
                            "The spend may still help, but the numbers can't show it: a two-week pause at one of them would tell."})
    disc = sorted([o for o in outlets if o["model"]["disc_confidence"] in ("likely", "confident") and o["model"]["disc_cost_per_extra"]],
                  key=lambda o: o["model"]["disc_cost_per_extra"])
    if disc:
        o, m = disc[0], disc[0]["model"]
        out.append({"tone": "good", "title": "Discounts clearly drive orders",
                    "text": f"At {o['outlet']}, about ₹{m['disc_cost_per_extra']:,} of discount brings one extra order "
                            f"(₹{m['avg_order']:,} average order, {m['disc_confidence']}). {len(disc)} outlet{'s' if len(disc) != 1 else ''} show the same."})
    cheaper = [o for o in spenders if sure(o["model"]) and o["model"]["disc_cost_per_extra"] and o["model"]["cost_per_extra"]
               and o["model"]["disc_confidence"] in ("likely", "confident") and o["model"]["disc_cost_per_extra"] < 0.7 * o["model"]["cost_per_extra"]]
    if cheaper:
        o, m = cheaper[0], cheaper[0]["model"]
        out.append({"tone": "idea", "title": f"At {o['outlet']}, discounts bring orders more cheaply than ads",
                    "text": f"About ₹{m['disc_cost_per_extra']:,} of discount per extra order versus ₹{m['cost_per_extra']:,} of ads."})
    heavy = sorted([o for o in spenders if (o["ad_pct"] or 0) >= 15 and o not in costly[:2]], key=lambda o: -(o["ad_pct"] or 0))
    for o in heavy[:1]:
        out.append({"tone": "warn", "title": f"{o['outlet']} spends {o['ad_pct']}% of sales on ads",
                    "text": "Most brands stay under 8–10%. Check whether this level is still bringing new customers."})
    if works and costly:
        out.append({"tone": "idea", "title": "Move budget to where it works",
                    "text": f"Shifting spend from {costly[0]['outlet']} to {works[0]['outlet']} would likely bring more orders for the same money."})
    always = [o for o in spenders if o["model"]["verdict"] == "always_on"]
    if len(always) >= 3:
        out.append({"tone": "warn", "title": f"{len(always)} outlets spend the same on ads every week",
                    "text": "With no change in spend there is nothing to measure against. Pausing ads at 2–3 similar outlets for two weeks would show what they really bring."})
    return out[:6]
