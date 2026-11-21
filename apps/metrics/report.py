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
    ("overall", "Sales and operations", "Sales, orders, average order value, cancellations, delays, prep time, online time"),
    ("growth", "Customer funnel", "Impressions, menu views, add to cart, orders, conversion"),
    ("ads", "Ads and discounts", "Ad spend, ad sales, ad return, discounts given"),
    ("reputation", "Ratings", "Platform rating, number of ratings, reviews, menu score"),
    ("complaints", "Complaints", "Complaints by type, per outlet and per 100 orders"),
    ("payouts", "Payouts", "Net order value, GST, fees, deductions and payout from the order statements"),
    ("months", "Month by month", "Sales, payout, ads and discounts for the last 6 months"),
]
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
    names = {k: (f"{o.outlet_name} · {o.area}" if o.area and o.area.lower() not in o.outlet_name.lower() else o.outlet_name) for k, o in outlets.items()}

    cov = coverage(outlets, names, f["platform"], start, end)
    period = {"start": start.isoformat(), "end": end.isoformat(), "days": span.days, "prev_start": p_start.isoformat(), "prev_end": p_end.isoformat()}
    if request.query_params.get("check"):  # the Export page asks only for the data check while a person picks dates
        return {"brand": brand.name, "period": period, "outlets": len(outlets), "coverage": cov, "modules": [{"key": k, "name": n, "about": a} for k, n, a in MODULES]}
    asked = {m for m in (request.query_params.get("modules") or "").split(",") if m}
    wanted = (asked & {k for k, _, _ in MODULES}) or {k for k, _, _ in MODULES}
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
    return {"brand": brand.name, "period": period, "outlets": len(outlets), "coverage": cov, "headline": headline, "platforms": by_platform, "highlights": notes[:6], "sections": sections, "months": months}


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


@api_view(["GET"])
def brand_report_pdf(request, brand_id):
    from .report_pdf import build_pdf

    try:
        data = build(request, brand_id)
    except ValueError:
        return Response({"detail": "Dates must look like 2026-11-20"}, status=400)
    p = data["period"]
    data["tables"] = request.query_params.get("tables") == "1"
    resp = HttpResponse(build_pdf(data), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="report_{p["start"]}_to_{p["end"]}.pdf"'
    return resp
