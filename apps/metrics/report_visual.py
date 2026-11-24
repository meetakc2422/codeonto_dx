"""The one-glance page of the report: pictures instead of tables. Built as one reportlab Drawing from the same data as the rest of the
report, so it can be placed on page 1 of the PDF and also rendered to a PNG for sharing."""

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.units import mm

from . import report_pdf as P

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
W, H = P.WIDTH, 128 * mm
INK, MUTE, CARD = P.NAVY, P.GREY, colors.HexColor("#F3F5F9")


def _total(r, section, code):
    for s in r["sections"]:
        if s["key"] == section:
            c = (s.get("total") or {}).get(code)
            return c["value"] if c else None
    return None


def _text(d, x, y, s, size=8, bold=False, color=INK, anchor="start"):
    d.add(String(x, y, s, fontSize=size, fontName=P.FB if bold else P.F, fillColor=color, textAnchor=anchor))


def _card(d, x, y, w, h, title):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=CARD, strokeColor=P.RULE, strokeWidth=0.4))
    _text(d, x + 10, y + h - 15, title, 8.5, True)


def _arrow(d, x, y, up, good, size=7):
    c = P.GREEN if good else P.RED
    pts = [x, y, x + size, y, x + size / 2, y + size] if up else [x, y + size, x + size, y + size, x + size / 2, y]
    d.add(Polygon(pts, fillColor=c, strokeColor=c))


def _tiles(d, r, top):
    hs = r.get("headline", [])
    if not hs:
        return
    gap, w = 8, (W - 8 * (len(hs) - 1)) / len(hs)
    for i, h in enumerate(hs):
        x = i * (w + gap)
        d.add(Rect(x, top - 52, w, 52, rx=5, ry=5, fillColor=colors.white, strokeColor=P.RULE, strokeWidth=0.5))
        _text(d, x + 10, top - 15, h["name"], 7.5, color=MUTE)
        _text(d, x + 10, top - 38, P.fmt(h["value"], h["unit"], short=True), 17, True)
        ch = h.get("change")
        if ch is not None:
            good = (ch >= 0) == h.get("higher_is_better", True)
            _arrow(d, x + w - 62, top - 36, ch >= 0, good)
            _text(d, x + w - 51, top - 36, f"{abs(ch):.0f}%", 9, True, P.GREEN if good else P.RED)


def _platforms(d, r, x, y, w, h):
    _card(d, x, y, w, h, "Where the sales come from")
    rows = [p for p in r.get("platforms", []) if p.get("sales")]
    total = sum(p["sales"] for p in rows)
    if not total:
        _text(d, x + 10, y + h / 2, "No platform sales in this period", 8, color=MUTE)
        return
    cx, cy, rad = x + 62, y + h / 2 - 8, 42
    start = 90.0
    for p in rows:
        sweep = p["sales"] / total * 360
        d.add(Wedge(cx, cy, rad, start - sweep, start, fillColor=P.PLATFORM_COLOR.get(p["code"], P.GREY), strokeColor=colors.white, strokeWidth=1))
        start -= sweep
    d.add(Circle(cx, cy, rad * 0.58, fillColor=CARD, strokeColor=CARD))
    _text(d, cx, cy - 3, P.fmt(total, "currency", short=True), 8, True, anchor="middle")
    ly = y + h - 44
    for p in rows:
        d.add(Rect(x + 128, ly, 8, 8, fillColor=P.PLATFORM_COLOR.get(p["code"], P.GREY), strokeColor=None))
        _text(d, x + 142, ly + 1, f'{p["name"]}  {p["share"]:.0f}%' if p.get("share") is not None else p["name"], 8.5, True)
        _text(d, x + 142, ly - 11, f'{P.fmt(p["sales"], "currency", short=True)}  |  {P.fmt(p["orders"], "count")} orders', 7, color=MUTE)
        bits = ([f'Rating {P.fmt(p["rating"], "rating")}'] if p.get("rating") else []) + ([f'{P.fmt(p["cancellation"], "percent")} cancelled'] if p.get("cancellation") is not None else [])
        _text(d, x + 142, ly - 21, "  |  ".join(bits), 7, color=MUTE)
        ly -= 38


