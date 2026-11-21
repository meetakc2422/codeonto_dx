"""The report as a multi-page PDF (A4 landscape): the same numbers as the Report page and the Excel file, laid out for sending to a client.

Uses only the standard PDF fonts, which have no rupee sign, so amounts are written "Rs 1,23,456" (Indian digit grouping)."""

import io
from datetime import date

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY, BLUE, GREEN, RED, GREY, LIGHT = colors.HexColor("#0B1229"), colors.HexColor("#408FCA"), colors.HexColor("#12803F"), colors.HexColor("#C4302B"), colors.HexColor("#6B7585"), colors.HexColor("#F3F5F9")
AMBER_BG, GREEN_BG = colors.HexColor("#FFF4E0"), colors.HexColor("#E8F7EE")
PAGE = landscape(A4)
WIDTH = PAGE[0] - 2 * 14 * mm


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
        return f"Rs {v / 1e7:.2f} Cr"
    if a >= 1e5:
        return f"Rs {v / 1e5:.2f} L"
    return f"Rs {indian(round(v))}"


def fmt(v, unit: str, short: bool = False) -> str:
    if v is None:
        return "-"
    if unit == "currency":
        return compact(v) if short else f"Rs {indian(round(v))}"
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
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontSize=22, leading=26, textColor=NAVY, alignment=0, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=ss["Normal"], fontSize=10, textColor=GREY, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=14, textColor=NAVY, spaceBefore=4, spaceAfter=6),
        "cell": ParagraphStyle("c", parent=ss["Normal"], fontSize=8.5, leading=10.5),
        "cellb": ParagraphStyle("cb", parent=ss["Normal"], fontSize=8.5, leading=10.5, fontName="Helvetica-Bold"),
        "head": ParagraphStyle("h", parent=ss["Normal"], fontSize=8, leading=10, textColor=colors.white, fontName="Helvetica-Bold"),
        "small": ParagraphStyle("sm", parent=ss["Normal"], fontSize=8, leading=10, textColor=GREY),
        "note": ParagraphStyle("n", parent=ss["Normal"], fontSize=9.5, leading=13),
        "tile_l": ParagraphStyle("tl", parent=ss["Normal"], fontSize=8, textColor=GREY, leading=10),
        "tile_v": ParagraphStyle("tv", parent=ss["Normal"], fontSize=17, leading=20, textColor=NAVY, fontName="Helvetica-Bold"),
    }


def _delta(ch, higher_is_better=True, size=7.5) -> str:
    if ch is None:
        return ""
    good = (ch >= 0) == higher_is_better
    color = "#12803F" if good else "#C4302B"
    if abs(ch) < 0.05:
        color = "#6B7585"
    return f'<br/><font size="{size}" color="{color}">{"+" if ch >= 0 else "-"}{abs(ch):.1f}%</font>'


def _cell(col, v, st):
    if v is None:
        return Paragraph("-", st["cell"])
    if isinstance(v, dict):
        if v.get("value") is None:
            return Paragraph("-", st["cell"])
        return Paragraph(f'<b>{fmt(v["value"], col["unit"])}</b>{_delta(v.get("change"), col.get("higher_is_better", True))}', st["cell"])
    return Paragraph(f'<b>{fmt(v, col["unit"])}</b>', st["cell"])


def _table(sec, st):
    cols = sec["columns"]
    head = [Paragraph("Outlet", st["head"])] + [Paragraph(c["name"], st["head"]) for c in cols]
    rows = [head] + [[Paragraph(r["name"], st["cell"])] + [_cell(c, r.get(c["code"]), st) for c in cols] for r in sec["rows"]]
    if len(sec["rows"]) > 1:
        rows.append([Paragraph("<b>Total</b>", st["cell"])] + [_cell(c, sec["total"].get(c["code"]), st) for c in cols])
    first = 150 if len(cols) > 6 else 190
    rest = (WIDTH - first) / len(cols)
    t = Table(rows, colWidths=[first] + [rest] * len(cols), repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
             ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDE2EA")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if len(sec["rows"]) > 1:
        style += [("LINEABOVE", (0, -1), (-1, -1), 1, NAVY), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E7ECF4"))]
    t.setStyle(TableStyle(style))
    return t


def _tiles(r, st):
    cells = []
    for h in r.get("headline", []):
        cells.append([Paragraph(h["name"], st["tile_l"]), Paragraph(fmt(h["value"], h["unit"], short=True), st["tile_v"]),
                      Paragraph((_delta(h.get("change"), h.get("higher_is_better", True), 9).replace("<br/>", "") + ' <font size="7" color="#6B7585">vs previous period</font>') if h.get("change") is not None else "", st["cell"])])
    if not cells:
        return None
    t = Table([cells], colWidths=[WIDTH / len(cells)] * len(cells))
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE2EA")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE2EA")),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.white), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    return t


def _gap_summary(cov):
    """(sentences for the front page, gaps still to list one by one). A platform with no data at all for any of its outlets is one sentence."""
    by = {}
    for g in cov["gaps"]:
        by.setdefault(g["platform"], []).append(g)
    lines, rest = [], []
    for plat, gs in by.items():
        if all(g["no_data"] for g in gs):
            lines.append(f'<b>{plat.title()}:</b> no data for {"its only outlet" if len(gs) == 1 else f"any of its {len(gs)} outlets"} in this period, so the figures below leave {plat.title()} out.')
        else:
            rest += gs
    return lines, rest


