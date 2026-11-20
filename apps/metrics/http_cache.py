"""A short shared cache for a dashboard page's heavy read-only calls.

The Overview asks for ten things at once and each is a sum over thousands of daily rows. The answers move slowly (collectors write every
few hours), so the answer to the same question from the same person is kept for `seconds` and shared by every worker. The key holds the
person and the exact address (brand, dates, outlet and platform filters), so nobody is ever handed another person's answer. The view
itself still does its login and access checks on every miss; a revoked person can see their own cached answer for at most `seconds`."""

import hashlib
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response


def cached_get(seconds: int = 60):
    def decorate(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method != "GET" or not settings.RESPONSE_CACHE:
                return view(request, *args, **kwargs)
            key = "resp:" + hashlib.md5(f"{request.user.pk}|{request.get_full_path()}".encode()).hexdigest()
            hit = cache.get(key)
            if hit is not None:
                return Response(hit)
            response = view(request, *args, **kwargs)
            if response.status_code == 200:
                cache.set(key, response.data, seconds)
            return response
        return wrapper
    return decorate
