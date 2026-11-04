"""Zomato reviews -> reviews table, for every Zomato id mapped to a store.

Pages through reviews/get/all (5 per page) per res_id, newest first, and stops at the
first page whose reviews are all already stored (or after ZOMATO_REVIEW_PAGES pages).
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

from core import config as cfg, db
from core.common import ConfigError, log, require_env

from .outlets import _cookies

ZOMATO_API = cfg.text("ZOMATO_API_BASE", "https://api.zomato.com/merchant-gw/web")
ZOMATO_ORIGIN = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
REVIEWS_URL = cfg.text("ZOMATO_REVIEWS_URL", f"{ZOMATO_API}/reviews/get/all")
DETAILS_URL = cfg.text("ZOMATO_REVIEW_DETAILS_URL", f"{ZOMATO_API}/reviews/get/details")
PAGE_SIZE = cfg.integer("ZOMATO_REVIEW_PAGE_SIZE", 5)
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def parse_date(text: str | None) -> datetime:
    """Zomato's display_date: 'today', 'yesterday', 'N days/hours/minutes ago', or a date."""
    now = datetime.now(IST)
    t = (text or "").strip().lower()
    if not t or t in ("now", "just now"):
        return now
    if t == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if t == "yesterday":
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    m = re.search(r"(\d+)\s+(minute|hour|day|week|month)s?\s+ago", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {"minute": timedelta(minutes=n), "hour": timedelta(hours=n), "day": timedelta(days=n),
                 "week": timedelta(weeks=n), "month": timedelta(days=30 * n)}[unit]
        return now - delta
    for fmt in ("%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d %b, %Y", "%Y-%m-%d", "%d/%m/%Y", "%d %b"):
        try:
            dt = datetime.strptime(text.strip(), fmt)
            if fmt == "%d %b":  # no year: this year, or last year if that would be in the future
                dt = dt.replace(year=now.year)
                if dt.replace(tzinfo=IST) > now:
                    dt = dt.replace(year=now.year - 1)
            return dt.replace(tzinfo=IST)
        except ValueError:
            pass
    log.warning("Unrecognised Zomato review date %r; using now", text)
    return now


def _headers(cookies: dict) -> dict:
    return {
        "accept": "application/json, text/plain, */*",
        "origin": ZOMATO_ORIGIN,
        "referer": ZOMATO_ORIGIN + "/",
        "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
        "x-zomato-csrft": cookies.get("csrf", ""),
        "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""),
        "x-client-id": cfg.text("ZOMATO_CLIENT_ID", "zomato_web_merchant"),
        "x-zomato-app-version": cfg.text("ZOMATO_APP_VERSION", "2"),
        "x-zomato-source-identifier": cfg.text("ZOMATO_SOURCE_ID", "merchant-dashboard"),
    }


def _get(url: str, cookies: dict, params: dict) -> dict:
    """GET with a polite pace and backoff on 429."""
    import time

    import requests

    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = requests.get(url, params=params, headers=_headers(cookies), timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp.json()
        log.warning("Zomato 429; waiting %ss", wait * 3 if wait > 1 else 15)
    resp.raise_for_status()


def _fetch_page(cookies: dict, res_id: str, offset: int) -> list[dict]:
    return _get(REVIEWS_URL, cookies, {"res_id": res_id, "offset": offset}).get("reviews") or []


def _fetch_replies(cookies: dict, res_id: str, review_id: str) -> list[dict]:
    return _get(DETAILS_URL, cookies, {"res_id": res_id, "review_id": review_id}).get("replies") or []


def _save_replies(cur, review_pk: int, replies: list[dict]) -> int:
    n = 0
    for rp in replies:
        msg = (rp.get("message") or "").strip()
        if not msg or rp.get("sender_type") != "RESTAURANT":
            continue
        cur.execute(
            """INSERT INTO review_replies (review_id, body, source, status, error, published_at, created_at)
               VALUES (%s, %s, 'platform', 'published', '', %s, %s)""",
            (review_pk, msg, rp.get("timestamp"), rp.get("timestamp")),
        )
        n += 1
    return n


def _row(review: dict, outlet_id: int) -> dict:
    info = review.get("review_info") or {}
    rating = info.get("rating")
    try:
        rating = float(rating) if rating not in (None, "") else None
    except (TypeError, ValueError):
        rating = None
    sentiment = cfg.sentiment(rating)
    return {
        "outlet": outlet_id, "ext": str(review["review_id"]),
        "author": ((review.get("customer_details") or {}).get("name") or "")[:255],
        "rating": rating, "body": review.get("review_text") or "", "sentiment": sentiment,
        "at": parse_date(info.get("display_date")),
        # reply_count > 0: the conversation already has a reply on Zomato
        "status": "replied" if (info.get("reply_count") or 0) > 0 else "pending",
        "raw": json.dumps(review, default=str),
    }


def _save(cur, rows: list[dict]) -> int:
    for r in rows:
        cur.execute(
            """INSERT INTO reviews (outlet_id, platform, external_review_id, author_name, rating, title, body,
                                    sentiment, reviewed_at, reply_status, raw, created_at, updated_at)
               VALUES (%(outlet)s, 'zomato', %(ext)s, %(author)s, %(rating)s, '', %(body)s, %(sentiment)s,
                       %(at)s, %(status)s, %(raw)s::jsonb, now(), now())
               ON CONFLICT (platform, external_review_id) DO UPDATE SET
                 outlet_id = EXCLUDED.outlet_id, rating = EXCLUDED.rating, body = EXCLUDED.body,
                 author_name = EXCLUDED.author_name, sentiment = EXCLUDED.sentiment, raw = EXCLUDED.raw,
                 reply_status = CASE WHEN EXCLUDED.reply_status = 'replied' THEN 'replied' ELSE reviews.reply_status END,
                 updated_at = now()""",
            r,
        )
    return len(rows)


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato reviews: %s", e)
        return False
    max_pages = cfg.integer("ZOMATO_REVIEW_PAGES", 10)

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        # every Zomato id mapped to a store, with the account it was found in
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND z.is_active""")
        stores = cur.fetchall()
    if not stores:
        log.info("zomato reviews: no Zomato ids are mapped to stores yet")
        return True

    by_id = {a["id"]: a for a in accs.values()}
    creds = {a["id"]: _cookies(db.load_credentials(a)) for a in accs.values()}
    default = next(iter(accs.values()))["id"]
    ok, total_new = True, 0
    for s in stores:
        acc_id = s["account_id"] if s["account_id"] in by_id else default
        try:
            with db.transaction() as cur:
                new = 0
                for page in range(max_pages):
                    batch = _fetch_page(creds[acc_id], s["res_id"], page * PAGE_SIZE)
                    if not batch:
                        break
                    rows = [_row(r, s["outlet_id"]) for r in batch if r.get("review_id")]
                    cur.execute("SELECT external_review_id FROM reviews WHERE platform = 'zomato' AND external_review_id = ANY(%s)",
                                ([r["ext"] for r in rows],))
                    known = {r["external_review_id"] for r in cur.fetchall()}
                    fresh = [r for r in rows if r["ext"] not in known]
                    _save(cur, rows)
                    new += len(fresh)
                    if not fresh:  # whole page already stored: we're caught up
                        break
            # replies: the list API only says reply_count; the text comes from reviews/get/details
            with db.transaction() as cur:
                cur.execute("""SELECT r.id, r.external_review_id FROM reviews r
                               WHERE r.platform = 'zomato' AND r.outlet_id = %s AND r.reply_status = 'replied'
                                 AND NOT EXISTS (SELECT 1 FROM review_replies rr WHERE rr.review_id = r.id)""",
                            (s["outlet_id"],))
                missing = cur.fetchall()
                got = 0
                for m in missing:
                    got += _save_replies(cur, m["id"], _fetch_replies(creds[acc_id], s["res_id"], m["external_review_id"]))
            log.info("zomato reviews %s (%s): %s replies saved", s["outlet_name"], s["res_id"], got)
            total_new += new
            log.info("zomato reviews %s · %s (%s): %s new", s["brand"], s["outlet_name"], s["res_id"], new)
        except PermissionError as e:
            log.error("zomato reviews: %s", e)
            return False
        except Exception as e:
            log.exception("zomato reviews %s failed: %s", s["res_id"], e)
            ok = False
    log.info("zomato reviews: %s new across %s stores", total_new, len(stores))
    return ok
