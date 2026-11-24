"""The client report: one page of the numbers an owner wants for any date range, per outlet and in total, with the change
against the previous period of the same length. The same data feeds the dashboard page and the Excel download, so they
can never disagree.

    GET /brands/<id>/report?start=&end=&outlet_id=&platform=       -> JSON
    GET /brands/<id>/report/xlsx?start=&end=&outlet_id=&platform=  -> .xlsx
"""

import calendar
import io
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.complaints.models import Complaint
from apps.masters.models import Kpi
from apps.outlets.access import get_brand, in_scope
from apps.payouts.models import PayoutOrder

from .models import MetricDaily

from . import report_insights as insights
from .api import _aggregate, _filters, _range

# (section key, title, KPI codes in column order)
SECTIONS = [
    ("overall", "Sales and operations", ["sales", "delivered_orders", "avg_order_value", "cancellation_rate", "cancellation_loss",
                                          "delayed_orders_pct", "avg_prep_time", "online_pct", "mfr_accuracy"]),
    ("growth", "Customer funnel", ["impressions", "menu_views", "add_to_cart", "funnel_orders", "menu_to_order_pct"]),
    ("ads", "Ads and discounts", ["ad_spend", "ad_sales", "ad_roi", "ad_orders", "discount_given", "discount_pct_revenue"]),
    ("reputation", "Ratings", ["listing_rating", "rating_count", "total_reviews", "menu_score"]),
]
ISSUES = [("packaging", "Packaging"), ("quality", "Quality"), ("wrong_items", "Wrong item"), ("missing_items", "Missing item"),
          ("quantity", "Quantity"), ("other", "Other")]
MONTHS_SHOWN = 6
# what a person can pick on the Export reports page (key, name, one-line description)
MODULES = [
    ("overview", "Written overview", "A few plain sentences on how the period went"),
    ("recommendations", "Recommended next steps", "The few things most worth doing, with the numbers behind them"),
    ("overall", "Sales and operations", "Sales, orders, average order value, cancellations, delays, prep time, online time"),
    ("growth", "Customer funnel", "Impressions, menu views, add to cart, orders, conversion"),
    ("ads", "Ads and discounts", "Ad spend, ad sales, ad return, discounts given"),
    ("reputation", "Ratings", "Platform rating, number of ratings, reviews, menu score"),
    ("complaints", "Complaints", "Complaints by type, per outlet and per 100 orders"),
    ("payouts", "Payouts", "Net order value, GST, fees, deductions and payout from the order statements"),
    ("months", "Month by month", "Sales, payout, ads and discounts for the last 6 months"),
    ("weekdays", "Weekdays vs weekends", "Average per day on weekdays (Mon-Fri) against weekends (Sat-Sun): sales, ads and the customer funnel"),
]
# the weekday/weekend tables: (title, KPI codes). Ratios are worked out from the group's own totals, not by averaging daily ratios.
DAYTYPE_TABLES = [("Sales, weekday vs weekend", ["sales", "delivered_orders", "avg_order_value"]),
                  ("Ads, weekday vs weekend", ["ad_spend", "ad_sales", "ad_orders", "ad_roi"]),
                  ("Funnel, weekday vs weekend", ["impressions", "menu_views", "add_to_cart", "funnel_orders", "menu_to_order_pct"])]
DAYTYPE_RATIOS = {"avg_order_value": ("sales", "delivered_orders", 1), "ad_roi": ("ad_sales", "ad_spend", 1), "menu_to_order_pct": ("funnel_orders", "menu_views", 100)}
WEEKEND = (5, 6)  # Saturday, Sunday
# Each app reports its own sales figure under its own name: Zomato's "Sales" is saved as gross_revenue, Swiggy's "Net Sales" as net_revenue.
# The report's Sales adds each platform's own figure, so Swiggy is counted too.
SALES_SOURCES = (("zomato", "gross_revenue"), ("swiggy", "net_revenue"))


class _Sales:
    code, name, unit, higher_is_better = "sales", "Sales", "currency", True


def _sales(outlet_ids, platform, s, e) -> dict[int, float]:
    q = Q(pk__in=[])
    for plat, code in SALES_SOURCES:
        if not platform or platform == plat:
            q |= Q(platform_id=plat, kpi__code=code)
    rows = MetricDaily.objects.filter(q, outlet_id__in=list(outlet_ids), metric_date__range=(s, e)).values("outlet_id").annotate(v=Sum("value"))
    return {r["outlet_id"]: float(r["v"]) for r in rows if r["v"] is not None}


