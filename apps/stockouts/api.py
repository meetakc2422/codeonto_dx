from collections import defaultdict
from datetime import date, datetime, time, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, outlet_ids
from apps.billing.access import require_module

from .models import StockOut


IST = ZoneInfo("Asia/Kolkata")
# the ₹ estimate stays out of the Excel export while it is hidden on the page (see SHOW_STOCK_LOSS in app.js)
EXPORT_LOSS = False
MEAL_LABELS = {"Snacks": "Evening Snacks", "Late Night": "Late Night Dinner"}
MEALS = ["Breakfast", "Lunch", "Evening Snacks", "Dinner", "Late Night Dinner"]
# out longer than this = most likely taken off the menu on purpose; listed apart so it doesn't swamp the real stock-outs
LONG_OFF_DAYS = 3


MEAL_HOURS = {"Breakfast": (5, 12), "Lunch": (12, 16), "Evening Snacks": (16, 19), "Dinner": (19, 23), "Late Night Dinner": (23, 29)}


def _meal_hits(r, lo, hi, now) -> set:
    a = max(r.first_detected_at.astimezone(IST), lo)
    b = min((r.restored_at or now).astimezone(IST), hi)
    hit = set()
    if b <= a:
        return hit
    d = a.date() - timedelta(days=1)
    while d <= b.date():  # per day: only the first meal it was out in, so it isn't repeated down the day
        base = datetime.combine(d, time.min, tzinfo=IST)
        for m, (h1, h2) in MEAL_HOURS.items():
            if base + timedelta(hours=h1) < b and base + timedelta(hours=h2) > a:
                hit.add(m)
                break
        d += timedelta(days=1)
    return hit


def _range_bounds(start: date, end: date):
    now = datetime.now(IST)
    # the meal day runs 5 am to 5 am (Late Night Dinner, 11 pm - 5 am, belongs to the day it started)
    return datetime.combine(start, time(5), tzinfo=IST), min(datetime.combine(end + timedelta(days=1), time(5), tzinfo=IST), now), now


def _meal_state(rows, start: date, end: date) -> dict:
    """meal -> stock-outs that were out during that meal's hours on any day of the period (never past now)."""
    lo, hi, now = _range_bounds(start, end)
    out = defaultdict(int)
    for r in rows:
        for m in _meal_hits(r, lo, hi, now):
            out[m] += 1
    return out


def _meal(s: StockOut) -> str:
    return MEAL_LABELS.get(s.mealtime, s.mealtime)


# the outlets' own city text is messy (Bengaluru Urban, Delhi_NCR, Chennai Corporation...): group it into metros
METROS = {"bangalore": "Bengaluru", "bengaluru": "Bengaluru", "chennai": "Chennai", "delhi": "Delhi NCR", "gurugram": "Delhi NCR",
          "gurgaon": "Delhi NCR", "noida": "Delhi NCR", "ghaziabad": "Delhi NCR", "faridabad": "Delhi NCR", "mumbai": "Mumbai",
          "thane": "Mumbai", "navi mumbai": "Mumbai", "hyderabad": "Hyderabad", "secunderabad": "Hyderabad", "pune": "Pune",
          "kolkata": "Kolkata"}


def metro(city: str) -> str:
    c = (city or "").strip().lower().replace("_", " ")
    for key, name in METROS.items():
        if key in c:
            return name
    return (city or "").strip().replace("_", " ").title() or "Other"


def _period_start(qp) -> date:
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    return date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)


def _long_cutoff():
    return datetime.now(IST) - timedelta(days=LONG_OFF_DAYS)


def _json(s: StockOut, loss=None, start: date | None = None, hours=None) -> dict:
    return {"period_minutes": None if hours is None else round(hours * 60),  # time out inside the selected period only
            "earlier": bool(start and s.log_date < start),
            "long_off": bool(s.is_active and s.first_detected_at and s.first_detected_at < _long_cutoff()),
            "lost": None if loss is None else round(loss), "city": metro(s.outlet.city), "id": s.id, "item_name": s.item_name, "category": s.category, "platform": s.platform_id,
            "outlet_id": s.outlet_id, "outlet_name": s.outlet.display_name,
            "mealtime": _meal(s), "is_active": s.is_active, "back_at": s.back_at, "first_detected_at": s.first_detected_at,
            "restored_at": s.restored_at, "downtime_minutes": s.downtime_minutes}


