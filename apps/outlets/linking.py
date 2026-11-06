"""Suggest which Zomato-only and Swiggy-only store rows are the same kitchen. Suggestions only: someone confirms each.

Platforms name the same place differently ("Kammanahalli/Kalyan Nagar" vs "Kalyan Nagar", "Bangalore" vs "Bengaluru"),
so areas are compared as word sets and by similarity, and cities through common aliases. Each row is used once:
the best-scoring pairs are taken first, and a pair whose runner-up scores almost as well is marked unsure."""

import re
from difflib import SequenceMatcher

NCR = {"delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram", "noida", "greater noida", "ghaziabad", "faridabad"}
CITY_ALIASES = {"bengaluru": "bangalore", "bombay": "mumbai", "navi mumbai": "mumbai", "thane": "mumbai", "secunderabad": "hyderabad",
                "madras": "chennai", "calcutta": "kolkata", "pimpri chinchwad": "pune"}
CITY_NOISE = r"\b(urban|rural|suburban|corporation|district|city|metropolitan|municipal)\b"
STOP = {"road", "rd", "nagar", "sector", "phase", "block", "the", "near", "main", "stage", "layout", "west", "east", "north", "south"}


def _city(c: str) -> str:
    c = re.sub(r"[^a-z ]", " ", (c or "").lower())
    c = re.sub(r"\s+", " ", re.sub(CITY_NOISE, " ", c)).strip()
    if c in NCR:
        return "ncr"
    return CITY_ALIASES.get(c, c)


def _words(a: str) -> set:
    return {w for w in re.findall(r"[a-z]+|\d+", (a or "").lower()) if w not in STOP and len(w) > 1}


def _near(w: str, others: set) -> bool:
    """Same word, or a spelling variant (hinjawadi / hinjewadi, mahadevapura / mahadevpura)."""
    return w in others or (len(w) >= 5 and any(len(o) >= 5 and SequenceMatcher(None, w, o).ratio() >= 0.85 for o in others))


def score(a: dict, b: dict) -> float:
    """0..1 that two rows (dicts with area, city) are the same place."""
    ca, cb = _city(a.get("city")), _city(b.get("city"))
    if ca and cb and ca != cb:
        return 0.0
    wa, wb = _words(a.get("area")), _words(b.get("area"))
    if not wa or not wb:
        return 0.0
    small, big = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    overlap = sum(_near(w, big) for w in small) / len(small)  # "kalyan" in both -> 1.0 even if one adds "kammanahalli"
    nums_a, nums_b = {w for w in wa if w.isdigit()}, {w for w in wb if w.isdigit()}
    if nums_a and nums_b and not nums_a & nums_b:  # Sector 14 vs Sector 41, 5th block vs 7th block: different places
        return 0.0
    text = SequenceMatcher(None, " ".join(sorted(wa)), " ".join(sorted(wb))).ratio()
    return round(0.65 * overlap + 0.35 * text, 3)


def suggest(zomato_only: list[dict], swiggy_only: list[dict], threshold: float = 0.6) -> list[dict]:
    """[{zomato, swiggy, score, sure}] one-to-one, best first."""
    pairs = sorted(((score(z, s), i, j) for i, z in enumerate(zomato_only) for j, s in enumerate(swiggy_only)), reverse=True)
    best_for = {}
    for sc, i, j in pairs:
        best_for.setdefault(("z", i), []).append(sc)
        best_for.setdefault(("s", j), []).append(sc)
    used_z, used_s, out = set(), set(), []
    for sc, i, j in pairs:
        if sc < threshold:
            break
        if i in used_z or j in used_s:
            continue
        used_z.add(i)
        used_s.add(j)
        rivals = [x for x in best_for[("z", i)][1:2] + best_for[("s", j)][1:2]]
        sure = sc >= 0.8 and all(r < sc - 0.15 for r in rivals)
        out.append({"zomato": zomato_only[i], "swiggy": swiggy_only[j], "score": sc, "sure": sure})
    return out
