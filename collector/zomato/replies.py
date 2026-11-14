"""Zomato review replies: posts the replies SocialSpork staff have switched on, and writes the automatic ones.

Nothing is sent for a client or outlet unless staff gave it an active row in `reply_service` (the Reply service page).
Each run, for the outlets that have one:
  1. posts every reply a person queued with "Send to Zomato" (review_replies.status = 'approved');
  2. for outlets in AI mode, writes a reply with Gemini for each new unreplied review and posts it, skipping risky reviews
     (food safety, refunds, legal) when the row says to hold them for a person.
Posting is POST merchant-gw/web/reviews/post/reply with the account's stored merchant login. Safe to run often: a review gets
one reply, a failed one is retried only after a pause, and per-run, per-day and Gemini caps apply.

    python run.py zomato replies --every 180
"""

import json
import random
import re
import time

from core import config as cfg, db
from core.common import ConfigError, log, require_env

from .outlets import _cookies

ZOMATO_API = cfg.text("ZOMATO_API_BASE", "https://api.zomato.com/merchant-gw/web")
REPLY_URL = cfg.text("ZOMATO_REPLY_URL", f"{ZOMATO_API}/reviews/post/reply")
CSRF_URL = cfg.text("ZOMATO_CSRF_URL", "https://api.zomato.com/merchant-gw/set-csrf")
ZOMATO_ORIGIN = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
GEMINI_MODEL = cfg.text("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_PER_RUN = cfg.integer("REPLY_MAX_PER_RUN", 40)           # replies posted in one run, all outlets together
PACE_SEC = cfg.integer("REPLY_PACE_SEC", 15)                 # between posts, to stay under Zomato's rate limits
GEMINI_MAX_PER_DAY = cfg.integer("GEMINI_MAX_CALLS_PER_DAY", 150)
GEMINI_PACE_SEC = float(cfg.text("GEMINI_MIN_SECONDS_BETWEEN_CALLS", "4"))
MAX_REVIEW_AGE_DAYS = cfg.integer("REPLY_MAX_REVIEW_AGE_DAYS", 3)  # older unreplied reviews are left for a person
RETRY_AFTER_HOURS = cfg.integer("REPLY_RETRY_AFTER_HOURS", 6)      # a failed reply is tried again after this long

# reviews an automatic reply must never answer when the row says to hold risky ones
RISKY = re.compile(r"stomach|food poison|vomit|puk(e|ing)|diarrh|hospital|infection|insect|cockroach|hair|worm|fungus|mould|mold|"
                   r"allerg|sick|refund|money back|legal|lawyer|consumer court|fssai|police|complain(t)? to", re.I)
TRANSIT = re.compile(r"late|delay|cold|took too long|spill|leak|damaged|crushed|squashed|messy|rider|delivery (boy|guy|partner|person)|"
                     r"rough handling|tampered|box (open|damaged)", re.I)
OPENINGS = [
    "Put {name}'s name naturally in the middle or end of the first sentence instead of starting with a greeting, then add a warm closing sentence.",
    "Start with 'Hi {name},' and react directly to the specific food or service detail they mentioned, then a warm closing sentence.",
    "Start with '{name},' followed by a genuine reaction to their review, and finish with a complete second sentence.",
    "Start with 'Hello {name},' and write 2 complete, flowing sentences.",
    "Start by reacting to what they ordered or experienced in the first sentence, then thank {name} and invite them back in the second.",
    "Start with 'Dear {name},' and write 2 warm, personal sentences in a restaurant-manager voice.",
]
VIBES = [
    "Write 2 complete, well-rounded sentences (25-42 words) that feel warm, polished and complete.",
    "Sound like a passionate head chef who cares about flavours and prep (2 complete sentences, 25-40 words).",
    "Sound like a friendly, down-to-earth floor manager talking to a valued guest (2 complete sentences).",
    "Write with warm, relaxed, conversational energy, with a specific acknowledgment and a proper closing sentence.",
]
BANNED = ("glad you enjoyed, glad to hear, wonderful to hear, so happy to read, made our day, your kind words, always striving to improve, "
          "is important to us, thank you for sharing your thoughts, always looking to")


def config(account: str) -> dict:
    return require_env("SOCIALSPORK_DATABASE_URL")


def is_risky(text: str | None) -> bool:
    return bool(RISKY.search(text or ""))


def is_dine_in(order_id) -> bool:
    return order_id is None or str(order_id).strip().lower() in ("", "0", "none", "dine in")


def build_prompt(review: dict, instructions: str, recent: str) -> str:
    name = (review.get("author_name") or "Guest").strip() or "Guest"
    directive = f"{random.choice(OPENINGS).format(name=name)} {random.choice(VIBES)}"
    dine = is_dine_in(review.get("order_id"))
    transit = ""
    if not dine and TRANSIT.search(review.get("body") or ""):
        transit = ("\nThe customer mentions delivery or transit trouble (delay, spill, cold food, rough handling). Do NOT accept blame for "
                   "the kitchen. Politely say the kitchen packs every order securely and transit and handling are managed by Zomato's "
                   "delivery partners. Stay empathetic, never defensive.")
    extra = f"\nExtra rules from the restaurant (follow them exactly):\n{instructions.strip()}\n" if instructions.strip() else ""
    return f"""You are a real human restaurant manager replying to a customer review for a {'dine-in visit' if dine else 'food delivery order'}.

Rules:
1. VARIANCE DIRECTIVE (must follow): {directive}
2. Write 2 complete, natural sentences (25-45 words in total): the first about their specific feedback, the second a warm closing. Never cut off.
3. Mention the specific details they wrote (a dish, a drink, a staff member) instead of generic filler.
4. Always speak as the restaurant: "we", "our team", "us". Never "I".
5. Never ask the customer to contact us (unless the extra rules give a number to use) and never mention refunds, discounts or compensation.
6. Banned overused phrases: {BANNED}.
7. Make the sentence structure completely different from every reply listed under RECENT REPLIES.
{extra}{transit}
---
Rating: {review.get('rating')} / 5
Customer Name: {name}
Review: "{review.get('body') or '[No review text provided]'}"
---

RECENT REPLIES (do not reuse any opening, structure or phrasing):
{recent}"""


def valid_reply(text: str) -> bool:
    words = len(text.split())
    return bool(text) and text[-1] in ".!?" and 8 <= words <= 80


_last_gemini = 0.0


class GeminiStop(Exception):
    """Quota, credits or the daily cap: stop the whole run."""


def gemini(prompt: str) -> str | None:
    """One Gemini call. None = this review failed (try later); raises GeminiStop when no more calls should be made."""
    import requests

    global _last_gemini
    key = cfg.text("GEMINI_API_KEY", "")
    if not key:
        raise GeminiStop("GEMINI_API_KEY is not set in the collector's .env")
    wait = GEMINI_PACE_SEC - (time.time() - _last_gemini)
    if wait > 0:
        time.sleep(wait)
    _last_gemini = time.time()
    try:
        resp = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent", params={"key": key},
                             json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.9, "topP": 0.95, "maxOutputTokens": 1024}},
                             timeout=40)
    except Exception as e:  # noqa: BLE001
        log.warning("zomato replies: Gemini unreachable: %s", e)
        return None
    if resp.status_code in (401, 403, 429) or "quota" in resp.text[:300].lower():
        raise GeminiStop(f"Gemini refused ({resp.status_code}): {resp.text[:160]}")
    if resp.status_code != 200:
        log.warning("zomato replies: Gemini answered %s", resp.status_code)
        return None
    try:
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:  # noqa: BLE001
        return None
    text = re.sub(r"\s*\n+\s*", " ", text)
    return text if valid_reply(text) else None


