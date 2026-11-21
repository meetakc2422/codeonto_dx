"""The report as a multi-page PDF (A4 landscape): the same numbers as the Report page and the Excel file, laid out for sending to a client.

Dense on purpose: small Inter type, a value and its change on one line, several sections to a page. Falls back to the standard
fonts if the Inter files are missing."""

import io
from datetime import date
from pathlib import Path

from django.conf import settings
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY, BLUE, GREEN, RED, GREY, LIGHT = colors.HexColor("#0B1229"), colors.HexColor("#408FCA"), colors.HexColor("#12803F"), colors.HexColor("#C4302B"), colors.HexColor("#6B7585"), colors.HexColor("#F3F5F9")
AMBER_BG, GREEN_BG, RULE = colors.HexColor("#FFF4E0"), colors.HexColor("#E8F7EE"), colors.HexColor("#DDE2EA")
ASSETS = Path(settings.BASE_DIR) / "frontend" / "assets"
PLATFORM_COLOR = {"zomato": colors.HexColor("#E23744"), "swiggy": colors.HexColor("#FC8019"), "district": colors.HexColor("#7C3AED")}
PAGE = landscape(A4)
MARGIN = 10 * mm
WIDTH = PAGE[0] - 2 * MARGIN

# fonts: Inter if its files are there (they also carry the rupee sign), else the standard ones
F, FB, FS, RUPEE = "Helvetica", "Helvetica-Bold", "Helvetica-Bold", "Rs "
try:
    for name, file in (("Inter", "Inter-Regular.ttf"), ("Inter-SemiBold", "Inter-SemiBold.ttf"), ("Inter-Bold", "Inter-Bold.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(ASSETS / "fonts" / file)))
    F, FS, FB, RUPEE = "Inter", "Inter-SemiBold", "Inter-Bold", "₹"
except Exception:  # noqa: BLE001  a report is worth more than its font
    pass


def indian(n: int) -> str:
    """1234567 -> 12,34,567"""
    s, sign = str(abs(int(n))), "-" if n < 0 else ""
    if len(s) <= 3:
        return sign + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return sign + ",".join(parts) + "," + tail


def compact(v: float) -> str:
    a = abs(v)
    if a >= 1e7:
        return f"{RUPEE}{v / 1e7:.2f} Cr"
    if a >= 1e5:
        return f"{RUPEE}{v / 1e5:.2f} L"
    return f"{RUPEE}{indian(round(v))}"


def fmt(v, unit: str, short: bool = False) -> str:
    if v is None:
        return "-"
    if unit == "currency":
        return compact(v) if short else f"{RUPEE}{indian(round(v))}"
    if unit == "percent":
        return f"{v:.1f}%"
    if unit == "rating":
        return f"{v:.2f}"
    if unit == "ratio":
        return f"{v:.2f}x"
    if unit == "seconds":
        m, sec = divmod(int(round(v)), 60)
        return f"{m}m {sec:02d}s"
    if unit == "minutes":
        return f"{v:.1f} min"
    return indian(round(v)) if abs(v) >= 1000 else (f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}")


def _styles():
    base = dict(fontName=F, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#1B2333"))
    return {
        "title": ParagraphStyle("t", fontName=FB, fontSize=16, leading=19, textColor=NAVY),
        "sub": ParagraphStyle("s", **{**base, "textColor": GREY, "fontSize": 8}),
        "h2": ParagraphStyle("h2", fontName=FB, fontSize=10.5, leading=13, textColor=NAVY, spaceBefore=7, spaceAfter=3, keepWithNext=True),
        "cell": ParagraphStyle("c", **base),
        "num": ParagraphStyle("n", **{**base, "alignment": 2}),
        "head": ParagraphStyle("h", **{**base, "fontName": FS, "fontSize": 7, "leading": 8.5, "textColor": colors.white}),
        "headr": ParagraphStyle("hr", **{**base, "fontName": FS, "fontSize": 7, "leading": 8.5, "textColor": colors.white, "alignment": 2}),
        "small": ParagraphStyle("sm", **{**base, "fontSize": 6.8, "textColor": GREY}),
        "note": ParagraphStyle("n2", **{**base, "fontSize": 8, "leading": 10.5}),
        "tile_l": ParagraphStyle("tl", **{**base, "fontSize": 7, "textColor": GREY}),
        "tile_v": ParagraphStyle("tv", fontName=FB, fontSize=14, leading=16, textColor=NAVY),
    }


def _chg(ch, hib=True, size=6.6) -> str:
    """The change as a small coloured figure on the same line as its value."""
    if ch is None:
        return ""
    color = "#6B7585" if abs(ch) < 0.05 else ("#12803F" if (ch >= 0) == hib else "#C4302B")
    return f' <font size="{size}" color="{color}">{"+" if ch >= 0 else "-"}{abs(ch):.1f}%</font>'


def _cell(col, v, st):
    if v is None:
        return Paragraph("-", st["num"])
    if isinstance(v, dict):
        if v.get("value") is None:
            return Paragraph("-", st["num"])
        return Paragraph(f'<font name="{FS}">{fmt(v["value"], col["unit"])}</font>{_chg(v.get("change"), col.get("higher_is_better", True))}', st["num"])
    return Paragraph(f'<font name="{FS}">{fmt(v, col["unit"])}</font>', st["num"])


def _logo(name, height_mm):
    """A logo from the app's own assets at a small height (so its pixels stay sharp); None when missing, so a report never fails over a picture."""
    try:
        from PIL import Image as PI

        path = ASSETS / name
        w, h = PI.open(path).size
        return Image(str(path), width=height_mm * mm * w / h, height=height_mm * mm)
    except Exception:  # noqa: BLE001
        return None


def _table(sec, st):
    cols = sec["columns"]
    head = [Paragraph("Outlet", st["head"])] + [Paragraph(c["name"], st["headr"]) for c in cols]
    rows = [head] + [[Paragraph(r["name"], st["cell"])] + [_cell(c, r.get(c["code"]), st) for c in cols] for r in sec["rows"]]
    if len(sec["rows"]) > 1:
        rows.append([Paragraph(f'<font name="{FB}">Total</font>', st["cell"])] + [_cell(c, sec["total"].get(c["code"]), st) for c in cols])
    first = 128 if len(cols) > 6 else 170
    rest = (WIDTH - first) / len(cols)
    t = Table(rows, colWidths=[first] + [rest] * len(cols), repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
             ("LINEBELOW", (0, 0), (-1, -1), 0.2, RULE), ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if len(sec["rows"]) > 1:
        style += [("LINEABOVE", (0, -1), (-1, -1), 0.8, NAVY), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E7ECF4"))]
    t.setStyle(TableStyle(style))
    return t


def _tiles(r, st):
    cells = []
    for h in r.get("headline", []):
        cells.append([Paragraph(h["name"], st["tile_l"]), Paragraph(fmt(h["value"], h["unit"], short=True), st["tile_v"]),
                      Paragraph(_chg(h.get("change"), h.get("higher_is_better", True), 7.5).strip() + ' <font size="6.3" color="#6B7585">vs previous period</font>' if h.get("change") is not None else "", st["cell"])])
    if not cells:
        return None
    t = Table([cells], colWidths=[WIDTH / len(cells)] * len(cells))
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.4, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.4, RULE), ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    return t


def _platform_block(r, st):
    rows = r.get("platforms") or []
    if not rows:
        return None
    head = [Paragraph("Platform", st["head"])] + [Paragraph(h, st["headr"]) for h in ("Sales", "Share", "Orders", "Avg order value", "Rating", "Cancellation")]
    body = []
    for x in rows:
        logo = _logo(f'{x["code"]}.png', 5)
        hexc = PLATFORM_COLOR.get(x["code"], GREY).hexval().replace("0x", "#")
        name = Paragraph(f'<font name="{FB}" color="{hexc}">{x["name"]}</font>', st["cell"])
        inner = Table([[logo, name]] if logo else [[name]], colWidths=([logo.drawWidth + 5, 70] if logo else [86]))
        inner.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        body.append([inner] + [Paragraph(f'<font name="{FS}">{fmt(v, u)}</font>', st["num"]) for v, u in
                               ((x["sales"], "currency"), (x["share"], "percent"), (x["orders"], "count"), (x["aov"], "currency"), (x["rating"], "rating"), (x["cancellation"], "percent"))])
    t = Table([head] + body, colWidths=[100] + [(WIDTH - 100) / 6] * 6, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
             ("LINEBELOW", (0, 1), (-1, -1), 0.2, RULE)]
    for i, x in enumerate(rows, start=1):
        style.append(("LINEBEFORE", (0, i), (0, i), 3, PLATFORM_COLOR.get(x["code"], GREY)))
    t.setStyle(TableStyle(style))
    return t


def _gap_summary(cov):
    """(sentences for the front page, gaps still to list one by one). A platform with no data at all for any of its outlets is one sentence."""
    by = {}
    for g in cov["gaps"]:
        by.setdefault(g["platform"], []).append(g)
    lines, rest = [], []
    for plat, gs in by.items():
        if all(g["no_data"] for g in gs):
            lines.append(f'<b>{plat.title()}:</b> no data for {"its only outlet" if len(gs) == 1 else f"any of its {len(gs)} outlets"} in this period, so the figures leave {plat.title()} out.')
        else:
            rest += gs
    return lines, rest


def _month_chart(months):
    if not any(m["sales"] for m in months):
        return None
    d = Drawing(WIDTH, 120)
    bc = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 50, 18, WIDTH - 80, 85
    bc.data = [[(m["sales"] or 0) for m in months], [(m["payout"] or 0) for m in months]]
    bc.categoryAxis.categoryNames = [m["month"] for m in months]
    bc.categoryAxis.labels.fontSize, bc.categoryAxis.labels.fontName = 7, F
    bc.valueAxis.labels.fontSize, bc.valueAxis.labels.fontName = 6.5, F
    bc.valueAxis.labelTextFormat = lambda v: compact(v).replace(RUPEE, "")
    bc.bars[0].fillColor, bc.bars[1].fillColor = BLUE, colors.HexColor("#9AA8E8")
    bc.barSpacing, bc.groupSpacing = 2, 14
    bc.valueAxis.valueMin = 0
    d.add(bc)
    d.add(String(50, 109, "Sales", fontSize=7, fontName=F, fillColor=BLUE))
    d.add(String(86, 109, "Payout", fontSize=7, fontName=F, fillColor=colors.HexColor("#6F7FD1")))
    return d


def build_pdf(r: dict) -> bytes:
    st = _styles()
    p, cov = r["period"], r["coverage"]
    nice = lambda iso: date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")
    title = "Weekly report" if p["days"] == 7 else "Report"
    logo = _logo("logo-full.png", 8)  # white wordmark: it sits on a dark band like the app's own header
    band = Table([[logo or Paragraph("SocialSpork", st["head"]), Paragraph(f'<font color="white" name="{FS}">{title}</font> <font color="#9AA8C7">| {nice(p["start"])} to {nice(p["end"])}</font>',
                                                                           ParagraphStyle("b", parent=st["cell"], alignment=2, fontSize=8.5, leading=11))]], colWidths=[WIDTH * 0.4, WIDTH * 0.6])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                              ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story = [band, Spacer(1, 6), Paragraph(r["brand"], st["title"]),
             Paragraph(f'{r["outlets"]} outlets &nbsp;|&nbsp; {p["days"]} days &nbsp;|&nbsp; compared with {nice(p["prev_start"])} to {nice(p["prev_end"])}', st["sub"]), Spacer(1, 5)]
    tiles = _tiles(r, st)
    if tiles:
        story += [tiles, Spacer(1, 5)]
    plat = _platform_block(r, st)
    if plat is not None:
        story += [plat, Spacer(1, 5)]

    # the data check goes early: a reader should know what the numbers rest on
    if not cov["days"]:
        story.append(Paragraph(cov.get("note", ""), st["small"]))
    elif cov["complete"]:
        box = Table([[Paragraph(f'<font color="#12803F"><b>Data check:</b> sales data is complete for all {cov["days"]} days ({nice(cov["from"])} to {nice(cov["to"])}).</font>', st["note"])]], colWidths=[WIDTH])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN_BG), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story.append(box)
    else:
        whole, partial = _gap_summary(cov)
        parts = whole + [f'{g["name"]} ({g["platform"].title()}): {", ".join(g["ranges"])}' for g in partial[:6]]
        more = f'<br/>...and {len(partial) - 6} more outlets with missing days (full list on the last page)' if len(partial) > 6 else ""
        box = Table([[Paragraph(f'<font color="#8A5A00"><b>Data check:</b> some data is not available yet.</font><br/>{"<br/>".join(parts)}{more}', st["note"])]], colWidths=[WIDTH])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AMBER_BG), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story.append(box)

    if r["highlights"]:
        story.append(Paragraph("What changed most", st["h2"]))
        half = (len(r["highlights"]) + 1) // 2
        cols = [r["highlights"][:half], r["highlights"][half:]]

        def line(n):
            color = "#12803F" if n["good"] else "#C4302B"
            return Paragraph(f'<font color="{color}" name="{FB}">{"+" if n["change"] >= 0 else "-"}{abs(n["change"]):.0f}%</font> {n["name"]}: {fmt(n["prev"], n["unit"])} to {fmt(n["value"], n["unit"])}', st["cell"])

        grid = [[line(cols[0][i]) if i < len(cols[0]) else "", line(cols[1][i]) if i < len(cols[1]) else ""] for i in range(half)]
        gt = Table(grid, colWidths=[WIDTH / 2] * 2)
        gt.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(gt)
    story.append(Spacer(1, 3))
    story.append(Paragraph("Sales are each app's own figure: Zomato's Sales plus Swiggy's Net Sales. Payout figures are summed from the platforms' order statements.", st["small"]))

    for sec in r["sections"]:  # sections follow one another: a short table shares the page with the next one
        block = [Paragraph(sec["title"], st["h2"]), _table(sec, st)]
        story += [KeepTogether(block)] if len(sec["rows"]) <= 12 else block
    chart = _month_chart(r["months"])
    if chart is not None:
        rows = [[Paragraph(h, st["head"] if i == 0 else st["headr"]) for i, h in enumerate(("Month", "Sales", "Payout", "Ads % of sales", "Discount % of sales"))]] + [
            [Paragraph(m["month"], st["cell"]), Paragraph(fmt(m["sales"], "currency"), st["num"]), Paragraph(fmt(m["payout"], "currency"), st["num"]),
             Paragraph(fmt(m["ads_pct"], "percent"), st["num"]), Paragraph(fmt(m["discount_pct"], "percent"), st["num"])] for m in r["months"]]
        t = Table(rows, colWidths=[WIDTH / 5] * 5, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2)]))
        story += [KeepTogether([Paragraph("Month by month", st["h2"]), chart, Spacer(1, 4), t])]
    if not cov["complete"] and cov["days"]:
        rows = [[Paragraph(h, st["head"]) for h in ("Outlet", "Platform", "Days missing", "Which days")]] + [
            [Paragraph(g["name"], st["cell"]), Paragraph(g["platform"].title(), st["cell"]), Paragraph(f'{g["missing_days"]}' + (" (all)" if g["no_data"] else ""), st["cell"]),
             Paragraph(", ".join(g["ranges"]), st["cell"])] for g in cov["gaps"]]
        t = Table(rows, colWidths=[250, 60, 70, WIDTH - 380], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2)]))
        story += [PageBreak(), Paragraph("Days with no sales data", st["h2"]),
                  Paragraph(f'Checked on daily delivered orders from {nice(cov["from"])} to {nice(cov["to"])}. The figures in this report leave these days out.', st["small"]), Spacer(1, 4), t]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(F, 6.8)
        canvas.setFillColor(GREY)
        try:
            canvas.drawImage(str(ASSETS / "logo-mark.png"), MARGIN, 5.4 * mm, width=3.8 * mm, height=4.0 * mm, mask="auto")
        except Exception:  # noqa: BLE001
            pass
        canvas.drawString(MARGIN + 5.5 * mm, 6.4 * mm, f'{r["brand"]} | {nice(p["start"])} to {nice(p["end"])} | SocialSpork')
        canvas.drawRightString(PAGE[0] - MARGIN, 6.4 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=PAGE, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=13 * mm,
                      title=f'{r["brand"]} {title}', author="SocialSpork").build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
