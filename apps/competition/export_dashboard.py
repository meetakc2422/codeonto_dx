"""The first sheet of a competition workbook: a one-page report a restaurant partner can read at a glance.
A header, a scorecard coloured best-to-worst on every measure, where the outlet ranks, plain-language key insights,
and charts. Built from the same data as the detailed sheets that follow it."""

from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .swiggy import _count

NAVY, BLUE, GREEN, RED, AMBER, GREY = "0B1229", "408FCA", "D7F2E3", "FBDADB", "FDF3E1", "F4F6FA"
THIN = Side(style="thin", color="E6EAF0")

# (label, how to read it from (restaurant, insights), better: "high" / "low" / None for no colouring, number format)
MEASURES = [
    ("Rating", lambda r, i: r.rating, "high", "0.0"),
    ("Ratings (votes)", lambda r, i: _count(r.votes), "high", "#,##0"),
    ("Menu items", lambda r, i: i.get("items"), None, "0"),
    ("Categories", lambda r, i: i.get("categories"), None, "0"),
    ("Average item price (₹)", lambda r, i: i.get("avg_price"), None, "#,##0"),
    ("Offers running", lambda r, i: len(r.offers or []), "high", "0"),
    ("Bestseller-tagged items", lambda r, i: len(i.get("bestsellers") or []), "high", "0"),
    ("Out of stock now %", lambda r, i: round(100 * len(i.get("out_of_stock") or []) / i["items"]) if i.get("items") else None, "low", "0\"%\""),
    ("Items with a photo %", lambda r, i: i.get("photo_pct"), "high", "0\"%\""),
    ("Items with a description %", lambda r, i: i.get("desc_pct"), "high", "0\"%\""),
    ("Veg items %", lambda r, i: i.get("veg_pct"), None, "0\"%\""),
]


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def insights(rows, ins, kinds) -> list[str]:
    """Plain sentences about where the outlet stands. rows: [(label, restaurant, is_us)]; kinds: {(dish, size): {res_id: [prices]}}."""
    us = next((r for _, r, is_us in rows if is_us), None)
    them = [r for _, r, is_us in rows if not is_us]
    if not us:
        return peer_insights(them, ins, kinds)
    if not them:
        return ["Add at least one competitor to see how you compare."]
    out = []
    ui = ins[us.res_id]
    # rating
    best = max(them, key=lambda r: r.rating or 0)
    if us.rating is not None and best.rating is not None:
        if us.rating >= best.rating:
            out.append(f"Your rating {us.rating:.1f}★ is the highest of the {len(rows)} restaurants compared.")
        else:
            out.append(f"Your rating {us.rating:.1f}★ is {best.rating - us.rating:.1f} below the best, {best.name} at {best.rating:.1f}★.")
    # overall price
    their_avg = _avg([ins[r.res_id].get("avg_price") for r in them])
    if ui.get("avg_price") and their_avg:
        gap = (ui["avg_price"] - their_avg) / their_avg * 100
        word = "above" if gap > 0 else "below"
        out.append(f"Your average item price is ₹{ui['avg_price']:,}, {abs(gap):.0f}% {word} the competitors' average of ₹{their_avg:,.0f}.")
    # price by dish type, where both sides sell it
    gaps = []
    for (dish, size), by in kinds.items():
        mine = by.get(us.res_id)
        others = [p for rid, ps in by.items() if rid != us.res_id for p in ps]
        if mine and others:
            a, b = _avg(mine), _avg(others)
            gaps.append((a - b, dish, size, a, b))
    dear = sorted([g for g in gaps if g[0] > 0], reverse=True)[:3]
    cheap = sorted([g for g in gaps if g[0] < 0])[:3]
    if dear:
        out.append("Priced above competitors on: " + "; ".join(f"{d}{'' if s == 'regular' else f' ({s})'} ₹{a:,.0f} vs ₹{b:,.0f}" for _, d, s, a, b in dear) + ".")
    if cheap:
        out.append("Priced below competitors on: " + "; ".join(f"{d}{'' if s == 'regular' else f' ({s})'} ₹{a:,.0f} vs ₹{b:,.0f}" for _, d, s, a, b in cheap) + ".")
    # what competitors sell that we don't
    missing = {}
    for (dish, size), by in kinds.items():
        if us.res_id not in by:
            n = sum(1 for rid in by if rid != us.res_id)
            if n >= max(1, min(2, len(them))):
                missing[dish] = max(missing.get(dish, 0), n)
    if missing:
        top = sorted(missing.items(), key=lambda kv: -kv[1])[:6]
        out.append("Dishes competitors sell that you don't: " + ", ".join(f"{d} ({n} of {len(them)})" for d, n in top) + ".")
    # offers
    their_offers = _avg([len(r.offers or []) for r in them]) or 0
    mine_offers = len(us.offers or [])
    if mine_offers < their_offers:
        lead = max(them, key=lambda r: len(r.offers or []))
        out.append(f"You run {mine_offers} offers; competitors run {their_offers:.1f} on average. "
                   f"{lead.name} runs {len(lead.offers or [])}, for example \"{(lead.offers or [{}])[0].get('text', '')}\".")
    else:
        out.append(f"You run {mine_offers} offers, as many as or more than competitors ({their_offers:.1f} on average).")
    # stock, photos, descriptions
    oos = len(ui.get("out_of_stock") or [])
    their_oos = _avg([len(ins[r.res_id].get("out_of_stock") or []) for r in them]) or 0
    if oos > their_oos:
        out.append(f"{oos} of your items are out of stock right now, against {their_oos:.0f} on average for competitors.")
    for key, what in (("photo_pct", "photo"), ("desc_pct", "description")):
        mine, theirs = ui.get(key), _avg([ins[r.res_id].get(key) for r in them])
        if mine is not None and theirs is not None and mine + 5 < theirs:
            n = len(ui.get("no_photo" if what == "photo" else "no_desc") or [])
            out.append(f"{mine}% of your items have a {what} against {theirs:.0f}% for competitors: {n} items to fix.")
    return out