def _sales_daily(outlet_ids, platform, s, e) -> dict[date, float]:
    q = Q(pk__in=[])
    for plat, code in SALES_SOURCES:
        if not platform or platform == plat:
            q |= Q(platform_id=plat, kpi__code=code)
    rows = MetricDaily.objects.filter(q, outlet_id__in=list(outlet_ids), metric_date__range=(s, e)).values("metric_date").annotate(v=Sum("value"))
    return {r["metric_date"]: float(r["v"]) for r in rows if r["v"] is not None}


def _daytype_sections(series: dict, meta: dict) -> list[dict]:
    """Average per day on weekdays and on weekends, from the daily series {code: {date: value}}. A day with no value for a figure is left out of that figure's average."""
    def total(code, weekend):
        days = [d for d, v in series.get(code, {}).items() if (d.weekday() in WEEKEND) == weekend]
        return sum(series[code][d] for d in days), days

    def value(code, weekend):
        if code in DAYTYPE_RATIOS:
            num, den, k = DAYTYPE_RATIOS[code]
            both = [d for d in series.get(num, {}) if d in series.get(den, {}) and (d.weekday() in WEEKEND) == weekend]
            n, d_ = sum(series[num][d] for d in both), sum(series[den][d] for d in both)
            return n / d_ * k if d_ else None
        t, days = total(code, weekend)
        return t / len(days) if days else None

    out = []
    for title, codes in DAYTYPE_TABLES:
        cols = [{"code": c, "name": meta[c].name, "unit": meta[c].unit, "higher_is_better": meta[c].higher_is_better} for c in codes if c in meta]
        wd = {c["code"]: value(c["code"], False) for c in cols}
        we = {c["code"]: value(c["code"], True) for c in cols}
        if all(v is None for v in wd.values()) and all(v is None for v in we.values()):
            continue
        def diff(c):
            pct = (we[c["code"]] - wd[c["code"]]) / wd[c["code"]] * 100
            return f'{c["name"].lower()} {"about the same" if abs(pct) < 0.5 else f"{pct:+.0f}%"}'
        diffs = [diff(c) for c in cols if we[c["code"]] is not None and wd[c["code"]]]
        note = ("Weekends against weekdays: " + ", ".join(diffs) + ".") if diffs else "Not enough weekday and weekend days in this period to compare."
        out.append({"key": "weekdays", "title": title, "kind": "daytype", "first": "Day type", "columns": cols, "note": note,
                    "rows": [{"outlet_id": 0, "name": "Weekday average (Mon-Fri)", **wd}, {"outlet_id": 0, "name": "Weekend average (Sat-Sun)", **we}],
                    "total": {}})
    return out


def _avg_days(by_day: dict) -> tuple:
    """(weekday average, weekend average) of a {date: value} series, each over the days that have a value."""
    wd = [v for d, v in by_day.items() if d.weekday() not in WEEKEND]
    we = [v for d, v in by_day.items() if d.weekday() in WEEKEND]
    return (sum(wd) / len(wd) if wd else None, sum(we) / len(we) if we else None)


