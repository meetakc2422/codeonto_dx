"""The report as an Excel workbook: a Summary page in the app's own look (logo band, headline tiles, Zomato vs Swiggy, what changed), one tidy sheet
per module with the same numbers as the PDF and the Report page, a Months sheet with a chart, and a Data gaps sheet when days are missing."""

import io
from datetime import date
from pathlib import Path

from django.conf import settings
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY, BLUE, GREEN, RED, GREY, BAND, RULE = "0B1229", "D9480F", "12803F", "C4302B", "6B7585", "F3F5F9", "DDE2EA"
PLATFORM_FILL = {"zomato": "E23744", "swiggy": "FC8019", "district": "7C3AED"}
ASSETS = Path(settings.BASE_DIR) / "frontend" / "assets"
FONT = "Calibri"

# Indian digit grouping in the number format itself, so the cell stays a real number (sortable, summable)
CUR = '[>=10000000]"₹"##\\,##\\,##\\,##0;[>=100000]"₹"##\\,##\\,##0;"₹"##,##0'
FORMATS = {"currency": CUR, "percent": '0.0"%"', "count": "#,##0", "rating": "0.00", "ratio": '0.00"x"', "seconds": '0.0" min"', "minutes": '0.0" min"'}
CHG = '+0.0"%";-0.0"%";0.0"%"'
thin = Side(style="thin", color=RULE)


def _num(v, unit):
    """The cell value for a unit: seconds become minutes, everything else stays as it is."""
    if v is None:
        return None
    if unit in ("seconds", "minutes"):
        return round(v / 60, 1) if unit == "seconds" else round(v, 1)
    if unit == "currency":
        return round(v)
    if unit == "percent":
        return round(v, 1)
    if unit in ("rating", "ratio"):
        return round(v, 2)
    return round(v) if abs(v - round(v)) < 1e-6 else round(v, 2)


def _fill(color):
    return PatternFill("solid", fgColor=color)


def _head(cell, text, align="center"):
    cell.value = text
    cell.fill, cell.font = _fill(NAVY), Font(name=FONT, bold=True, color="FFFFFF", size=10)
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)


def _chg_font(ch, hib):
    if ch is None or abs(ch) < 0.05:
        return Font(name=FONT, size=9, color=GREY)
    return Font(name=FONT, size=9, bold=True, color=GREEN if (ch >= 0) == hib else RED)


def _logo(ws, anchor, height_px):
    try:
        img = XlImage(str(ASSETS / "logo-full.png"))
        img.width, img.height = int(height_px * 268 / 70), height_px
        ws.add_image(img, anchor)
    except Exception:  # noqa: BLE001  the report is worth more than its logo
        pass


