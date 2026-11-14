"""What a review is about, from its words. A review can be in several topics; one with none is "other".
Patterns are lower-case regular expressions that work both in Python and in a database regex match (no \\b or \\w), and
each only matches at the start of a word. Add a word here and the buckets, counts and filter all follow."""
import re

from django.db.models import Q

TOPICS = [
    ("food_safety", "Food safety", r"stomach|food poison|vomit|puk(e|ing)|diarrh|hospital|infection|insect|cockroach|hair|worm|fungus|mould|mold|gagg|nause|sick|illness|allerg"),
    ("cold", "Cold food", r"cold|not hot|wasn.?t hot|not warm|lukewarm|didn.?t heat|not heated|refrigerat|not served hot"),
    ("freshness", "Freshness", r"stale|rotten|spoil|not fresh|wasn.?t fresh|old (food|chicken|oil|fries|burger|patty|bread|meat)|(tast|look|seem|smell|feel)[a-z]* (like )?old|smell|stink|reheat|left.?over|expired|frozen|gandi"),
    ("taste", "Taste", r"tast|bland|flavo|salty|salt|spic|season|bitter|sour|chemical|masala|sweet"),
    ("quality", "Overall quality", r"quality|standard|expectation|disappoint|degrad|dropped|deteriorat|not (the )?same|not like (before|earlier|previous)|used to be|worse|downhill|letdown|let down"),
    ("cooking", "Cooking and texture", r"undercook|uncook|half.?(fried|cooked|baked)|raw|burn|over.?(fried|cook)|dry|greas|oil|soggy|chewy|hard|stiff|gristl|tough|rubber|not (baked|cooked)|double fried|dripping"),
    ("items", "Wrong or missing items", r"wrong|missing|missed|not (delivered|received|given|provided|sent|there|put)|didn.?t (give|provide|send|get|receive|add|put)|did not (give|provide|send|add)|no (sauce|ketchup|drink|coke|cutlery|spoon|fork|napkin|mayo|dip|tissue|cheese)|instead of|instead|received (chicken|a |some|fried)|ordered.*(but|and|n) (got|received)|different|add.?on|forgot|only (bun|the)|removed the"),
    ("quantity", "Quantity", r"quantity|quatity|portion|small|tiny|less (chicken|patty|filling|sauce|cheese|quantity)|very less|too less|not enough|barely|skimp|little (chicken|patty|filling)|half (a |of )?(patty|burger)|shrunk"),
    ("price", "Price and value", r"pric|expensive|costly|overpriced|worth|waste of money|money|rupee|rupay|rs\.? ?[0-9]|₹|value|paise|paisa|cost"),
    ("packaging", "Packaging", r"packag|packing|box|container|spill|leak|seal|tamper|wrapper|butter paper|plastic|branding|crushed|squash|messy"),
    ("service", "Delivery and service", r"delay|late|slow|waiting|took (too )?long|hours|rider|delivery (boy|guy|man|partner|executive)|not on time|support|refund|respond|response|rude|behav|staff|customer (care|service)|executive|helpful|helping|complain|attitude|ignore|chatbot"),
]
TOPIC_LABELS = {slug: label for slug, label, _ in TOPICS}
_PATTERNS = {slug: r"(^|[^a-z])(" + pat.replace(r"\b", "") + ")" for slug, _, pat in TOPICS}
_COMPILED = {slug: re.compile(p, re.I) for slug, p in _PATTERNS.items()}


def topics_of(text: str) -> list[str]:
    """The topics a review's words touch: [] when none do (the "other" bucket)."""
    text = text or ""
    return [slug for slug, rx in _COMPILED.items() if rx.search(text)]


def topic_q(slug: str) -> Q:
    """A queryset filter for one topic ("other" = none of them)."""
    if slug == "other":
        q = Q()
        for p in _PATTERNS.values():
            q |= Q(body__iregex=p)
        return ~q & ~Q(body="")
    if slug not in _PATTERNS:
        return Q(pk__in=[])
    return Q(body__iregex=_PATTERNS[slug])
