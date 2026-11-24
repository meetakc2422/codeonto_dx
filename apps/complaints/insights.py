"""What the complaints are about, read from their text: which dishes come up most and what exactly went wrong.

The platforms word the same thing differently, so the dish is pulled out of a few shapes:
    "1 x Chinese Wok Fried Rice"                       Zomato / Swiggy missing and wrong items
    "Burnt food | Pad Thai (Pad Thai) with Addons: X"   Swiggy quality: reason, then the dish
    "Addons: Garlic Bread in 1 x Avocado Toast"         an add-on that was wrong: the dish is the part after "in"
    "1 x Burger, 1 x With Lettuce, 1 x 2 Pcs"           add-ons listed as items: only the real dishes count
"""
import re
from collections import Counter, defaultdict

_SPLIT = re.compile(r",\s*(?=\d+\s*x\s)")
_QTY = re.compile(r"^\s*\d+\s*x\s*", re.I)
_NOISE = re.compile(r"^(with|without|add|extra|no)\b|^\d+\s*(pcs?|pieces?)\b|^(regular|large|medium|small|half|full)$", re.I)
_REPEAT = re.compile(r"(\d+)\s+orders?", re.I)


def dishes_of(items: str) -> list[str]:
    """The dish names in a complaint's item text ([] when there is none)."""
    text = (items or "").strip()
    if not text:
        return []
    if " | " in text:  # "Burnt food | Pad Thai": what follows the bar is the dish
        text = text.split(" | ", 1)[1]
    out = []
    for part in _SPLIT.split(text):
        part = part.strip()
        if " in " in part and part.lower().startswith("addons"):
            part = part.rsplit(" in ", 1)[1]
        part = _QTY.sub("", part)
        part = re.sub(r"\s+with (other side-dish\(es\)|addons?:.*)$", "", part, flags=re.I)
        part = re.sub(r"\s*\(([^()]*)\)\s*$", lambda m: "" if m.group(1).strip().lower() in part.lower().replace(m.group(0).lower(), "") else m.group(0), part)
        part = part.strip(" ,")
        if part and not _NOISE.match(part) and len(part) > 2:
            out.append(part)
    return out


def reason_of(items: str, issue_detail: str) -> str:
    """What exactly went wrong: Swiggy's own words before the bar ("Burnt food"), else the platform's reason."""
    text = (items or "").strip()
    if " | " in text:
        return text.split(" | ", 1)[0].strip().capitalize()
    return (issue_detail or "").split(" · ")[0].strip()


def repeat_customer(context: str) -> bool | None:
    """True for a customer with more than one order, False for a first order, None when the text doesn't say."""
    m = _REPEAT.search(context or "")
    return None if not m else int(m.group(1)) > 1


def build(rows) -> dict:
    """rows: (items, issue_type, issue_detail, customer_context, refund_amount, outlet_id) for the complaints in view.
    Besides the top dishes and reasons it returns `links`: how often each dish, issue, outlet and reason occur together, so the
    page can light up everything connected to whatever is clicked."""
    rows = list(rows)
    names, count, issues, refunds = {}, Counter(), defaultdict(Counter), defaultdict(float)
    reasons, repeat, first = Counter(), 0, 0
    for items, issue_type, detail, context, refund, _outlet in rows:
        for d in set(dishes_of(items)):
            key = d.lower()
            names.setdefault(key, Counter())[d] += 1
            count[key] += 1
            issues[key][issue_type or "other"] += 1
            refunds[key] += float(refund or 0)
        r = reason_of(items, detail)
        if r:
            reasons[r] += 1
        who = repeat_customer(context)
        repeat += who is True
        first += who is False
    top = [{"dish": names[k].most_common(1)[0][0], "count": n, "refunds": refunds[k],
            "issues": [{"issue_type": t, "count": c} for t, c in issues[k].most_common(3)]} for k, n in count.most_common(8)]
    top_keys = {k for k, _ in count.most_common(8)}
    top_reasons = {r for r, _ in reasons.most_common(8)}
    links = Counter()
    for items, issue_type, detail, _context, _refund, outlet in rows:
        shown = [names[d.lower()].most_common(1)[0][0] for d in set(dishes_of(items)) if d.lower() in top_keys] or [""]
        r = reason_of(items, detail)
        for dish in shown:
            links[(dish, issue_type or "other", outlet, r if r in top_reasons else "")] += 1
    return {"by_item": top, "by_reason": [{"reason": r, "count": n} for r, n in reasons.most_common(8)],
            "repeat": {"repeat": repeat, "first": first},
            "links": [{"dish": d, "issue": i, "outlet": o, "reason": r, "n": n} for (d, i, o, r), n in links.most_common(800)]}
