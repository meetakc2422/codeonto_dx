"""Client management for Codeonto staff (the dashboard's Client management section)."""

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import Client, GoogleLocation, SwiggyOutlet, ZomatoOutlet

# platform code -> (catalog model, id field, extra column)
ID_PLATFORMS = {
    "zomato": (ZomatoOutlet, "res_id", "area"),
    "swiggy": (SwiggyOutlet, "swiggy_id", "area"),
    "google": (GoogleLocation, "location_id", "address"),
}


class IsStaff(BasePermission):
    message = "Only Codeonto staff can manage clients"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


def _client_json(c: Client, counts: bool = True) -> dict:
    data = {"id": c.id, "name": c.name, "contact_name": c.contact_name, "contact_email": c.contact_email,
            "contact_phone": c.contact_phone, "is_active": c.is_active}
    if counts:
        data.update({"brands": c.n_brands, "users": c.n_users,
                     "ids": {"zomato": c.n_zomato, "swiggy": c.n_swiggy, "google": c.n_google}})
    return data


def _with_counts(qs):
    return qs.annotate(
        n_brands=Count("brands", distinct=True), n_users=Count("members", distinct=True),
        n_zomato=Count("zomatooutlet_set", distinct=True), n_swiggy=Count("swiggyoutlet_set", distinct=True),
        n_google=Count("googlelocation_set", distinct=True),
    )


def _fields(data: dict) -> dict:
    out = {k: (data.get(k) or "").strip() for k in ("name", "contact_name", "contact_email", "contact_phone") if k in data}
    if "is_active" in data:
        out["is_active"] = bool(data["is_active"])
    return out


@api_view(["GET", "POST"])
@permission_classes([IsStaff])
def clients(request):
    if request.method == "POST":
        fields = _fields(request.data)
        if not fields.get("name"):
            return Response({"detail": "Client name is required"}, status=400)
        if Client.objects.filter(name__iexact=fields["name"]).exists():
            return Response({"detail": f"A client called '{fields['name']}' already exists"}, status=400)
        c = Client.objects.create(**fields)
        return Response(_client_json(_with_counts(Client.objects.filter(pk=c.pk)).get()), status=201)
    qs = _with_counts(Client.objects.all()).order_by("-is_active", "name")
    q = (request.query_params.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(contact_name__icontains=q) | Q(contact_email__icontains=q))
    unassigned = {code: m.objects.filter(client__isnull=True, is_active=True).count()
                  for code, (m, _, _) in ID_PLATFORMS.items()}
    return Response({"clients": [_client_json(c) for c in qs], "unassigned_ids": unassigned})


@api_view(["GET", "PATCH"])
@permission_classes([IsStaff])
def client_detail(request, client_id):
    c = get_object_or_404(_with_counts(Client.objects.all()), pk=client_id)
    if request.method == "PATCH":
        fields = _fields(request.data)
        if "name" in fields and not fields["name"]:
            return Response({"detail": "Client name cannot be empty"}, status=400)
        if fields.get("name") and Client.objects.filter(name__iexact=fields["name"]).exclude(pk=c.pk).exists():
            return Response({"detail": f"A client called '{fields['name']}' already exists"}, status=400)
        Client.objects.filter(pk=c.pk).update(**fields)
        c = _with_counts(Client.objects.all()).get(pk=c.pk)
    brands = c.brands.annotate(n_outlets=Count("outlets")).select_related("industry").order_by("name")
    users = c.members.select_related("user").order_by("user__username")
    return Response({
        **_client_json(c),
        "brand_list": [{"id": b.id, "name": b.name, "industry": b.industry.name, "stores": b.n_outlets,
                        "is_active": b.is_active} for b in brands],
        "user_list": [{"id": m.user_id, "username": m.user.username, "name": m.user.get_full_name(),
                       "email": m.user.email, "role": m.role, "is_active": m.user.is_active,
                       "last_login": m.user.last_login} for m in users],
    })


@api_view(["GET", "POST"])
@permission_classes([IsStaff])
def client_ids(request, client_id, platform):
    """GET ?scope=available|owned&q=&page=  ·  POST {"op": "assign"|"remove", "ids": [...]}"""
    c = get_object_or_404(Client, pk=client_id)
    if platform not in ID_PLATFORMS:
        return Response({"detail": f"Unknown platform '{platform}'"}, status=404)
    model, pk, extra = ID_PLATFORMS[platform]

    if request.method == "POST":
        ids = [str(i) for i in request.data.get("ids") or []]
        op = request.data.get("op")
        if not ids or op not in ("assign", "remove"):
            return Response({"detail": "Send op (assign/remove) and ids"}, status=400)
        if op == "assign":
            done = model.objects.filter(pk__in=ids, client__isnull=True).update(client=c)
            return Response({"done": done, "skipped": len(ids) - done,
                             "message": f"Assigned {done} IDs to {c}"
                                        + (f"; {len(ids) - done} skipped (already belong to a client)" if done < len(ids) else "")})
        in_use = model.objects.filter(pk__in=ids, client=c, brand_outlet__isnull=False).count()
        done = model.objects.filter(pk__in=ids, client=c, brand_outlet__isnull=True).update(client=None)
        return Response({"done": done, "skipped": in_use,
                         "message": f"Removed {done} IDs from {c}"
                                    + (f"; {in_use} kept because a store uses them" if in_use else "")})

    qp = request.query_params
    if qp.get("scope") == "owned":
        qs = model.objects.filter(client=c).select_related("brand_outlet__brand")
    else:
        qs = model.objects.filter(client__isnull=True, is_active=True)
    q = (qp.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(**{f"{pk}__icontains": q}) | Q(name__icontains=q) | Q(city__icontains=q)
                       | Q(**{f"{extra}__icontains": q}))
    page = Paginator(qs.order_by("-is_active", "name", "city"), 100).get_page(qp.get("page"))
    rows = []
    for o in page:
        bo = getattr(o, "brand_outlet", None) if qp.get("scope") == "owned" else None
        rows.append({"id": getattr(o, pk), "name": o.name, "extra": getattr(o, extra), "city": o.city,
                     "is_active": o.is_active, "store": f"{bo.brand} · {bo.outlet_name}" if bo else None})
    return Response({"total": page.paginator.count, "page": page.number, "pages": page.paginator.num_pages,
                     "extra_label": extra.title(), "results": rows})
