"""Statement lines (section + item) of a payout, normalised so the same line on different dates is one type."""

import re

AD_SECTIONS = {"investments_in_growth", "investments_in_growth_v2", "growth_investments_in_ads"}
ORDER_SECTIONS = {"total_order_value", "total_customer_paid", "total_fees", "total_taxes", "order_level_deductions", "tax_deductions",
                  "additions", "complaint_cancellation_charges"}


def norm(label: str) -> str:
    return re.sub(r"\d+", "#", (label or "").strip())[:255]


def lines(cycle):
    """(section id, section label, normalised item label, item label as shown, value) for every non-zero item."""
    for s in cycle.breakdown or []:
        for i in s.get("items") or []:
            try:
                v = float(i.get("value") or 0)
            except (TypeError, ValueError):
                continue
            if v:
                yield s.get("id") or "", s.get("label") or "", norm(i.get("label")), i.get("label") or "", v


def guess_kind(section: str, label: str) -> str:
    if section in AD_SECTIONS or re.search(r"\bads?\b|advert|topical|promoted", label, re.I):
        return "ad"
    return "order" if section in ORDER_SECTIONS else "deduction"


# The sections both platforms' statements are known to have. Lines inside them are expected: they never need a person's
# review, except one that reads like advertising outside the ad sections (that decides what counts as ad spend).
KNOWN_SECTIONS = ORDER_SECTIONS | AD_SECTIONS | {
    # Zomato's current statement layout
    "gross_order_value", "discounts_and_promotions", "net_order_value_subtotal", "service_fee", "tax_deductions_v2",
    "refunds_and_additions", "penalties_and_other_deductions", "food_delivery_statement_subtotal", "hyperpure_purchases",
    "previous_settlements", "est_net_payout_soa_v2", "misc_deductions", "carried_forward",
}
_AD_LOOK = re.compile(r"\bads?\b|advert|topical|promoted", re.I)


def needs_review(section: str, label: str) -> bool:
    """False for an expected line in a known section; True for anything in a section we have not seen, or an ad-like
    line outside the ad sections."""
    if section not in KNOWN_SECTIONS:
        return True
    return section not in AD_SECTIONS and bool(_AD_LOOK.search(label or "")) and section != "previous_settlements"
