"""The first sheet of a competition workbook: a one-page report a restaurant partner can read at a glance.
A header, a scorecard coloured best-to-worst on every measure, where the outlet ranks, plain-language key insights,
and charts. Built from the same data as the detailed sheets that follow it."""

import math
import statistics

from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

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


def _short(label: str, limit: int = 24) -> str:
    """A name that fits under a bar: the first words, cut at the limit."""
    label = (label or "").strip()
    return label if len(label) <= limit else label[: limit - 1].rstrip(" ,-–") + "…"


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
    # offers (only when the menu read showed any: otherwise zero would read as "nobody has offers")
    their_offers = _avg([len(r.offers or []) for r in them]) or 0
    mine_offers = len(us.offers or [])
    if "Offers running" in not_seen(rows, ins):
        pass
    elif mine_offers < their_offers:
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

# measures that are only meaningful when the menu read actually showed them: all zeros means "not captured", not "nobody has any"
SEEN_ONLY = {"Offers running", "Bestseller-tagged items"}


def not_seen(rows, ins) -> set:
    """Names of measures that read zero for every restaurant: the app's menu page did not show them, so they are not compared."""
    out = set()
    if not any(len(r.offers or []) for _, r, _ in rows):
        out.add("Offers running")
    if not any(len(ins[r.res_id].get("bestsellers") or []) for _, r, _ in rows):
        out.add("Bestseller-tagged items")
    return out


def print_ready(ws, title_rows: str | None = None, landscape: bool = True) -> None:
    """The same print and reading setup on every sheet: fits one page wide, repeats the header row, page numbers in the footer."""
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.6
    if title_rows:
        ws.print_title_rows = title_rows
    ws.oddFooter.left.text = "SocialSpork competition report"
    ws.oddFooter.right.text = "Page &P of &N"


def _pct_gap(mine, other):
    return (mine - other) / other * 100 if other else None


