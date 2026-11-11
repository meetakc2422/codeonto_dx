"""Retries for live monitors (stock-outs): a store's check should never be lost to a passing network blip.

call()       one request: retries timeouts, dropped connections, 5xx and lost DB connections a few times, and waits
             longer on rate limits / firewall blocks. A dead login is not retried (it needs a new session).
fetch_all()  every store in parallel, then one more slow, one-at-a-time round for the stores that still failed.
"""

import time
from concurrent.futures import ThreadPoolExecutor

from . import config as cfg
from .common import log

ATTEMPTS = cfg.integer("STOCKOUT_RETRY_ATTEMPTS", 3)
WAITS = cfg.numbers("STOCKOUT_RETRY_WAIT_SEC", "3,10")          # between attempts on a network error
SLOW_WAITS = cfg.numbers("STOCKOUT_RATE_LIMIT_WAIT_SEC", "30,60")  # between attempts on 429 / blocked
ROUND_WAIT = cfg.integer("STOCKOUT_RETRY_ROUND_WAIT_SEC", 20)      # pause before re-trying the failed stores
GIVE_UP_AFTER = cfg.integer("STOCKOUT_RATE_LIMIT_GIVE_UP", 3)      # stores refused even after retries before the pass backs off


def is_transient(e: Exception) -> bool:
    """A failure that is likely gone in a few seconds."""
    if getattr(e, "transient", False):
        return True
    try:
        import requests

        if isinstance(e, (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError)):
            return True
        if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code >= 500:
            return True
    except ImportError:
        pass
    name = type(e).__name__
    return name in ("OperationalError", "InterfaceError", "TimeoutError", "ConnectionError", "ConnectionResetError")


def call(fn, what: str, slow: tuple = (), quiet: bool = False):
    """fn() with retries. `slow` are exception types (rate limit, firewall) that get the longer waits.
    quiet: log only the error type (for signed download links, whose URL must stay out of the logs)."""
    for attempt in range(ATTEMPTS):
        try:
            return fn()
        except Exception as e:
            if isinstance(e, slow):
                waits = SLOW_WAITS
            elif is_transient(e):
                waits = WAITS
            else:
                raise
            if attempt == ATTEMPTS - 1:
                raise
            wait = waits[min(attempt, len(waits) - 1)]
            log.warning("%s: %s%s; retry %s of %s in %ss", what, type(e).__name__, "" if quiet else f" ({str(e)[:160]})",
                        attempt + 1, ATTEMPTS - 1, wait)
            time.sleep(wait)


def fetch_all(stores: list, fetch_one, workers: int, what: str, slow: tuple = ()) -> list[tuple]:
    """[(store, result, error)] in the stores' order. Stores that still fail on a retryable error get one more go,
    one at a time, after a pause, so a short outage in the middle of a pass does not leave them unchecked."""

    import threading

    refused, lock = [], threading.Lock()

    def work(s):
        # the platform keeps refusing (rate limit / firewall): stop asking for this pass instead of making it worse
        if len(refused) >= GIVE_UP_AFTER:
            return s, None, refused[-1]
        try:
            return s, call(lambda: fetch_one(s), f"{what} {s.get('res_id')}", slow), None
        except Exception as e:
            if slow and isinstance(e, slow):
                with lock:
                    refused.append(e)
            return s, None, e

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(work, stores))
    again = [i for i, (_, _, e) in enumerate(results) if e is not None and (isinstance(e, slow) or is_transient(e))]
    if len(refused) >= GIVE_UP_AFTER:
        log.warning("%s: refused %s times even after waiting; backing off until the next cycle (%s stores not checked)",
                    what, len(refused), sum(1 for _, _, e in results if e is not None and isinstance(e, slow)))
        again = [i for i in again if not isinstance(results[i][2], slow)]
    if again:
        log.info("%s: %s stores failed; trying them again one at a time in %ss", what, len(again), ROUND_WAIT)
        time.sleep(ROUND_WAIT)
        for i in again:
            results[i] = work(results[i][0])
        still = sum(1 for i in again if results[i][2] is not None)
        log.info("%s: retry round recovered %s of %s", what, len(again) - still, len(again))
    return results
