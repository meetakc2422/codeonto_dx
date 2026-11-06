"""Statement lines (section + item) of a payout, normalised so the same line on different dates is one type."""

import re

AD_SECTIONS = {"investments_in_growth", "growth_investments_in_ads"}
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