def peer_insights(them, ins, kinds) -> list[str]:
    """How the chosen restaurants compare with each other, for an analysis without the outlet itself."""
    if len(them) < 2:
        return ["Pick at least two restaurants to compare them with each other."]
    out = []
    rated = [r for r in them if r.rating is not None]
    if rated:
        hi, lo = max(rated, key=lambda r: r.rating), min(rated, key=lambda r: r.rating)
        out.append(f"Highest rated: {hi.name} at {hi.rating:.1f}★{f'; lowest: {lo.name} at {lo.rating:.1f}★' if lo is not hi else ''}.")
    voted = [(r, _count(r.votes)) for r in them if _count(r.votes)]
    if voted:
        r, n = max(voted, key=lambda x: x[1])
        out.append(f"Most reviewed: {r.name} with {r.votes} ratings, the biggest customer base of the group.")
    priced = [(r, ins[r.res_id].get("avg_price")) for r in them if ins[r.res_id].get("avg_price")]
    if len(priced) > 1:
        dear, cheap = max(priced, key=lambda x: x[1]), min(priced, key=lambda x: x[1])
        out.append(f"Most expensive menu: {dear[0].name} (average ₹{dear[1]:,}); cheapest: {cheap[0].name} (₹{cheap[1]:,}).")
    sized = [(r, ins[r.res_id].get("items") or 0) for r in them]
    big, small = max(sized, key=lambda x: x[1]), min(sized, key=lambda x: x[1])
    out.append(f"Largest menu: {big[0].name} with {big[1]} items; smallest: {small[0].name} with {small[1]}.")
    lead = max(them, key=lambda r: len(r.offers or []))
    if lead.offers:
        out.append(f"Most offers: {lead.name} with {len(lead.offers)}, for example \"{lead.offers[0].get('text', '')}\".")
    oos = [(r, len(ins[r.res_id].get("out_of_stock") or [])) for r in them]
    worst = max(oos, key=lambda x: x[1])
    if worst[1]:
        out.append(f"Most items out of stock right now: {worst[0].name} with {worst[1]}.")
    # dish types several of them sell, with who is cheapest
    common = [(k, by) for k, by in kinds.items() if sum(1 for r in them if r.res_id in by) >= 2]
    common = sorted(common, key=lambda kb: -len(kb[1]))[:4]
    for (dish, size), by in common:
        prices = [(r.name, _avg(by[r.res_id])) for r in them if r.res_id in by]
        c = min(prices, key=lambda x: x[1])
        e = max(prices, key=lambda x: x[1])
        out.append(f"{dish}{'' if size == 'regular' else f' ({size})'}: cheapest at {c[0]} (₹{c[1]:,.0f}), dearest at {e[0]} (₹{e[1]:,.0f}).")
    return out


