"""Google: every Business Profile location each login can manage -> google_locations.

For each login: list its Business accounts (agency, location groups, client accounts it was
added to), then every location in each account.
"""

import time

from core import outlets
from core.catalog import Outlet
from core.common import log

from .session import credentials_from

config = outlets.config

ACCOUNTS_URL = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
LOCATIONS_URL = "https://mybusinessbusinessinformation.googleapis.com/v1/{account}/locations"
READ_MASK = "name,title,storefrontAddress"


def _get(session, url: str, params: dict) -> dict:
    """GET with a few retries on rate limits (Business Profile quotas are low)."""
    for attempt in range(5):
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        if resp.status_code in (401, 403):
            detail = resp.json().get("error", {}).get("message", "") if resp.content else ""
            raise PermissionError(f"Google API refused access ({resp.status_code}): {detail}")
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()


def _pages(session, url: str, params: dict, key: str):
    token = None
    while True:
        data = _get(session, url, {**params, **({"pageToken": token} if token else {})})
        yield from data.get(key, [])
        token = data.get("nextPageToken")
        if not token:
            return


def _address(addr: dict) -> tuple[str, str]:
    lines = [*addr.get("addressLines", []), addr.get("sublocality", ""), addr.get("locality", ""),
             addr.get("administrativeArea", ""), addr.get("postalCode", "")]
    return ", ".join(x for x in lines if x), addr.get("locality", "")


def fetch(credentials: dict) -> list[Outlet]:
    from google.auth.transport.requests import AuthorizedSession

    session = AuthorizedSession(credentials_from(credentials))
    found: dict[str, Outlet] = {}
    for account in _pages(session, ACCOUNTS_URL, {"pageSize": 20}, "accounts"):
        n = 0
        for loc in _pages(session, LOCATIONS_URL.format(account=account["name"]),
                          {"readMask": READ_MASK, "pageSize": 100}, "locations"):
            location_id = loc["name"].split("/")[-1]
            if location_id in found:  # same location reachable through two accounts
                continue
            address, city = _address(loc.get("storefrontAddress") or {})
            found[location_id] = Outlet(external_id=location_id, name=loc.get("title") or location_id,
                                        city=city, address=address, business_account=account["name"])
            n += 1
        log.info("  %s (%s): %s locations", account.get("accountName", "?"), account["name"], n)
    return list(found.values())


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    return outlets.sync("google", accounts, fetch, force)
