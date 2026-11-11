"""Reviewers' shared phone numbers (Zomato's opt-in) for older reviews, and re-checks of saved ones.

The reviews job already asks for every NEW Zomato review. This fills in reviews from before that, and re-checks
saved numbers so a customer who withdrew their consent on Zomato drops off the dashboard. Numbers are never printed.

    python review_contacts.py --from 2026-11-01                       # every client, reviews since 1 Nov, saved
    python review_contacts.py --client shoyu --from 2026-11-01        # one client
    python review_contacts.py --client shoyu --from 2026-11-01 --count-only   # just count, save nothing
    python review_contacts.py --recheck                               # re-ask saved numbers checked over 7 days ago
"""

import argparse
import random
import sys
import time
from collections import Counter
from datetime import date, timedelta

from core import db
from core.common import log, setup_logging
from zomato import contacts
from zomato.outlets import _cookies

ACCOUNTS = "SELECT id, label, credentials_ref, is_active, client_id, only_ids FROM platform_accounts WHERE id = ANY(%s)"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", help="client name (as on the dashboard); default: every client")
    ap.add_argument("--from", dest="start", metavar="YYYY-MM-DD")
    ap.add_argument("--to", dest="end", metavar="YYYY-MM-DD", help="default: today")
    ap.add_argument("--limit", type=int, help="ask for at most this many reviews")
    ap.add_argument("--count-only", action="store_true", help="count who shared, save nothing")
    ap.add_argument("--recheck", action="store_true", help="re-ask saved numbers so withdrawn consent is removed")
    ap.add_argument("--recheck-days", type=int, default=7)
    args = ap.parse_args()
    setup_logging()
    if not args.recheck and not args.start:
        ap.error("pass --from YYYY-MM-DD (or --recheck)")

    where, params = ["r.platform = 'zomato'", "coalesce(r.raw->>'order_id', '') NOT IN ('', '0')"], []
    with db.transaction() as cur:
        if args.client:
            cur.execute("SELECT id, name FROM clients WHERE name ILIKE %s", (args.client,))
            found = cur.fetchall()
            if len(found) != 1:
                sys.exit(f"Client '{args.client}': found {len(found)} matches {[c['name'] for c in found]}")
            where.append("b.client_id = %s")
            params.append(found[0]["id"])
        if args.recheck:
            where.append("c.shared AND c.checked_at < now() - make_interval(days => %s)")
            params.append(args.recheck_days)
        else:
            start = date.fromisoformat(args.start)
            end = date.fromisoformat(args.end) if args.end else date.today()
            where += ["r.reviewed_at >= %s", "r.reviewed_at < %s"]
            params += [start, end + timedelta(days=1)]
            if not args.count_only:
                where.append("c.review_id IS NULL")  # asked before: skip
        cur.execute(f"""SELECT r.id, r.raw->>'order_id' AS order_id, z.account_id
                        FROM reviews r JOIN brand_outlets bo ON bo.id = r.outlet_id JOIN brands b ON b.id = bo.brand_id
                        JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                        LEFT JOIN review_contacts c ON c.review_id = r.id
                        WHERE {' AND '.join(where)} ORDER BY r.reviewed_at DESC""", params)
        todo = cur.fetchall()
        cur.execute(ACCOUNTS, (list({t["account_id"] for t in todo}),))
        accounts = {a["id"]: a for a in cur.fetchall()}
    if args.limit:
        todo = todo[:args.limit]
    log.info("%s Zomato reviews to ask%s", len(todo), " (re-check)" if args.recheck else "")

    cookies = {i: _cookies(db.load_credentials(a)) for i, a in accounts.items()}
    tally = Counter()
    for n, t in enumerate(todo, 1):
        try:
            shared, phone = contacts.lookup(cookies[t["account_id"]], t["order_id"])
        except PermissionError as e:
            log.error("stopped: %s", e)
            break
        except Exception as e:
            tally["failed"] += 1
            log.warning("review %s: %s", t["id"], type(e).__name__)
            continue
        tally["shared" if shared and phone else "not shared"] += 1
        if not args.count_only:
            with db.transaction() as cur:
                contacts.save(cur, t["id"], t["order_id"], shared, phone)
        if n % 25 == 0:
            log.info("%s/%s asked: %s", n, len(todo), dict(tally))
        time.sleep(random.uniform(1.5, 3.0))
    log.info("done: %s asked -> %s%s", sum(tally.values()), dict(tally), "" if args.count_only else " (saved)")


if __name__ == "__main__":
    main()
