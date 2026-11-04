"""What a menu item is, whatever the restaurant calls it: dish type, main protein and portion, from a dictionary of
common dishes. Lets 'Hyderabadi Chicken Dum Biryani' and 'Chicken Biryani Handi' be compared as the same dish
without any paid service. Checks the name first, then Zomato's search alias and the menu category; the description
only ever adds the protein."""

import re

# (dish type, words that mean it). Order matters: the first match wins, so specific dishes come before general ones
TYPES = [
    ("Butter Chicken", ["butter chicken", "murgh makhani", "chicken makhani"]),
    ("Tikka Masala", ["tikka masala"]),
    ("Dal Makhani", ["dal makhani", "daal makhani"]),
    ("Biryani", ["biryani", "biriyani", "dum pukht"]),
    ("Pulao", ["pulao", "pulav"]),
    ("Fried Rice", ["fried rice"]),
    ("Rice Bowl", ["rice bowl"]),
    ("Ramen", ["ramen"]),
    ("Noodles", ["noodle", "hakka", "chowmein", "chow mein", "lo mein", "pad thai", "udon", "soba"]),
    ("Manchurian", ["manchurian"]),
    ("Kung Pao", ["kung pao"]),
    ("Chilli Basil", ["chilli basil", "chili basil"]),
    ("Chilli", ["chilli", "chili"]),
    ("Sushi", ["sushi", "maki", "uramaki", "nigiri", "sashimi"]),
    ("Dim Sum", ["momo", "dumpling", "dim sum", "dimsum", "gyoza", "har gow", "siu mai", "wonton", "wanton"]),
    ("Bao", ["bao"]),
    ("Spring Roll", ["spring roll"]),
    ("Roll / Wrap", ["kathi", "kati roll", "wrap", "frankie", "roll"]),
    ("Burger", ["burger"]), ("Pizza", ["pizza"]), ("Pasta", ["pasta", "spaghetti", "penne", "fettuccine", "lasagna", "lasagne", "mac and cheese"]),
    ("Sandwich", ["sandwich", "panini", "sub "]), ("Shawarma", ["shawarma", "shwarma"]), ("Taco", ["taco"]),
    ("Nachos", ["nacho"]), ("Quesadilla", ["quesadilla"]),
    ("Kebab", ["kebab", "kabab", "seekh", "galouti", "shami", "reshmi"]),
    ("Tikka", ["tikka"]), ("Tandoori", ["tandoori"]),
    ("Curry", ["curry", "masala", "korma", "kadai", "kadhai", "do pyaza", "rogan josh", "saag", "makhani", "gravy", "bhuna", "vindaloo", "chettinad"]),
    ("Dal", ["dal", "daal"]),
    ("Thali / Meal", ["thali", "meals", "meal"]),
    ("Dosa", ["dosa"]), ("Idli", ["idli"]), ("Vada", ["vada", "wada"]), ("Uttapam", ["uttapam", "uthappam"]),
    ("Chaat", ["chaat", "pani puri", "golgappa", "bhel", "sev puri", "dahi puri"]), ("Pav Bhaji", ["pav bhaji"]),
    ("Naan", ["naan"]), ("Roti", ["roti", "chapati", "phulka"]), ("Paratha", ["paratha", "parotta"]), ("Kulcha", ["kulcha"]),
    ("Soup", ["soup"]), ("Salad", ["salad"]),
    ("Fries", ["fries", "wedges"]), ("Wings", ["wings"]), ("Nuggets", ["nugget", "popcorn chicken", "strips"]),
    ("Cheesecake", ["cheesecake"]), ("Brownie", ["brownie"]), ("Cake", ["cake", "pastry"]),
    ("Ice Cream", ["ice cream", "sundae", "kulfi", "gelato"]), ("Gulab Jamun", ["gulab jamun"]),
    ("Indian Sweet", ["rasmalai", "kheer", "halwa", "phirni", "rasgulla", "jalebi", "shahi tukda", "double ka meetha"]),
    ("Mousse", ["mousse"]), ("Waffle / Pancake", ["waffle", "pancake"]), ("Cookie", ["cookie"]), ("Donut", ["donut", "doughnut"]),
    ("Shake", ["shake", "frappe", "smoothie"]), ("Lassi", ["lassi"]), ("Mojito", ["mojito", "mocktail", "lemonade", "cooler"]),
    ("Coffee", ["coffee", "latte", "cappuccino", "americano", "espresso"]), ("Tea", ["tea", "chai"]),
    ("Soft Drink", ["coke", "pepsi", "sprite", "fanta", "thums up", "7up", "soda", "soft drink"]),
    ("Water", ["water"]), ("Juice", ["juice"]),
]
PROTEINS = [("Chicken", ["chicken", "murgh", "murg"]), ("Mutton", ["mutton", "lamb", "gosht", "goat"]), ("Prawn", ["prawn", "shrimp", "jhinga"]),
            ("Fish", ["fish", "basa", "salmon", "tuna", "pomfret", "surmai"]), ("Crab", ["crab"]), ("Pork", ["pork", "bacon", "ham"]),
            ("Beef", ["beef", "buff"]), ("Egg", ["egg", "anda"]), ("Paneer", ["paneer", "cottage cheese"]), ("Tofu", ["tofu"]),
            ("Mushroom", ["mushroom"])]
# dishes named without a protein: 'Cheesecake', not 'Veg Cheesecake'
NO_PROTEIN = {"Butter Chicken", "Tikka Masala", "Dal Makhani", "Dal", "Naan", "Roti", "Paratha", "Kulcha", "Soup", "Salad", "Fries",
              "Cheesecake", "Brownie", "Cake", "Ice Cream", "Gulab Jamun", "Indian Sweet", "Mousse", "Waffle / Pancake", "Cookie", "Donut",
              "Shake", "Lassi", "Mojito", "Coffee", "Tea", "Soft Drink", "Water", "Juice", "Thali / Meal", "Dosa", "Idli", "Vada", "Uttapam",
              "Chaat", "Pav Bhaji"}
LARGE = re.compile(r"family|party|bucket|handi|serves? ?[3-9]|for ?[3-9]|[3-9] ?pax|\bfull\b|platter|feast")
SMALL = re.compile(r"\bbowl\b|\bmini\b|\bhalf\b|\bsmall\b|\bsingle\b|for one|serves? ?1")
COMBO = re.compile(r"\bcombo\b|\bbox\b|\s\+\s|\bwith\b.*\b(drink|coke|dessert|jamun|starter)")


def _has(text: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(w.strip())}", text) for w in words)


def classify(item: dict) -> dict:
    """{type, protein, portion, label}: e.g. Biryani / Chicken / regular / 'Chicken Biryani'. type is '' when unknown."""
    name = item.get("name", "").lower()
    sources = [name, (item.get("alias") or "").lower(), (item.get("category") or "").lower()]
    dish = next((t for src in sources for t, words in TYPES if _has(src, words)), "")
    protein = next((p for p, words in PROTEINS if _has(name, words)), "") or \
        next((p for p, words in PROTEINS if _has((item.get("desc") or "").lower(), words)), "")
    if not protein and item.get("veg"):
        protein = "Veg"
    portion = "combo" if COMBO.search(name) else "large" if LARGE.search(name) else "small" if SMALL.search(name) else "regular"
    label = (dish if dish in NO_PROTEIN or not protein else f"{protein} {dish}") if dish else ""
    return {"type": dish, "protein": protein, "portion": portion, "label": label}


def _words(name: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9 ]", " ", name.lower()).split())


def _distinct(name: str, c: dict) -> set[str]:
    """The words of a name beyond its dish type, protein and size: what makes 'Tom Yum Soup' not just any soup."""
    words = {w for t, ws in TYPES if t == c["type"] for x in ws for w in x.split()} | \
        {w for p, ws in PROTEINS if p == c["protein"] for x in ws for w in x.split()}
    return _words(name) - words - FILLER


# words that describe how a dish is made or sold rather than which dish it is
FILLER = {"veg", "vegetable", "vegetables", "non", "with", "and", "the", "of", "in", "on", "a", "bowl", "box", "combo", "regular", "family",
          "hot", "cold", "crispy", "crunchy", "fresh", "classic", "special", "signature", "house", "chef", "chefs", "style", "tossed",
          "fried", "fry", "spicy", "sweet", "sour", "smoky", "grilled", "roasted", "steamed", "baked", "stir", "wok", "loaded",
          "boneless", "dry", "gravy", "large", "small", "mini", "half", "full", "pcs", "pc", "piece", "pieces", "new", "our", "home",
          "homemade", "authentic", "original", "premium", "royal", "desi"}


def match(item: dict, menu: list[dict]) -> tuple[dict | None, str]:
    """The competitor dish to compare ours with, and how it was matched:
    'same dish'  same type, protein and size, and they share what's distinctive in the name (Kung Pao Chicken)
    'same kind'  same type, protein and size only (Tom Yum Soup against Hot & Sour Soup)
    '... other size'  the same, but one is a bowl or family pack and the other isn't: prices aren't comparable
    None when their menu has nothing of the kind."""
    me = classify(item)
    if not me["type"]:
        return None, ""
    same, other_size = [], []
    for o in menu:
        if bool(o.get("veg")) != bool(item.get("veg")):
            continue
        c = classify(o)
        if c["type"] != me["type"] or c["protein"] != me["protein"]:
            continue
        (same if c["portion"] == me["portion"] else other_size).append(o)
    pool = same or other_size
    if not pool:
        return None, ""
    mine = _distinct(item["name"], me)
    best = max(pool, key=lambda o: (len(mine & _distinct(o["name"], classify(o))), -abs((o.get("price") or 0) - (item.get("price") or 0))))
    basis = "same dish" if mine & _distinct(best["name"], classify(best)) else "same kind"
    return best, basis if same else f"{basis}, other size"