def _bars(d, x, y, w, h, title, items, color_of, note=None, label_w=92, chars=20):
    """Horizontal bars. items: [(label, value, text)]."""
    _card(d, x, y, w, h, title)
    items = [i for i in items if i[1] and i[1] > 0]
    if not items:
        _text(d, x + 10, y + h / 2 - 6, note or "Nothing to show for this period", 8, color=MUTE)
        return
    top = max(i[1] for i in items)
    n = len(items)
    row = min(22, (h - 34) / n)
    bar_w = w - label_w - 100
    for k, (label, val, text) in enumerate(items):
        by = y + h - 36 - k * row
        _text(d, x + 10, by, (label if len(label) <= chars else label[: chars - 1] + "…"), 7.5)
        d.add(Rect(x + 10 + label_w, by - 2, bar_w, 9, rx=2, ry=2, fillColor=colors.white, strokeColor=None))
        d.add(Rect(x + 10 + label_w, by - 2, max(2, bar_w * val / top), 9, rx=2, ry=2, fillColor=color_of(k, label), strokeColor=None))
        _text(d, x + w - 8, by, text, 7.5, True, anchor="end")


def _funnel(d, r, x, y, w, h):
    steps = [("Saw the listing", "impressions"), ("Opened the menu", "menu_views"), ("Added to cart", "add_to_cart"), ("Ordered", "funnel_orders")]
    vals = [(n, _total(r, "growth", c)) for n, c in steps]
    items = [(n, v, f"{v:,.0f}" if v is not None else "") for n, v in vals if v]
    _bars(d, x, y, w, h, "Customer funnel: where people drop off", items, lambda k, _l: P.BLUE if k < len(items) - 1 else P.GREEN,
          "No funnel data in this period")
    # drop-off between steps
    if len(items) > 1:
        top = items[0][1]
        row = min(22, (h - 34) / len(items))
        for k in range(1, len(items)):
            keep = items[k][1] / items[k - 1][1] * 100
            _text(d, x + w - 8, y + h - 36 - k * row - 9, f"{keep:.0f}% continue", 6.2, color=MUTE, anchor="end")


def _losses(d, r, x, y, w, h):
    sales = sum(p["sales"] or 0 for p in r.get("platforms", [])) or None
    pairs = [("Cancelled orders", _total(r, "overall", "cancellation_loss")), ("Discounts given", _total(r, "ads", "discount_given")),
             ("Ad spend", _total(r, "ads", "ad_spend"))]
    items = [(n, v, P.fmt(v, "currency", short=True) + (f"  ({v / sales * 100:.0f}%)" if sales else "")) for n, v in pairs if v]
    items.sort(key=lambda i: -i[1])
    _bars(d, x, y, w, h, "Where money went (and % of sales)", items, lambda k, _l: P.RED if k == 0 else colors.HexColor("#E8A09D"),
          "No cancellation, discount or ad data")


def _outlets(d, r, x, y, w, h):
    rows = []
    for s in r["sections"]:
        if s["key"] == "overall":
            rows = [(q["name"], (q.get("sales") or {}).get("value")) for q in s["rows"]]
    rows = sorted([q for q in rows if q[1]], key=lambda q: -q[1])
    cap = 7
    shown = rows[:cap]
    areas = [n.split(" · ")[-1] for n, _ in shown]
    # the area tells outlets apart; where two share one, the start of the name goes in front
    items = [(a if areas.count(a) == 1 else f'{n.split(" · ")[0][:11].rstrip()} · {a}', v, P.fmt(v, "currency", short=True)) for a, (n, v) in zip(areas, shown)]
    last = len(items) - 1
    _bars(d, x, y, w, h, f"Outlets by sales ({len(rows)})", items, lambda k, _l: P.RED if (k == last and len(items) > 2) else P.BLUE, "No outlet sales", label_w=100, chars=22)


