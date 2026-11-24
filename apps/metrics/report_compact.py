"""The pages of the short report that are pictures: the platforms side by side (cards of big numbers), weekdays against weekends,
and payouts. Same look as the one-glance page (rounded cards, bars), fewer numbers."""

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors

from . import report_pdf as P
from .report_visual import CARD, INK, MUTE, W, _arrow, _bars, _card, _text

WEEKEND_COLOR = colors.HexColor("#E8A09D")
GAP = 10


def _fmt(v, unit):
    return "-" if v is None else P.fmt(v, unit, short=unit == "currency")


def _tile(d, x, y, w, h, label, value, change=None, good_when_up=True):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=colors.white, strokeColor=P.RULE, strokeWidth=0.5))
    _text(d, x + 8, y + h - 12, label, 6.8, color=MUTE)
    _text(d, x + 8, y + 9, value, 12.5, True)
    if change is not None and abs(change) >= 0.5:
        good = (change >= 0) == good_when_up
        _arrow(d, x + w - 38, y + 9, change >= 0, good, 6)
        _text(d, x + w - 29, y + 9, f"{abs(change):.0f}%", 7.4, True, P.GREEN if good else P.RED)


def _platform_card(d, x, y, w, h, pl):
    _card(d, x, y, w, h, "")
    col = P.PLATFORM_COLOR.get(pl["code"], P.GREY)
    d.add(Rect(x + 10, y + h - 20, 9, 9, rx=2, ry=2, fillColor=col, strokeColor=None))
    _text(d, x + 24, y + h - 19, pl["name"], 10.5, True)
    tw, th, gap = (w - 20 - 2 * 6) / 3, 38, 6
    tiles = [("Sales", _fmt(pl["sales"], "currency"), pl["sales_change"]), ("Orders", _fmt(pl["orders"], "count"), pl["orders_change"]), ("Average order value", _fmt(pl["aov"], "currency"), None),
             ("Online time", _fmt(pl["online"], "percent"), None), ("Delayed orders", _fmt(pl["delayed"], "percent"), None), ("Return on ads", _fmt(pl["ad_roi"], "ratio"), None)]
    for i, (label, value, ch) in enumerate(tiles):
        r_, c_ = divmod(i, 3)
        _tile(d, x + 10 + c_ * (tw + gap), y + h - 28 - th - r_ * (th + gap), tw, th, label, value, ch, good_when_up=label != "Delayed orders")
    ads = f'Ad spend {_fmt(pl["ad_spend"], "currency")}  |  Discounts {_fmt(pl["discount"], "currency")}' + (f' ({pl["discount_pct"]:.0f}% of order value)' if pl["discount_pct"] is not None else "")
    _text(d, x + 10, y + 26, ads, 7.2, color=MUTE)
    pay = pl["pay"]
    if pay["payout"] is not None:
        _text(d, x + 10, y + 9, f'{_fmt(pay["payout"], "currency")} paid out', 9.5, True, P.GREEN)
        if pay["kept"] is not None:
            _text(d, x + w - 10, y + 9, f'{pay["kept"]:.0f}% of order value', 7.6, color=MUTE, anchor="end")
    else:
        _text(d, x + 10, y + 9, "No payout statements in this period", 7.6, color=MUTE)