def _compact(outlets, names, f, base, start, end, p_start, p_end) -> dict:
    """What the short report and the platform and outlet pages need, platform by platform: the headline figures, funnel, ads, complaints, payouts and the
    weekday/weekend averages; plus the same key figures for every outlet on every platform (the scorecards) and payouts outlet by outlet."""
    mapped = [p for p in ("zomato", "swiggy") if (not f["platform"] or f["platform"] == p) and any(getattr(o, f"{p}_id") for o in outlets.values())]
    out, card = [], defaultdict(dict)
    for pl in mapped:
        pb = {**base, "platform": pl}
        t = {r["code"]: r["value"] for r in _aggregate(False, False, start=start, end=end, **pb)}
        tp = {r["code"]: r["value"] for r in _aggregate(False, False, start=p_start, end=p_end, **pb)}
        sales_by_outlet = _sales(outlets, pl, start, end)
        sales, sales_prev = sum(sales_by_outlet.values()) or None, sum(_sales(outlets, pl, p_start, p_end).values()) or None
        po = PayoutOrder.objects.filter(cycle__outlet_id__in=list(outlets), cycle__platform_id=pl, order_date__date__range=(start, end)).aggregate(
            n=Count("id"), net=Sum("net_order_value"), gst=Sum("gst_collected"), fees=Sum("fees_total"), ded=Sum("net_deductions"), pay=Sum("payout"))
        net, pay = (float(po["net"]) if po["net"] is not None else None), (float(po["pay"]) if po["pay"] is not None else None)
        ads_daily = {r["metric_date"]: r["value"] for r in _aggregate(True, False, start=start, end=end, **pb) if r["code"] == "ad_spend" and r["value"] is not None}
        cq = Complaint.objects.filter(outlet_id__in=list(outlets), platform_id=pl, raised_at__date__range=(start, end))
        cby = {r["issue_type"] or "other": r["n"] for r in cq.values("issue_type").annotate(n=Count("id"))}
        c_out = {r["outlet_id"]: r["n"] for r in cq.values("outlet_id").annotate(n=Count("id"))}
        out.append({"code": pl, "name": pl.title(), "sales": sales, "sales_change": _pct_change(sales, sales_prev), "orders": t.get("delivered_orders"),
                    "orders_change": _pct_change(t.get("delivered_orders"), tp.get("delivered_orders")), "aov": t.get("avg_order_value"), "rating": t.get("listing_rating"),
                    "rating_count": t.get("rating_count"), "reviews": t.get("total_reviews"), "menu_score": t.get("menu_score"), "cancellation": t.get("cancellation_rate"),
                    "online": t.get("online_pct"), "delayed": t.get("delayed_orders_pct"), "prep": t.get("avg_prep_time"), "accuracy": t.get("mfr_accuracy"),
                    "ad_spend": t.get("ad_spend"), "ad_sales": t.get("ad_sales"), "ad_roi": t.get("ad_roi"), "ad_orders": t.get("ad_orders"),
                    "discount": t.get("discount_given"), "discount_pct": t.get("discount_pct_revenue"),
                    "funnel": [t.get(c) for c in ("impressions", "menu_views", "add_to_cart", "funnel_orders")], "complaints": cby, "complaints_total": sum(cby.values()),
                    "pay": {"orders": po["n"], "net": net, "gst": float(po["gst"] or 0), "fees": float(po["fees"] or 0), "deductions": float(po["ded"] or 0), "payout": pay,
                            "kept": round(pay / net * 100, 1) if pay is not None and net else None},
                    "weekday": {"sales": _avg_days(_sales_daily(outlets, pl, start, end)), "ad_spend": _avg_days(ads_daily)}})
        by_out = defaultdict(dict)
        for r_ in _aggregate(False, True, start=start, end=end, **pb):
            if r_["outlet_id"] in outlets:
                by_out[r_["outlet_id"]][r_["code"]] = r_["value"]
        for oid in outlets:
            v = by_out.get(oid, {})
            row = {"sales": sales_by_outlet.get(oid), "orders": v.get("delivered_orders"), "aov": v.get("avg_order_value"), "rating": v.get("listing_rating"), "online": v.get("online_pct"),
                   "delayed": v.get("delayed_orders_pct"), "ad_spend": v.get("ad_spend"), "ad_roi": v.get("ad_roi"), "complaints": c_out.get(oid)}
            if any(x is not None for x in row.values()):
                card[oid][pl] = row
    rows = defaultdict(dict)
    for r_ in PayoutOrder.objects.filter(cycle__outlet_id__in=list(outlets), order_date__date__range=(start, end), **({"cycle__platform_id": f["platform"]} if f["platform"] else {})
                                         ).values("cycle__outlet_id", "cycle__platform_id").annotate(net=Sum("net_order_value"), pay=Sum("payout")):
        rows[r_["cycle__outlet_id"]][r_["cycle__platform_id"]] = (float(r_["net"] or 0), float(r_["pay"] or 0))
        card[r_["cycle__outlet_id"]].setdefault(r_["cycle__platform_id"], {})["payout"] = float(r_["pay"] or 0)
    by_outlet = [{"name": names[oid], **{pl: rows[oid].get(pl) for pl in mapped}, "payout": sum(v[1] for v in rows[oid].values())} for oid in sorted(outlets, key=lambda i: names[i]) if rows.get(oid)]
    scorecards = [{"name": names[oid], "by": card[oid]} for oid in sorted(outlets, key=lambda i: -(sum((v.get("sales") or 0) for v in card[oid].values()))) if card.get(oid)]
    return {"platforms": out, "outlets": by_outlet, "scorecards": scorecards}