def _summary(wb, r):
    ws = wb.active
    ws.title = "Summary"
    ws.sheet_view.showGridLines = False
    p, cov = r["period"], r["coverage"]
    for i, w in enumerate((30, 17, 17, 17, 17, 17, 17, 17), start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for col in range(1, 9):
        ws.cell(row=1, column=col).fill = _fill(NAVY)
    ws.row_dimensions[1].height = 40
    _logo(ws, "A1", 32)
    ws["H1"].value = "Weekly report" if p["days"] == 7 else "Report"
    ws["H1"].font, ws["H1"].alignment = Font(name=FONT, bold=True, color="FFFFFF", size=11), Alignment(horizontal="right", vertical="center")
    ws.merge_cells("A2:H2")
    ws["A2"].value, ws["A2"].font = r["brand"], Font(name=FONT, bold=True, size=20, color=NAVY)
    ws.row_dimensions[2].height = 30
    ws.merge_cells("A3:H3")
    nice = lambda iso: date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")
    ws["A3"].value = f'{nice(p["start"])} to {nice(p["end"])} ({p["days"]} days)  |  {r["outlets"]} outlets  |  compared with {nice(p["prev_start"])} to {nice(p["prev_end"])}'
    ws["A3"].font = Font(name=FONT, size=10, color=GREY)

    ws.merge_cells("A4:H4")
    if not cov["days"]:
        text, bg, fg = cov.get("note", ""), BAND, GREY
    elif cov["complete"]:
        text, bg, fg = f'Data check: sales data is complete for all {cov["days"]} days ({nice(cov["from"])} to {nice(cov["to"])}).', "E8F7EE", GREEN
    else:
        text, bg, fg = f'Data check: {len(cov["gaps"])} outlet/platform(s) are missing some days. Totals leave those days out. See the "Data gaps" sheet.', "FFF4E0", "8A5A00"
    ws["A4"].value, ws["A4"].font, ws["A4"].fill = text, Font(name=FONT, bold=True, size=10, color=fg), _fill(bg)
    ws["A4"].alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[4].height = 22

    # headline tiles: four, two columns each
    row = 6
    for k, h in enumerate(r.get("headline", [])[:4]):
        c1, c2 = 1 + k * 2, 2 + k * 2  # tiles take two columns each
        for rr, val, font in ((row, h["name"], Font(name=FONT, size=9, color=GREY)), (row + 1, _num(h["value"], h["unit"]), Font(name=FONT, size=18, bold=True, color=NAVY))):
            ws.merge_cells(start_row=rr, start_column=c1, end_row=rr, end_column=c2)
            cell = ws.cell(row=rr, column=c1, value=val)
            cell.font, cell.alignment = font, Alignment(horizontal="left", indent=1)
            if rr == row + 1:
                cell.number_format = FORMATS.get(h["unit"], "General")
        ws.merge_cells(start_row=row + 2, start_column=c1, end_row=row + 2, end_column=c2)
        chg = ws.cell(row=row + 2, column=c1, value=h.get("change"))
        chg.number_format, chg.font, chg.alignment = CHG, _chg_font(h.get("change"), h.get("higher_is_better", True)), Alignment(horizontal="left", indent=1)
        for rr in (row, row + 1, row + 2):
            for cc in (c1, c2):
                ws.cell(row=rr, column=cc).fill = _fill(BAND)
        ws.row_dimensions[row + 1].height = 28
    row += 4

    if r.get("platforms"):
        ws.cell(row=row, column=1, value="By platform").font = Font(name=FONT, bold=True, size=12, color=NAVY)
        row += 1
        for i, h in enumerate(("Platform", "Sales", "Share of sales", "Orders", "Avg order value", "Rating", "Cancellation rate"), start=1):
            _head(ws.cell(row=row, column=i), h, "left" if i == 1 else "right")
        for x in r["platforms"]:
            row += 1
            vals = ((x["name"], None), (x["sales"], "currency"), (x["share"], "percent"), (x["orders"], "count"), (x["aov"], "currency"), (x["rating"], "rating"), (x["cancellation"], "percent"))
            for i, (v, u) in enumerate(vals, start=1):
                c = ws.cell(row=row, column=i, value=_num(v, u) if u else v)
                c.border = Border(bottom=thin)
                if i == 1:
                    c.fill, c.font = _fill(PLATFORM_FILL.get(x["code"], GREY)), Font(name=FONT, bold=True, color="FFFFFF")
                else:
                    c.number_format, c.font, c.alignment = FORMATS.get(u, "General"), Font(name=FONT, size=10), Alignment(horizontal="right")
        row += 2

    if r["highlights"]:
        ws.cell(row=row, column=1, value="What changed most").font = Font(name=FONT, bold=True, size=12, color=NAVY)
        row += 1
        for i, h in enumerate(("Measure", "Now", "Before", "Change"), start=1):
            _head(ws.cell(row=row, column=i), h, "left" if i == 1 else "right")
        for n in r["highlights"]:
            row += 1
            ws.cell(row=row, column=1, value=n["name"]).font = Font(name=FONT, size=10)
            for col, v in ((2, n["value"]), (3, n["prev"])):
                c = ws.cell(row=row, column=col, value=_num(v, n["unit"]))
                c.number_format, c.alignment, c.font = FORMATS.get(n["unit"], "General"), Alignment(horizontal="right"), Font(name=FONT, size=10)
            c = ws.cell(row=row, column=4, value=n["change"])
            c.number_format, c.alignment = CHG, Alignment(horizontal="right")
            c.font = Font(name=FONT, size=10, bold=True, color=GREEN if n["good"] else RED)
            for col in range(1, 5):
                ws.cell(row=row, column=col).border = Border(bottom=thin)
        row += 2
    ws.cell(row=row, column=1, value="Sales are each app's own figure: Zomato's Sales plus Swiggy's Net Sales. Payout figures are summed from the platforms' order statements.").font = Font(name=FONT, size=8, color=GREY)
    ws.page_setup.orientation, ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = "landscape", 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _section(wb, sec, r):
    ws = wb.create_sheet(sec["title"][:31])
    ws.sheet_view.showGridLines = False
    cols = sec["columns"]
    with_change = sec.get("kind") is None
    p = r["period"]
    ws["A1"].value, ws["A1"].font = sec["title"], Font(name=FONT, bold=True, size=14, color=NAVY)
    ws["A2"].value = f'{r["brand"]}  |  {p["start"]} to {p["end"]}' + ("  |  Before = the previous period of the same length" if with_change else "")
    ws["A2"].font = Font(name=FONT, size=9, color=GREY)
    top = 4
    width = 3 if with_change else 1
    _head(ws.cell(row=top, column=1), "Outlet", "left")
    if with_change:
        ws.merge_cells(start_row=top, start_column=1, end_row=top + 1, end_column=1)
    for i, c in enumerate(cols):
        c1 = 2 + i * width
        label = c["name"] + (" (min)" if c["unit"] == "seconds" else "")
        if with_change:
            ws.merge_cells(start_row=top, start_column=c1, end_row=top, end_column=c1 + 2)
            _head(ws.cell(row=top, column=c1), label)
            for k, sub in enumerate(("Now", "Before", "Change")):
                _head(ws.cell(row=top + 1, column=c1 + k), sub)
                ws.column_dimensions[get_column_letter(c1 + k)].width = (13, 13, 9)[k]
        else:
            _head(ws.cell(row=top, column=c1), label)
            ws.column_dimensions[get_column_letter(c1)].width = 16
    ws.row_dimensions[top].height = 32
    first = top + (2 if with_change else 1)
    ws.column_dimensions["A"].width = 38

    def put(row, name, values, bold=False):
        a = ws.cell(row=row, column=1, value=name)
        a.font = Font(name=FONT, size=10, bold=bold)
        for i, c in enumerate(cols):
            v = values.get(c["code"])
            c1 = 2 + i * width
            fmt = FORMATS.get(c["unit"], "General")
            if with_change:
                now = ws.cell(row=row, column=c1, value=_num(v["value"], c["unit"]) if v else None)
                before = ws.cell(row=row, column=c1 + 1, value=_num(v["prev"], c["unit"]) if v else None)
                chg = ws.cell(row=row, column=c1 + 2, value=v["change"] if v else None)
                now.number_format = before.number_format = fmt
                chg.number_format = CHG
                now.font = Font(name=FONT, size=10, bold=True)
                before.font = Font(name=FONT, size=10, color=GREY)
                chg.font = _chg_font(v["change"] if v else None, c.get("higher_is_better", True))
                for cell in (now, before, chg):
                    cell.alignment = Alignment(horizontal="right")
            else:
                cell = ws.cell(row=row, column=c1, value=_num(v, c["unit"]))
                cell.number_format, cell.font, cell.alignment = fmt, Font(name=FONT, size=10, bold=bold), Alignment(horizontal="right")
        for col in range(1, 2 + len(cols) * width):
            cell = ws.cell(row=row, column=col)
            cell.border = Border(bottom=thin, top=Side(style="medium", color=NAVY) if bold else None)
            if bold:
                cell.fill = _fill("E7ECF4")
            elif (row - first) % 2:
                cell.fill = _fill(BAND)

    row = first
    for rrow in sec["rows"]:
        put(row, rrow["name"], rrow)
        row += 1
    if len(sec["rows"]) > 1:
        put(row, "Total", sec["total"], bold=True)
    ws.freeze_panes = ws.cell(row=first, column=2)
    ws.page_setup.orientation, ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = "landscape", 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _months(wb, r):
    if not any(m["sales"] for m in r["months"]):
        return
    ws = wb.create_sheet("Months")
    ws.sheet_view.showGridLines = False
    ws["A1"].value, ws["A1"].font = "Month by month", Font(name=FONT, bold=True, size=14, color=NAVY)
    for i, h in enumerate(("Month", "Sales", "Payout", "Ads % of sales", "Discount % of sales"), start=1):
        _head(ws.cell(row=3, column=i), h, "left" if i == 1 else "right")
        ws.column_dimensions[get_column_letter(i)].width = 20 if i > 1 else 14
    for k, m in enumerate(r["months"], start=4):
        for i, (v, fmt) in enumerate(((m["month"], None), (_num(m["sales"], "currency"), CUR), (_num(m["payout"], "currency"), CUR), (m["ads_pct"], '0.0"%"'), (m["discount_pct"], '0.0"%"')), start=1):
            c = ws.cell(row=k, column=i, value=v)
            c.font, c.border = Font(name=FONT, size=10), Border(bottom=thin)
            if fmt:
                c.number_format, c.alignment = fmt, Alignment(horizontal="right")
    last = 3 + len(r["months"])
    ch = BarChart()
    ch.type, ch.title, ch.height, ch.width = "col", "Sales and payout", 8.5, 20
    ch.add_data(Reference(ws, min_col=2, max_col=3, min_row=3, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=4, max_row=last))
    ch.series[0].graphicalProperties.solidFill, ch.series[1].graphicalProperties.solidFill = BLUE, "9AA8E8"
    ws.add_chart(ch, f"A{last + 3}")


def _gaps(wb, r):
    cov = r["coverage"]
    if cov["complete"] or not cov["days"]:
        return
    ws = wb.create_sheet("Data gaps")
    ws.sheet_view.showGridLines = False
    ws["A1"].value, ws["A1"].font = "Days with no sales data", Font(name=FONT, bold=True, size=14, color=NAVY)
    ws["A2"].value = f'Checked on daily delivered orders from {cov["from"]} to {cov["to"]}. The figures in this workbook leave these days out.'
    ws["A2"].font = Font(name=FONT, size=9, color=GREY)
    for i, h in enumerate(("Outlet", "Platform", "Days missing", "Which days"), start=1):
        _head(ws.cell(row=4, column=i), h, "left")
    for k, g in enumerate(cov["gaps"], start=5):
        for i, v in enumerate((g["name"], g["platform"].title(), f'{g["missing_days"]}' + (" (all)" if g["no_data"] else ""), ", ".join(g["ranges"])), start=1):
            c = ws.cell(row=k, column=i, value=v)
            c.font, c.border = Font(name=FONT, size=10), Border(bottom=thin)
    for col, w in zip("ABCD", (42, 12, 14, 70)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"


def build_xlsx(r: dict) -> bytes:
    wb = Workbook()
    _summary(wb, r)
    for sec in r["sections"]:
        _section(wb, sec, r)
    _months(wb, r)
    _gaps(wb, r)
    wb.properties.title, wb.properties.creator = f'{r["brand"]} report', "Codeonto"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