def _weekday_card(d, x, y, w, h, plats):
    _card(d, x, y, w, h, "Weekdays vs weekends (average per day)")
    d.add(Rect(x + w - 190, y + h - 17, 8, 8, fillColor=P.BLUE, strokeColor=None))
    _text(d, x + w - 179, y + h - 16, "Weekday (Mon-Fri)", 7, color=MUTE)
    d.add(Rect(x + w - 92, y + h - 17, 8, 8, fillColor=WEEKEND_COLOR, strokeColor=None))
    _text(d, x + w - 81, y + h - 16, "Weekend (Sat-Sun)", 7, color=MUTE)
    half = (w - 30) / 2
    if not any(pl["weekday"][k][0] is not None or pl["weekday"][k][1] is not None for pl in plats for k in ("sales", "ad_spend")):
        _text(d, x + 10, y + h / 2 - 6, "Not enough weekday and weekend days in this period", 8, color=MUTE)
        return
    for c_, (key, label) in enumerate((("sales", "Sales per day"), ("ad_spend", "Ad spend per day"))):
        cx = x + 10 + c_ * (half + 10)
        _text(d, cx, y + h - 40, label, 8, True)
        top = max([v for pl in plats for v in pl["weekday"][key] if v is not None] or [1]) or 1
        bar_x, bar_w = cx + 52, half - 52 - 128
        for i, pl in enumerate(plats):
            by = y + h - 60 - i * 36
            _text(d, cx, by + 2, pl["name"], 8, True, P.PLATFORM_COLOR.get(pl["code"], P.GREY))
            wd, we = pl["weekday"][key]
            for k, (v, colr) in enumerate(((wd, P.BLUE), (we, WEEKEND_COLOR))):
                if v is None:
                    continue
                yy = by + 6 - k * 12
                bw = max(2, bar_w * v / top)
                d.add(Rect(bar_x, yy - 1, bw, 9, rx=2, ry=2, fillColor=colr, strokeColor=None))
                _text(d, bar_x + bw + 4, yy, P.fmt(v, "currency", short=True), 7.2, True)
            if wd and we:
                ch = (we - wd) / wd * 100
                _text(d, cx + half, by + 2, "about the same" if abs(ch) < 0.5 else f"weekends {ch:+.0f}%", 7.8, True, P.GREEN if ch >= 0.5 and key == "sales" else MUTE, anchor="end")


def platforms_page(r) -> Drawing:
    plats = r["compact"]["platforms"]
    ch, wh = 150, 118 + 18 * max(1, len(plats))
    d = Drawing(W, ch + GAP + wh)
    n = max(1, len(plats))
    cw = (W - GAP * (n - 1)) / n
    for i, pl in enumerate(plats):
        _platform_card(d, i * (cw + GAP), wh + GAP, cw, ch, pl)
    _weekday_card(d, 0, 0, W, wh, plats)
    return d


def payouts_page(r) -> Drawing:
    c = r["compact"]
    plats, outs = c["platforms"], c["outlets"]
    top = sorted(outs, key=lambda o: -o["payout"])[:8]
    ph, oh = 132, 40 + 24 * max(1, len(top))
    d = Drawing(W, ph + GAP + oh)
    n = max(1, len(plats))
    cw = (W - GAP * (n - 1)) / n
    for i, pl in enumerate(plats):
        pay = pl["pay"]
        items = [("Net order value", pay["net"], P.fmt(pay["net"], "currency", short=True) if pay["net"] else ""), ("GST collected", pay["gst"], P.fmt(pay["gst"], "currency", short=True)),
                 ("Platform fees", pay["fees"], P.fmt(pay["fees"], "currency", short=True)), ("Deductions", pay["deductions"], P.fmt(pay["deductions"], "currency", short=True)),
                 ("Payout", pay["payout"], P.fmt(pay["payout"], "currency", short=True) if pay["payout"] else "")]
        colors_ = [P.BLUE, colors.HexColor("#8A94A6"), P.RED, WEEKEND_COLOR, P.GREEN]
        _bars(d, i * (cw + GAP), oh + GAP, cw, ph, f'{pl["name"]} payouts' + (f' ({pay["kept"]:.0f}% of order value paid out)' if pay["kept"] is not None else ""), items,
              lambda k, _l, cs=colors_: cs[k % len(cs)], f'No {pl["name"]} payout statements in this period')
    pls = [pl["code"] for pl in plats]
    items = []
    for o in top:
        name = o["name"].split(" · ")[-1]
        both = [pl for pl in pls if o.get(pl)]
        split = "  |  ".join(f'{pl[:1].upper()} {P.fmt(o[pl][1], "currency", short=True)}' for pl in both)  # shown only when the outlet is paid by more than one platform
        items.append((name, o["payout"], P.fmt(o["payout"], "currency", short=True) + (f"   ({split})" if len(both) > 1 else "")))
    _bars(d, 0, 0, W, oh, f"Payout by outlet (top {len(top)})" if len(outs) > len(top) else "Payout by outlet", items, lambda k, _l: P.BLUE, "No payout statements in this period", label_w=130, chars=28)
    return d