def _pct_change(cur, prev):
    if cur is None or prev in (None, 0):
        return None
    return round((cur - prev) / abs(prev) * 100, 1)


def _month_starts(end: date, n: int) -> list[date]:
    y, m, out = end.year, end.month, []
    for _ in range(n):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def _ranges(days: list[date]) -> list[str]:
    """[12 Nov, 13 Nov, 14 Nov, 20 Nov] -> ["12 Nov – 14 Nov", "20 Nov"]"""
    out, run = [], []
    for d in sorted(days):
        if run and (d - run[-1]).days == 1:
            run.append(d)
            continue
        if run:
            out.append(run)
        run = [d]
    if run:
        out.append(run)
    f = lambda d: f"{d.day} {d.strftime('%b')}"
    return [f(r[0]) if len(r) == 1 else f"{f(r[0])} – {f(r[-1])}" for r in out]


def coverage(outlets: dict, names: dict, platform, start: date, end: date) -> dict:
    """Which days have no sales data, per outlet and platform. Checked on daily delivered orders, which both Zomato and Swiggy report and which every other business figure
    arrives with. Today is left out: its numbers are still filling in. Only platforms an outlet is mapped to are expected."""
    last = min(end, date.today() - timedelta(days=1))
    if last < start:
        return {"checked": "Orders", "from": start.isoformat(), "to": last.isoformat(), "days": 0, "complete": True, "gaps": [], "note": "Today only: its numbers are still filling in."}
    days = [start + timedelta(days=i) for i in range((last - start).days + 1)]
    swiggy_last = min(last, date.today() - timedelta(days=2))  # Swiggy's business report is only final up to two days back: the newest days are "not ready", not "missing"
    have = defaultdict(set)
    for oid, plat, d in MetricDaily.objects.filter(outlet_id__in=list(outlets), kpi__code="delivered_orders", metric_date__range=(start, last)).values_list("outlet_id", "platform_id", "metric_date"):
        have[(oid, plat)].add(d)
    gaps = []
    for oid, o in outlets.items():
        plats = [p for p, ok in (("zomato", o.zomato_id and not o.zomato.is_dining), ("swiggy", o.swiggy_id)) if ok and (not platform or platform == p)]
        for p in plats:
            miss = [d for d in days if d not in have[(oid, p)] and not (p == "swiggy" and d > swiggy_last)]
            if miss:
                gaps.append({"outlet_id": oid, "name": names[oid], "platform": p, "missing_days": len(miss), "no_data": len(miss) == len(days), "ranges": _ranges(miss)})
    gaps.sort(key=lambda g: (-g["missing_days"], g["name"]))
    return {"checked": "Orders", "from": start.isoformat(), "to": last.isoformat(), "days": len(days), "complete": not gaps, "gaps": gaps,
            "note": "Swiggy's newest two days are not final yet, so they are not counted as missing."}


def _operating(outlets: dict, platform, start: date, end: date) -> set:
    """The outlets with any data at all in the period (a figure, or a payout order). An outlet with none is not operating, so the report leaves it out."""
    ids = list(outlets)
    md = MetricDaily.objects.filter(outlet_id__in=ids, metric_date__range=(start, end))
    po = PayoutOrder.objects.filter(cycle__outlet_id__in=ids, order_date__date__range=(start, end))
    if platform:
        md, po = md.filter(platform_id=platform), po.filter(cycle__platform_id=platform)
    return set(md.values_list("outlet_id", flat=True).distinct()) | set(po.values_list("cycle__outlet_id", flat=True).distinct())


