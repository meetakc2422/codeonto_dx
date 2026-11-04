from datetime import datetime
from decimal import Decimal

import httpx

from apps.integrations.connectors.base import Connector, NormalizedReview

_STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
_BASE = "https://mybusiness.googleapis.com/v4"


class GoogleConnector(Connector):
    """Google Business Profile reviews.

    listing external_id = "accounts/{account_id}/locations/{location_id}"
    credentials = {"access_token": "..."} (OAuth token with business.manage scope)
    """

    platform_code = "google"

    def _headers(self) -> dict:
        token = self.credentials.get("access_token")
        if not token:
            raise RuntimeError("Google connection has no access_token")
        return {"Authorization": f"Bearer {token}"}

    def fetch_reviews(self, listing_external_id: str, since: datetime | None) -> list[NormalizedReview]:
        reviews: list[NormalizedReview] = []
        page_token = None
        with httpx.Client(timeout=30) as client:
            while True:
                params = {"pageSize": 50, "orderBy": "updateTime desc"}
                if page_token:
                    params["pageToken"] = page_token
                resp = client.get(f"{_BASE}/{listing_external_id}/reviews", headers=self._headers(), params=params)
                resp.raise_for_status()
                data = resp.json()
                for r in data.get("reviews", []):
                    updated = datetime.fromisoformat(r["updateTime"].replace("Z", "+00:00"))
                    if since and updated <= since:
                        return reviews  # sorted newest first, so the rest are already synced
                    reviews.append(
                        NormalizedReview(
                            external_review_id=r["reviewId"],
                            rating=Decimal(_STARS.get(r.get("starRating"), 0)) or None,
                            body=r.get("comment"),
                            reviewed_at=datetime.fromisoformat(r["createTime"].replace("Z", "+00:00")),
                            author_name=(r.get("reviewer") or {}).get("displayName"),
                            existing_reply=(r.get("reviewReply") or {}).get("comment"),
                            raw=r,
                        )
                    )
                page_token = data.get("nextPageToken")
                if not page_token:
                    return reviews

    def post_reply(self, listing_external_id: str, external_review_id: str, body: str) -> None:
        resp = httpx.put(
            f"{_BASE}/{listing_external_id}/reviews/{external_review_id}/reply",
            headers=self._headers(),
            json={"comment": body},
            timeout=30,
        )
        resp.raise_for_status()
