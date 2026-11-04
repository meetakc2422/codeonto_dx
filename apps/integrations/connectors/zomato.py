import json
from datetime import datetime
from pathlib import Path

import httpx

from django.conf import settings
from apps.integrations.connectors.base import Connector, NormalizedOrder, NormalizedReview, StoreStatus

_DEFAULT_GW = "https://api.zomato.com/merchant-gw/web"
_WEB = "https://www.zomato.com"


def _normalize_session(credentials: dict | list) -> dict:
    """Accept either our session shape or a raw cookie export and return our session shape."""
    if isinstance(credentials, dict) and "cookie" in credentials:
        return credentials
    if isinstance(credentials, dict) and "cookies" in credentials:
        credentials = credentials["cookies"]
    if isinstance(credentials, list):
        credentials = {c["name"]: c["value"] for c in credentials}
    if not credentials:
        return {}
    return {
        "cookie": "; ".join(f"{k}={v}" for k, v in credentials.items()),
        "csrf_token": credentials.get("csrf", ""),
        "mx_csrf_token": credentials.get("__Host-zmxcsrft", ""),
    }


class ZomatoConnector(Connector):
    """Zomato merchant dashboard (session based). listing external_id = Zomato res_id.

    Credentials, via platform_connections.credentials_ref, either:
      - {"cookie": "<Cookie header>", "csrf_token": "...", "mx_csrf_token": "..."}, or
      - a raw cookie export ({"name": "value"}, [{"name", "value"}] or {"cookies": [...]}),
        e.g. file:/.../zomato_cookies.json kept fresh by the pipeline's zomato_refresh_session.py.
    With no credentials_ref, falls back to ZOMATO_COOKIE_FILE from settings.
    """

    platform_code = "zomato"

    def __init__(self, credentials: dict):
        if not credentials and settings.ZOMATO_COOKIE_FILE:
            path = Path(settings.ZOMATO_COOKIE_FILE).expanduser()
            if path.exists():
                credentials = json.loads(path.read_text())
        super().__init__(_normalize_session(credentials))
        self.gw_url = (settings.ZOMATO_BASE_URL or _DEFAULT_GW).rstrip("/")

    def _client(self) -> httpx.Client:
        cookie = self.credentials.get("cookie")
        if not cookie:
            raise RuntimeError("Zomato connection has no session cookie")
        return httpx.Client(
            timeout=30,
            headers={
                "accept": "application/json, text/plain, */*",
                "content-type": "application/json",
                "cookie": cookie,
                "x-zomato-csrft": self.credentials.get("csrf_token", ""),
                "x-zomato-mx-csrf-token": self.credentials.get("mx_csrf_token", ""),
                "x-client-id": "zomato_web_merchant",
                "x-zomato-app-version": "2",
                "x-zomato-source-identifier": "merchant-dashboard",
                "origin": _WEB,
                "referer": f"{_WEB}/",
            },
        )

    @staticmethod
    def _json(resp: httpx.Response) -> dict:
        if resp.status_code in (401, 403):
            raise PermissionError("Zomato session expired or unauthorized; refresh the connection's cookies")
        resp.raise_for_status()
        return resp.json()

    # --- implemented: request formats confirmed from dashboard captures ---------------

    def post_reply(self, listing_external_id: str, external_review_id: str, body: str) -> None:
        with self._client() as c:
            self._json(c.post(
                f"{self.gw_url}/reviews/post/reply",
                json={"comment": body, "res_id": listing_external_id, "review_id": external_review_id},
            ))

    def fetch_review_details(self, listing_external_id: str, external_review_id: str) -> dict:
        """Raw review payload. Becomes a NormalizedReview once a sample response is mapped."""
        with self._client() as c:
            return self._json(c.get(
                f"{self.gw_url}/reviews/get/details",
                params={"res_id": listing_external_id, "review_id": external_review_id},
            ))

    def fetch_menu_raw(self, listing_external_id: str) -> dict:
        """Raw delivery menu incl. item stock flags. Feeds menu_items / stock_out_events once mapped."""
        with self._client() as c:
            return self._json(c.get(
                f"{_WEB}/php/online_ordering/menu_edit",
                params={"action": "get_content_menu", "res_id": listing_external_id,
                        "service_role": "DELIVERY_TAKEAWAY"},
            ))

    # --- pending: need the dashboard request that lists these ---------------------------

    def fetch_reviews(self, listing_external_id: str, since: datetime | None) -> list[NormalizedReview]:
        raise NotImplementedError("zomato: need the merchant dashboard 'reviews list' request to implement")

    def fetch_orders(self, listing_external_id: str, since: datetime | None) -> list[NormalizedOrder]:
        raise NotImplementedError("zomato: need the merchant dashboard 'order history' request to implement")

    def fetch_store_status(self, listing_external_id: str) -> StoreStatus:
        raise NotImplementedError("zomato: need the merchant dashboard 'outlet online status' request to implement")