def build(request, brand_id: int) -> dict:
    brand = get_brand(request.user, brand_id)
    start, end = _range(request)
    span = end - start + timedelta(days=1)
    p_end, p_start = start - timedelta(days=1), start - span
    f = _filters(request)
    base = {"brand_id": brand_id, **f}

    outlets = {o.id: o for o in in_scope(brand.outlets.filter(is_active=True).select_related("zomato"), request.user, "id")}
    if f["outlet_id"]:
        outlets = {k: v for k, v in outlets.items() if k in set(f["outlet_id"])}
    live = _operating(outlets, f["platform"], start, end)
    if live:  # an outlet with no data at all in the period is not operating: it is left out of the report, with no mention (if none has data, all stay so the report says so)
        outlets = {k: v for k, v in outlets.items() if k in live}
    names = {k: (f"{o.outlet_name} · {o.area}" if o.area and o.area.lower() not in o.outlet_name.lower() else o.outlet_name) for k, o in outlets.items()}

    cov = coverage(outlets, names, f["platform"], start, end)
    period = {"start": start.isoformat(), "end": end.isoformat(), "days": span.days, "prev_start": p_start.isoformat(), "prev_end": p_end.isoformat()}
    if request.query_params.get("check"):  # the Export page asks only for the data check while a person picks dates
        return {"brand": brand.name, "period": period, "outlets": len(outlets), "coverage": cov, "modules": [{"key": k, "name": n, "about": a} for k, n, a in MODULES]}
    valid = [k for k, _, _ in MODULES]
    raw = request.query_params.get("modules")  # absent: every module; present but empty: none (the headline numbers only)
    order = valid if raw is None else list(dict.fromkeys(m for m in raw.split(",") if m in valid))  # the order asked for is the order shown
    wanted = set(order)
    codes = [c for _, _, cs in SECTIONS for c in cs]
    meta = {k.code: k for k in Kpi.objects.filter(code__in=codes)}
    meta["sales"] = _Sales

    def pull(s, e, by_outlet):
        rows = _aggregate(False, by_outlet, start=s, end=e, **base)
        if by_outlet:
            out = defaultdict(dict)
            for r in rows:
                if r["outlet_id"] in outlets:
                    out[r["outlet_id"]][r["code"]] = r["value"]
            return out
        return {r["code"]: r["value"] for r in rows}

    cur_total, prev_total = pull(start, end, False), pull(p_start, p_end, False)
    cur_out, prev_out = pull(start, end, True), pull(p_start, p_end, True)
    for src, out, tot in ((_sales(outlets, f["platform"], start, end), cur_out, cur_total), (_sales(outlets, f["platform"], p_start, p_end), prev_out, prev_total)):
        for oid, v in src.items():
            out[oid]["sales"] = v
        if src:
            tot["sales"] = sum(src.values())

    def cell(cur, prev):
        return {"value": cur, "prev": prev, "change": _pct_change(cur, prev)}

    sections = []
    for key, title, cs in SECTIONS:
        if key not in wanted:
            continue
        cs = [c for c in cs if c in meta]
        cols = [{"code": c, "name": "Gross revenue (Zomato only)" if c == "gross_revenue" else meta[c].name, "unit": meta[c].unit, "higher_is_better": meta[c].higher_is_better} for c in cs]
        rows = [{"outlet_id": oid, "name": names[oid], **{c: cell(cur_out.get(oid, {}).get(c), prev_out.get(oid, {}).get(c)) for c in cs}}
                for oid in sorted(outlets, key=lambda i: names[i])]
        rows = [r for r in rows if any(r[c]["value"] is not None for c in cs)]
        total = {c: cell(cur_total.get(c), prev_total.get(c)) for c in cs}
        if rows or any(v["value"] is not None for v in total.values()):
            sections.append({"key": key, "title": title, "columns": cols, "rows": rows, "total": total})

    # complaints by type, per outlet, in the period
    cq = Complaint.objects.filter(outlet_id__in=list(outlets), raised_at__date__range=(start, end)) if "complaints" in wanted else Complaint.objects.none()
    if f["platform"]:
        cq = cq.filter(platform_id=f["platform"])
    by_out = defaultdict(lambda: defaultdict(int))
    for r in cq.values("outlet_id", "issue_type").annotate(n=Count("id")):
        by_out[r["outlet_id"]][r["issue_type"] if r["issue_type"] in dict(ISSUES) else "other"] += r["n"]
    c_rows = []
    for oid in sorted(outlets, key=lambda i: names[i]):
        d = by_out.get(oid, {})
        orders = (cur_out.get(oid, {}).get("delivered_orders") or 0)
        total_c = sum(d.values())
        if total_c or orders:
            c_rows.append({"outlet_id": oid, "name": names[oid], "total": total_c, "per_100_orders": round(total_c / orders * 100, 1) if orders else None,
                           **{k: d.get(k, 0) for k, _ in ISSUES}})
    if c_rows and "complaints" in wanted:
        tot = {"total": sum(r["total"] for r in c_rows), **{k: sum(r[k] for r in c_rows) for k, _ in ISSUES}}
        all_orders = cur_total.get("delivered_orders") or 0
        tot["per_100_orders"] = round(tot["total"] / all_orders * 100, 1) if all_orders else None
        sections.append({"key": "complaints", "title": "Customer complaints", "kind": "complaints",
                         "columns": [{"code": "total", "name": "Complaints", "unit": "count"}, {"code": "per_100_orders", "name": "Per 100 orders", "unit": "ratio"},
                                     *[{"code": k, "name": n, "unit": "count"} for k, n in ISSUES]], "rows": c_rows, "total": tot})

    # payouts: what the platforms' own order statements add up to in the period
    pq = PayoutOrder.objects.filter(cycle__outlet_id__in=list(outlets), order_date__date__range=(start, end)) if "payouts" in wanted else PayoutOrder.objects.none()
    if f["platform"]:
        pq = pq.filter(cycle__platform_id=f["platform"])
    agg = {r["cycle__outlet_id"]: r for r in pq.values("cycle__outlet_id").annotate(
        n=Count("id"), net=Sum("net_order_value"), gst=Sum("gst_collected"), fees=Sum("fees_total"), ded=Sum("net_deductions"), pay=Sum("payout"))}
    p_rows = []
    for oid in sorted(outlets, key=lambda i: names[i]):
        a = agg.get(oid)
        if a:
            p_rows.append({"outlet_id": oid, "name": names[oid], "orders": a["n"], "net_order_value": float(a["net"] or 0), "gst": float(a["gst"] or 0),
                           "fees": float(a["fees"] or 0), "deductions": float(a["ded"] or 0), "payout": float(a["pay"] or 0)})
    if p_rows:
        keys = ["orders", "net_order_value", "gst", "fees", "deductions", "payout"]
        sections.append({"key": "payouts", "title": "Payouts from order statements", "kind": "payouts",
                         "columns": [{"code": "orders", "name": "Orders", "unit": "count"}, {"code": "net_order_value", "name": "Net order value", "unit": "currency"},
                                     {"code": "gst", "name": "GST collected", "unit": "currency"}, {"code": "fees", "name": "Platform fees", "unit": "currency"},
                                     {"code": "deductions", "name": "Net deductions", "unit": "currency"}, {"code": "payout", "name": "Payout", "unit": "currency"}],
                         "rows": p_rows, "total": {k: sum(r[k] for r in p_rows) for k in keys}})

    # with both platforms in the report, the same payouts split by platform, and outlet by outlet within each platform
    if p_rows and not f["platform"]:
        by_plat = defaultdict(dict)
        for r_ in pq.values("cycle__outlet_id", "cycle__platform_id").annotate(n=Count("id"), net=Sum("net_order_value"), gst=Sum("gst_collected"),
                                                                              fees=Sum("fees_total"), ded=Sum("net_deductions"), pay=Sum("payout")):
            by_plat[r_["cycle__platform_id"]][r_["cycle__outlet_id"]] = {"orders": r_["n"], "net_order_value": float(r_["net"] or 0), "gst": float(r_["gst"] or 0),
                                                                          "fees": float(r_["fees"] or 0), "deductions": float(r_["ded"] or 0), "payout": float(r_["pay"] or 0)}
        mapped = {p_ for p_ in ("zomato", "swiggy") if any(getattr(o, f"{p_}_id") for o in outlets.values())}  # a platform the outlets are on shows even with no statements, as "no data"
        plats = [p_ for p_ in ("zomato", "swiggy") if p_ in by_plat or p_ in mapped] + [p_ for p_ in sorted(by_plat) if p_ not in ("zomato", "swiggy")]
        if len(plats) > 1:
            keys = ["orders", "net_order_value", "gst", "fees", "deductions", "payout"]
            cols = sections[[sec["key"] for sec in sections].index("payouts")]["columns"]
            sections.append({"key": "payouts", "title": "Payouts by platform", "kind": "payouts", "first": "Platform", "columns": cols,
                             "rows": [{"outlet_id": 0, "name": pl.title(), **({k: sum(v[k] for v in by_plat[pl].values()) for k in keys} if by_plat.get(pl) else {k: None for k in keys})} for pl in plats],
                             "total": {k: sum(v[k] for pl in plats for v in by_plat.get(pl, {}).values()) for k in keys}})
            m_cols = [c for pl in plats for c in ({"code": f"{pl}_net", "name": f"{pl.title()} net order value", "unit": "currency"},
                                                   {"code": f"{pl}_payout", "name": f"{pl.title()} payout", "unit": "currency"})] + [{"code": "payout", "name": "Total payout", "unit": "currency"}]
            m_rows = []
            for oid in sorted(outlets, key=lambda i: names[i]):
                row = {"outlet_id": oid, "name": names[oid], "payout": 0.0}
                for pl in plats:
                    v = by_plat.get(pl, {}).get(oid)
                    row[f"{pl}_net"], row[f"{pl}_payout"] = (v["net_order_value"], v["payout"]) if v else (None, None)
                    row["payout"] += v["payout"] if v else 0.0
                if any(row[f"{pl}_net"] is not None for pl in plats):
                    m_rows.append(row)
            sections.append({"key": "payouts", "title": "Payouts by outlet and platform", "kind": "payouts", "columns": m_cols, "rows": m_rows,
                             "total": {c["code"]: sum(r[c["code"]] or 0 for r in m_rows) for c in m_cols}})

    # month by month (calendar months ending with the month of the end date)
    months = []
    mp = {r["m"]: r for r in (PayoutOrder.objects.filter(cycle__outlet_id__in=list(outlets), order_date__date__gte=_month_starts(end, MONTHS_SHOWN)[0],
                                                          order_date__date__lte=end) if "months" in wanted else PayoutOrder.objects.none())
          .extra(select={"m": "to_char(order_date, 'YYYY-MM')"}).values("m").annotate(pay=Sum("payout"))}
    for ms in (_month_starts(end, MONTHS_SHOWN) if "months" in wanted else []):
        me = min(date(ms.year, ms.month, calendar.monthrange(ms.year, ms.month)[1]), end)
        t = pull(ms, me, False)
        key = f"{ms.year}-{ms.month:02d}"
        sales, ads, disc = sum(_sales(outlets, f["platform"], ms, me).values()) or None, t.get("ad_spend"), t.get("discount_given")
        months.append({"month": key, "sales": sales, "payout": float(mp[key]["pay"]) if key in mp and mp[key]["pay"] is not None else None,
                       "ads_pct": round(ads / sales * 100, 1) if sales and ads is not None else None,
                       "discount_pct": round(disc / sales * 100, 1) if sales and disc is not None else None})

    # weekday and weekend averages
    if "weekdays" in wanted:
        series = defaultdict(dict)
        for r_ in _aggregate(True, False, start=start, end=end, **base):
            if r_["value"] is not None:
                series[r_["code"]][r_["metric_date"]] = r_["value"]
        series["sales"] = _sales_daily(outlets, f["platform"], start, end)
        sections += _daytype_sections(series, meta)

    # what changed most, in plain words (only changes of 10% or more, and only where there was something before)
    notes = []
    for key, title, cs in SECTIONS:
        for c in (cs if key in wanted else []):
            if c not in meta:
                continue
            ch = _pct_change(cur_total.get(c), prev_total.get(c))
            if ch is not None and abs(ch) >= 10:
                good = (ch > 0) == meta[c].higher_is_better
                notes.append({"code": c, "name": meta[c].name, "change": ch, "good": good, "value": cur_total.get(c), "prev": prev_total.get(c), "unit": meta[c].unit})
    notes.sort(key=lambda n: -abs(n["change"]))

    # the headline numbers do not depend on which modules were ticked
    headline = []
    for title, code, unit, hib in (("Sales", "sales", "currency", True), ("Orders", "delivered_orders", "count", True),
                                   ("Average order value", "avg_order_value", "currency", True), ("Rating", "listing_rating", "rating", True)):
        v = cur_total.get(code)
        if v is not None:
            headline.append({"name": title, "unit": unit, "value": v, "change": _pct_change(v, prev_total.get(code)), "higher_is_better": hib})
    # each delivery platform on its own: what the owner compares first
    by_platform, total_sales = [], sum(_sales(outlets, f["platform"], start, end).values()) or 0
    for code, name in (("zomato", "Zomato"), ("swiggy", "Swiggy")):
        if f["platform"] and f["platform"] != code:
            continue
        t = {r["code"]: r["value"] for r in _aggregate(False, False, start=start, end=end, **{**base, "platform": code})}
        sales = sum(_sales(outlets, code, start, end).values()) or None
        if sales is None and t.get("delivered_orders") is None:
            continue
        by_platform.append({"code": code, "name": name, "sales": sales, "orders": t.get("delivered_orders"), "aov": t.get("avg_order_value"),
                            "rating": t.get("listing_rating"), "cancellation": t.get("cancellation_rate"),
                            "share": round(sales / total_sales * 100, 1) if sales and total_sales else None})
    sections.sort(key=lambda sec: order.index(sec["key"]) if sec["key"] in order else 99)
    result = {"brand": brand.name, "period": period, "outlets": len(outlets), "coverage": cov, "headline": headline, "platforms": by_platform, "highlights": notes[:6], "sections": sections, "months": months, "module_order": order}
    if "overview" in wanted:
        result["overview"] = insights.overview(result)
    if "recommendations" in wanted:
        result["recommendations"] = insights.recommendations(result)
    result["compact"] = _compact(outlets, names, f, base, start, end, p_start, p_end)  # platform pages and outlet scorecards, and the whole short report
    return result