def _trend(d, r, x, y, w, h):
    ms = [m for m in r.get("months", []) if m.get("sales")]
    _card(d, x, y, w, h, "Last months: sales vs payout")
    if len(ms) < 2:
        _text(d, x + 10, y + h / 2 - 6, "Needs at least 2 months of data (tick Month by month)", 8, color=MUTE)
        return
    px, py, pw, ph = x + 14, y + 22, w - 28, h - 56
    top = max(max(m["sales"] or 0, m["payout"] or 0) for m in ms) or 1
    step = pw / (len(ms) - 1)

    def line(key, color):
        pts = [(px + i * step, py + ph * (m[key] or 0) / top) for i, m in enumerate(ms) if m.get(key) is not None]
        for a, b in zip(pts, pts[1:]):
            d.add(Line(a[0], a[1], b[0], b[1], strokeColor=color, strokeWidth=1.8))
        for a in pts:
            d.add(Circle(a[0], a[1], 2.4, fillColor=color, strokeColor=colors.white, strokeWidth=0.6))

    line("sales", P.BLUE)
    line("payout", colors.HexColor("#9AA8E8"))
    for i, m in enumerate(ms):
        _text(d, px + i * step, y + 9, MONTHS[int(m["month"][5:7]) - 1] + " " + m["month"][2:4], 6.5, color=MUTE, anchor="middle")
    _text(d, x + w - 46, y + h - 15, "Sales", 7, True, P.BLUE, "end")
    if any(m.get("payout") for m in ms):
        _text(d, x + w - 10, y + h - 15, "Payout", 7, True, colors.HexColor("#6F7FD1"), "end")


def _section(r, key):
    return next((s for s in r["sections"] if s["key"] == key), None)


def _ratings(d, r, x, y, w, h):
    sec = _section(r, "reputation")
    _card(d, x, y, w, h, "Ratings")
    tot = (sec or {}).get("total") or {}
    val = (tot.get("listing_rating") or {}).get("value")
    if val is None:
        _text(d, x + 10, y + h / 2 - 6, "No rating data in this period", 8, color=MUTE)
        return
    _text(d, x + 10, y + h - 46, f"{val:.2f}", 22, True)
    _text(d, x + 62, y + h - 44, "★", 16, True, colors.HexColor("#F5A524"))
    cnt = (tot.get("rating_count") or {}).get("value")
    if cnt:
        _text(d, x + 10, y + h - 60, f"{P.fmt(cnt, 'count', short=True)} ratings", 7.5, color=MUTE)
    rows = [(q["name"].split(" · ")[-1], (q.get("listing_rating") or {}).get("value")) for q in (sec or {}).get("rows", [])]
    rows = sorted([q for q in rows if q[1]], key=lambda q: -q[1])[:3]
    for k, (name, v) in enumerate(rows):
        by = y + h - 84 - k * 15
        _text(d, x + 10, by, name[:18], 7.5)
        d.add(Rect(x + 90, by - 2, w - 90 - 50, 8, rx=2, ry=2, fillColor=colors.white, strokeColor=None))
        d.add(Rect(x + 90, by - 2, max(2, (w - 90 - 50) * v / 5), 8, rx=2, ry=2, fillColor=P.GREEN if v >= 4 else colors.HexColor("#F5A524") if v >= 3.5 else P.RED, strokeColor=None))
        _text(d, x + w - 10, by, f"{v:.2f}", 7.5, True, anchor="end")


def _complaints(d, r, x, y, w, h):
    sec = _section(r, "complaints")
    tot = (sec or {}).get("total") or {}
    items = [(label, tot.get(k), f"{tot.get(k):,.0f}") for k, label in ((c["code"], c["name"]) for c in (sec or {}).get("columns", [])) if k not in ("total", "per_100_orders") and tot.get(k)]
    items.sort(key=lambda i: -i[1])
    sub = f"{tot['total']:,.0f} complaints" + (f" · {tot['per_100_orders']:.1f} per 100 orders" if tot.get("per_100_orders") is not None else "") if tot.get("total") else ""
    _bars(d, x, y, w, h, "Customer complaints" + (f" ({sub})" if sub and w > 260 else ""), items, lambda k, _l: P.RED if k == 0 else colors.HexColor("#E8A09D"), "No complaints in this period")


