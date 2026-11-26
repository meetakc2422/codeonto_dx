"""Dining view of the Performance page: for the brand's Zomato dining ids, the latest reading of each offer and how many
slots were left, how that changed across the readings so far, and which 15-minute slots are still open."""

from collections import defaultdict
from datetime import date, timedelta

from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, outlet_ids
from apps.outlets.models import BrandOutlet

import re
from difflib import SequenceMatcher

from apps.insights.models import ItemSalesDaily

from .models import DiningMenuItem, DiningMenuPage, DiningMenuStatus, DiningOfferSnapshot as Offer, DiningSlotSnapshot as Slot


def _logo(bo) -> str:
    """The brand's logo if one is set (admin: Brand, logo url), else the outlet's first photo on District."""
    if bo.brand.logo_url:
        return bo.brand.logo_url
    st = DiningMenuStatus.objects.filter(res_id=str(bo.zomato_id)).only("photo_url").first()
    return st.photo_url if st else ""


def _dining_outlets(request, brand_id):
    qs = BrandOutlet.objects.filter(brand_id=brand_id, is_active=True, zomato__is_dining=True, zomato__is_active=True).select_related("zomato", "brand")
    qs = in_scope(qs, request.user, "id")
    ids = outlet_ids(request.query_params.get("outlet_id"))
    return qs.filter(id__in=ids) if ids else qs


def _past(rid, start, end):
    """Past dining dates in the range: for each date, meal and offer, the most slots we ever saw, the last reading, and so
    how many were taken (an estimate: a cancellation or a manual change also moves the count)."""
    if end < start:
        return []
    groups = defaultdict(list)  # (for_date, meal, offer) -> [slots_left] oldest first
    for o in Offer.objects.filter(res_id=rid, for_date__gte=start, for_date__lte=end, slots_left__isnull=False).order_by("taken_at"):
        groups[(o.for_date, o.meal_time, o.offer)].append(o.slots_left)
    rows = []
    for (d, meal, offer), v in sorted(groups.items(), reverse=True):
        cap, last = max(v), v[-1]
        rows.append({"date": d.isoformat(), "meal": meal, "offer": offer, "capacity": cap, "left": last, "booked": cap - last,
                     "fill_pct": round(100 * (cap - last) / cap) if cap else None, "readings": len(v)})
    return rows


@api_view(["GET"])
def brand_dining(request, brand_id):
    get_brand(request.user, brand_id)
    if request.query_params.get("summary"):  # the sidebar only needs to know whether to show the link
        return Response({"has_dining": _dining_outlets(request, brand_id).exists()})
    return Response(_dining_data(request, brand_id))


def _dining_data(request, brand_id) -> dict:
    outlets = list(_dining_outlets(request, brand_id))
    out = []
    today = date.today().isoformat()
    try:
        end = date.fromisoformat(request.query_params["end"]) if request.query_params.get("end") else date.today()
        start = date.fromisoformat(request.query_params["start"]) if request.query_params.get("start") else end - timedelta(days=29)
    except ValueError:
        end = date.today(); start = end - timedelta(days=29)
    for bo in outlets:
        rid = bo.zomato_id
        times = list(Offer.objects.filter(res_id=rid).order_by("-taken_at").values_list("taken_at", flat=True).distinct()[:40])
        row = {"outlet_id": bo.id, "name": bo.display_name, "res_id": rid, "logo": _logo(bo), "last_checked": times[0] if times else None, "readings": len(times), "days": []}
        if times:
            latest = times[0]
            history = defaultdict(list)  # (date, meal, offer) -> [(taken_at, slots_left)] oldest first
            for o in Offer.objects.filter(res_id=rid, taken_at__in=times).order_by("taken_at"):
                history[(o.for_date, o.meal_time, o.offer)].append((o.taken_at, o.slots_left))
            days = defaultdict(lambda: {"offers": [], "slots": []})
            for o in Offer.objects.filter(res_id=rid, taken_at=latest, for_date__gte=today).order_by("for_date", "meal_time"):
                h = [v for _, v in history[(o.for_date, o.meal_time, o.offer)] if v is not None]
                top = max(h) if h else None
                days[o.for_date.isoformat()]["offers"].append({
                    "meal": o.meal_time, "offer": o.offer, "discount_pct": o.discount_pct, "window": o.window, "slots_left": o.slots_left,
                    "cover_charge": float(o.cover_charge) if o.cover_charge is not None else None,
                    "booked_since_first": (top - o.slots_left) if top is not None and o.slots_left is not None else None, "trend": h[-12:]})
            seen = defaultdict(set)
            for s in Slot.objects.filter(res_id=rid, taken_at__in=times, for_date__gte=today).values("for_date", "slot_time"):
                seen[s["for_date"]].add(s["slot_time"])
            for s in Slot.objects.filter(res_id=rid, taken_at=latest, for_date__gte=today).order_by("for_date", "id"):
                days[s.for_date.isoformat()]["slots"].append({"time": s.slot_time, "meal": s.meal_time, "discount_pct": s.discount_pct})
            for d, v in sorted(days.items()):
                open_times = {s["time"] for s in v["slots"]}
                v["gone"] = sorted(seen[date.fromisoformat(d)] - open_times)  # was bookable earlier, not now: full or closed
                row["days"].append({"date": d, **v})
        row["past"] = _past(rid, start, min(end, date.today() - timedelta(days=1)))
        out.append(row)
    return {"has_dining": bool(outlets), "outlets": out}


