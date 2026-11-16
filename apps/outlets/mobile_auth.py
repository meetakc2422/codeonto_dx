"""Login for the mobile app: a signed token sent as `Authorization: Bearer <token>`.

The website keeps its session cookie. The app can't use that cleanly, so it signs in here and sends the token with every
request; the same access rules apply (a client sees only its own brands and outlets). A token is stateless: it carries the
user id and a fingerprint of the password, so changing the password signs the app out everywhere, and it expires after
TOKEN_DAYS."""
import hashlib

from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

SALT = "codeonto-mobile"
TOKEN_DAYS = 30


def _fingerprint(user) -> str:
    return hashlib.sha256(f"{user.pk}:{user.password}".encode()).hexdigest()[:16]


def make_token(user) -> str:
    return signing.dumps({"u": user.pk, "f": _fingerprint(user)}, salt=SALT)


class MobileTokenAuth(BaseAuthentication):
    """`Authorization: Bearer <token>`. Returns None (not an error) when the header is absent, so session logins still work."""

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        try:
            data = signing.loads(header[7:].strip(), salt=SALT, max_age=TOKEN_DAYS * 86400)
        except signing.BadSignature:
            raise AuthenticationFailed("Sign in again")
        user = get_user_model().objects.filter(pk=data.get("u"), is_active=True).first()
        if not user or data.get("f") != _fingerprint(user):
            raise AuthenticationFailed("Sign in again")
        return user, None