def _session(cookies: dict):
    """A requests session carrying the account's merchant login, with a fresh CSRF token from Zomato's gateway."""
    import requests

    s = requests.Session()
    for k, v in cookies.items():
        s.cookies.set(str(k), str(v), domain=".zomato.com")
    s.headers.update({
        "accept": "application/json, text/plain, */*", "content-type": "application/json", "origin": ZOMATO_ORIGIN, "referer": ZOMATO_ORIGIN + "/",
        "user-agent": cfg.user_agent(), "x-client-id": cfg.text("ZOMATO_CLIENT_ID", "zomato_web_merchant"),
        "x-zomato-app-version": cfg.text("ZOMATO_APP_VERSION", "2"), "x-zomato-source-identifier": cfg.text("ZOMATO_SOURCE_ID", "merchant-dashboard"),
        "x-zomato-csrft": cookies.get("csrf", ""), "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""),
    })
    try:
        r = s.post(CSRF_URL, json={}, timeout=10)
        token = r.json().get("csrf") if r.ok else None
        if token:
            s.headers["x-zomato-csrft"] = s.headers["x-zomato-mx-csrf-token"] = token
    except Exception:  # noqa: BLE001  the stored tokens may still work
        pass
    return s


def post_reply(session, res_id: str, review_id: str, text: str) -> tuple[bool, str]:
    """(posted, error). 401/403 raises PermissionError: the login is dead, so every other post this run would fail too."""
    try:
        resp = session.post(REPLY_URL, json={"comment": text, "res_id": str(res_id), "review_id": str(review_id)}, timeout=cfg.http_timeout())
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {str(e)[:150]}"
    if resp.status_code in (401, 403):
        raise PermissionError("Zomato session expired; refresh it on the Sessions page")
    if resp.status_code == 200:
        return True, ""
    return False, f"Zomato answered {resp.status_code}: {resp.text[:160]}"


