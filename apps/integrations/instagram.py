"""Instagram listening: connect a client's Instagram Business accounts through Facebook Login, then read what
Instagram's official API allows: posts that tag the account, its own posts and the comments on them.

connect     -> the Facebook consent URL (signed `state`, 10 minutes, tied to the logged-in user)
callback    -> Facebook redirects here with a code; we swap it for a long-lived token, list the Pages' Instagram accounts,
               and store each Page token (they do not expire) encrypted
sync        -> read tags, own posts and their comments into InstagramPost
feed        -> what we have kept, newest first
"""

import logging
import secrets
from datetime import datetime, timezone as dt_tz
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.core import signing
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.outlets import access

from . import crypto
from .models import InstagramConnection, InstagramPost

logger = logging.getLogger(__name__)
GRAPH = "https://graph.facebook.com/v21.0"
DIALOG = "https://www.facebook.com/v21.0/dialog/oauth"
SCOPES = "instagram_basic,instagram_manage_comments,instagram_manage_insights,pages_show_list"
STATE_SALT, STATE_MAX_AGE = "instagram-oauth", 600
LOCAL_HOSTS = {"localhost", "127.0.0.1"}
OWN_POSTS, COMMENT_POSTS = 15, 8  # recent posts read per sync, and how many of those get their comments read


class InstagramError(Exception):
    pass


def configured() -> bool:
    return bool(settings.META_APP_ID and settings.META_APP_SECRET and settings.GOOGLE_TOKEN_KEY)


def _check_configured():
    if not configured():
        logger.error("Instagram connection is not set up: META_APP_ID / META_APP_SECRET / GOOGLE_TOKEN_KEY missing")
        raise ValidationError("Connecting Instagram isn't available yet. Please contact Codeonto.")


def _redirect_uri(request) -> str:
    """Opened on localhost, the redirect comes back to this machine (add that address to the Meta app's valid OAuth redirect URIs)."""
    if request.get_host().split(":")[0] in LOCAL_HOSTS:
        return request.build_absolute_uri("/api/instagram/callback").replace("127.0.0.1", "localhost")
    return "https://compass.codeonto.com/api/instagram/callback"


def _get(path: str, token: str, **params) -> dict:
    try:
        r = httpx.get(f"{GRAPH}/{path}", params={**params, "access_token": token}, timeout=30)
        data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise InstagramError(f"Couldn't reach Instagram: {e}") from e
    if "error" in data:
        raise InstagramError(data["error"].get("message") or "Instagram refused the request")
    return data


def _serialize(c: InstagramConnection) -> dict:
    return {"id": c.id, "username": c.username, "followers": c.followers, "status": c.status, "error": c.last_error,
            "connected_at": c.connected_at, "synced_at": c.synced_at}


@api_view(["GET"])
def connect(request):
    """?client_id=  ->  {"url": Facebook consent URL}"""
    client = access.get_client(request.user, request.query_params.get("client_id"))
    access.require_manage(request.user)
    _check_configured()
    nonce = secrets.token_urlsafe(16)
    request.session["instagram_oauth_nonce"] = nonce
    state = signing.dumps({"c": client.id, "u": request.user.id, "n": nonce}, salt=STATE_SALT)
    params = {"client_id": settings.META_APP_ID, "redirect_uri": _redirect_uri(request), "response_type": "code", "state": state}
    if settings.META_LOGIN_CONFIG_ID:  # Login for Business takes a configuration instead of a scope list
        params["config_id"] = settings.META_LOGIN_CONFIG_ID
    else:
        params["scope"] = SCOPES
    return Response({"url": DIALOG + "?" + urlencode(params)})


def _back(result: str, reason: str = "") -> HttpResponseRedirect:
    return HttpResponseRedirect("/#/setup?" + urlencode({"instagram": result, **({"reason": reason} if reason else {})}))