def _month_chart(months):
    if not any(m["sales"] for m in months):
        return None
    d = Drawing(WIDTH, 170)
    bc = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 60, 25, WIDTH - 90, 125
    bc.data = [[(m["sales"] or 0) for m in months], [(m["payout"] or 0) for m in months]]
    bc.categoryAxis.categoryNames = [m["month"] for m in months]
    bc.categoryAxis.labels.fontSize = 8
    bc.valueAxis.labels.fontSize = 7
    bc.valueAxis.labelTextFormat = lambda v: compact(v).replace("Rs ", "")
    bc.bars[0].fillColor, bc.bars[1].fillColor = BLUE, colors.HexColor("#9AA8E8")
    bc.barSpacing, bc.groupSpacing = 2, 14
    bc.valueAxis.valueMin = 0
    d.add(bc)
    d.add(String(60, 158, "Sales", fontSize=8, fillColor=BLUE))
    d.add(String(100, 158, "Payout", fontSize=8, fillColor=colors.HexColor("#6F7FD1")))
    return d


def build_pdf(r: dict) -> bytes:
    st = _styles()
    p, cov = r["period"], r["coverage"]
    nice = lambda iso: date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")
    title = "Weekly report" if p["days"] == 7 else "Report"
    story = [Paragraph(f'{r["brand"]}', st["title"]),
             Paragraph(f'{title} &nbsp;|&nbsp; {nice(p["start"])} to {nice(p["end"])} ({p["days"]} days) &nbsp;|&nbsp; {r["outlets"]} outlets &nbsp;|&nbsp; '
                       f'compared with {nice(p["prev_start"])} to {nice(p["prev_end"])}', st["sub"])]
    tiles = _tiles(r, st)
    if tiles:
        story += [tiles, Spacer(1, 10)]

    # the data check goes first: a reader should know what the numbers rest on
    if not cov["days"]:
        story.append(Paragraph(cov.get("note", ""), st["small"]))
    elif cov["complete"]:
        box = Table([[Paragraph(f'<font color="#12803F"><b>Data check:</b> sales data is complete for all {cov["days"]} days ({nice(cov["from"])} to {nice(cov["to"])}).</font>', st["note"])]], colWidths=[WIDTH])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN_BG), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(box)
    else:
        whole, partial = _gap_summary(cov)
        parts = whole + [f'{g["name"]} ({g["platform"].title()}): {", ".join(g["ranges"])}' for g in partial[:6]]
        more = f'<br/>...and {len(partial) - 6} more outlets with missing days (full list on the last page)' if len(partial) > 6 else ""
        box = Table([[Paragraph(f'<font color="#8A5A00"><b>Data check:</b> some data is not available yet.</font><br/><font size="8.5">{"<br/>".join(parts)}{more}</font>', st["note"])]], colWidths=[WIDTH])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AMBER_BG), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(box)
    story.append(Spacer(1, 10))

    if r["highlights"]:
        story.append(Paragraph("What changed most", st["h2"]))
        for n in r["highlights"]:
            color = "#12803F" if n["good"] else "#C4302B"
            story.append(Paragraph(f'<font color="{color}"><b>{"+" if n["change"] >= 0 else "-"}{abs(n["change"]):.0f}%</b></font> &nbsp;{n["name"]}: '
                                   f'{fmt(n["prev"], n["unit"])} to {fmt(n["value"], n["unit"])}', st["note"]))
    story.append(Paragraph("Sales are each app's own figure: Zomato's Sales plus Swiggy's Net Sales. Payout figures are summed from the platforms' order statements.", st["small"]))

    for i, sec in enumerate(r["sections"]):
        story += ([Spacer(1, 12)] if i == 0 else [PageBreak()]) + [Paragraph(sec["title"], st["h2"]), _table(sec, st)]  # the first table follows the summary on page 1
    chart = _month_chart(r["months"])
    if chart is not None:
        rows = [[Paragraph(h, st["head"]) for h in ("Month", "Sales", "Payout", "Ads % of sales", "Discount % of sales")]] + [
            [Paragraph(m["month"], st["cell"]), Paragraph(fmt(m["sales"], "currency"), st["cell"]), Paragraph(fmt(m["payout"], "currency"), st["cell"]),
             Paragraph(fmt(m["ads_pct"], "percent"), st["cell"]), Paragraph(fmt(m["discount_pct"], "percent"), st["cell"])] for m in r["months"]]
        t = Table(rows, colWidths=[WIDTH / 5] * 5, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story += [PageBreak(), Paragraph("Month by month", st["h2"]), KeepTogether([chart, Spacer(1, 8), t])]
    if not cov["complete"] and cov["days"]:
        rows = [[Paragraph(h, st["head"]) for h in ("Outlet", "Platform", "Days missing", "Which days")]] + [
            [Paragraph(g["name"], st["cell"]), Paragraph(g["platform"].title(), st["cell"]), Paragraph(f'{g["missing_days"]}' + (" (all)" if g["no_data"] else ""), st["cell"]),
             Paragraph(", ".join(g["ranges"]), st["cell"])] for g in cov["gaps"]]
        t = Table(rows, colWidths=[260, 70, 80, WIDTH - 410], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story += [PageBreak(), Paragraph("Days with no sales data", st["h2"]),
                  Paragraph(f'Checked on daily delivered orders from {nice(cov["from"])} to {nice(cov["to"])}. The figures in this report leave these days out.', st["small"]), Spacer(1, 6), t]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREY)
        canvas.drawString(14 * mm, 8 * mm, f'{r["brand"]} | {nice(p["start"])} to {nice(p["end"])} | SocialSpork')
        canvas.drawRightString(PAGE[0] - 14 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=PAGE, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                      title=f'{r["brand"]} {title}', author="SocialSpork").build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