def _rule_for(rules: list[dict], client_id, res_id) -> dict | None:
    """An outlet's own row beats the client-wide one; no row = no replies."""
    own = next((r for r in rules if r["client_id"] == client_id and r["res_id"] == str(res_id)), None)
    return own or next((r for r in rules if r["client_id"] == client_id and not r["res_id"]), None)


def _mark(cur, reply_id: int, review_id: int, ok: bool, error: str) -> None:
    if ok:
        cur.execute("UPDATE review_replies SET status = 'published', published_at = now(), error = '' WHERE id = %s", (reply_id,))
        cur.execute("UPDATE reviews SET reply_status = 'replied', updated_at = now() WHERE id = %s", (review_id,))
    else:
        cur.execute("UPDATE review_replies SET status = 'failed', error = %s WHERE id = %s", (error[:500], reply_id))


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato replies: %s", e)
        return False
    with db.transaction() as cur:
        cur.execute("SELECT id, client_id, res_id, mode, hold_risky, instructions, max_per_day FROM reply_service WHERE is_active AND platform = 'zomato'")
        rules = cur.fetchall()
        if not rules:
            log.info("zomato replies: no outlet has the reply service switched on: nothing to do")
            return True
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id, b.client_id
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND z.is_active""")
        stores = {s["outlet_id"]: s for s in cur.fetchall() if _rule_for(rules, s["client_id"], s["res_id"])}
    if not stores:
        log.info("zomato replies: the switched-on clients have no mapped Zomato outlets")
        return True
    by_id = {a["id"]: a for a in accs.values()}
    default = next(iter(by_id))
    sessions: dict[int, object] = {}
    posted = failed = 0
    dead: set[int] = set()

    def send(reply_id, review_id, store, ext_review_id, text) -> bool:
        """Post one reply. Each database write commits on its own, so a crash can never lose the record of a reply that
        was posted: it is marked 'sending' first, and a reply stuck in that state is never posted a second time."""
        nonlocal posted, failed
        acc = store["account_id"] if store["account_id"] in by_id else default
        if acc in dead:
            return False
        with db.transaction() as cur:
            cur.execute("UPDATE review_replies SET status = 'failed', error = 'sending (if this stays, check Zomato for the reply)' WHERE id = %s", (reply_id,))
        try:
            if acc not in sessions:
                sessions[acc] = _session(_cookies(db.load_credentials(by_id[acc])))
            ok, err = post_reply(sessions[acc], store["res_id"], ext_review_id, text)
        except PermissionError as e:
            dead.add(acc)
            with db.transaction() as cur:
                cur.execute("UPDATE review_replies SET status = 'approved', error = '' WHERE id = %s", (reply_id,))  # not sent: try again after the login is fixed
            db.mark_session_expired(acc, f"zomato replies: {e}")
            log.error("zomato replies: login %s refused: %s", by_id[acc]["label"], e)
            return False
        with db.transaction() as cur:
            _mark(cur, reply_id, review_id, ok, err)
        posted, failed = posted + ok, failed + (not ok)
        log.info("zomato replies: review %s %s%s", ext_review_id, "posted" if ok else "failed", f": {err}" if err else "")
        time.sleep(PACE_SEC)
        return ok

    # 1. replies a person queued with Send to Zomato (the switch is checked again here: turning the service off stops them)
    with db.transaction() as cur:
        cur.execute("""SELECT rp.id, rp.body, r.id AS review_id, r.external_review_id, r.outlet_id
                       FROM review_replies rp JOIN reviews r ON r.id = rp.review_id
                       WHERE rp.status = 'approved' AND r.platform = 'zomato' AND r.outlet_id = ANY(%s) ORDER BY rp.created_at LIMIT %s""",
                    (list(stores), MAX_PER_RUN))
        queued = cur.fetchall()
    for q in queued:
        if posted + failed >= MAX_PER_RUN:
            break
        send(q["id"], q["review_id"], stores[q["outlet_id"]], q["external_review_id"], q["body"])

    # 2. automatic replies, only for outlets in AI mode
    ai_outlets = [oid for oid, s in stores.items() if _rule_for(rules, s["client_id"], s["res_id"])["mode"] == "ai"]
    gemini_stopped = False
    for oid in ai_outlets:
        if posted + failed >= MAX_PER_RUN or gemini_stopped:
            break
        store = stores[oid]
        rule = _rule_for(rules, store["client_id"], store["res_id"])
        with db.transaction() as cur:
            cur.execute("SELECT count(*) AS n FROM review_replies rp JOIN reviews r ON r.id = rp.review_id WHERE r.outlet_id = %s AND rp.source = 'ai' "
                        "AND rp.created_at > date_trunc('day', now() at time zone 'Asia/Kolkata') at time zone 'Asia/Kolkata'", (oid,))
            done_today = cur.fetchone()["n"]
            cur.execute("SELECT count(*) AS n FROM review_replies WHERE source = 'ai' AND created_at > date_trunc('day', now() at time zone 'Asia/Kolkata') at time zone 'Asia/Kolkata'")
            gemini_today = cur.fetchone()["n"]
            room = min(rule["max_per_day"] - done_today, GEMINI_MAX_PER_DAY - gemini_today, MAX_PER_RUN - posted - failed)
            if room <= 0:
                continue
            cur.execute("""SELECT r.id, r.external_review_id, r.author_name, r.rating, r.body, r.raw->>'order_id' AS order_id FROM reviews r
                           WHERE r.outlet_id = %s AND r.platform = 'zomato' AND r.reply_status = 'pending'
                             AND r.reviewed_at > now() - make_interval(days => %s)
                             AND NOT EXISTS (SELECT 1 FROM review_replies x WHERE x.review_id = r.id AND (x.status IN ('approved', 'published')
                                             OR (x.status = 'failed' AND x.created_at > now() - make_interval(hours => %s))))
                           ORDER BY r.reviewed_at LIMIT %s""", (oid, MAX_REVIEW_AGE_DAYS, RETRY_AFTER_HOURS, room))
            reviews = cur.fetchall()
            cur.execute("""SELECT rp.body FROM review_replies rp JOIN reviews r ON r.id = rp.review_id JOIN brand_outlets bo ON bo.id = r.outlet_id
                           JOIN brands b ON b.id = bo.brand_id WHERE rp.source = 'ai' AND b.client_id = %s ORDER BY rp.created_at DESC LIMIT 30""",
                        (store["client_id"],))
            recent = "\n".join(f"- {x['body']}" for x in cur.fetchall())
        for rv in reviews:
            if rule["hold_risky"] and is_risky(rv["body"]):
                log.info("zomato replies: review %s held for a person (risky wording)", rv["external_review_id"])
                continue
            try:
                text = gemini(build_prompt(rv, rule["instructions"], recent))
            except GeminiStop as e:
                log.error("zomato replies: stopping automatic replies: %s", e)
                gemini_stopped = True
                break
            if not text:
                continue
            with db.transaction() as cur:
                cur.execute("INSERT INTO review_replies (review_id, body, source, status, error, created_at) VALUES (%s, %s, 'ai', 'approved', '', now()) RETURNING id",
                            (rv["id"], text))
                reply_id = cur.fetchone()["id"]
            if send(reply_id, rv["id"], store, rv["external_review_id"], text):
                recent = f"- {text}\n{recent}"
            if posted + failed >= MAX_PER_RUN:
                break
    log.info("zomato replies: %s posted, %s failed", posted, failed)
    return failed == 0
