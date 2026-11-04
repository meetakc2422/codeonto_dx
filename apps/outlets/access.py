"""Who can see and change what. Every API view goes through these helpers.

Staff users (Codeonto) see every client. Everyone else sees only the client their ClientUser row points to:
admins see and manage all of it, viewers can read all of it but not change anything, and managers see only
their assigned outlets, where they can do day-to-day work but not change brands, mapping or the team.
"""

from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from .models import Brand, Client


def membership(user):
    return getattr(user, "client_membership", None)


def is_staff(user) -> bool:
    return bool(user and user.is_authenticated and user.is_staff)


def visible_client_ids(user) -> set[int] | None:
    """None = all clients (staff)."""
    if is_staff(user):
        return None
    m = membership(user)
    if not m:
        raise PermissionDenied("This login is not linked to a client yet. Ask Codeonto to add you.")
    return {m.client_id}


def outlet_limit(user) -> set[int] | None:
    """The only outlets this login may see. None = no limit within what its client allows."""
    if is_staff(user):
        return None
    m = membership(user)
    if not m:
        return set()
    if not m.is_outlet_limited:
        return None
    # the client check drops an assignment left behind if a brand or login later moves to another client
    return set(m.outlets.filter(brand__client_id=m.client_id).values_list("pk", flat=True))


def in_scope(qs, user, field: str = "outlet_id"):
    """Limit a queryset of outlets, or of rows belonging to an outlet, to what this login may see."""
    limit = outlet_limit(user)
    return qs if limit is None else qs.filter(**{f"{field}__in": limit})


def clients_for(user):
    ids = visible_client_ids(user)
    qs = Client.objects.filter(is_active=True)
    return qs if ids is None else qs.filter(pk__in=ids)


def brands_for(user):
    ids = visible_client_ids(user)
    qs = Brand.objects.filter(is_active=True).select_related("client", "industry")
    if ids is not None:
        qs = qs.filter(client_id__in=ids)
    limit = outlet_limit(user)
    return qs if limit is None else qs.filter(outlets__in=limit).distinct()


def require_manage(user) -> None:
    """Brands, outlet mapping, platform connections and the team: staff and client admins only."""
    if is_staff(user):
        return
    m = membership(user)
    if not m or not m.can_manage:
        raise PermissionDenied("Only the account owner can change this.")


def require_whole_client(user) -> None:
    """For views of client-wide data that a login limited to some outlets must not read."""
    if outlet_limit(user) is not None:
        raise PermissionDenied("Your login is limited to your assigned outlets.")


def require_outlet_edit(user, outlet_id: int) -> None:
    """Day-to-day work on one outlet, such as drafting a review reply."""
    if is_staff(user):
        return
    m = membership(user)
    if not m or not m.can_edit:
        raise PermissionDenied("Your role can view but not change this.")
    limit = outlet_limit(user)
    if limit is not None and outlet_id not in limit:
        raise Http404("Outlet not found")


def get_brand(user, brand_id: int, manage: bool = False) -> Brand:
    brand = brands_for(user).filter(pk=brand_id).first()
    if not brand:
        raise Http404("Brand not found")
    if manage:
        require_manage(user)
    return brand


def get_client(user, client_id) -> Client:
    client = clients_for(user).filter(pk=client_id).first()
    if not client:
        raise Http404("Client not found")
    return client


def user_json(user) -> dict:
    m = membership(user)
    return {
        "username": user.get_username(),
        "name": user.get_full_name() or user.get_username(),
        "email": user.email,
        "is_staff": user.is_staff,
        "client": {"id": m.client_id, "name": m.client.name} if m else None,
        "role": "staff" if user.is_staff else (m.role if m else None),
        "can_edit": is_staff(user) or bool(m and m.can_edit),
        "can_manage": is_staff(user) or bool(m and m.can_manage),
        "outlet_limited": outlet_limit(user) is not None,
    }