# ---------- the full report: one set of pages per platform, then the best and worst outlets ----------
def _tile_card(d, x, y, w, h, title, items):
    """A card of mini tiles (two across). items: [(label, value text, change or None, higher is better)]."""
    _card(d, x, y, w, h, title)
    rows = (len(items) + 1) // 2
    gap = 6
    tw = (w - 20 - gap) / 2
    th = min(40, (h - 30 - gap * (rows - 1)) / max(1, rows))
    for i, (label, value, ch, hib) in enumerate(items):
        r_, c_ = divmod(i, 2)
        _tile(d, x + 10 + c_ * (tw + gap), y + h - 26 - th - r_ * (th + gap), tw, th, label, value, ch, good_when_up=hib)


def _panels_for(pl, order):
    """The panels one platform's page holds for the sections that were ticked: [(draw function, columns it takes)]."""
    mins = lambda v: "-" if v is None else f"{v / 60:.0f} min"
    pay = pl["pay"]
    p = []

    def sales(d, x, y, w, h):
        _tile_card(d, x, y, w, h, "Sales", [("Sales", _fmt(pl["sales"], "currency"), pl["sales_change"], True), ("Orders", _fmt(pl["orders"], "count"), pl["orders_change"], True),
                                           ("Average order value", _fmt(pl["aov"], "currency"), None, True), ("Cancelled", _fmt(pl["cancellation"], "percent"), None, False)])

    def ops(d, x, y, w, h):
        _tile_card(d, x, y, w, h, "Operations", [("Online time", _fmt(pl["online"], "percent"), None, True), ("Delayed orders", _fmt(pl["delayed"], "percent"), None, False),
                                                ("Kitchen prep time", mins(pl["prep"]), None, False), ("Order-ready accuracy", _fmt(pl["accuracy"], "percent"), None, True)])

    def ratings(d, x, y, w, h):
        _tile_card(d, x, y, w, h, "Ratings", [("Rating", _fmt(pl["rating"], "rating"), None, True), ("Number of ratings", _fmt(pl["rating_count"], "count"), None, True),
                                             ("Reviews", _fmt(pl["reviews"], "count"), None, True), ("Menu score", _fmt(pl["menu_score"], "percent"), None, True)])

    def ads(d, x, y, w, h):
        _tile_card(d, x, y, w, h, "Marketing", [("Ad spend", _fmt(pl["ad_spend"], "currency"), None, False), ("Sales from ads", _fmt(pl["ad_sales"], "currency"), None, True),
                                               ("Return on ads", _fmt(pl["ad_roi"], "ratio"), None, True), ("Discounts given", _fmt(pl["discount"], "currency"), None, False)])

    def funnel(d, x, y, w, h):
        steps = [("Saw the listing", pl["funnel"][0]), ("Opened the menu", pl["funnel"][1]), ("Added to cart", pl["funnel"][2]), ("Ordered", pl["funnel"][3])]
        items = [(n, v, f"{v:,.0f}") for n, v in steps if v]
        _bars(d, x, y, w, h, "Customer funnel", items, lambda k, _l: P.BLUE if k < len(items) - 1 else P.GREEN, "No funnel data in this period")

    def customers(d, x, y, w, h):
        c = pl["customers"]
        _card(d, x, y, w, h, "Customers")
        parts = [("New", c["new"], P.BLUE), ("Repeat", c["repeat"], P.GREEN), ("Lapsed", c["lapsed"], WEEKEND_COLOR)]
        cx, cy, rad = x + 54, y + h / 2 - 8, 34
        start = 90.0
        from reportlab.graphics.shapes import Circle, Wedge

        for _n, v, colr in parts:
            if v:
                sweep = v / 100 * 360
                d.add(Wedge(cx, cy, rad, start - sweep, start, fillColor=colr, strokeColor=colors.white, strokeWidth=1))
                start -= sweep
        d.add(Circle(cx, cy, rad * 0.58, fillColor=CARD, strokeColor=CARD))
        for i, (name, v, colr) in enumerate(parts):
            ly = y + h - 34 - i * 22
            d.add(Rect(x + 104, ly, 8, 8, fillColor=colr, strokeColor=None))
            _text(d, x + 118, ly, name, 8, True)
            _text(d, x + w - 10, ly, "-" if v is None else f"{v:.0f}%", 9, True, anchor="end")
            ch = c["change"].get(name.lower())
            if ch is not None and abs(ch) >= 0.5:
                _text(d, x + 118, ly - 10, f"{ch:+.0f} points vs previous period", 6.4, color=MUTE)

    def complaints(d, x, y, w, h):
        names = {"packaging": "Packaging", "quality": "Quality", "wrong_items": "Wrong item", "missing_items": "Missing item", "quantity": "Quantity", "other": "Other"}
        items = sorted([(names.get(k, k), v, str(v)) for k, v in pl["complaints"].items() if v], key=lambda i: -i[1])
        _bars(d, x, y, w, h, f'Complaints ({pl["complaints_total"]})' if pl["complaints_total"] else "Complaints", items, lambda k, _l: P.RED if k == 0 else WEEKEND_COLOR, "No complaints in this period")

    def payouts(d, x, y, w, h):
        items = [("Net order value", pay["net"], P.fmt(pay["net"], "currency", short=True) if pay["net"] else ""), ("GST collected", pay["gst"], P.fmt(pay["gst"], "currency", short=True)),
                 ("Platform fees", pay["fees"], P.fmt(pay["fees"], "currency", short=True)), ("Deductions", pay["deductions"], P.fmt(pay["deductions"], "currency", short=True)),
                 ("Payout", pay["payout"], P.fmt(pay["payout"], "currency", short=True) if pay["payout"] else "")]
        cs = [P.BLUE, colors.HexColor("#8A94A6"), P.RED, WEEKEND_COLOR, P.GREEN]
        _bars(d, x, y, w, h, "Payouts" + (f' ({pay["kept"]:.0f}% of order value paid out)' if pay["kept"] is not None else ""), items, lambda k, _l: cs[k % len(cs)], "No payout statements in this period")

    def weekdays(d, x, y, w, h):
        _weekday_card(d, x, y, w, h, [pl])

    table = {"overall": [(sales, 1), (ops, 1)], "reputation": [(ratings, 1)], "ads": [(ads, 1)], "growth": [(funnel, 1)] + [(customers, 1)] if pl.get("customers") else [(funnel, 1)], "complaints": [(complaints, 1)], "payouts": [(payouts, 1)],
             "weekdays": [(weekdays, 2)]}
    for m in order:
        p += table.get(m, [])
    return p


