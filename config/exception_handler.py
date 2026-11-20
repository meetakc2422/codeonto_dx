"""One place that turns an unexpected failure on the competition pages into a plain answer.

Those pages call Zomato, Swiggy and Google, whose answers change without warning. Our own errors are already caught where they happen
(ZomatoAppError, SwiggyAppError, PlacesError); anything else (an answer that isn't shaped as before, a missing key, bad text) used to
reach the browser as a bare 500. Now it is logged in full for us and the person gets one plain sentence with a 502 (not our bug in the
sense of a crashed page, but something upstream that did not answer in a usable way). Login, access and not-found answers pass through
untouched, and every other part of the API keeps Django's normal behaviour."""

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.competition.errors import FRIENDLY

log = logging.getLogger(__name__)


def handler(exc, context):
    response = drf_exception_handler(exc, context)  # DRF's own errors (401, 403, 404, 400 ...) are answered as always
    if response is not None:
        return response
    request = context.get("request")
    if request is not None and "/competition" in getattr(request, "path", ""):
        log.error("competition request failed: %s %s", request.method, request.path, exc_info=exc)
        return Response({"detail": FRIENDLY}, status=502)
    return None
