"""Zomato: every outlet each account can access -> zomato_outlets.

Uses the cookie file saved by `run.py zomato session` (found via the account's credentials_ref).
"""

import json

from core import outlets
from core.catalog import Outlet
from core.common import ConfigError

config = outlets.config

FILTERS_URL = "https://api.zomato.com/merchant-gw/web/finance/get-filters"


def _cookies(credentials) -> dict:
    """Accept the flat {"name": "value"} file, [{"name", "value"}] or {"cookies": [...]}."""
    if isinstance(credentials, dict) and "cookies" in credentials:
        credentials = credentials["cookies"]
    if isinstance(credentials, list):
        credentials = {c["name"]: c["value"] for c in credentials}
    if not credentials:
        raise ConfigError("Cookie file is empty; run `run.py zomato session` for this account")
    return credentials


def fetch(credentials) -> list[Outlet]:
    import requests

    cookies = _cookies(credentials)
    resp = requests.post(
        FILTERS_URL, timeout=30,
        headers={
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
            "x-zomato-csrft": cookies.get("csrf", ""),
            "x-zomato-mx-csrf-token": cookies.get("__Host-zmxcsrft", ""),
            "x-client-id": "zomato_web_merchant",
            "x-zomato-source-identifier": "merchant_finance",
            "origin": "https://www.zomato.com",
            "referer": "https://www.zomato.com/",
        },
        json={"postbackParams": json.dumps({
            "start_date": "0001-01-01", "end_date": "0001-01-01",
            "config_postback_params": [{"entityType": "outlets", "entityIds": []}], "entity_ids": [],
        }, separators=(",", ":"))},
    )
    if resp.status_code in (401, 403):
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
    resp.raise_for_status()
    items = (((resp.json().get("filterConfig") or {}).get("views") or {}).get("outlets") or {}).get("items") or []
    result = []
    for x in items:
        if not x.get("id"):
            continue
        # subtitle: "Patrakar Puram, Lucknow | ID: 22319596"
        place = ((x.get("subtitle") or {}).get("value") or "").split("|")[0]
        parts = [p.strip() for p in place.split(",") if p.strip()]
        result.append(Outlet(external_id=str(x["id"]), name=((x.get("title") or {}).get("value") or str(x["id"])).strip(),
                             area=", ".join(parts[:-1]), city=parts[-1] if parts else ""))
    return result


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    return outlets.sync("zomato", accounts, fetch, force)
