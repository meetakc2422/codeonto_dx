"""Connect a client's Google Business Profile with one click ("Connect with Google").

connect      -> returns the Google consent URL for a client (signed `state`, 10 minutes, tied to the logged-in user)
callback     -> Google redirects here with a code; we swap it for tokens, store the refresh token encrypted, and
                create a platform account the collectors can use
disconnect   -> revoke at Google, forget the token
"""

import logging
import re
import secrets
import subprocess
from pathlib import Path
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.core import signing
from django.http import HttpResponseRedirect
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.outlets import access
from apps.outlets.models import PlatformAccount

from . import crypto
from .models import GoogleConnection

logger = logging.getLogger(__name__)
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
BUSINESS_SCOPE = "https://www.googleapis.com/auth/business.manage"
SCOPES = f"{BUSINESS_SCOPE} openid email"
# no include_granted_scopes: the same Google client may hold older Sheets/Drive grants (restricted scopes), and adding
# them back would show users Google's "unverified app" warning; we ask for exactly these three
STATE_SALT, STATE_MAX_AGE = "google-oauth", 600


def _check_configured():
    missing = [n for n in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_REDIRECT_URI", "GOOGLE_TOKEN_KEY") if not getattr(settings, n, "")]
    if missing:
        raise ValidationError(f"Google connection is not set up: add {', '.join(missing)} to .env")


LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def _redirect_uri(request) -> str:
    """Production uses GOOGLE_OAUTH_REDIRECT_URI. Opened on localhost, the redirect comes back to this machine instead,
    so testing needs no .env edit (add that localhost address to the Google client's authorized redirect URIs)."""
    if request.get_host().split(":")[0] in LOCAL_HOSTS:
        return request.build_absolute_uri("/g/oauth/callback/").replace("127.0.0.1", "localhost")
    return settings.GOOGLE_OAUTH_REDIRECT_URI


def _serialize(c: GoogleConnection) -> dict:
    return {"id": c.id, "email": c.email, "status": c.status, "connected_at": c.connected_at, "label": c.account.label if c.account else None}


@api_view(["GET"])
def connect(request):
    """?client_id=  ->  {"url": consent URL}"""
    client = access.get_client(request.user, request.query_params.get("client_id"))
    access.require_manage(request.user)
    _check_configured()
    nonce = secrets.token_urlsafe(16)
    request.session["google_oauth_nonce"] = nonce
    state = signing.dumps({"c": client.id, "u": request.user.id, "n": nonce}, salt=STATE_SALT)
    return Response({"url": AUTH_URL + "?" + urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID, "redirect_uri": _redirect_uri(request), "response_type": "code",
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state})})


def _back(result: str, reason: str = "") -> HttpResponseRedirect:
    return HttpResponseRedirect("/#/setup?" + urlencode({"google": result, **({"reason": reason} if reason else {})}))