def findings(rows, ins, kinds) -> list[dict]:
    """The few things that matter most, most important first: {priority, title, evidence, action}. Only built from what the menu read actually showed."""
    us = next((r for _, r, is_us in rows if is_us), None)
    them = [r for _, r, is_us in rows if not is_us]
    if not us or not them:
        return []
    ui, seen_missing = ins[us.res_id], not_seen(rows, ins)
    out = []

    def add(score, title, evidence, action):
        out.append({"score": score, "title": title, "evidence": evidence, "action": action})

    rated = [r for r in them if r.rating is not None]
    if us.rating is not None and rated:
        best = max(rated, key=lambda r: r.rating)
        med = statistics.median(r.rating for r in rated)
        if best.rating - us.rating >= 0.2:
            add((best.rating - us.rating) * 65, "Your rating trails the best in the group",
                f"{us.rating:.1f}★ against {best.rating:.1f}★ at {best.name}; the median of the others is {med:.1f}★.",
                "Read your recent low-rated reviews for the common cause and fix that first, then ask satisfied customers to rate.")
    mine_votes, theirs = _count(us.votes), [v for v in (_count(r.votes) for r in them) if v]
    if mine_votes is not None and theirs:
        med = statistics.median(theirs)
        if med and mine_votes < 0.25 * med:
            add(min(60, 100 * (1 - mine_votes / med) * 0.5), "Far fewer ratings than the others",
                f"{us.votes} ratings against a median of {med:,.0f} for the others (the app rounds these counts).",
                "A small base moves easily in either direction. Ask every happy customer for a rating, for example with a card in the bag or a message after delivery.")
    their_avg = _avg([ins[r.res_id].get("avg_price") for r in them])
    if ui.get("avg_price") and their_avg:
        gap = _pct_gap(ui["avg_price"], their_avg)
        if abs(gap) >= 15:
            above = gap > 0
            add(abs(gap), f"Your menu is priced {abs(gap):.0f}% {'above' if above else 'below'} the others",
                f"Average item price ₹{ui['avg_price']:,} against ₹{their_avg:,.0f} for the others. This is the average of listed menu prices, not of what customers pay.",
                "If the premium is intended, make the reasons visible (photos, descriptions, portions). Otherwise check the dishes priced above others." if above
                else "Check whether you are leaving margin on the table: compare the dishes priced below others on the 'Dish prices' sheet.")
    gaps = []
    for (dish, size), by in kinds.items():
        mine = by.get(us.res_id)
        others = [p for rid, ps in by.items() if rid != us.res_id for p in ps]
        if mine and others and _avg(others):
            gaps.append((_pct_gap(_avg(mine), _avg(others)), dish, size, _avg(mine), _avg(others)))
    dear = sorted([g for g in gaps if g[0] >= 25], reverse=True)[:3]
    if dear:
        add(min(45, sum(g[0] for g in dear) / len(dear) * 0.5), "Some dishes cost much more than the same dish elsewhere",
            "; ".join(f"{d}{'' if sz == 'regular' else f' ({sz})'} ₹{a:,.0f} vs ₹{b:,.0f}" for _, d, sz, a, b in dear) + ".",
            "Check each is a deliberate premium (size, ingredients). If not, test a lower price.")
    missing = {}
    for (dish, size), by in kinds.items():
        if us.res_id not in by:
            n = sum(1 for rid in by if rid != us.res_id)
            if n >= max(1, min(2, len(them))):
                missing[dish] = max(missing.get(dish, 0), n)
    if missing:
        top = sorted(missing.items(), key=lambda kv: -kv[1])[:4]
        add(min(40, 8 * len(missing)), "Dishes that most others sell and you don't",
            ", ".join(f"{d} ({n} of {len(them)})" for d, n in top) + ".",
            "Consider testing one or two, if they fit your kitchen and cuisine.")
    for key, what, bad in (("photo_pct", "photo", "no_photo"), ("desc_pct", "description", "no_desc")):
        mine, others = ui.get(key), _avg([ins[r.res_id].get(key) for r in them])
        if mine is not None and others is not None and mine + 5 < others:
            n = len(ui.get(bad) or [])
            add((others - mine) * 0.8, f"Menu content: fewer items with a {what} than the others",
                f"{mine}% of your items have a {what} against {others:.0f}% for the others: {n} items to fix.",
                f"Add a {what} to the {n} items listed on the 'Menu gaps' sheet, starting with your best sellers.")
    if "Offers running" not in seen_missing:
        mine_o, their_o = len(us.offers or []), _avg([len(r.offers or []) for r in them]) or 0
        if mine_o < their_o:
            lead = max(them, key=lambda r: len(r.offers or []))
            add((their_o - mine_o) * 10, "You run fewer offers than the others",
                f"{mine_o} offers against {their_o:.1f} on average. {lead.name} runs {len(lead.offers or [])}, for example \"{(lead.offers or [{}])[0].get('text', '')}\".",
                "Decide whether a matching offer is worth the margin on your busiest dishes.")
    oos, their_oos = len(ui.get("out_of_stock") or []), _avg([len(ins[r.res_id].get("out_of_stock") or []) for r in them]) or 0
    if oos > their_oos and oos >= 2:
        add((oos - their_oos) * 6, "More of your items are out of stock than the others'",
            f"{oos} of your items are out of stock right now against {their_oos:.0f} on average for the others.", "Switch the items back on, or take them off the menu.")
    out.sort(key=lambda f: -f["score"])
    for k, f in enumerate(out[:6]):
        f["priority"] = "High" if k < 2 else "Medium" if k < 4 else "Low"
    if not out:
        return [{"priority": "—", "title": "No large gap against the group", "evidence": "On the measures read, you are within the range of the others.",
                 "action": "Keep an eye on the rating and the prices when you read the next report.", "score": 0}]
    return out[:6]


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
    has_us = any(is_us for _, _, is_us in rows)
    hidden = not_seen(rows, ins)  # measures the menu read did not show for anyone: marked "not seen", never compared
    if has_us:
        ws.column_dimensions[get_column_letter(2 + n)].width = 15
        ws.column_dimensions[get_column_letter(3 + n)].width = 16
    cols = 3 + n if has_us else 1 + n  # the table's last column: the scorecard has a peer median and a difference after the restaurants
    last = get_column_letter(cols)

    # header
    ws.merge_cells(f"A1:{last}1")
    ws["A1"] = f"{platform_name} competition · {outlet_name}" if any(is_us for _, _, is_us in rows) else f"{platform_name} competitor comparison · near {outlet_name}"
    ws["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws["A1"].alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 34
    ws.merge_cells(f"A2:{last}2")
    others = n - 1 if has_us else n
    ws["A2"] = f"As customers see it around {spot} · menus read {read_at} · {others} {'competitor' if has_us else 'restaurant'}{'s' if others != 1 else ''}" + ("" if has_us else " compared with each other")
    ws["A2"].font = Font(color="64748B")
    ws["A2"].alignment = Alignment(indent=1)

    # executive summary: the few things that matter most, in order, each with its evidence and what to do about it
    top = 4
    fs = findings(rows, ins, kinds)
    if fs:
        ws.cell(top, 1, "Executive summary").font = Font(size=13, bold=True)
        top += 1
        tone = {"High": RED, "Medium": AMBER, "Low": GREY}
        for k, f in enumerate(fs, 1):
            a = ws.cell(top, 1, f"{k}  ·  {f['priority']} priority" if f["priority"] != "—" else "Overall")
            a.font = Font(bold=True)
            a.fill = PatternFill("solid", fgColor=tone.get(f["priority"], GREY))
            a.alignment = Alignment(vertical="top", wrap_text=True)
            ws.merge_cells(start_row=top, start_column=2, end_row=top, end_column=cols)
            text = f"{f['title']}. {f['evidence']}  →  {f['action']}"
            b = ws.cell(top, 2, text)
            b.alignment = Alignment(wrap_text=True, vertical="top")
            b.border = Border(bottom=THIN)
            ws.row_dimensions[top].height = 16 * max(2, math.ceil(len(text) / max(30, (cols - 1) * 20))) + 4
            top += 1
        top += 1

    # scorecard
    ws.cell(top, 1, "Scorecard").font = Font(size=13, bold=True)
    head = top + 1
    ws.cell(head, 1, "Measure")
    for j, (label, r, is_us) in enumerate(rows, 2):
        c = ws.cell(head, j, label)
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    if has_us:
        ws.cell(head, 2 + n, "Peer median").alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.cell(head, 3 + n, "You vs median").alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    for c in ws[head][:cols]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=BLUE)
    ws.row_dimensions[head].height = 32
    rank_rows = []
    for k, (name, get, better, fmt) in enumerate(MEASURES):
        row = head + 1 + k
        ws.cell(row, 1, name).font = Font(bold=True)
        if name in hidden:  # every restaurant reads zero: the menu read did not show this, so say so instead of comparing zeros
            for j in range(2, 2 + n):
                c = ws.cell(row, j, "not seen")
                c.font, c.alignment = Font(italic=True, color="94A3B8"), Alignment(horizontal="center")
            for j in range(1, cols + 1):
                ws.cell(row, j).border = Border(bottom=THIN)
            continue
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
        if has_us:  # the middle of the others, and how far you are from it
            others_v = [v for v, (_, _, is_us) in zip(vals, rows) if not is_us and isinstance(v, (int, float))]
            mine_v = next((v for v, (_, _, is_us) in zip(vals, rows) if is_us), None)
            if others_v:
                med = statistics.median(others_v)
                c = ws.cell(row, 2 + n, med)
                c.number_format, c.alignment = fmt, Alignment(horizontal="center")
                if isinstance(mine_v, (int, float)) and med:
                    d = ws.cell(row, 3 + n, (mine_v - med) / med)
                    d.number_format, d.alignment = "+0%;-0%;0%", Alignment(horizontal="center")
                    if better and mine_v != med:
                        d.font = Font(bold=True, color="12A150" if (mine_v > med) == (better == "high") else "E5484D")
        for j in range(1, cols + 1):
            ws.cell(row, j).border = Border(bottom=THIN)
    for j, (_, _, is_us) in enumerate(rows, 2):
        if is_us:
            ws.cell(head, j).fill = PatternFill("solid", fgColor=NAVY)
    end = head + len(MEASURES)
    note = "Green = best of the group, red = worst, on measures where higher or lower is clearly better. Peer median = the middle value of the other restaurants."
    if hidden:
        note += f" Not seen in the menu read, so not compared: {', '.join(sorted(hidden))} (a dash is not a zero)."
    ws.cell(end + 1, 1, note).font = Font(italic=True, color="64748B", size=9)

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

    row += 1

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
    ws.freeze_panes = "A3"
    print_ready(ws)
    return ws


