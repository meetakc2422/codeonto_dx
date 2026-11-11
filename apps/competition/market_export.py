"""Excel workbook comparing an outlet's menu on a delivery app (Zomato or Swiggy) with competitors', in every aspect we read."""

import re
from functools import lru_cache
from io import BytesIO
from zoneinfo import ZoneInfo

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import dishes
from .api import _outlet
from .models import MarketCompetitor, MarketRestaurant, MarketSpot
from .export_dashboard import add_dashboard
from .market_api import _area, _insights, _market, load_menu, our_res_id

IST = ZoneInfo("Asia/Kolkata")
MATCH_AT = 0.6  # share of the dishes' distinctive words they must have in common to count as the same dish
NOISE = re.compile(r"\(.*?\)|\[.*?\]|regular packaging|serves? \d+|\d+\s*(pcs|pc|pieces|ml|gm|g|kg)\b|[^a-z0-9 ]")
PROTEINS = {"chicken", "mutton", "lamb", "fish", "prawn", "prawns", "egg", "paneer", "tofu", "pork", "beef", "crab", "veg", "mushroom"}
# words too common to tell dishes apart on their own
GENERIC = PROTEINS | {"and", "with", "in", "of", "the", "a", "sauce", "special", "bowl", "combo", "fried", "fry", "spicy", "classic",
                      "boneless", "full", "half", "large", "small", "regular", "box", "meal", "dish", "style", "new",
                      "make", "your", "own", "hamper", "pack", "platter", "bucket", "family", "party"}


@lru_cache(maxsize=None)
def _cached_words(name: str) -> frozenset:
    return frozenset(NOISE.sub(" ", name.lower()).split())


def _words(name: str) -> frozenset:
    return _cached_words(name)  # matching compares every dish with every other dish, so each name is cleaned once


def _size(item: dict) -> tuple:
    """Portion plus piece count / bucket, so '3 pcs' wings never line up with a 12-piece bucket."""
    name = item["name"].lower()
    pcs = re.search(r"(\d+)\s*(?:pcs|pc|pieces)\b", name)
    return dishes.classify(item)["portion"], pcs.group(1) if pcs else "", "bucket" in name


def _match(item: dict, menu: list[dict]) -> tuple[dict | None, float]:
    """The competitor dish most like ours: same veg / non-veg, same main protein, and most of their distinctive words
    shared (Kung Pao Chicken matches Kung Pao Chicken, not Bang Bang Chicken). None when nothing is close enough."""
    mine = _words(item["name"])
    key, protein = mine - GENERIC, mine & PROTEINS
    if not key:
        return None, 0.0
    best, score = None, 0.0
    for other in menu:
        if other.get("veg") != item.get("veg"):
            continue
        theirs = _words(other["name"])
        if protein and (theirs & PROTEINS) and not (protein & theirs):
            continue
        tk = theirs - GENERIC
        if not tk:
            continue
        s = len(key & tk) / max(len(key), len(tk))
        if s > score:
            best, score = other, s
    return (best, score) if score >= MATCH_AT else (None, score)


def _restaurants(mk, outlet, res_ids, with_us=True):
    """[(label, MarketRestaurant, is_us)]: ours first when with_us and known, then the asked-for (default: every tracked)
    competitors. A restaurant whose menu was never read is read now."""
    place = _area(outlet, mk)
    ours = our_res_id(outlet, mk, find=with_us)[0]
    wanted = [r for r in res_ids if r and r != ours] or list(
        MarketCompetitor.objects.filter(outlet=outlet, restaurant__platform=mk.code).order_by("-restaurant__rating").values_list("restaurant__res_id", flat=True))
    out = []
    for rid, is_us in ([(ours, True)] if ours and with_us else []) + [(r, False) for r in wanted]:
        r = MarketRestaurant.objects.filter(platform=mk.code, res_id=rid).first()
        if (not r or not r.items) and place:
            r = load_menu(mk, rid, place)
        if r:
            out.append(("You · " + r.name if is_us else r.name, r, is_us))
    return out


