"""Every platform connector converts its API's data into these shapes.

The rest of the app only ever sees these dataclasses, so adding a platform
means writing one Connector subclass and registering it.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class NormalizedReview:
    external_review_id: str
    rating: Decimal | None
    body: str | None
    reviewed_at: datetime
    author_name: str | None = None
    title: str | None = None
    existing_reply: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class NormalizedOrder:
    external_order_id: str
    placed_at: datetime
    status: str                       # placed/accepted/ready/picked_up/delivered/cancelled/rejected
    order_value: Decimal | None = None
    item_total: Decimal | None = None
    discount_restaurant: Decimal | None = None
    discount_platform: Decimal | None = None
    commission: Decimal | None = None
    expected_payout: Decimal | None = None
    prep_time_sec: int | None = None
    is_delayed: bool | None = None
    cancelled_by: str | None = None
    cancel_reason: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class StoreStatus:
    is_online: bool
    checked_at: datetime
    reason: str | None = None


class Connector:
    platform_code: str = ""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    def fetch_reviews(self, listing_external_id: str, since: datetime | None) -> list[NormalizedReview]:
        raise NotImplementedError(f"{self.platform_code}: fetch_reviews not implemented")

    def post_reply(self, listing_external_id: str, external_review_id: str, body: str) -> None:
        raise NotImplementedError(f"{self.platform_code}: post_reply not implemented")

    def fetch_orders(self, listing_external_id: str, since: datetime | None) -> list[NormalizedOrder]:
        raise NotImplementedError(f"{self.platform_code}: fetch_orders not implemented")

    def fetch_store_status(self, listing_external_id: str) -> StoreStatus:
        raise NotImplementedError(f"{self.platform_code}: fetch_store_status not implemented")

    def set_store_online(self, listing_external_id: str) -> None:
        raise NotImplementedError(f"{self.platform_code}: set_store_online not implemented")
