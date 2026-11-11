"""Count how many reviewers of a client shared their phone number with the restaurant (Zomato's opt-in).

Zomato lets a customer agree, after ordering, to share their number with the restaurant for offers. The merchant
dashboard reads it with order/customer-connect-info. This script asks that for each order behind the client's
Zomato reviews in a date range, using the client's own Zomato login, and prints COUNTS ONLY: no numbers are
printed, logged or saved. (Saving them for win-back campaigns comes later, encrypted and per client.)

    python review_contacts.py --client shoyu --from 2026-11-01
    python review_contacts.py --client shoyu --from 2026-11-01 --to 2026-11-09 --limit 20    # try a few first
    python review_contacts.py --client shoyu --from 2026-11-01 --show-shape                 # field names of one answer, values hidden
"""

import argparse
import json
import os
import random
import re
import sys
import time
from collections import Counter
from datetime import date, timedelta

from core import config as cfg, db
from core.common import log, setup_logging
from zomato.outlets import _cookies

URL = "https://api.zomato.com/merchant-gw/web/order/customer-connect-info"
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")  # a full Indian mobile number
MASKED = re.compile(r"[xX*•]{3,}")


def _strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)
    elif isinstance(o, (str, int)):
        yield str(o)


def _shape(o):
    """Same structure with every value replaced by its type, so nothing personal is shown."""
    if isinstance(o, dict):
        return {k: _shape(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_shape(o[0])] if o else []
    return type(o).__name__


def ask(cookies: dict, order_id: str):
    import requests

    headers = {"accept": "application/json, text/plain, */*", "content-type": "application/json",
               "origin": "https://www.zomato.com", "referer": "https://www.zomato.com/", "user-agent": cfg.user_agent(),
               "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
               "x-zomato-csrft": cookies.get("csrf", ""), "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""),
               "x-zomato-app-version": "2", "x-client-id": "zomato_web_merchant", "x-zomato-source-identifier": "merchant-dashboard",
               "x-zomato-trace-id": "web" + os.urandom(16).hex()}
    for wait in cfg.retry_waits():
        time.sleep(wait)
        r = requests.post(URL, headers=headers, json={"order_id": str(order_id)}, timeout=cfg.http_timeout())
        if r.status_code in (401, 403):
            raise PermissionError("Zomato session expired or this order isn't on the login")
        if r.status_code == 429 or r.status_code >= 500:
            continue
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {}
    return 429, {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True, help="client name (as on the dashboard)")
    ap.add_argument("--from", dest="start", required=True, metavar="YYYY-MM-DD")
    ap.add_argument("--to", dest="end", metavar="YYYY-MM-DD", help="default: today")
    ap.add_argument("--limit", type=int, help="ask for at most this many orders")
    ap.add_argument("--show-shape", action="store_true", help="print the field names of the first answer (values hidden)")
    args = ap.parse_args()
    setup_logging()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end) if args.end else date.today()

    with db.transaction() as cur:
        cur.execute("SELECT id, name FROM clients WHERE name ILIKE %s", (args.client,))
        clients = cur.fetchall()
        if len(clients) != 1:
            sys.exit(f"Client '{args.client}': found {len(clients)} matches {[c['name'] for c in clients]}")
        cur.execute("""SELECT DISTINCT r.raw->>'order_id' AS order_id, z.account_id
                       FROM reviews r JOIN brand_outlets bo ON bo.id = r.outlet_id JOIN brands b ON b.id = bo.brand_id
                       JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       WHERE b.client_id = %s AND r.platform = 'zomato' AND r.reviewed_at >= %s AND r.reviewed_at < %s
                         AND coalesce(r.raw->>'order_id', '') NOT IN ('', '0')""",
                    (clients[0]["id"], start, end + timedelta(days=1)))
        orders = cur.fetchall()
        cur.execute("SELECT id, label, credentials_ref, is_active, client_id, only_ids FROM platform_accounts WHERE id = ANY(%s)",
                    (list({o["account_id"] for o in orders}),))
        accounts = {a["id"]: a for a in cur.fetchall()}
    if args.limit:
        orders = orders[:args.limit]
    log.info("%s: %s Zomato reviews with an order id, %s to %s", clients[0]["name"], len(orders), start, end)
    if not orders:
        return

    cookies = {i: _cookies(db.load_credentials(a)) for i, a in accounts.items()}
    tally = Counter()
    for n, o in enumerate(orders, 1):
        try:
            status, body = ask(cookies[o["account_id"]], o["order_id"])
        except PermissionError as e:
            log.error("stopped: %s", e)
            break
        if args.show_shape and n == 1:
            print(json.dumps({"http": status, "shape": _shape(body)}, indent=1))
        texts = list(_strings(body))
        flag = str(((body.get("trackingParams") or {}).get("meta_data") or {}).get("contactNumberPresent", "")).strip().lower()
        if status != 200:
            tally[f"http {status}"] += 1
        elif flag in ("true", "1", "yes"):
            tally["shared"] += 1
            if any(PHONE.search(t) for t in texts if not MASKED.search(t)):
                tally["shared, number in answer"] += 1
            if args.show_shape and not tally["shown_shared"]:
                tally["shown_shared"] += 1
                sections = [s.get("type") for s in ((body.get("body") or {}).get("sections") or [])]
                print(json.dumps({"first shared answer, section types": sections, "shape": _shape(body)}, indent=1))
        elif flag in ("false", "0", "no"):
            tally["not shared"] += 1
        else:
            tally[f"flag '{flag or 'missing'}'"] += 1
        if n % 25 == 0:
            log.info("%s/%s asked: %s", n, len(orders), dict(tally))
        time.sleep(random.uniform(1.5, 3.0))  # gentle on the login
    tally.pop("shown_shared", None)
    log.info("done: %s orders asked -> %s", sum(v for k, v in tally.items() if k != "shared, number in answer"), dict(tally))


if __name__ == "__main__":
    main()
