"""Which modules a client's plan unlocks. Billing, not security: who sees what is still apps.outlets.access."""

from datetime import date

from rest_framework.exceptions import PermissionDenied

from apps.outlets.access import is_staff

ALWAYS_OPEN = {"overview"}  # so a lapsed account still lands somewhere and can reach billing


def subscription(client):
    return getattr(client, "subscription", None)


def unlocked(client, module_code: str) -> bool:
    sub = subscription(client)
    if sub is None or module_code in ALWAYS_OPEN:
        return True
    if sub.status == "cancelled" or (sub.status == "trial" and sub.trial_ends_on and sub.trial_ends_on < date.today()):
        return False
    return sub.plan.unlocks(module_code)


def require_module(user, brand, module_code: str) -> None:
    if not is_staff(user) and not unlocked(brand.client, module_code):
        raise PermissionDenied("Your plan doesn't include this. The account owner can upgrade under Billing.")
