import json
from datetime import datetime
from pathlib import Path

import httpx
from django.conf import settings

from apps.integrations.connectors.base import Connector, NormalizedOrder, NormalizedReview, StoreStatus

_COMPOSER = "https://vhc-composer.swiggy.com/query"


class SwiggyConnector(Connector):
    """Swiggy partner portal (session based). Outlet id = Swiggy rest_id.

    Credentials: the session file written daily by the pipeline's swiggy_refresh_token_mn.py
    ({"access_token": ..., "cookies": {...}, "outlets": [...], "updated_at": ...}), via the
    account's credentials_ref (file:/path) or SWIGGY_SESSION_FILE.
    """

    platform_code = "swiggy"

    def __init__(self, credentials: dict):
        if not credentials and settings.SWIGGY_SESSION_FILE:
            path = Path(settings.SWIGGY_SESSION_FILE).expanduser()
            if path.exists():
                credentials = json.loads(path.read_text())
        super().__init__(credentials)

    def _client(self) -> httpx.Client:
        token = self.credentials.get("access_token")
        if not token:
            raise PermissionError("Swiggy session has no access_token; re-run the Swiggy session refresh")
        return httpx.Client(
            timeout=30,
            headers={"content-type": "application/json", "access_token": token},
            cookies=self.credentials.get("cookies") or {},
        )

    @staticmethod
    def _json(resp: httpx.Response) -> dict:
        if resp.status_code in (401, 403):
            raise PermissionError("Swiggy session expired or unauthorized; re-run the Swiggy session refresh")
        resp.raise_for_status()
        return resp.json()

    def fetch_reviews(self, listing_external_id: str, since: datetime | None) -> list[NormalizedReview]:
        raise NotImplementedError("swiggy: reviews request not wired yet")

    def fetch_orders(self, listing_external_id: str, since: datetime | None) -> list[NormalizedOrder]:
        raise NotImplementedError("swiggy: orders request not wired yet")

    def fetch_store_status(self, listing_external_id: str) -> StoreStatus:
        raise NotImplementedError("swiggy: store status request not wired yet")
