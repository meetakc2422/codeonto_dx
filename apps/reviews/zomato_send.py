"""Post a reply to a Zomato review straight from the site, with the outlet's saved merchant login (the same one the Windows
collector uses). When that is not possible (no login saved, the login or this server refused, a connection error before
anything was sent), the reply simply stays queued and the collector's "Zomato review replies" task posts it later.

Safety: the reply is marked 'failed (sending...)' before the request goes out, so a crash or a lost answer can never lead
to a second post of the same reply; the collector only picks up 'approved' replies."""
import json
import logging

from django.conf import settings
from django.utils import timezone

from apps.integrations.crypto import decrypt
from apps.integrations.models import PlatformSession

log = logging.getLogger(__name__)

API = getattr(settings, "ZOMATO_MERCHANT_API", "https://api.zomato.com/merchant-gw/web")
REPLY_URL = f"{API}/reviews/post/reply"
CSRF_URL = "https://api.zomato.com/merchant-gw/set-csrf"
ORIGIN = "https://www.zomato.com"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0.0.0 Safari/537.36")
SENDING = "sending (if this stays, check Zomato for the reply)"


def _cookies(raw) -> dict:
    """The saved session is {"name": "value"}, [{"name", "value"}] or {"cookies": [...]}."""
    if isinstance(raw, dict) and "cookies" in raw:
        raw = raw["cookies"]
    if isinstance(raw, list):
        raw = {c["name"]: c["value"] for c in raw}
    return raw or {}


def _login_cookies(outlet) -> dict | None:
    account = getattr(outlet.zomato, "account", None) if outlet.zomato_id else None
    if not account:
        return None
    row = PlatformSession.objects.filter(account=account, kind="merchant", platform="zomato").first()
    if not row:
        return None
    try:
        return _cookies(json.loads(decrypt(row.data_enc))) or None
    except Exception:  # noqa: BLE001  unreadable session: let the collector deal with it
        log.exception("could not read the saved Zomato session for account %s", account.id)
        return None


def post_now(review, reply) -> dict:
    """Try to post `reply` to Zomato now. {"sent": bool, "queued": bool, "error": str}. Never raises."""
    import requests

    res_id = review.outlet.zomato_id
    cookies = _login_cookies(review.outlet)
    if not res_id or not cookies:
        return {"sent": False, "queued": True, "error": "no saved Zomato login for this outlet"}
    s = requests.Session()
    for k, v in cookies.items():
        s.cookies.set(str(k), str(v), domain=".zomato.com")
    s.headers.update({
        "accept": "application/json, text/plain, */*", "content-type": "application/json", "origin": ORIGIN, "referer": ORIGIN + "/",
        "user-agent": USER_AGENT, "x-client-id": "zomato_web_merchant", "x-zomato-app-version": "2",
        "x-zomato-source-identifier": "merchant-dashboard",
        "x-zomato-csrft": cookies.get("csrf", ""), "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""),
    })
    try:
        r = s.post(CSRF_URL, json={}, timeout=8)
        token = r.json().get("csrf") if r.ok else None
        if token:
            s.headers["x-zomato-csrft"] = s.headers["x-zomato-mx-csrf-token"] = token
    except Exception:  # noqa: BLE001  the saved tokens may still work
        pass

    reply.status, reply.error = "failed", SENDING  # recorded first: a reply that may have gone out is never posted twice
    reply.save(update_fields=["status", "error"])
    try:
        resp = s.post(REPLY_URL, json={"comment": reply.body, "res_id": str(res_id), "review_id": str(review.external_review_id)}, timeout=20)
    except (requests.ConnectionError, requests.exceptions.ConnectTimeout) as e:  # nothing reached Zomato: the collector can still post it
        reply.status, reply.error = "approved", ""
        reply.save(update_fields=["status", "error"])
        return {"sent": False, "queued": True, "error": type(e).__name__}
    except Exception as e:  # noqa: BLE001  the request may or may not have gone through: do not retry, tell the person
        reply.error = f"{SENDING} ({type(e).__name__})"
        reply.save(update_fields=["error"])
        return {"sent": False, "queued": False, "error": "Zomato did not confirm. Check the review on Zomato before sending again."}

    if resp.status_code == 200:
        reply.status, reply.error, reply.published_at = "published", "", timezone.now()
        reply.save(update_fields=["status", "error", "published_at"])
        review.reply_status = "replied"
        review.save(update_fields=["reply_status", "updated_at"])
        return {"sent": True, "queued": False, "error": ""}
    if resp.status_code in (401, 403, 429):  # login expired, this server blocked, or rate limited: nothing was posted
        reply.status, reply.error = "approved", ""
        reply.save(update_fields=["status", "error"])
        return {"sent": False, "queued": True, "error": f"Zomato answered {resp.status_code}"}
    reply.error = f"Zomato answered {resp.status_code}: {resp.text[:160]}"
    reply.save(update_fields=["error"])
    return {"sent": False, "queued": False, "error": reply.error}