def callback(request):
    """Facebook sends the browser here after the consent screen."""
    if request.GET.get("error"):
        return _back("error", "Access was not granted")
    try:
        state = signing.loads(request.GET.get("state", ""), salt=STATE_SALT, max_age=STATE_MAX_AGE)
    except signing.BadSignature:
        return _back("error", "The connection link expired; try again")
    if not request.user.is_authenticated or state["u"] != request.user.id or state["n"] != request.session.pop("instagram_oauth_nonce", None):
        return _back("error", "Please log in and try again")
    try:
        client = access.get_client(request.user, state["c"])
        access.require_manage(request.user)
        _check_configured()
        code = request.GET.get("code")
        if not code:
            return _back("error", "Facebook did not send a code")
        short = _get("oauth/access_token", "", client_id=settings.META_APP_ID, client_secret=settings.META_APP_SECRET,
                     redirect_uri=_redirect_uri(request), code=code)["access_token"]
        long = _get("oauth/access_token", "", grant_type="fb_exchange_token", client_id=settings.META_APP_ID,
                    client_secret=settings.META_APP_SECRET, fb_exchange_token=short)["access_token"]
        # Page tokens made from a long-lived user token do not expire
        pages = _get("me/accounts", long, fields="id,name,access_token,instagram_business_account{id,username,followers_count}", limit=50)
    except InstagramError as e:
        logger.warning("Instagram connect failed: %s", e)
        return _back("error", str(e))
    except Exception as e:
        return _back("error", str(getattr(e, "detail", e)))
    logger.warning("Instagram connect: Facebook returned %d Page(s): %s", len(pages.get("data", [])),
                   [(pg.get("name"), "instagram linked" if pg.get("instagram_business_account") else "no instagram") for pg in pages.get("data", [])])
    found = 0
    for page in pages.get("data", []):
        ig = page.get("instagram_business_account")
        if not ig:
            continue
        InstagramConnection.objects.update_or_create(client=client, ig_user_id=ig["id"], defaults={
            "username": ig.get("username", ""), "followers": ig.get("followers_count"), "page_id": page["id"],
            "token_enc": crypto.encrypt(page["access_token"]), "status": "connected", "last_error": "", "connected_by": request.user})
        found += 1
    if not found:
        return _back("error", "No Instagram Business account is linked to the Facebook Pages you shared. Link it to a Page and try again")
    return _back("connected")


