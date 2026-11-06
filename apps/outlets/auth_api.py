import logging
import threading

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db.models import Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .access import user_json
from .models import LoginCode

logger = logging.getLogger(__name__)
User = get_user_model()
RESET_MAILS_PER_HOUR = 3


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def me(request):
    """Current login, or 401. Also sets the CSRF cookie the dashboard sends back on writes."""
    if not request.user.is_authenticated:
        return Response({"detail": "Not logged in"}, status=401)
    return Response(user_json(request.user))


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    user = authenticate(request, username=(request.data.get("username") or "").strip(),
                        password=request.data.get("password") or "")
    if not user:
        return Response({"detail": "Wrong username or password"}, status=400)
    if not user.is_active:
        return Response({"detail": "This login is disabled"}, status=403)
    login(request, user)
    return Response(user_json(user))


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response({"ok": True})


@api_view(["POST"])
def change_password(request):
    """Change your own password. Keeps this session logged in; other sessions are signed out."""
    user = request.user
    new_password = request.data.get("new_password") or ""
    if not user.check_password(request.data.get("current_password") or ""):
        return Response({"detail": "Current password is wrong"}, status=400)
    if not new_password:
        return Response({"detail": "New password is required"}, status=400)
    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return Response({"detail": " ".join(e.messages)}, status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    update_session_auth_hash(request, user)
    return Response({"ok": True})


def _deliver(message: EmailMessage) -> None:
    try:
        message.send()
    except Exception:
        logger.exception("Could not send a password reset email")


def _send_in_background(message: EmailMessage) -> None:
    """Sending takes time only when the account exists, so waiting for it would reveal which accounts do."""
    threading.Thread(target=_deliver, args=(message,), daemon=True).start()


def _reset_message(request, user) -> EmailMessage:
    base = (settings.DASHBOARD_URL or request.build_absolute_uri("/")).rstrip("/")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    body = (f"Hi {user.get_full_name() or user.get_username()},\n\n"
            f"Use this link to choose a new password for your Codeonto login ({user.get_username()}):\n\n"
            f"{base}/#/reset?uid={uid}&token={token}\n\n"
            f"The link works once and expires in {settings.PASSWORD_RESET_TIMEOUT // 60} minutes. "
            "If you didn't ask for this, you can ignore this email and your password stays the same.\n")
    return EmailMessage("Reset your Codeonto password", body, None, [user.email])


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def forgot_password(request):
    """{identifier: username or email}. Always the same answer, so it can't be used to find out which accounts exist."""
    identifier = str(request.data.get("identifier") or "").strip()
    if identifier:
        users = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True).exclude(email="")
        for user in users:
            key = f"password-reset-mails:{user.pk}"
            cache.add(key, 0, 60 * 60)
            if cache.incr(key) <= RESET_MAILS_PER_HOUR and user.has_usable_password():
                _send_in_background(_reset_message(request, user))
    return Response({"ok": True})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def reset_password(request):
    """{uid, token, new_password}. Changing the password ends the link and signs the login out everywhere."""
    invalid = Response({"detail": "This link is invalid or has expired. Please request a new one."}, status=400)
    try:
        pk = force_str(urlsafe_base64_decode(str(request.data.get("uid") or "")))
        user = User.objects.filter(pk=int(pk), is_active=True).first()
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
        return invalid
    if not user or not default_token_generator.check_token(user, str(request.data.get("token") or "")):
        return invalid
    new_password = request.data.get("new_password") or ""
    if not new_password:
        return Response({"detail": "New password is required"}, status=400)
    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return Response({"detail": " ".join(e.messages)}, status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return Response({"ok": True})


# ---------- login with an emailed one-time code ----------
CODE_MINUTES = 10
CODE_ATTEMPTS = 5
CODES_PER_HOUR = 5
CODE_GAP_SECONDS = 60


def _code_hash(code: str) -> str:
    import hashlib
    import hmac
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def _code_users(identifier: str):
    return list(User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True).exclude(email=""))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def otp_request(request):
    """{identifier: email or username}. Emails a 6-digit login code. Always the same answer, so it can't be used to
    find out which accounts exist."""
    import secrets
    from datetime import timedelta

    from django.utils import timezone

    identifier = str(request.data.get("identifier") or "").strip()
    now = timezone.now()
    for user in _code_users(identifier) if identifier else []:
        recent = LoginCode.objects.filter(user=user, created_at__gte=now - timedelta(hours=1))
        if recent.count() >= CODES_PER_HOUR or recent.filter(created_at__gte=now - timedelta(seconds=CODE_GAP_SECONDS)).exists():
            continue
        code = f"{secrets.randbelow(10 ** 6):06d}"
        LoginCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)  # only the newest code works
        LoginCode.objects.create(user=user, code_hash=_code_hash(code), expires_at=now + timedelta(minutes=CODE_MINUTES))
        _send_in_background(EmailMessage(
            subject=f"{code} is your Codeonto login code",
            body=(f"Hi {user.first_name or user.username},\n\nYour Codeonto login code is {code}\n\n"
                  f"It works once and expires in {CODE_MINUTES} minutes. If you didn't try to sign in, you can ignore this email.\n"),
            to=[user.email]))
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([AllowAny])
def otp_verify(request):
    """{identifier, code}: signs in when the code matches that account's latest unused, unexpired code."""
    import hmac

    from django.utils import timezone

    identifier = str(request.data.get("identifier") or "").strip()
    code = "".join(ch for ch in str(request.data.get("code") or "") if ch.isdigit())
    now = timezone.now()
    users = _code_users(identifier) if identifier else []
    for user in users:
        lc = LoginCode.objects.filter(user=user, used_at__isnull=True, expires_at__gt=now).order_by("-created_at").first()
        if not lc:
            continue
        lc.attempts += 1
        if hmac.compare_digest(lc.code_hash, _code_hash(code)) and lc.attempts <= CODE_ATTEMPTS:
            lc.used_at = now
            lc.save(update_fields=["attempts", "used_at"])
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return Response(user_json(user))
        if lc.attempts >= CODE_ATTEMPTS:
            lc.used_at = now  # too many wrong guesses: this code is dead, ask for a new one
        lc.save(update_fields=["attempts", "used_at"])
    return Response({"detail": "That code is wrong or has expired. Ask for a new one."}, status=400)