def _filtered(request, brand_id):
    require_module(request.user, get_brand(request.user, brand_id), "stock_outs")
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)
    # A stock-out is dated by the day it started; show every one that overlaps the range:
    # started by the end date, and still out or came back on/after the start date
    in_range = Q(log_date__lte=end) & (Q(is_active=True) | Q(restored_at__date__gte=start))
    qs = in_scope(StockOut.objects.filter(in_range, outlet__brand_id=brand_id), request.user).select_related("outlet__brand")
    if outlet_ids(qp.get("outlet_id")):
        qs = qs.filter(outlet_id__in=outlet_ids(qp.get("outlet_id")))
    if qp.get("platform"):
        qs = qs.filter(platform_id=qp["platform"])
    if qp.get("mealtime"):  # out during that meal's hours somewhere in the period
        end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
        lo, hi, now = _range_bounds(start, end)
        ids = [r.id for r in qs if qp["mealtime"] in _meal_hits(r, lo, hi, now)]
        qs = qs.filter(id__in=ids)
    return qs, qp


def _status(qs, qp):
    """The list's status tabs. 'All' and 'Out now' leave out items off for days (their own tab)."""
    st, long_q = qp.get("status"), Q(is_active=True, first_detected_at__lt=_long_cutoff())
    if st == "out":  # every item out now (the page splits them itself)
        return qs.filter(is_active=True)
    if st == "active":
        return qs.filter(is_active=True).exclude(long_q)
    if st == "restored":
        return qs.filter(is_active=False)
    if st == "long":
        return qs.filter(long_q)
    if st == "earlier":  # still out, started before the period (the ones off for days have their own tab)
        return qs.filter(is_active=True, log_date__lt=_period_start(qp)).exclude(long_q)
    if st == "new":  # started in the period
        return qs.filter(log_date__gte=_period_start(qp))
    return qs


def _losses(rows: list, qp) -> dict:
    """stock-out id -> (hours out inside the period, ₹ of usual sales missed or None when the item has no sales history).
    Same estimate as the item scorecard: the item's usual ₹ a day, spread over the outlet's hour-by-hour order pattern."""
    from apps.insights.api import stockout_losses

    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)
    since = datetime.combine(start, time.min, tzinfo=IST)
    until = datetime.combine(end + timedelta(days=1), time.min, tzinfo=IST)
    return {s.id: (hours, loss) for s, hours, loss in stockout_losses(rows, end, since, until)[0]}


@api_view(["GET"])
def brand_stock_outs(request, brand_id):
    qs, qp = _filtered(request, brand_id)
    qs = _status(qs, qp)
    if qp.get("q"):
        qs = qs.filter(item_name__icontains=qp["q"])
    offset, limit = int(qp.get("offset", 0)), min(int(qp.get("limit", 50)), 5000)
    rows = list(qs[offset:offset + limit])
    losses = _losses(rows, qp)
    start = _period_start(qp)
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    lo, hi, now = _range_bounds(start, end)
    return Response([{**_json(s, losses[s.id][1], start, losses[s.id][0]), "range_meals": sorted(_meal_hits(s, lo, hi, now))} for s in rows])


@api_view(["GET"])
def stock_outs_summary(request, brand_id):
    qs, qp = _filtered(request, brand_id)
    totals = qs.aggregate(events=Count("id"), active=Count("id", filter=Q(is_active=True)),
                          restored=Count("id", filter=Q(is_active=False)),
                          avg_downtime=Avg("downtime_minutes"))
    totals["avg_downtime"] = round(float(totals["avg_downtime"])) if totals["avg_downtime"] is not None else None
    start = _period_start(qp)
    meal_counts, meal_out = defaultdict(int), defaultdict(int)  # started in the period / out right now (not off for days)
    for r in qs.filter(log_date__gte=start).values("mealtime").annotate(count=Count("id")):
        meal_counts[MEAL_LABELS.get(r["mealtime"], r["mealtime"])] += r["count"]
    for r in (qs.filter(is_active=True).exclude(first_detected_at__lt=_long_cutoff())
              .values("mealtime").annotate(count=Count("id"))):
        meal_out[MEAL_LABELS.get(r["mealtime"], r["mealtime"])] += r["count"]
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    meal_state = _meal_state(list(qs.exclude(is_active=True, first_detected_at__lt=_long_cutoff())), start, end)
    losses = _losses(list(qs), qp)
    lost = [v[1] for v in losses.values() if v[1] is not None]
    by_item = defaultdict(lambda: {"lost": 0.0, "hours": 0.0, "outlets": set(), "out_now": 0})
    for s in qs:
        hours, loss = losses[s.id]
        d = by_item[s.item_name]
        d["lost"] += loss or 0
        d["hours"] += hours
        d["outlets"].add(s.outlet_id)
        d["out_now"] += s.is_active
    top = sorted(by_item.items(), key=lambda kv: -kv[1]["lost"])
    return Response({
        **totals,
        "lost_sales": round(sum(lost)),
        "lost_unpriced": len(losses) - len(lost),  # stock-outs of items with no sales history: no ₹ estimate
        "top_losses": [{"item_name": k, "lost": round(d["lost"]), "hours": round(d["hours"], 1), "outlets": len(d["outlets"]),
                        "out_now": d["out_now"]} for k, d in top[:5] if d["lost"] >= 1],
        "outlets_affected": qs.filter(is_active=True).values("outlet_id").distinct().count(),
        "earlier": qs.filter(is_active=True, log_date__lt=start).exclude(first_detected_at__lt=_long_cutoff()).count(),  # still out, started before the period
        "long_off": qs.filter(is_active=True, first_detected_at__lt=_long_cutoff()).count(),
        "long_off_days": LONG_OFF_DAYS,
        "by_meal": [{"meal": m, "count": meal_state.get(m, 0), "new": meal_counts.get(m, 0), "out": meal_out.get(m, 0)} for m in MEALS],
        "top_items": list(qs.values("item_name").annotate(count=Count("id")).order_by("-count")[:8]),
        "by_outlet": [{"outlet_id": r["outlet_id"], "outlet": f"{r['outlet__outlet_name']}", "active": r["active"], "events": r["events"]}
                      for r in qs.values("outlet_id", "outlet__outlet_name").annotate(
                          events=Count("id"), active=Count("id", filter=Q(is_active=True))).order_by("-active", "-events")],
    })



