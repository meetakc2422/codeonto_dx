"""What a person sees when Zomato, Swiggy or Google doesn't answer: one plain sentence. The real error (a library's text,
a host name, a missing setting) goes to the server log, never to the browser."""

import logging

from rest_framework.response import Response

log = logging.getLogger(__name__)
FRIENDLY = "The platform didn't answer just now. Please try again in a moment."


def upstream_error(e: Exception) -> Response:
    log.warning("competition upstream error: %s: %s", type(e).__name__, e)
    return Response({"detail": FRIENDLY}, status=502)