def _payouts(d, r, x, y, w, h):
    sec = _section(r, "payouts")
    tot = (sec or {}).get("total") or {}
    pairs = [("Net order value", tot.get("net_order_value"), P.BLUE), ("GST collected", tot.get("gst"), colors.HexColor("#8A94A6")), ("Platform fees", tot.get("fees"), P.RED),
             ("Deductions", tot.get("deductions"), colors.HexColor("#E8A09D")), ("Payout", tot.get("payout"), P.GREEN)]
    pairs = [p for p in pairs if p[1]]
    _card(d, x, y, w, h, "Payouts from order statements")
    if not pairs:
        _text(d, x + 10, y + h / 2 - 6, "No payout statements in this period", 8, color=MUTE)
        return
    split = next((q for q in r["sections"] if q["title"] == "Payouts by platform"), None)  # present when both platforms are in the report
    top = max(abs(v) for _, v, _ in pairs) or 1
    room = 14 + 11 * len(split["rows"]) if split else 0  # the space under the bars for one line per platform
    row = min(22, (h - 40 - room) / len(pairs))
    for k, (label, v, colr) in enumerate(pairs):
        by = y + h - 36 - k * row
        _text(d, x + 10, by, label, 7.5)
        d.add(Rect(x + 92, by - 2, w - 92 - 70, 9, rx=2, ry=2, fillColor=colors.white, strokeColor=None))
        d.add(Rect(x + 92, by - 2, max(2, (w - 92 - 70) * abs(v) / top), 9, rx=2, ry=2, fillColor=colr, strokeColor=None))
        _text(d, x + w - 8, by, P.fmt(v, "currency", short=True), 7.5, True, anchor="end")
    if split:
        _text(d, x + 10, y + 8 + 11 * len(split["rows"]), "By platform: net order value / payout", 6.8, True, color=MUTE)
        for k, q in enumerate(split["rows"]):
            by = y + 8 + 11 * (len(split["rows"]) - 1 - k)
            _text(d, x + 10, by, q["name"], 7.5, True)
            got = q["payout"] is not None
            _text(d, x + w - 8, by, f'{P.fmt(q["net_order_value"], "currency", short=True)} / {P.fmt(q["payout"], "currency", short=True)}' if got else "no payout statements", 7.5, anchor="end", color=INK if got else MUTE)


# which module draws which panel(s), and how many of the three columns each needs
PANELS = {"overall": [(_platforms, 1), (_outlets, 1)], "growth": [(_funnel, 1)], "ads": [(_losses, 1)], "reputation": [(_ratings, 1)],
          "complaints": [(_complaints, 1)], "payouts": [(_payouts, 1)], "months": [(_trend, 2)]}


def _rows_of(cells):
    """Pack panels into rows of three columns."""
    rows, cur, used = [], [], 0
    for fn, wt in cells:
        if used + wt > 3:
            rows.append(cur); cur, used = [], 0
        cur.append((fn, wt)); used += wt
    rows.append(cur)
    return rows


def build_drawings(r: dict, with_tiles: bool = True) -> list[Drawing]:
    """The picture pages: the headline tiles (unless a written page already has them), then one panel for each module asked for,
    in the order asked, three to a row and two rows to a page (more panels carry on to a second page)."""
    order = r.get("module_order") or list(PANELS)
    cells = [(fn, wt) for m in order for fn, wt in PANELS.get(m, [])]
    gap = 8
    if not cells:
        if not with_tiles:
            return []
        first = Drawing(W, H)
        _tiles(first, r, H)
        _text(first, 0, H - 90, "No sections picked: the headline numbers above are all this report holds.", 9, color=MUTE)
        return [first]
    rows = _rows_of(cells)
    col = (W - 2 * gap) / 3
    row_h = (H - 52 - 3 * gap) / 2  # the height a full page gives each of its two rows

    def lay(d, chunk, top, h):
        for i, row in enumerate(chunk):
            y = top - (i + 1) * h - i * gap
            x = 0
            for fn, wt in row:
                w = col * wt + gap * (wt - 1)
                fn(d, r, x, y, w, h)
                x += w + gap

    pages = []
    if with_tiles:
        rest = rows[2:]
        if len(rest) == 1:  # a lone last row would leave a near-empty page: fit all three rows on the first page
            first = Drawing(W, H)
            _tiles(first, r, H)
            lay(first, rows, H - 52 - gap, (H - 52 - 4 * gap) / 3)
            return [first]
        first = Drawing(W, H)
        _tiles(first, r, H)
        lay(first, rows[:2], H - 52 - gap, min(row_h, 200) if len(rows) > 1 else min(row_h, 170))
        pages.append(first)
    else:
        rest = rows
    chunks = [rest[k:k + 2] for k in range(0, len(rest), 2)]
    if len(chunks) > 1 and len(chunks[-1]) == 1:  # same for the later pages: fold the lone row into the page before
        chunks[-2] = chunks[-2] + chunks.pop()
    for chunk in chunks:
        h = row_h if len(chunk) < 3 else (2 * row_h + gap - (len(chunk) - 1) * gap) / len(chunk)
        d = Drawing(W, len(chunk) * h + (len(chunk) - 1) * gap)
        lay(d, chunk, d.height, h)
        pages.append(d)
    return pages


def build_drawing(r: dict) -> Drawing:
    return build_drawings(r)[0]
