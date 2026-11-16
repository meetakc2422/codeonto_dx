"""The mobile app's sign-in (the token itself is in mobile_auth.py)."""
from django.contrib.auth import authenticate
from django.core.cache import cache
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .access import user_json
from .mobile_auth import TOKEN_DAYS, make_token

MAX_FAILS = 8  # wrong passwords per username in WINDOW seconds
WINDOW = 15 * 60


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_login(request):
    """{username, password} -> {token, user}. Wrong passwords are limited per username."""
    username = (request.data.get("username") or "").strip()
    key = f"mobile-login-fails:{username.lower()}"
    if cache.get(key, 0) >= MAX_FAILS:
        return Response({"detail": "Too many attempts. Try again in a few minutes."}, status=429)
    user = authenticate(request, username=username, password=request.data.get("password") or "")
    if not user:
        cache.set(key, cache.get(key, 0) + 1, WINDOW)
        return Response({"detail": "Wrong username or password"}, status=400)
    if not user.is_active:
        return Response({"detail": "This login is disabled"}, status=403)
    cache.delete(key)
    return Response({"token": make_token(user), "expires_days": TOKEN_DAYS, "user": user_json(user)})