def add_dashboard(wb, platform_name, outlet_name, spot, read_at, rows, ins, kinds):
    ws = wb.create_sheet("Dashboard", 0)
    wb.active = 0
    ws.sheet_view.showGridLines = False
    n = len(rows)
    last = get_column_letter(1 + n)
    ws.column_dimensions["A"].width = 30
    for c in range(2, 2 + n):
        ws.column_dimensions[get_column_letter(c)].width = 22

    # header
    ws.merge_cells(f"A1:{last}1")
    ws["A1"] = f"{platform_name} competition · {outlet_name}" if any(is_us for _, _, is_us in rows) else f"{platform_name} competitor comparison · near {outlet_name}"
    ws["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws["A1"].alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 34
    ws.merge_cells(f"A2:{last}2")
    has_us = any(is_us for _, _, is_us in rows)
    others = n - 1 if has_us else n
    ws["A2"] = f"As customers see it around {spot} · menus read {read_at} · {others} {'competitor' if has_us else 'restaurant'}{'s' if others != 1 else ''}" + ("" if has_us else " compared with each other")
    ws["A2"].font = Font(color="64748B")
    ws["A2"].alignment = Alignment(indent=1)

    # scorecard
    top = 4
    ws.cell(top, 1, "Scorecard").font = Font(size=13, bold=True)
    head = top + 1
    ws.cell(head, 1, "Measure")
    for j, (label, r, is_us) in enumerate(rows, 2):
        c = ws.cell(head, j, label)
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    for c in ws[head][: 1 + n]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=BLUE)
    ws.row_dimensions[head].height = 32
    rank_rows = []
    for k, (name, get, better, fmt) in enumerate(MEASURES):
        row = head + 1 + k
        ws.cell(row, 1, name).font = Font(bold=True)
        vals = [get(r, ins[r.res_id]) for _, r, _ in rows]
        for j, v in enumerate(vals, 2):
            c = ws.cell(row, j, v)
            c.number_format = fmt
            c.alignment = Alignment(horizontal="center")
        nums = [v for v in vals if isinstance(v, (int, float))]
        if better and len(set(nums)) > 1:
            hi, lo = max(nums), min(nums)
            good, bad = (hi, lo) if better == "high" else (lo, hi)
            for j, v in enumerate(vals, 2):
                if v == good:
                    ws.cell(row, j).fill = PatternFill("solid", fgColor=GREEN)
                elif v == bad:
                    ws.cell(row, j).fill = PatternFill("solid", fgColor=RED)
            us_val = next((v for v, (_, _, is_us) in zip(vals, rows) if is_us), None)
            if isinstance(us_val, (int, float)):
                order = sorted(nums, reverse=better == "high")
                rank_rows.append((name, order.index(us_val) + 1, len(nums)))
        for j in range(1, 2 + n):
            ws.cell(row, j).border = Border(bottom=THIN)
    for j, (_, _, is_us) in enumerate(rows, 2):
        if is_us:
            ws.cell(head, j).fill = PatternFill("solid", fgColor=NAVY)
    end = head + len(MEASURES)
    ws.cell(end + 1, 1, "Green = best of the group, red = worst, on measures where higher or lower is clearly better.").font = Font(italic=True, color="64748B", size=9)

    # where you rank
    row = end + 3
    if rank_rows:
        ws.cell(row, 1, "Where you rank").font = Font(size=13, bold=True)
        row += 1
        for name, rank, of in rank_rows:
            ws.cell(row, 1, name)
            c = ws.cell(row, 2, f"#{rank} of {of}")
            c.font = Font(bold=True, color="12A150" if rank == 1 else "E5484D" if rank == of else "0F172A")
            row += 1
        row += 1

    # key insights
    ws.cell(row, 1, "Key insights").font = Font(size=13, bold=True)
    row += 1
    for text in insights(rows, ins, kinds):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=1 + n)
        c = ws.cell(row, 1, f"•  {text}")
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.fill = PatternFill("solid", fgColor=GREY)
        ws.row_dimensions[row].height = 30 if len(text) < 110 else 45
        row += 1

    # charts: drawn from a plain column-wise block (one restaurant per row), the layout every spreadsheet app reads
    row += 1
    ws.cell(row, 1, "Chart data").font = Font(bold=True, color="64748B")
    data_head = row + 1
    for j, h in enumerate(["Restaurant", "Rating", "Average item price (₹)", "Menu items"], 1):
        ws.cell(data_head, j, h).font = Font(bold=True)
    for k, (label, r, _) in enumerate(rows, 1):
        i = ins[r.res_id]
        for j, v in enumerate([label, r.rating, i.get("avg_price"), i.get("items")], 1):
            ws.cell(data_head + k, j, v)
    data_end = data_head + n
    chart_row = data_end + 2
    for col, title, anchor in ((2, "Rating", "A"), (3, "Average item price (₹)", "E"), (4, "Menu items", "I")):
        ch = BarChart()
        ch.type, ch.title = "col", title
        ch.legend = None
        ch.height, ch.width = 7.5, 11
        ch.add_data(Reference(ws, min_col=col, min_row=data_head, max_row=data_end), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=data_head + 1, max_row=data_end))
        ws.add_chart(ch, f"{anchor}{chart_row}")
    row = chart_row + 17

    # dish types both sides sell, average price per restaurant
    us_id = next((r.res_id for _, r, is_us in rows if is_us), None)
    shared = [k for k, by in kinds.items() if (us_id in by if us_id else True) and len(by) >= 2]
    shared = sorted(shared, key=lambda k: -len(kinds[k]))[:10]
    if shared:
        ws.cell(row, 1, "Average price on dishes you both sell (₹)" if us_id else "Average price on dishes they have in common (₹)").font = Font(size=13, bold=True)
        row += 1
        h = row
        ws.cell(h, 1, "Dish type")
        for j, (label, _, _) in enumerate(rows, 2):
            ws.cell(h, j, label).alignment = Alignment(wrap_text=True, horizontal="center")
        for c in ws[h][: 1 + n]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=BLUE)
        ws.row_dimensions[h].height = 32
        for k, (dish, size) in enumerate(shared, 1):
            ws.cell(h + k, 1, dish if size == "regular" else f"{dish} ({size})")
            for j, (_, r, _) in enumerate(rows, 2):
                ps = kinds[(dish, size)].get(r.res_id)
                c = ws.cell(h + k, j, round(sum(ps) / len(ps)) if ps else None)
                c.number_format = "#,##0"
                c.alignment = Alignment(horizontal="center")
        ch = BarChart()
        # vertical columns: Apple Numbers crashes opening horizontal bar charts written this way
        ch.type, ch.title = "col", "Average price per dish type (₹)"
        ch.height, ch.width = 9, 6 + len(shared) * 2.2
        ch.add_data(Reference(ws, min_col=2, max_col=1 + n, min_row=h, max_row=h + len(shared)), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=h + 1, max_row=h + len(shared)))
        ws.add_chart(ch, f"{get_column_letter(n + 3)}{h}")
    ws.freeze_panes = "A4"
    return ws