def platform_pages(r, pl) -> list:
    """The pages for one platform: its panels for every ticked section, three to a row and four rows to a page."""
    order = r.get("module_order") or list(("overall", "reputation", "ads", "growth", "complaints", "payouts", "weekdays"))
    cells = _panels_for(pl, order)
    if not cells:
        return []
    rows, cur, used = [], [], 0
    for fn, wt in cells:
        if used + wt > 3:
            rows.append(cur); cur, used = [], 0
        cur.append((fn, wt)); used += wt
    rows.append(cur)
    col, rh = (W - 2 * GAP) / 3, 104
    pages = []
    for k in range(0, len(rows), 4):
        chunk = rows[k:k + 4]
        d = Drawing(W, len(chunk) * rh + (len(chunk) - 1) * GAP)
        for i, row in enumerate(chunk):
            y = d.height - (i + 1) * rh - i * GAP
            x = 0
            for fn, wt in row:
                w = col * wt + GAP * (wt - 1)
                fn(d, x, y, w, rh)
                x += w + GAP
        pages.append(d)
    return pages


def _combined(card):
    """One outlet's key figures with its platforms added together (ratings and percentages averaged over the platforms that have them)."""
    vals = list(card.values())
    s = lambda k: sum(v.get(k) or 0 for v in vals) or None
    avg = lambda k: (sum(v[k] for v in vals if v.get(k) is not None) / len([v for v in vals if v.get(k) is not None])) if any(v.get(k) is not None for v in vals) else None
    spend = sum(v.get("ad_spend") or 0 for v in vals)
    roi = sum((v.get("ad_roi") or 0) * (v.get("ad_spend") or 0) for v in vals) / spend if spend else None
    return {"sales": s("sales"), "orders": s("orders"), "rating": avg("rating"), "online": avg("online"), "delayed": avg("delayed"), "ad_roi": roi, "complaints": s("complaints"), "payout": s("payout")}


