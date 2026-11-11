"""A reviewer's shared phone number (Zomato's opt-in) -> review_contacts, encrypted.

Zomato lets a customer agree, after ordering, to share their number with the restaurant. The merchant dashboard reads
it with order/customer-connect-info; trackingParams.meta_data.contactNumberPresent says whether they did. We ask once
per review (new reviews from the reviews job, older ones with review_contacts.py) and keep the answer:
shared numbers encrypted with GOOGLE_TOKEN_KEY plus a masked hint for the dashboard; "not shared" so we don't ask again.
Numbers are never logged. ZOMATO_REVIEW_CONTACTS=0 turns this off.
"""

import os
import random
import re
import time
from datetime import datetime, timezone

from core import config as cfg, db

URL = cfg.text("ZOMATO_CUSTOMER_CONNECT_URL", "https://api.zomato.com/merchant-gw/web/order/customer-connect-info")
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{9})(?!\d)")
MASKED = re.compile(r"[xX*•]{3,}")


def enabled() -> bool:
    return cfg.text("ZOMATO_REVIEW_CONTACTS", "1") not in ("0", "false", "no")


def _strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)
    elif isinstance(o, (str, int)):
        yield str(o)


def hint(phone: str) -> str:
    return f"{phone[:2]}•••••{phone[-3:]}"


def lookup(cookies: dict, order_id: str) -> tuple[bool, str | None]:
    """(shared, 10-digit number or None). Raises PermissionError when the login can't see the order."""
    import requests

    headers = {"accept": "application/json, text/plain, */*", "content-type": "application/json",
               "origin": "https://www.zomato.com", "referer": "https://www.zomato.com/", "user-agent": cfg.user_agent(),
               "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
               "x-zomato-csrft": cookies.get("csrf", ""), "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""),
               "x-zomato-app-version": "2", "x-client-id": "zomato_web_merchant", "x-zomato-source-identifier": "merchant-dashboard",
               "x-zomato-trace-id": "web" + os.urandom(16).hex()}
    resp = None
    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = requests.post(URL, headers=headers, json={"order_id": str(order_id)}, timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            raise PermissionError("Zomato session expired, or the order isn't on this login")
        if resp.status_code != 429 and resp.status_code < 500:
            break
    resp.raise_for_status()
    body = resp.json() if resp.content else {}
    flag = str(((body.get("trackingParams") or {}).get("meta_data") or {}).get("contactNumberPresent", "")).strip().lower()
    if flag not in ("true", "1", "yes"):
        return False, None
    for t in _strings(body):
        if not MASKED.search(t):
            m = PHONE.search(t)
            if m:
                return True, m.group(1)
    return True, None  # shared, but the number wasn't in the answer: keep the flag, show nothing


def save(cur, review_id: int, order_id: str, shared: bool, phone: str | None) -> None:
    enc = db._fernet().encrypt(phone.encode()).decode() if phone else ""
    cur.execute("""INSERT INTO review_contacts (review_id, order_id, shared, phone_enc, hint, checked_at)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (review_id) DO UPDATE SET order_id = EXCLUDED.order_id, shared = EXCLUDED.shared,
                     phone_enc = EXCLUDED.phone_enc, hint = EXCLUDED.hint, checked_at = EXCLUDED.checked_at""",
                (review_id, str(order_id), shared and bool(phone), enc, hint(phone) if phone else "", datetime.now(timezone.utc)))


def fetch_for(cookies: dict, reviews: list[dict]) -> tuple[int, int]:
    """reviews: [{id, order_id}]. Asks Zomato for each and saves the answer. Returns (asked, shared)."""
    asked = shared = 0
    for r in reviews:
        if not r.get("order_id"):
            continue
        ok, phone = lookup(cookies, r["order_id"])
        with db.transaction() as cur:
            save(cur, r["id"], r["order_id"], ok, phone)
        asked += 1
        shared += bool(ok and phone)
        time.sleep(random.uniform(*cfg.numbers("ZOMATO_CONTACT_PACE_SEC", "1.5,3")))
    return asked, shared