def callback(request):
    """Google sends the browser here after the consent screen."""
    if request.GET.get("error"):
        return _back("error", "Access was not granted")
    try:
        state = signing.loads(request.GET.get("state", ""), salt=STATE_SALT, max_age=STATE_MAX_AGE)
    except signing.BadSignature:
        return _back("error", "The connection link expired; try again")
    if not request.user.is_authenticated or state["u"] != request.user.id or state["n"] != request.session.pop("google_oauth_nonce", None):
        return _back("error", "Please log in and try again")
    try:
        client = access.get_client(request.user, state["c"])
        access.require_manage(request.user)
        _check_configured()
    except Exception as e:
        return _back("error", str(getattr(e, "detail", e)))
    code = request.GET.get("code")
    if not code:
        return _back("error", "Google did not send a code")

    tokens = httpx.post(TOKEN_URL, timeout=20, data={
        "code": code, "client_id": settings.GOOGLE_CLIENT_ID, "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": _redirect_uri(request), "grant_type": "authorization_code"}).json()
    if "error" in tokens:  # for example invalid_client, invalid_grant, redirect_uri_mismatch
        logger.warning("Google connect: token exchange failed: %s", tokens)
        return _back("error", f"Google refused the code: {tokens.get('error')} ({tokens.get('error_description', 'no details')})")
    if "refresh_token" not in tokens:
        logger.warning("Google connect: no refresh token in response: %s", {k: v for k, v in tokens.items() if "token" not in k})
        return _back("error", "Google did not return a long-lived login; remove Codeonto from your Google account permissions and connect again")
    if BUSINESS_SCOPE not in (tokens.get("scope") or ""):
        granted = (tokens.get("scope") or "none").replace("https://www.googleapis.com/auth/", "")
        logger.warning("Google connect: Business Profile scope missing; granted: %s", granted)
        return _back("error", f"Google did not grant Business Profile access (granted: {granted}). "
                              "Add the business.manage scope under OAuth consent screen > Data access, then try again")
    email = httpx.get(USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"}, timeout=20).json().get("email")
    if not email:
        return _back("error", "Could not read the Google account email")

    conn, _ = GoogleConnection.objects.update_or_create(client=client, email=email, defaults={
        "refresh_token_enc": crypto.encrypt(tokens["refresh_token"]), "scopes": tokens.get("scope", ""),
        "status": "connected", "connected_by": request.user})
    label = f"c{client.id}-" + re.sub(r"[^a-z0-9]+", "-", email.split("@")[0].lower()).strip("-")
    account, _ = PlatformAccount.objects.update_or_create(platform_id="google", label=label, defaults={
        "client": client, "credentials_ref": f"db:google:{conn.id}", "is_active": True})
    if conn.account_id != account.id:
        conn.account = account
        conn.save(update_fields=["account"])
    _start_location_sync(label)
    return _back("connected")


def _start_location_sync(label: str) -> bool:
    """Discover a login's locations in the background (the collector job `google outlets`). Output goes to
    collector/logs/google-sync-<label>.log. False when this server has no collector set up."""
    collector = Path(settings.COLLECTOR_DIR)
    python = collector / ".venv" / "bin" / "python"
    if not python.exists():
        logger.warning("Google location sync for %s skipped: no collector virtualenv at %s", label, python)
        return False
    try:
        (collector / "logs").mkdir(exist_ok=True)
        log = open(collector / "logs" / f"google-sync-{label}.log", "ab")
        subprocess.Popen([str(python), str(collector / "run.py"), "google", "outlets", "--account", label], cwd=collector,
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        return True
    except OSError:
        logger.exception("Google location sync for %s could not start", label)
        return False


@api_view(["POST"])
def sync(request, pk):
    """Sync locations now for one connected Google account (same job as right after connecting)."""
    conn = GoogleConnection.objects.filter(pk=pk).select_related("account").first()
    if not conn:
        raise ValidationError("Connection not found")
    access.get_client(request.user, conn.client_id)
    access.require_manage(request.user)
    if conn.status != "connected" or not conn.account:
        raise ValidationError("Reconnect this Google account first")
    if not _start_location_sync(conn.account.label):
        return Response({"detail": "Location sync isn't set up on this server yet; ask Codeonto to finish the setup."}, status=503)
    return Response({"started": True})


@api_view(["GET"])
def client_connections(request, client_id):
    client = access.get_client(request.user, client_id)
    access.require_whole_client(request.user)
    rows = GoogleConnection.objects.filter(client=client).exclude(status="revoked").select_related("account")
    return Response({"configured": all(getattr(settings, n, "") for n in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_REDIRECT_URI", "GOOGLE_TOKEN_KEY")),
                     "connections": [_serialize(c) for c in rows]})


@api_view(["DELETE"])
def disconnect(request, pk):
    conn = GoogleConnection.objects.filter(pk=pk).select_related("account").first()
    if not conn:
        raise ValidationError("Connection not found")
    access.get_client(request.user, conn.client_id)
    access.require_manage(request.user)
    try:
        httpx.post(REVOKE_URL, params={"token": crypto.decrypt(conn.refresh_token_enc)}, timeout=20)
    except Exception:
        pass  # already revoked at Google, or the key changed: either way we forget it
    conn.refresh_token_enc, conn.status = "", "revoked"
    conn.save(update_fields=["refresh_token_enc", "status", "updated_at"])
    if conn.account:
        conn.account.is_active = False
        conn.account.save(update_fields=["is_active", "updated_at"])
    return Response({"status": "revoked"})