@api_view(["GET"])
def brand_report(request, brand_id):
    try:
        return Response(build(request, brand_id))
    except ValueError:
        return Response({"detail": "Dates must look like 2026-11-20"}, status=400)


def _display(v, unit):
    """Excel value for a unit: minutes for seconds, plain numbers otherwise."""
    if v is None:
        return None
    return round(v / 60, 1) if unit == "seconds" else round(v, 2) if isinstance(v, float) else v


@api_view(["GET"])
def brand_report_xlsx(request, brand_id):
    from .report_xlsx import build_xlsx

    try:
        data = build(request, brand_id)
    except ValueError:
        return Response({"detail": "Dates must look like 2026-11-20"}, status=400)
    p = data["period"]
    resp = HttpResponse(build_xlsx(data), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="report_{p["start"]}_to_{p["end"]}.xlsx"'
    return resp


def _pdf_bytes(request, brand_id):
    """(pdf bytes, start, end) for the same filters the PDF download takes. Raises ValueError on bad dates."""
    from .report_pdf import build_compact_pdf, build_pdf

    data = build(request, brand_id)
    data["tables"] = request.query_params.get("tables") == "1"
    p = data["period"]
    return (build_compact_pdf(data) if request.query_params.get("layout") == "compact" else build_pdf(data)), p["start"], p["end"]


@api_view(["GET"])
def brand_report_pdf(request, brand_id):
    try:
        pdf, start, end = _pdf_bytes(request, brand_id)
    except ValueError:
        return Response({"detail": "Dates must look like 2026-11-20"}, status=400)
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="report_{start}_to_{end}.pdf"'
    return resp


SHARE_DAYS = 7  # a shared report link works this long


@api_view(["POST"])
def brand_report_share(request, brand_id):
    """Build the same PDF as /report/pdf, keep it under a long random address and return that address, so the report can be sent
    as a link (a browser on a computer cannot attach a file to WhatsApp). The link needs no login and stops working after SHARE_DAYS."""
    import os
    import secrets
    import time
    from pathlib import Path

    from django.conf import settings

    try:
        pdf, start, end = _pdf_bytes(request, brand_id)
    except ValueError:
        return Response({"detail": "Dates must look like 2026-11-20"}, status=400)
    root = Path(settings.SHARED_REPORTS_DIR)
    root.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - SHARE_DAYS * 86400
    for old in root.glob("*.pdf"):  # tidy up expired files whenever a new one is made
        try:
            if old.stat().st_mtime < cutoff:
                os.remove(old)
        except OSError:
            pass
    token = secrets.token_urlsafe(24)
    (root / f"{token}.pdf").write_bytes(pdf)
    return Response({"path": f"/r/{token}/report_{start}_to_{end}.pdf", "expires_days": SHARE_DAYS})


def shared_report(request, token, name):
    """The public side of a shared report: the file for this token while it is still fresh. `name` is only for how the link looks."""
    import re
    import time
    from pathlib import Path

    from django.conf import settings
    from django.http import FileResponse, Http404

    if not re.fullmatch(r"[A-Za-z0-9_-]{20,64}", token):
        raise Http404
    f = Path(settings.SHARED_REPORTS_DIR) / f"{token}.pdf"
    if not f.is_file() or f.stat().st_mtime < time.time() - SHARE_DAYS * 86400:
        raise Http404
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:80] or "report.pdf"
    resp = FileResponse(open(f, "rb"), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{safe}"'
    resp["Cache-Control"] = "private, max-age=0"
    resp["X-Robots-Tag"] = "noindex"
    return resp
