"""Google reviews -> reviews table, for every Google location mapped to a store (fetch only; no replying).

Uses the Business Profile v4 reviews endpoint on each location's business account (stored by
`run.py google outlets`). Stops at the first page that is already fully stored, or after
GOOGLE_REVIEW_PAGES pages (default 10, 50 reviews per page). A review's existing owner reply is
saved as a published platform reply.
"""

import json
import os
import time
from datetime import datetime, timezone

from core import config as cfg, db
from core.common import ConfigError, log, require_env

from .session import credentials_from

REVIEWS_URL = cfg.text("GOOGLE_REVIEWS_URL", "https://mybusiness.googleapis.com/v4/{business_account}/locations/{location_id}/reviews")
STARS = cfg.mapping("google_star_rating")  # mappings/google_star_rating.json
PAGE_SIZE = cfg.integer("GOOGLE_REVIEW_PAGE_SIZE", 50)


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _ts(text: str | None) -> datetime:
    if not text:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _get(session, url: str, params: dict) -> dict:
    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = session.get(url, params=params, timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            detail = resp.json().get("error", {}).get("message", "") if resp.content else ""
            raise PermissionError(f"Google API refused access ({resp.status_code}): {detail}")
        if resp.status_code == 429 or resp.status_code >= 500:
            log.warning("Google %s; backing off", resp.status_code)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return {}


def _row(r: dict, outlet_id: int) -> dict:
    rating = STARS.get(r.get("starRating"))
    sentiment = cfg.sentiment(rating)
    return {
        "outlet": outlet_id, "ext": r["name"].split("/")[-1],  # accounts/…/locations/…/reviews/<id>
        "author": ((r.get("reviewer") or {}).get("displayName") or "")[:255],
        "rating": rating, "body": r.get("comment") or "", "sentiment": sentiment, "at": _ts(r.get("createTime")),
        "status": "replied" if r.get("reviewReply") else "pending",
        "reply": (r.get("reviewReply") or {}).get("comment"), "reply_at": (r.get("reviewReply") or {}).get("updateTime"),
        "raw": json.dumps(r, default=str),
    }


def _save(cur, r: dict) -> None:
    cur.execute(
        """INSERT INTO reviews (outlet_id, platform, external_review_id, author_name, rating, title, body,
                                sentiment, reviewed_at, reply_status, raw, created_at, updated_at)
           VALUES (%(outlet)s, 'google', %(ext)s, %(author)s, %(rating)s, '', %(body)s, %(sentiment)s,
                   %(at)s, %(status)s, %(raw)s::jsonb, now(), now())
           ON CONFLICT (platform, external_review_id) DO UPDATE SET
             outlet_id = EXCLUDED.outlet_id, rating = EXCLUDED.rating, body = EXCLUDED.body,
             author_name = EXCLUDED.author_name, sentiment = EXCLUDED.sentiment, raw = EXCLUDED.raw,
             reply_status = CASE WHEN EXCLUDED.reply_status = 'replied' THEN 'replied' ELSE reviews.reply_status END,
             updated_at = now()
           RETURNING id""",
        r,
    )
    review_pk = cur.fetchone()["id"]
    if r["reply"]:
        cur.execute(
            """INSERT INTO review_replies (review_id, body, source, status, error, published_at, created_at)
               SELECT %(pk)s, %(reply)s, 'platform', 'published', '', %(at)s, %(at)s
               WHERE NOT EXISTS (SELECT 1 FROM review_replies WHERE review_id = %(pk)s AND source = 'platform')""",
            {"pk": review_pk, "reply": r["reply"], "at": _ts(r["reply_at"])},
        )


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("google reviews: %s", e)
        return False
    from google.auth.transport.requests import AuthorizedSession

    max_pages = cfg.integer("GOOGLE_REVIEW_PAGES", 10)
    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "google", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.google_location_id AS location_id, g.business_account, g.account_id,
                              b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN google_locations g ON g.location_id = bo.google_location_id
                       JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND g.is_active AND g.business_account <> ''""")
        stores = cur.fetchall()
    if not stores:
        log.info("google reviews: no Google locations are mapped to stores yet")
        return True

    by_id = {a["id"]: a for a in accs.values()}
    sessions = {}
    for a in accs.values():
        try:
            sessions[a["id"]] = AuthorizedSession(credentials_from(db.load_credentials(a)))
        except (PermissionError, ConfigError) as e:
            log.error("google reviews: account %s: %s", a["label"], e)
            return False
    default = next(iter(by_id))
    # a location is only readable by the login that owns it: skip the others instead of trying them (404s)
    stores = [s for s in stores if s["account_id"] is None or s["account_id"] in by_id]
    ok, total = True, 0
    for s in stores:
        session = sessions[s["account_id"] if s["account_id"] in by_id else default]
        url = REVIEWS_URL.format(business_account=s["business_account"], location_id=s["location_id"])
        try:
            new, token = 0, None
            for _ in range(max_pages):
                data = _get(session, url, {"pageSize": PAGE_SIZE, **({"pageToken": token} if token else {})})
                rows = [_row(r, s["outlet_id"]) for r in data.get("reviews") or []]
                if not rows:
                    break
                with db.transaction() as cur:
                    cur.execute("SELECT external_review_id FROM reviews WHERE platform = 'google' AND external_review_id = ANY(%s)",
                                ([r["ext"] for r in rows],))
                    known = {r["external_review_id"] for r in cur.fetchall()}
                    for r in rows:
                        _save(cur, r)
                fresh = sum(1 for r in rows if r["ext"] not in known)
                new += fresh
                token = data.get("nextPageToken")
                if not token or not fresh:  # no more pages, or this one was already fully stored
                    break
            total += new
            log.info("google reviews %s · %s: %s new", s["brand"], s["outlet_name"], new)
        except PermissionError as e:
            log.error("google reviews: %s", e)
            return False
        except Exception as e:
            log.exception("google reviews %s failed: %s", s["location_id"], e)
            ok = False
    log.info("google reviews: %s new across %s stores", total, len(stores))
    return ok
