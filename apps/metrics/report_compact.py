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
