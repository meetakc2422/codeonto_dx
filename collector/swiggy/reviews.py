"""Swiggy reviews -> reviews table, for every Swiggy id mapped to a store.

One getRestaurantRatingsAndReviews call per store covering the last SWIGGY_REVIEW_DAYS days
(default 60). Each store uses the session of the account whose restaurant list contains its id.
Swiggy has no public reply text: ratingState tells us whether the review still needs action.
"""

import json
import os
import time
from datetime import datetime, timezone

from core import config as cfg, db
from core.common import ConfigError, log, require_env

SWIGGY_ORIGIN = cfg.text("SWIGGY_PARTNER_ORIGIN", "https://partner-self-client.swiggy.com")
REVIEWS_URL = cfg.text("SWIGGY_REVIEWS_URL", "https://vhc-composer.swiggy.com/query?query=getRestaurantRatingsAndReviews")
QUERY = """query { getRestaurantRatingsAndReviews(requestInput: {restaurantIds: ["%s"], startDateEpoch: %d,
  endDateEpoch: %d, pageSize: %d, pageKey: ""}) { ordersInfo { orderID restaurantID rating ratingTimeEpoch
  orderTimeEpoch ratingState customerReview feedbackExpiryTimeEpoch itemsInfo { id name quantity marking }
  customerInfo { id name type } } } }"""
# ratingState -> reply status (mappings/swiggy_rating_state.json). VENDOR_ACTION_PENDING: the restaurant can
# still act; CLOSED: handled; EXPIRED: window passed unanswered
STATUS = cfg.mapping("swiggy_rating_state")


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _headers(token: str) -> dict:
    return {
        "Content-Type": "application/json", "Accept": "*/*", "access_token": token,
        "Origin": SWIGGY_ORIGIN, "Referer": SWIGGY_ORIGIN + "/", "User-Agent": cfg.user_agent(),
    }


def _fetch(creds: dict, res_id: str, start_ms: int, end_ms: int) -> list[dict]:
    import requests

    token = creds.get("access_token")
    if not token:
        raise ConfigError("Session file has no access_token; run `run.py swiggy session` for this account")
    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = requests.post(REVIEWS_URL, headers=_headers(token), timeout=cfg.http_timeout(),
                             json={"query": QUERY % (res_id, start_ms, end_ms, cfg.integer("SWIGGY_REVIEW_PAGE_SIZE", 1000)), "variables": {}})
        if resp.status_code in (401, 403):
            raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
        if resp.status_code != 429:
            resp.raise_for_status()
            data = (resp.json().get("data") or {}).get("getRestaurantRatingsAndReviews") or {}
            return data.get("ordersInfo") or []
        log.warning("Swiggy 429; backing off")
    resp.raise_for_status()


def _row(review: dict, outlet_id: int) -> dict:
    rating = review.get("rating")
    rating = float(rating) if rating not in (None, "") else None
    sentiment = cfg.sentiment(rating)
    at = datetime.fromtimestamp((review.get("ratingTimeEpoch") or 0) / 1000, tz=timezone.utc)
    return {
        "outlet": outlet_id, "ext": str(review["orderID"]),
        "author": ((review.get("customerInfo") or {}).get("name") or "")[:255],
        "rating": rating, "body": review.get("customerReview") or "", "sentiment": sentiment, "at": at,
        "status": STATUS.get(review.get("ratingState"), "pending"),
        "raw": json.dumps(review, default=str),
    }


def _save(cur, r: dict) -> None:
    cur.execute(
        """INSERT INTO reviews (outlet_id, platform, external_review_id, author_name, rating, title, body,
                                sentiment, reviewed_at, reply_status, raw, created_at, updated_at)
           VALUES (%(outlet)s, 'swiggy', %(ext)s, %(author)s, %(rating)s, '', %(body)s, %(sentiment)s,
                   %(at)s, %(status)s, %(raw)s::jsonb, now(), now())
           ON CONFLICT (platform, external_review_id) DO UPDATE SET
             outlet_id = EXCLUDED.outlet_id, rating = EXCLUDED.rating, body = EXCLUDED.body,
             author_name = EXCLUDED.author_name, sentiment = EXCLUDED.sentiment, raw = EXCLUDED.raw,
             reply_status = CASE WHEN reviews.reply_status = 'drafted' THEN 'drafted' ELSE EXCLUDED.reply_status END,
             updated_at = now()""",
        r,
    )


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("swiggy reviews: %s", e)
        return False
    days = cfg.integer("SWIGGY_REVIEW_DAYS", 60)
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "swiggy", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.swiggy_id AS res_id, s.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id
                       JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND s.is_active""")
        stores = cur.fetchall()
    if not stores:
        log.info("swiggy reviews: no Swiggy ids are mapped to stores yet")
        return True

    creds = {a["id"]: db.load_credentials(a) for a in accs.values()}
    by_id = {a["id"]: a for a in accs.values()}
    ok, total = True, 0
    for s in stores:
        # the account whose restaurant list has this id; else the catalog's owner; else the first account
        acc_id = next((i for i, c in creds.items() if s["res_id"] in {str(x) for x in c.get("outlets") or []}), None)
        if acc_id is None:
            acc_id = s["account_id"] if s["account_id"] in by_id else next(iter(by_id))
        try:
            rows = [_row(r, s["outlet_id"]) for r in _fetch(creds[acc_id], s["res_id"], start_ms, end_ms) if r.get("orderID")]
            with db.transaction() as cur:
                cur.execute("SELECT external_review_id FROM reviews WHERE platform = 'swiggy' AND external_review_id = ANY(%s)",
                            ([r["ext"] for r in rows],))
                known = {r["external_review_id"] for r in cur.fetchall()}
                for r in rows:
                    _save(cur, r)
            new = sum(1 for r in rows if r["ext"] not in known)
            total += new
            log.info("swiggy reviews %s · %s (%s) via %s: %s new, %s total in %sd", s["brand"], s["outlet_name"],
                     s["res_id"], by_id[acc_id]["label"], new, len(rows), days)
        except PermissionError as e:
            log.error("swiggy reviews: %s", e)
            return False
        except Exception as e:
            log.exception("swiggy reviews %s failed: %s", s["res_id"], e)
            ok = False
    log.info("swiggy reviews: %s new across %s stores", total, len(stores))
    return ok