@api_view(["GET"])
def export(request, brand_id, outlet_id, platform):
    """?res_ids=a,b (default: every tracked competitor); ?us=0 leaves the outlet itself out. Sheets: summary, dish prices, dish types, offers, best sellers,
    categories, combos, out of stock, menu gaps, full menus."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    mk = _market(platform)
    outlet = _outlet(request, brand_id, outlet_id)
    ids = [x.strip() for x in (request.query_params.get("res_ids") or "").split(",") if x.strip()]
    try:
        rows = _restaurants(mk, outlet, ids, with_us=request.query_params.get("us", "1") != "0")
    except mk.Error as e:
        return Response({"detail": str(e)}, status=502)
    if not rows:
        return Response({"detail": f"Nothing to export yet: compare with at least one {mk.name} restaurant first."}, status=400)
    ins = {r.res_id: _insights(r) for _, r, _ in rows}
    us = next((r for _, r, is_us in rows if is_us), None)

    wb = Workbook()
    sheets = []

    def sheet(title, head, data, widths=None):
        ws = wb.create_sheet(title) if sheets else wb.active
        ws.title = title
        ws.append(head)
        for row in data:
            ws.append(row)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="0B1229")
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.freeze_panes = "B2" if title == "Summary" else "A2"
        for i, col in enumerate(ws.columns, 1):
            width = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), (widths or {}).get(i, 48))
        sheets.append(ws)
        return ws

    # 1. summary: one column per restaurant, one row per measure
    def pct(n, of):
        return round(100 * n / of) if of else None
    measures = [
        (f"{mk.name} restaurant ID", lambda r, i: r.res_id),
        ("Cost for two", lambda r, i: (r.info or {}).get("cost_for_two", "")),
        ("Cuisines", lambda r, i: ", ".join((r.info or {}).get("cuisines") or [])),
        ("Rating", lambda r, i: r.rating), ("Ratings (votes)", lambda r, i: r.votes),
        ("Menu items", lambda r, i: i.get("items")), ("Categories", lambda r, i: i.get("categories")),
        ("Average item price (₹)", lambda r, i: i.get("avg_price")), ("Veg items %", lambda r, i: i.get("veg_pct")),
        ("Items out of stock now", lambda r, i: len(i.get("out_of_stock") or [])),
        ("Out of stock %", lambda r, i: pct(len(i.get("out_of_stock") or []), i.get("items"))),
        ("Items with a photo %", lambda r, i: i.get("photo_pct")), ("Items without a photo", lambda r, i: len(i.get("no_photo") or [])),
        ("Items with a description %", lambda r, i: i.get("desc_pct")), ("Items without a description", lambda r, i: len(i.get("no_desc") or [])),
        ("Offers running", lambda r, i: len(r.offers or [])), ("Best offer", lambda r, i: (r.offers or [{}])[0].get("text", "")),
        ("Combos shown", lambda r, i: len(r.combos or [])),
        ("Top dish", lambda r, i: ((i.get("top_sellers") or [{}])[0]).get("name", "")),
        ("Top dish price (₹)", lambda r, i: ((i.get("top_sellers") or [{}])[0]).get("price")),
        ("Bestseller-tagged items", lambda r, i: len(i.get("bestsellers") or [])),
        ("Menu read at (IST)", lambda r, i: r.menu_refreshed_at.astimezone(IST).strftime("%d %b %Y %H:%M") if r.menu_refreshed_at else ""),
    ]
    sheet("Summary", ["Measure", *[label for label, _, _ in rows]],
          [[name, *[f(r, ins[r.res_id]) for _, r, _ in rows]] for name, f in measures], {1: 30})

    # side by side: the same dish on every selected menu on one row, prices in neighbouring columns
    groups = []  # {"rep": first item seen, "by": {res_id: item}}
    for _, r, _ in rows:
        for item in r.items:
            free = [g for g in groups if r.res_id not in g["by"]]
            # the same name first; else the closest name of the same size (a 12-piece bucket is not 3 wings)
            size = _size(item)
            same_size = [g for g in free if _size(g["rep"]) == size]
            g = next((g for g in same_size if _words(g["rep"]["name"]) == _words(item["name"])), None)
            if not g:
                m, _score = _match(item, [g["rep"] for g in same_size])
                g = next((g for g in free if g["rep"] is m), None) if m else None
            if g:
                g["by"][r.res_id] = item
            else:
                groups.append({"rep": item, "by": {r.res_id: item}})
    groups.sort(key=lambda g: (-len(g["by"]), dishes.classify(g["rep"])["label"] or "~", g["rep"]["name"]))
    head = ["Dish", "Dish type", "Size", f"On menus (of {len(rows)})"]
    head += [f"{label}: price (₹)" for label, _, _ in rows] + ["Lowest (₹)", "Highest (₹)", "Gap (₹)"]
    head += [f"{label}: dish" for label, _, _ in rows]
    data = []
    for g in groups:
        c = dishes.classify(g["rep"])
        prices = [(g["by"].get(r.res_id) or {}).get("price") for _, r, _ in rows]
        have = [p for p in prices if p]
        data.append([g["rep"]["name"], c["label"], c["portion"], len(g["by"]), *prices,
                     min(have) if have else None, max(have) if have else None, (max(have) - min(have)) if len(have) > 1 else None,
                     *[(g["by"].get(r.res_id) or {}).get("name", "") for _, r, _ in rows]])
    sheet("Side by side", head, data, {1: 40})

    # 2. our dishes against the most alike dish on each competitor's menu
    comps = [(label, r) for label, r, is_us in rows if not is_us]
    if us and comps:
        head = ["Our dish", "Dish type", "Size", "Our price (₹)"]
        for label, _ in comps:
            head += [f"{label}: dish", "price (₹)", "difference (₹)", "how matched"]
        data = []
        for item in sorted(us.items, key=lambda i: (dishes.classify(i)["label"] or "~", i["name"])):
            c = dishes.classify(item)
            row = [item["name"], c["label"], c["portion"], item["price"]]
            for _, r in comps:
                m, basis = dishes.match(item, r.items)
                if not m:
                    m, _score = _match(item, r.items)
                    basis = "similar name" if m else ""
                comparable = m and m["price"] and item["price"] and "other size" not in basis
                row += [m["name"], m["price"], (m["price"] - item["price"]) if comparable else None, basis] if m else ["", None, None, ""]
            data.append(row)
        sheet("Dish prices", head, data, {1: 44})

    # each dish type and size on every menu: how many variants and at what price, side by side
    kinds = {}
    for label, r, _ in rows:
        for i in r.items:
            c = dishes.classify(i)
            if c["label"] and i.get("price"):
                kinds.setdefault((c["label"], c["portion"]), {}).setdefault(r.res_id, []).append(i["price"])
    order = sorted(kinds, key=lambda k: (-(us.res_id in kinds[k]) if us else 0, -len(kinds[k]), k))
    head = ["Dish type", "Size"]
    for label, _, _ in rows:
        head += [f"{label}: items", "avg (₹)", "lowest (₹)"]
    data = []
    for k in order:
        row = [*k]
        for _, r, _ in rows:
            ps = kinds[k].get(r.res_id) or []
            row += [len(ps) or None, round(sum(ps) / len(ps)) if ps else None, min(ps) if ps else None]
        data.append(row)
    sheet("Dish types", head, data, {1: 28})

    every = [(label, r) for label, r, _ in rows]
    sheet("Offers", ["Restaurant", "Offer", "Code"], [[label, o.get("text", ""), o.get("code", "")] for label, r in every for o in r.offers or []])
    sheet("Best sellers", ["Restaurant", "Rank", "Dish", "Price (₹)", "Repeat rate %", "Ratings / popularity"],
          [[label, n, t["name"], t["price"], round(t["reorder"] * 100) if t.get("reorder") is not None else None, round(t["popularity"]) if t.get("popularity") else None]
           for label, r in every for n, t in enumerate(ins[r.res_id].get("top_sellers") or [], 1)])
    sheet("Categories", ["Restaurant", "Category", "Items", "Average price (₹)", "Lowest (₹)", "Highest (₹)"],
          [[label, c, v["items"], v["avg_price"], v["min"], v["max"]] for label, r in every for c, v in (ins[r.res_id].get("by_category") or {}).items()])
    sheet("Combos", ["Restaurant", "Combo", "Price", "Ordered by"], [[label, c["name"], c["price"], c["ordered_by"]] for label, r in every for c in r.combos or []])
    sheet("Out of stock", ["Restaurant", "Item"], [[label, n] for label, r in every for n in ins[r.res_id].get("out_of_stock") or []])
    sheet("Menu gaps", ["Restaurant", "Item", "Missing"],
          [[label, n, what] for label, r in every for what, key in (("Photo", "no_photo"), ("Description", "no_desc")) for n in ins[r.res_id].get(key) or []])
    sheet("Full menus", ["Restaurant", "Section", "Category", "Item", "Dish type", "Price (₹)", "Lowest variant (₹)", "Highest variant (₹)", "Veg",
                         "In stock", "Photo", "Tags", "Repeat rate %", "Description"],
          [[label, i["section"], i["category"], i["name"], dishes.classify(i)["label"], i["price"], i["min_price"], i["max_price"], "Veg" if i["veg"] else "Non-veg",
            "Yes" if i["in_stock"] else "No", "Yes" if i["has_photo"] else "No", ", ".join(i["tags"]),
            round(i["reorder_score"] * 100) if i.get("reorder_score") is not None else None, i.get("desc", "")]
           for label, r in every for i in r.items], {14: 60})

    read = max((r.menu_refreshed_at for _, r, _ in rows if r.menu_refreshed_at), default=None)
    spot = (MarketSpot.objects.filter(outlet=outlet, platform=mk.code).values_list("title", flat=True).first() or "the outlet")
    add_dashboard(wb, mk.name, outlet.display_name, spot, read.astimezone(IST).strftime("%d %b %Y %H:%M") if read else "",
                  rows, ins, kinds)

    buf = BytesIO()
    wb.save(buf)
    name = f"{mk.code}-competition-{(outlet.area or outlet.outlet_name).lower().replace(' ', '-')}-{timezone.localdate():%Y-%m-%d}.xlsx"
    resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp


def _safe(name: str) -> str:
    return re.sub(r"[^\w\- ]+", "", name or "").strip()[:80] or "item"


@api_view(["GET"])
def images(request, brand_id, outlet_id, platform, res_id):
    """A zip of one restaurant's menu photos, one folder per category, from the menu as last read."""
    import zipfile
    from concurrent.futures import ThreadPoolExecutor

    import httpx

    mk = _market(platform)
    _outlet(request, brand_id, outlet_id)
    r = MarketRestaurant.objects.filter(platform=mk.code, res_id=res_id).first()
    items = [i for i in (r.items if r else []) if i.get("image")]
    if not items:
        return Response({"detail": "No menu photos saved yet. Open or refresh the restaurant's menu first."}, status=404)

    def get(url):
        # Zomato hands out WebP (?output-format=webp), which many Windows PCs can't open; the same URL without it is JPEG
        if "zmtcdn.com" in url:
            url = url.split("?")[0]
        try:
            resp = httpx.get(url, timeout=20, follow_redirects=True)
            return resp.content if resp.status_code == 200 else None
        except httpx.HTTPError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        blobs = list(pool.map(get, [i["image"] for i in items]))
    buf, used = BytesIO(), set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for i, data in zip(items, blobs):
            if not data:
                continue
            path = f"{_safe(i.get('category'))}/{_safe(i.get('name'))}"
            n, base = 2, path
            while path in used:
                path, n = f"{base} ({n})", n + 1
            used.add(path)
            ext = ".png" if data[:4] == b"\x89PNG" else ".webp" if data[8:12] == b"WEBP" else ".jpg"
            z.writestr(path + ext, data)
    name = f"{mk.code}-{_safe(r.name).lower().replace(' ', '-')}-photos.zip"
    resp = HttpResponse(buf.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp
