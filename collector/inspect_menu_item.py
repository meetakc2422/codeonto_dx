"""Show what Zomato's menu editor returns for one item at one store, to see why it counts as out of stock.

    .venv\\Scripts\\python inspect_menu_item.py <res_id> "Nashville Style Chicken Burger" [login]

Prints the item's catalogue entry as Zomato sends it (only that item, nothing else from the menu), and says whether the
stock-out rule treats it as out. Read only: nothing is saved."""

import json
import sys

import requests

from core import config as cfg, db
from core.common import setup_logging
from zomato import stockouts
from zomato.outlets import _cookies


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    res_id, wanted = sys.argv[1], (sys.argv[2].strip().lower() if len(sys.argv) > 2 else "")
    label = sys.argv[3] if len(sys.argv) > 3 else "main"
    setup_logging()
    with db.transaction() as cur:
        acc = db.get_account(cur, "zomato", label)
    cookies = _cookies(db.load_credentials(acc))
    headers = {"Accept": "application/json, text/plain, */*", "Content-Type": "application/json", "User-Agent": cfg.user_agent(),
               "Referer": stockouts.ZOMATO_SITE + "/partners/onlineordering/menu/editor", "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())}
    resp = requests.get(stockouts.MENU_URL, params={"action": "get_content_menu", "res_id": res_id, "service_role": cfg.text("ZOMATO_SERVICE_ROLE", "DELIVERY_TAKEAWAY")},
                        headers=headers, timeout=30)
    resp.raise_for_status()
    menu = (resp.json().get("data") or {}).get("menuResponse") or {}
    if not wanted:  # every item the rule counts as out, with the reason
        rows, reasons = [], {"switched off (has a turn-on time)": 0, "every variant out": 0}
        for w in menu.get("catalogueWrappers") or []:
            cat = w.get("catalogue") or {}
            vs = [(vw.get("variant") or {}) for vw in w.get("variantWrappers") or []]
            if "autoTurnOnTime" in cat:
                why = "switched off (has a turn-on time)"
            elif vs and all(v.get("inStock") is False for v in vs):
                why = "every variant out"
            else:
                continue
            reasons[why] += 1
            rows.append(f"  {why:36} | {(cat.get('name') or '')[:46]:46} | turn-on: {cat.get('autoTurnOnTime') or [v.get('turnOnTime') for v in vs][:1]}")
        print(f"store {res_id}: {len(menu.get('catalogueWrappers') or [])} items on the menu, {len(rows)} counted as out")
        print("\n".join(rows[:60]))
        print(reasons)
        return
    found = [w for w in menu.get("catalogueWrappers") or [] if ((w.get("catalogue") or {}).get("name") or "").strip().lower() == wanted]
    print(f"{len(found)} listing(s) named '{sys.argv[2]}' at store {res_id}")
    for i, w in enumerate(found, 1):
        print(f"\n--- listing {i} ---")
        print(json.dumps(w, indent=1, ensure_ascii=False)[:6000])
    out = [x["item_name"].lower() for x in stockouts.out_items(menu)]
    print("\nThe stock-out rule says this item is:", "OUT of stock" if wanted in out else "in stock")
    print("Items the rule counts as out at this store:", len(out))


if __name__ == "__main__":
    main()