def _when(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S%z").astimezone(dt_tz.utc) if text else None
    except ValueError:
        return None


def sync_connection(c: InstagramConnection) -> int:
    """Read tags, own posts and their comments. Returns how many items are new."""
    token = crypto.decrypt(c.token_enc)
    new = 0
    media_fields = "id,caption,media_type,permalink,timestamp,like_count,comments_count,username"

    def save(kind, ext_id, **fields):
        nonlocal new
        _, made = InstagramPost.objects.update_or_create(connection=c, kind=kind, ext_id=ext_id, defaults=fields)
        new += made

    try:
        me = _get(c.ig_user_id, token, fields="username,followers_count")
        c.username, c.followers = me.get("username", c.username), me.get("followers_count")
        for m in _get(f"{c.ig_user_id}/tags", token, fields=media_fields, limit=50).get("data", []):
            save("tag", m["id"], username=m.get("username", ""), text=m.get("caption", ""), permalink=m.get("permalink", ""),
                 media_type=m.get("media_type", ""), likes=m.get("like_count") or 0, comments=m.get("comments_count") or 0,
                 posted_at=_when(m.get("timestamp")))
        own = _get(f"{c.ig_user_id}/media", token, fields=media_fields, limit=OWN_POSTS).get("data", [])
        for i, m in enumerate(own):
            save("own", m["id"], username=c.username, text=m.get("caption", ""), permalink=m.get("permalink", ""),
                 media_type=m.get("media_type", ""), likes=m.get("like_count") or 0, comments=m.get("comments_count") or 0,
                 posted_at=_when(m.get("timestamp")))
            if i < COMMENT_POSTS and m.get("comments_count"):
                for cm in _get(f"{m['id']}/comments", token, fields="id,text,username,timestamp,like_count", limit=50).get("data", []):
                    save("comment", cm["id"], username=cm.get("username", ""), text=cm.get("text", ""),
                         parent_permalink=m.get("permalink", ""), likes=cm.get("like_count") or 0, posted_at=_when(cm.get("timestamp")))
        c.status, c.last_error = "connected", ""
    except InstagramError as e:
        c.status, c.last_error = "error", str(e)[:300]
        logger.warning("Instagram sync for @%s failed: %s", c.username, e)
    c.synced_at = timezone.now()
    c.save()
    return new


@api_view(["GET"])
def client_connections(request, client_id):
    client = access.get_client(request.user, client_id)
    access.require_whole_client(request.user)
    rows = InstagramConnection.objects.filter(client=client).exclude(status="revoked")
    return Response({"configured": configured(), "connections": [_serialize(c) for c in rows]})


def _own(request, pk) -> InstagramConnection:
    c = InstagramConnection.objects.filter(pk=pk).first()
    if not c:
        raise ValidationError("Connection not found")
    access.get_client(request.user, c.client_id)
    access.require_manage(request.user)
    return c


@api_view(["POST"])
def sync(request, pk):
    c = _own(request, pk)
    new = sync_connection(c)
    if c.status == "error":
        return Response({"detail": c.last_error or "Instagram could not be read"}, status=400)
    return Response({"new": new})


@api_view(["DELETE"])
def disconnect(request, pk):
    c = _own(request, pk)
    c.status, c.token_enc = "revoked", ""
    c.save(update_fields=["status", "token_enc"])
    return Response({"ok": True})


@api_view(["GET"])
def feed(request, client_id):
    """?kind=tag|own|comment  ->  what we kept for this client's accounts, newest first (up to 100)."""
    client = access.get_client(request.user, client_id)
    qs = InstagramPost.objects.filter(connection__client=client).exclude(connection__status="revoked").select_related("connection")
    kind = request.query_params.get("kind")
    if kind in {k for k, _ in InstagramPost.KINDS}:
        qs = qs.filter(kind=kind)
    return Response({"posts": [{
        "id": p.id, "kind": p.kind, "account": p.connection.username, "username": p.username, "text": p.text, "permalink": p.permalink or p.parent_permalink,
        "media_type": p.media_type, "likes": p.likes, "comments": p.comments, "posted_at": p.posted_at} for p in qs[:100]]})


POST_FIELDS = "id,caption,media_type,permalink,timestamp,like_count,comments_count"


def _card(m: dict, who: str = "") -> dict:
    return {"username": who or m.get("username", ""), "text": m.get("caption", ""), "permalink": m.get("permalink", ""), "likes": m.get("like_count") or 0,
            "comments": m.get("comments_count") or 0, "media_type": m.get("media_type", ""), "posted_at": m.get("timestamp")}


@api_view(["POST"])
def search(request, client_id):
    """{type: "hashtag"|"username", q}  ->  public posts for a hashtag, or a public Business/Creator account's profile and recent posts.
    Runs through the client's first connected Instagram account."""
    client = access.get_client(request.user, client_id)
    q = (request.data.get("q") or "").strip().lstrip("#@").lower()
    kind = request.data.get("type")
    if not q or kind not in ("hashtag", "username"):
        return Response({"detail": "Enter a hashtag or a username."}, status=400)
    c = InstagramConnection.objects.filter(client=client, status="connected").exclude(token_enc="").first()
    if not c:
        return Response({"detail": "Connect an Instagram account first."}, status=400)
    token = crypto.decrypt(c.token_enc)
    try:
        if kind == "hashtag":
            hid = (_get("ig_hashtag_search", token, user_id=c.ig_user_id, q=q).get("data") or [{}])[0].get("id")
            if not hid:
                return Response({"type": kind, "q": q, "posts": [], "detail": "Instagram found nothing for that hashtag."})
            top = _get(f"{hid}/top_media", token, user_id=c.ig_user_id, fields=POST_FIELDS, limit=25).get("data", [])
            recent = _get(f"{hid}/recent_media", token, user_id=c.ig_user_id, fields=POST_FIELDS, limit=25).get("data", [])
            return Response({"type": kind, "q": q, "top": [_card(m) for m in top], "recent": [_card(m) for m in recent]})
        d = _get(c.ig_user_id, token, fields="business_discovery.username(%s){username,name,biography,followers_count,follows_count,media_count,"
                 "media.limit(12){%s}}" % (q, POST_FIELDS)).get("business_discovery") or {}
        posts = [_card(m, d.get("username", q)) for m in (d.get("media") or {}).get("data", [])]
        avg = lambda k: round(sum(p[k] for p in posts) / len(posts), 1) if posts else 0
        return Response({"type": kind, "q": q, "profile": {k: d.get(k) for k in ("username", "name", "biography", "followers_count", "follows_count", "media_count")},
                         "avg_likes": avg("likes"), "avg_comments": avg("comments"), "posts": posts})
    except InstagramError as e:
        if "Public Content Access" in str(e):
            return Response({"detail": "Hashtag search needs Meta's approval for 'Instagram Public Content Access' (an app review). Username lookups work now."}, status=400)
        if kind == "username" and ("Invalid user" in str(e) or "does not exist" in str(e)):
            return Response({"detail": f"We couldn't read @{q}. It must be a public Business or Creator account, spelled exactly as on Instagram. Personal and private accounts can't be read."}, status=400)
        return Response({"detail": str(e)}, status=400)