@api_view(["GET"])
def brand_dining_export(request, brand_id):
    """The Slots & offers page as an Excel file: the upcoming offers and the past days of the chosen dates, every outlet in one sheet each."""
    from io import BytesIO

    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    get_brand(request.user, brand_id)
    data = _dining_data(request, brand_id)
    wb = Workbook()
    past = wb.active
    past.title = "Past days"
    past.append(["Outlet", "Date", "Day", "Meal", "Offer", "Slots", "Booked", "Filled %"])
    up = wb.create_sheet("Upcoming offers")
    up.append(["Outlet", "Date", "Day", "Meal", "Offer", "Discount %", "Window", "Slots left", "Booked so far"])
    for o in data["outlets"]:
        for r in o.get("past", []):
            d = date.fromisoformat(r["date"])
            past.append([o["name"], d, d.strftime("%a"), r["meal"], r["offer"], r["capacity"], r["booked"], r["fill_pct"]])
        for day in o["days"]:
            d = date.fromisoformat(day["date"])
            for f in day["offers"]:
                up.append([o["name"], d, d.strftime("%a"), f["meal"], f["offer"], f["discount_pct"], f["window"], f["slots_left"], f["booked_since_first"]])
    for sheet in (past, up):
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="0B1229")
            cell.alignment = Alignment(vertical="center")
        for row in sheet.iter_rows(min_row=2, min_col=2, max_col=2):
            row[0].number_format = "dd mmm yyyy"
        sheet.freeze_panes = "A2"
        for i, col in enumerate(sheet.columns, 1):
            width = max((len(str(c.value)) for c in list(col)[:300] if c.value is not None), default=8)
            sheet.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 48)
    buf = BytesIO()
    wb.save(buf)
    resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="slots-and-offers_{date.today().isoformat()}.xlsx"'
    return resp


def _norm(x: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", x.lower())).strip()


def _delivery_prices(brand_id, outlet) -> dict:
    """{normalised dish name: (name, price)}: the latest delivery price of each dish. Prefers the delivery store with the same
    name and area as this dining outlet; falls back to the brand's other delivery stores."""
    qs = ItemSalesDaily.objects.filter(outlet__brand_id=brand_id, unit_price__isnull=False, outlet__zomato__is_dining=False).order_by("day")
    same = qs.filter(outlet__outlet_name=outlet.outlet_name, outlet__area=outlet.area)
    rows = same if same.exists() else qs
    out = {}
    for r in rows.values("item_name", "unit_price"):  # oldest first, so the latest day wins
        out[_norm(r["item_name"])] = (r["item_name"], float(r["unit_price"]))
    return out


def _match(name, note, delivery):
    """The delivery dish for a dining dish: exact name (with the size when that helps), else a close spelling."""
    for cand in (_norm(f"{name} {note}") if note else None, _norm(name)):
        if cand and cand in delivery:
            return delivery[cand]
    n = _norm(name)
    best, score = None, 0.0
    for k, v in delivery.items():
        r = SequenceMatcher(None, n, k).ratio()
        if r > score:
            best, score = v, r
    return best if score >= 0.88 else None


@api_view(["GET"])
def brand_dining_menu(request, brand_id):
    """Each dining outlet's menu prices next to what the same dish costs on delivery."""
    get_brand(request.user, brand_id)
    out = []
    for bo in _dining_outlets(request, brand_id):
        rid = str(bo.zomato_id)
        pages = DiningMenuPage.objects.filter(res_id=rid)
        total, read = pages.count(), pages.filter(read_at__isnull=False).count()
        images = list(pages.order_by("position").values_list("image_url", flat=True))
        items = list(DiningMenuItem.objects.filter(res_id=rid, price__isnull=False).order_by("page__position", "id"))
        delivery = _delivery_prices(brand_id, bo) if items else {}
        rows, unmatched = [], []
        for it in items:
            m = _match(it.name, it.note, delivery)
            price = float(it.price)
            if m and m[1]:
                rows.append({"name": it.name, "note": it.note, "section": it.section, "dining": price, "delivery": m[1],
                             "diff_pct": round(100 * (price - m[1]) / m[1], 1)})
            else:
                unmatched.append({"name": it.name, "note": it.note, "section": it.section, "dining": price})
        rows.sort(key=lambda r: -abs(r["diff_pct"]))
        st = DiningMenuStatus.objects.filter(res_id=rid).first()
        avg = round(sum(r["diff_pct"] for r in rows) / len(rows), 1) if rows else None
        out.append({"outlet_id": bo.id, "name": bo.display_name, "logo": _logo(bo), "images": images, "pages": total, "pages_read": read, "dishes": len(items),
                    "compared": len(rows), "avg_diff_pct": avg,
                    "menu_updated": st.updated_text if st else "", "checked_at": st.checked_at if st else None, "synced_at": st.synced_at if st else None, "differ": sum(1 for r in rows if abs(r["diff_pct"]) >= 1),
                    "rows": rows, "unmatched": unmatched})
    return Response({"outlets": out})