def _outlet_rank(d, x, y, w, h, title, rows, color, top):
    _card(d, x, y, w, h, title)
    cols = [("Orders", 166), ("Rating", 114), ("Online", 62), ("Ads return", 10)]  # right edges, counted from the card's right side
    for label, off in cols:
        _text(d, x + w - off, y + h - 15, label, 6.8, color=MUTE, anchor="end")
    if not rows:
        _text(d, x + 10, y + h / 2 - 6, "No outlets to compare in this period", 8, color=MUTE)
        return
    rh = min(34, (h - 34) / len(rows))
    peak = max(c["sales"] or 0 for _, c in rows) or 1
    bar_w = w - 28 - 166 - 30 - 54
    for i, (name, c) in enumerate(rows):
        by = y + h - 36 - i * rh
        d.add(Rect(x + 8, by - 2, 14, 14, rx=7, ry=7, fillColor=color, strokeColor=None))
        _text(d, x + 15, by + 2, str(i + 1), 7.4, True, colors.white, "middle")
        _text(d, x + 28, by + 7, (name if len(name) <= 26 else name[:25] + "…"), 8, True)
        d.add(Rect(x + 28, by - 4, bar_w, 6, rx=3, ry=3, fillColor=colors.white, strokeColor=None))
        d.add(Rect(x + 28, by - 4, max(2, bar_w * (c["sales"] or 0) / peak), 6, rx=3, ry=3, fillColor=color, strokeColor=None))
        _text(d, x + 28 + bar_w + 6, by - 3, P.fmt(c["sales"], "currency", short=True) if c["sales"] else "-", 7.4, True)
        for text, (label, off) in zip((_fmt(c["orders"], "count"), _fmt(c["rating"], "rating"), _fmt(c["online"], "percent"), _fmt(c["ad_roi"], "ratio")), cols):
            _text(d, x + w - off, by + 1, text, 7.6, anchor="end")


def outlet_page(r):
    """The five best and five worst outlets by sales, each with its platforms added together. None when there are fewer than two outlets."""
    cards = [(c["name"].split(" · ")[-1] if " · " in c["name"] else c["name"], _combined(c["by"])) for c in r["compact"]["scorecards"]]
    cards = [c for c in cards if c[1]["sales"]]
    if len(cards) < 2:
        return None
    cards.sort(key=lambda c: -c[1]["sales"])
    n = min(5, len(cards) // 2) if len(cards) < 10 else 5
    best, worst = cards[:n], list(reversed(cards[-n:]))
    rh = 40 + 34 * n
    d = Drawing(W, rh)
    half = (W - GAP) / 2
    _outlet_rank(d, 0, 0, half, rh, f"Best {n} outlets by sales", best, P.GREEN, True)
    _outlet_rank(d, half + GAP, 0, half, rh, f"Weakest {n} outlets by sales", worst, P.RED, False)
    return d
