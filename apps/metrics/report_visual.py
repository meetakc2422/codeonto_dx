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


def build_drawing(r: dict) -> Drawing:
    d = Drawing(W, H)
    _tiles(d, r, H)
    gap = 8
    row_h = (H - 52 - 3 * gap - 0) / 2
    y2 = 0
    y1 = row_h + gap
    third = (W - 2 * gap) / 3
    _platforms(d, r, 0, y1, third, row_h)
    _funnel(d, r, third + gap, y1, third, row_h)
    _losses(d, r, 2 * (third + gap), y1, third, row_h)
    _outlets(d, r, 0, y2, third * 1.0, row_h)
    _trend(d, r, third + gap, y2, third * 2 + gap, row_h)
    return d
