"""The account owner's Team page: logins for their own client and which outlets each manager can see.
Codeonto staff can use it for any client."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from . import access
from .models import BrandOutlet, ClientUser

User = get_user_model()


def _member_json(m: ClientUser) -> dict:
    return {"id": m.user_id, "username": m.user.username, "name": m.user.get_full_name(), "email": m.user.email,
            "role": m.role, "is_active": m.user.is_active, "last_login": m.user.last_login,
            "outlet_ids": sorted(o.pk for o in m.outlets.all()) if m.is_outlet_limited else []}


def _client(request, client_id):
    client = access.get_client(request.user, client_id)
    access.require_manage(request.user)
    return client


def _outlets(client, ids) -> list[BrandOutlet]:
    """The outlets for these ids. Raises ValueError unless every id is an outlet of this client."""
    if not isinstance(ids, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
        raise ValueError("outlet_ids must be a list of outlet ids")
    found = list(BrandOutlet.objects.filter(pk__in=ids, brand__client=client))
    if len(found) != len(set(ids)):
        raise ValueError("Some of those outlets don't belong to this account")
    return found


@api_view(["GET", "POST"])
def team(request, client_id):
    """GET the logins and the outlets they can be given.  POST {username, name, email, password, role, outlet_ids}."""
    client = _client(request, client_id)
    if request.method == "GET":
        members = client.members.select_related("user").prefetch_related("outlets").order_by("user__username")
        brands = client.brands.filter(is_active=True).prefetch_related("outlets").order_by("name")
        return Response({
            "client": {"id": client.id, "name": client.name},
            "users": [_member_json(m) for m in members],
            "brands": [{"id": b.id, "name": b.name,
                        "outlets": [{"id": o.id, "name": o.area or o.outlet_name, "city": o.city, "zomato_id": o.zomato_id}
                                    for o in sorted(b.outlets.all(), key=lambda o: (o.city, o.area, o.outlet_name)) if o.is_active]}
                       for b in brands],
        })
    d = request.data
    username, password = (d.get("username") or "").strip(), d.get("password") or ""
    role = d.get("role") or "manager"
    if not username or not password:
        return Response({"detail": "Username and password are required"}, status=400)
    if role not in dict(ClientUser.ROLE_CHOICES):
        return Response({"detail": "Role must be admin, manager or viewer"}, status=400)
    if User.objects.filter(username__iexact=username).exists():
        return Response({"detail": f"Username '{username}' is taken"}, status=400)
    sub = getattr(client, "subscription", None)
    if sub and sub.plan.max_logins and not access.is_staff(request.user) and client.members.filter(user__is_active=True).count() >= sub.plan.max_logins:
        return Response({"detail": f"Your {sub.plan.name} plan includes {sub.plan.max_logins} logins. Disable one or upgrade under Billing."}, status=400)
    try:
        outlets = _outlets(client, d.get("outlet_ids", [])) if role == "manager" else []
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    if role == "manager" and not outlets:
        return Response({"detail": "Pick at least one outlet for this manager"}, status=400)
    first, _, last = (d.get("name") or "").strip().partition(" ")
    user = User(username=username, email=(d.get("email") or "").strip(), first_name=first, last_name=last)
    try:
        validate_password(password, user)
    except ValidationError as e:
        return Response({"detail": " ".join(e.messages)}, status=400)
    with transaction.atomic():
        user.set_password(password)
        user.save()
        m = ClientUser.objects.create(user=user, client=client, role=role)
        m.outlets.set(outlets)
    return Response(_member_json(m), status=201)


@api_view(["PATCH", "DELETE"])
def team_member(request, client_id, user_id):
    """PATCH {role?, outlet_ids?, is_active?, password?}. Everything is checked before anything is saved.
    DELETE removes the login (staff only; owners disable instead)."""
    client = _client(request, client_id)
    m = get_object_or_404(ClientUser.objects.select_related("user"), client=client, user_id=user_id)
    if (m.user.is_staff or m.user.is_superuser) and not access.is_staff(request.user):
        raise PermissionDenied("Only Codeonto staff can change this login.")
    if m.user_id == request.user.id:
        return Response({"detail": "You can't change your own login here. Use Profile to change your password."}, status=400)
    if request.method == "DELETE":
        if not access.is_staff(request.user):
            raise PermissionDenied("Only Codeonto staff can delete a login. You can disable it instead.")
        m.user.delete()
        return Response({"deleted": True})
    d = request.data
    role = d.get("role", m.role)
    if role not in dict(ClientUser.ROLE_CHOICES):
        return Response({"detail": "Role must be admin, manager or viewer"}, status=400)
    try:
        outlets = _outlets(client, d["outlet_ids"]) if "outlet_ids" in d else list(m.outlets.all())
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    if role == "manager" and not outlets:
        return Response({"detail": "Pick at least one outlet for this manager"}, status=400)
    if d.get("password"):
        try:
            validate_password(d["password"], m.user)
        except ValidationError as e:
            return Response({"detail": " ".join(e.messages)}, status=400)
    with transaction.atomic():
        m.role = role
        m.save(update_fields=["role", "updated_at"])
        m.outlets.set(outlets)
        if "is_active" in d:
            m.user.is_active = bool(d["is_active"])
        if d.get("password"):
            m.user.set_password(d["password"])
        m.user.save(update_fields=["is_active", "password"])
    return Response(_member_json(m))