def add_notes(wb, platform_name, outlet_name, spot, read_at, rows, ins):
    """'How to read this report': what it is, what each measure means, and what it can't tell you. Reports people act on carry this."""
    ws = wb.create_sheet("Notes", 1)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 100
    ws.merge_cells("A1:B1")
    ws["A1"] = "How to read this report"
    ws["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws["A1"].alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 34
    hidden = sorted(not_seen(rows, ins))
    has_us = any(is_us for _, _, is_us in rows)
    row = 3

    def block(title, items):
        nonlocal row
        ws.cell(row, 1, title).font = Font(size=13, bold=True)
        row += 1
        for k, v in items:
            a, b = ws.cell(row, 1, k), ws.cell(row, 2, v)
            a.font, a.alignment, b.alignment = Font(bold=True), Alignment(vertical="top", wrap_text=True), Alignment(vertical="top", wrap_text=True)
            a.border = b.border = Border(bottom=THIN)
            ws.row_dimensions[row].height = 16 * max(1, math.ceil(len(str(v)) / 105)) + 3
            row += 1
        row += 1

    block("About this report", [
        ("Platform", platform_name),
        ("Compared from", f"{outlet_name}{'' if not spot or str(spot) in outlet_name else f' ({spot})'}. Search results, distances and delivery depend on the address, so a report read from another address can differ."),
        ("Read at", f"{read_at}. Everything here is a snapshot of what the app showed at that moment."),
        ("Restaurants", f"{len(rows)} compared" + (" (you and the others)." if has_us else ".")),
    ])
    block("What each measure means", [
        ("Rating", "The restaurant's average rating shown on the app."),
        ("Ratings (votes)", "How many ratings that average rests on. The app rounds large counts (for example 27K+), so small differences are not visible."),
        ("Menu items / Categories", "How many dishes and menu sections the menu page lists."),
        ("Average item price (₹)", "The average of the listed menu prices. It describes the menu. It does not weigh dishes by how much they sell and it is not what customers pay."),
        ("Offers running", "Offers the menu page showed at the time of the read."),
        ("Bestseller-tagged items", "Dishes the app itself tags as a bestseller or most ordered."),
        ("Out of stock now %", "Share of menu items marked unavailable at the time of the read."),
        ("Items with a photo / description %", "Share of menu items that have a photo, or a description of at least a sentence."),
        ("Peer median / You vs median", "The middle value of the other restaurants, and how far you are from it (+10% means ten percent above)."),
    ])
    limits = [
        ("Not seen is not zero", "A cell that says 'not seen' means the menu read did not show that item for any restaurant, for example offers. It is left out of the comparison instead of being counted as zero."
         + (f" This report: {', '.join(hidden)}." if hidden else "")),
        ("No sales or order figures", "The app does not publish orders, sales or average order value for other restaurants, so none are shown or estimated here."),
        ("Ads and personalisation", "The app orders results differently for each customer and mixes in paid placements. This report therefore does not rank restaurants by their position in the app."),
        ("Prices", "Prices are the listed prices. Offers, delivery fees and taxes at checkout are not included."),
    ]
    block("What this report can't tell you", limits)
    print_ready(ws, landscape=False)
    return ws