def _local(ts):
    """Excel has no time zones: write India time as a plain date-time."""
    return ts.astimezone(IST).replace(tzinfo=None) if ts else None


@api_view(["GET"])
def stock_outs_export(request, brand_id):
    """The stock-outs the page is showing, as an Excel workbook: one sheet of episodes, one summary per dish."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    qs, qp = _filtered(request, brand_id)
    qs = _status(qs, qp)
    if qp.get("q"):
        qs = qs.filter(item_name__icontains=qp["q"])
    rows = list(qs.order_by("-first_detected_at")[:50000])
    losses = _losses(rows, qp)

    wb = Workbook()
    ws = wb.active
    ws.title = "Stock-outs"
    head = ["Brand", "Outlet", "Platform", "Item", "Category", "Mealtime", "Status", "Went out (IST)", "Back in (IST)",
            "Downtime (min)", "Platform says back"] + (["Sales missed (₹, estimate)"] if EXPORT_LOSS else [])
    ws.append(head)
    for r in rows:
        ws.append([r.outlet.brand.name, r.outlet.display_name.split(" · ", 1)[-1], r.platform_id, r.item_name, r.category,
                   _meal(r), "Out of stock" if r.is_active else "Back in stock", _local(r.first_detected_at),
                   _local(r.restored_at), r.downtime_minutes,
                   (r.back_at or "").replace("Out of stock till ", "")]
                  + ([None if losses[r.id][1] is None else round(losses[r.id][1])] if EXPORT_LOSS else []))

    by_item: dict[tuple, dict] = {}
    for r in rows:
        d = by_item.setdefault((r.item_name, r.category), {"events": 0, "now": 0, "down": 0, "outlets": set(), "lost": 0.0})
        d["events"] += 1
        d["now"] += r.is_active
        d["down"] += r.downtime_minutes or 0
        d["outlets"].add(r.outlet_id)
        d["lost"] += losses[r.id][1] or 0
    summary = wb.create_sheet("By dish")
    summary.append(["Item", "Category", "Times out of stock", "Out now (outlets)", "Outlets affected", "Total downtime (min)"]
                   + (["Sales missed (₹, estimate)"] if EXPORT_LOSS else []))
    for (item, category), d in sorted(by_item.items(), key=lambda kv: (-(kv[1]["lost"] if EXPORT_LOSS else 0), -kv[1]["now"], -kv[1]["events"])):
        summary.append([item, category, d["events"], d["now"], len(d["outlets"]), d["down"]] + ([round(d["lost"])] if EXPORT_LOSS else []))

    for sheet in (ws, summary):
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="0B1229")
            cell.alignment = Alignment(vertical="center")
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for i, col in enumerate(sheet.columns, 1):
            width = max((len(str(c.value)) for c in list(col)[:300] if c.value is not None), default=8)
            sheet.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 48)
    for col in ("H", "I"):
        for cell in ws[col][1:]:
            cell.number_format = "dd mmm yyyy hh:mm"

    buf = BytesIO()
    wb.save(buf)
    name = f"stock-outs_{date.today().isoformat()}.xlsx"
    resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp
