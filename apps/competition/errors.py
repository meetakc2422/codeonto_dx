"""What a person sees when Zomato, Swiggy or Google doesn't answer: one plain sentence. The real error (a library's text,
a host name, a missing setting) goes to the server log, never to the browser."""

import logging
import time

from rest_framework.response import Response

log = logging.getLogger(__name__)
FRIENDLY = "The platform didn't answer just now. Please try again in a moment."


def upstream_error(e: Exception, staff: bool = False) -> Response:
    """The plain sentence for everyone. SocialSpork staff also get the real reason after it, so a failure can be diagnosed from the page itself."""
    log.warning("competition upstream error: %s: %s", type(e).__name__, e)
    return Response({"detail": f"{FRIENDLY} [staff: {type(e).__name__}: {str(e)[:240]}]" if staff else FRIENDLY}, status=502)


RETRY_STATUS = {429, 502, 503, 504}  # "busy" answers worth one more try


def send_with_retry(send, retries: int = 1, pause: float = 0.7):
    """Run send() (one HTTP request that only reads or searches) and try once more after a short pause on a network error or a busy
    answer. Anything else (a refused session, a blocked address) is returned at once: asking again would not change it."""
    import httpx

    for attempt in range(retries + 1):
        try:
            resp = send()
        except httpx.HTTPError:
            if attempt == retries:
                raise
            time.sleep(pause)
            continue
        if resp.status_code in RETRY_STATUS and attempt < retries:
            time.sleep(pause)
            continue
        return resp
