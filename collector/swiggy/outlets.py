"""Swiggy: every restaurant each account can access -> swiggy_outlets.

Uses the session saved by `run.py swiggy session` (found via the account's credentials_ref).
"""

from core import outlets
from core.catalog import Outlet
from core.common import ConfigError

from .session import list_restaurants

config = outlets.config


def fetch(credentials: dict) -> list[Outlet]:
    token = credentials.get("access_token")
    if not token:
        raise ConfigError("Session file has no access_token; run `run.py swiggy session` for this account")
    try:
        rows = list_restaurants(token, credentials.get("cookies") or {})
    except Exception as e:
        if getattr(getattr(e, "response", None), "status_code", None) in (401, 403):
            raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account") from e
        raise
    return [Outlet(external_id=r["rest_id"], name=(r.get("rest_name") or r["rest_id"]).strip(),
                   area=(r.get("area_name") or "").strip()) for r in rows]


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    return outlets.sync("swiggy", accounts, fetch, force)
