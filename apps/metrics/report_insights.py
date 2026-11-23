"""The written parts of the client report: a short plain-language overview of the period, and a handful of recommended next steps.

Both are worked out from the numbers already in the report (never invented), so they follow the dates, the outlets and whichever
sections were picked: a section that is left out contributes nothing to either. Pure functions of the report dict, easy to test.
"""

from datetime import date


def _inr(v) -> str:
    """₹ amounts the way the report prints them: 1,20,000 -> ₹1.20 L."""
    v = float(v or 0)
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1e7:
        return f"{sign}₹{a / 1e7:.2f} Cr"
    if a >= 1e5:
        return f"{sign}₹{a / 1e5:.2f} L"
    if a >= 1e3:
        return f"{sign}₹{a / 1e3:.1f}k"
    return f"{sign}₹{a:,.0f}"


def _day(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")


def _section(r: dict, key: str) -> dict | None:
    return next((s for s in r.get("sections", []) if s["key"] == key), None)


def _tot(r: dict, key: str, code: str):
    sec = _section(r, key)
    cell = ((sec or {}).get("total") or {}).get(code)
    return cell.get("value") if isinstance(cell, dict) else cell


def _chg(r: dict, key: str, code: str):
    cell = (((_section(r, key) or {}).get("total")) or {}).get(code)
    return cell.get("change") if isinstance(cell, dict) else None


def _head(r: dict, name: str) -> dict | None:
    return next((h for h in r.get("headline", []) if h["name"] == name), None)


def _plain(name: str) -> str:
    """A KPI's name in a sentence: lower case, but ROI, MFR and the like stay as they are."""
    return " ".join(w if w.isupper() and len(w) > 1 else w.lower() for w in name.split())


def _move(change) -> str:
    return "" if change is None else f"{'up' if change >= 0 else 'down'} {abs(change):.0f}%"


def overview(r: dict) -> list[str]:
    """Four to seven plain sentences on how the period went."""
    p = r["period"]
    out = []
    sales, orders, aov = _head(r, "Sales"), _head(r, "Orders"), _head(r, "Average order value")
    if sales and sales.get("value"):
        s = f"{r['brand']} sold {_inr(sales['value'])}"
        if orders and orders.get("value"):
            s += f" from {orders['value']:,.0f} orders"
        s += f" across {r['outlets']} outlet{'' if r['outlets'] == 1 else 's'} between {_day(p['start'])} and {_day(p['end'])}"
        if sales.get("change") is not None:
            s += f", {_move(sales['change'])} on the previous {p['days']} days"
        out.append(s + ".")
        if aov and aov.get("value"):
            out[-1] = out[-1][:-1] + f", at an average of {_inr(aov['value'])} an order."
    plats = [x for x in r.get("platforms", []) if x.get("sales")]
    if len(plats) > 1:
        out.append(f"{plats[0]['name']} brought {plats[0]['share']:.0f}% of the sales and {plats[1]['name']} {plats[1]['share']:.0f}%.")
    elif len(plats) == 1:
        out.append(f"All the sales came from {plats[0]['name']}.")
    sales_v = (sales or {}).get("value") or 0
    meaningful = [n for n in r.get("highlights", []) if not (
        (n.get("unit") == "percent" and abs(n.get("value") or 0) < 1)  # 0.1% to 0.2% is a 100% move that means nothing
        or (n.get("unit") == "currency" and sales_v and abs(n.get("value") or 0) < sales_v * 0.01))]  # nor is a loss of 0.3% of sales
    big = sorted(meaningful, key=lambda n: -abs(n["change"]))[:3]
    if big:
        out.append("The biggest changes: " + "; ".join(f"{_plain(n['name'])} {_move(n['change'])}" for n in big) + ".")
    rating = _tot(r, "reputation", "listing_rating") or (_head(r, "Rating") or {}).get("value")
    if rating:
        chg = _chg(r, "reputation", "listing_rating") if _tot(r, "reputation", "listing_rating") else (_head(r, "Rating") or {}).get("change")
        out.append(f"The platform rating is {rating:.1f} ★" + (f" ({_move(chg)})" if chg is not None and abs(chg) >= 0.5 else "") + ".")
    online = _tot(r, "overall", "online_pct")
    if online is not None:
        out.append(f"Stores were online {online:.0f}% of their opening hours.")
    comp = _section(r, "complaints")
    if comp and (comp.get("total") or {}).get("total"):
        t = comp["total"]
        issues = sorted(((c["name"], t.get(c["code"]) or 0) for c in comp["columns"] if c["code"] not in ("total", "per_100_orders")), key=lambda x: -x[1])
        top = f", mostly about {issues[0][0].lower()}" if issues and issues[0][1] else ""
        per = f" ({t['per_100_orders']:.1f} per 100 orders)" if t.get("per_100_orders") is not None else ""
        out.append(f"Customers raised {t['total']:,.0f} complaints{per}{top}.")
    pay = _section(r, "payouts")
    if pay and (pay.get("total") or {}).get("payout") and pay["total"].get("net_order_value"):
        t = pay["total"]
        out.append(f"The platforms paid out {_inr(t['payout'])}, {t['payout'] / t['net_order_value'] * 100:.0f}% of the {_inr(t['net_order_value'])} net order value, after fees and deductions.")
    cov = r.get("coverage") or {}
    if cov.get("gaps"):
        out.append(f"{len(cov['gaps'])} outlet{'' if len(cov['gaps']) == 1 else 's'} had days with no sales data, and the totals leave those days out.")
    return out


def recommendations(r: dict, limit: int = 5) -> list[dict]:
    """The few things most worth doing next, each with the number behind it: [{title, detail, level}], most important first."""
    recs = []

    def add(score, title, detail):
        recs.append({"score": score, "title": title, "detail": detail, "level": "High" if score >= 50 else "Medium" if score >= 35 else "Low"})

    sales = (_head(r, "Sales") or {}).get("value") or 0
    loss, canc = _tot(r, "overall", "cancellation_loss"), _tot(r, "overall", "cancellation_rate")
    if loss and sales and (loss / sales >= 0.01 or (canc or 0) >= 2):
        add(50 + loss / sales * 1000, "Cut cancellations",
            f"Cancelled orders cost about {_inr(loss)} ({loss / sales * 100:.1f}% of sales). Keep out-of-stock items off the menu and watch the kitchen's load at peak hours.")
    late, prep = _tot(r, "overall", "delayed_orders_pct"), _tot(r, "overall", "avg_prep_time")
    if late is not None and late >= 10:
        add(40 + late, "Speed up orders", f"{late:.0f}% of orders ran late" + (f" and kitchens took {prep / 60:.0f} minutes on average" if prep else "") + ". Add a hand at peak hours and look at the slowest outlets first.")
    online = _tot(r, "overall", "online_pct")
    if online is not None and online < 95:
        rows = [(q["name"].split(" · ")[-1], (q.get("online_pct") or {}).get("value")) for q in (_section(r, "overall") or {}).get("rows", [])]
        worst = [n for n, v in sorted((x for x in rows if x[1] is not None), key=lambda x: x[1])[:2]]
        add(45 + (100 - online), "Keep stores online", f"Stores were online only {online:.0f}% of opening hours, and every offline hour is lost orders." + (f" Worst: {', '.join(worst)}." if worst else ""))
    rating = _tot(r, "reputation", "listing_rating")
    if rating is not None:
        rchg = _chg(r, "reputation", "listing_rating")
        if rating < 4.0:
            add(55, "Lift the rating", f"The rating is {rating:.1f} ★. Reply to waiting reviews and fix the most common complaint first.")
        elif rchg is not None and rchg <= -2:
            add(45, "The rating is slipping", f"It fell {abs(rchg):.0f}% to {rating:.1f} ★. Look at this period's low-star reviews for what changed.")
    comp = _section(r, "complaints")
    if comp and (comp.get("total") or {}).get("per_100_orders") is not None and comp["total"]["per_100_orders"] >= 2:
        t = comp["total"]
        issues = sorted(((c["name"], t.get(c["code"]) or 0) for c in comp["columns"] if c["code"] not in ("total", "per_100_orders")), key=lambda x: -x[1])
        add(42 + t["per_100_orders"] * 3, "Fix the top complaint",
            f"There were {t['total']:,.0f} complaints ({t['per_100_orders']:.1f} per 100 orders)." + (f" The biggest cause is {issues[0][0].lower()} ({issues[0][1]:,.0f})." if issues and issues[0][1] else ""))
    roi, spend = _tot(r, "ads", "ad_roi"), _tot(r, "ads", "ad_spend")
    if roi and spend:
        if roi < 3:
            add(36, "Tighten ad spend", f"Ads returned {roi:.1f}x on {_inr(spend)} spent. Pause the weakest outlets and keep the best ones going.")
        elif roi >= 6 and sales and spend / sales < 0.1:
            add(32, "Put more behind ads", f"Ads returned {roi:.1f}x. Raising the budget at the best outlets should pay back.")
    given = _tot(r, "ads", "discount_given")
    if given and sales and given / sales >= 0.2:
        add(38, "Review discounts", f"Discounts came to {_inr(given)}, {given / sales * 100:.0f}% of sales. Try smaller offers on the best sellers and see whether orders hold.")
    conv = _tot(r, "growth", "menu_to_order_pct")
    if conv is not None and 0 < conv < 8:
        add(33, "Turn more menu visitors into orders", f"Only {conv:.1f}% of people who open the menu order. Better photos, short descriptions and a clear best-seller section help.")
    pay = _section(r, "payouts")
    if pay and (pay.get("total") or {}).get("net_order_value"):
        t = pay["total"]
        cost = abs(t.get("deductions") or 0)  # net deductions already include the platform fees
        if cost / t["net_order_value"] >= 0.3:
            add(30, "Watch deductions", f"Fees, taxes and other deductions took {cost / t['net_order_value'] * 100:.0f}% of net order value ({_inr(cost)}). Check the statements for charges that can be disputed.")
    rows = [(q["name"], (q.get("sales") or {}).get("value")) for q in (_section(r, "overall") or {}).get("rows", [])]
    rows = [x for x in rows if x[1]]
    if len(rows) >= 3:
        mean = sum(v for _, v in rows) / len(rows)
        name, low = min(rows, key=lambda x: x[1])
        if low < mean * 0.25:
            add(28, "Check the weakest outlet", f"{name.split(' · ')[-1]} sold {low / mean * 100:.0f}% of the average outlet. Look at its hours, photos and offers.")
    cov = r.get("coverage") or {}
    if cov.get("gaps"):
        add(20, "Fill the missing data", f"{len(cov['gaps'])} outlet{'' if len(cov['gaps']) == 1 else 's'} have days with no sales data, so totals leave them out. The last page of the report lists the days.")
    recs.sort(key=lambda x: -x["score"])
    if not recs:
        recs = [{"score": 0, "title": "Nothing urgent this period", "detail": "No number stands out as a problem. Keep an eye on the rating and on online time.", "level": "Low"}]
    return [{k: v for k, v in x.items() if k != "score"} for x in recs[:limit]]
