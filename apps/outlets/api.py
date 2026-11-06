from functools import reduce
from operator import or_

from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.masters.models import Industry, Kpi, Platform

from apps.billing.access import unlocked

from . import access
from .catalog import CATALOGS
from .mapping import MappingConflict, MappingError, save_brand_outlets
from .models import Brand, BrandOutlet, Client


def _brand_json(b: Brand) -> dict:
    return {"id": b.id, "name": b.name, "client_id": b.client_id, "client": b.client.name,
            "industry_code": b.industry.code, "industry_name": b.industry.name, "is_active": b.is_active}


def _outlet_json(o: BrandOutlet) -> dict:
    return {"id": o.id, "outlet_name": o.outlet_name, "area": o.area, "city": o.city, "address": o.address,
            "is_active": o.is_active, **o.platform_ids(),
            "labels": {code: str(getattr(o, f)) for code, f in BrandOutlet.PLATFORM_FIELDS.items() if getattr(o, f)}}


@api_view(["GET"])
def industries(request):
    return Response([{"code": i.code, "name": i.name} for i in Industry.objects.filter(is_active=True)])


@api_view(["GET", "POST"])
def clients(request):
    if request.method == "POST":
        if not access.is_staff(request.user):
            raise PermissionDenied("Only Codeonto staff can create clients")
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "Client name is required"}, status=400)
        c = Client.objects.create(name=name, contact_name=request.data.get("contact_name", ""),
                                  contact_email=request.data.get("contact_email", ""))
        return Response({"id": c.id, "name": c.name}, status=201)
    return Response([{"id": c.id, "name": c.name} for c in access.clients_for(request.user)])


@api_view(["GET", "POST"])
def brands(request):
    if request.method == "POST":
        access.require_manage(request.user)
        name = (request.data.get("name") or "").strip()
        m = access.membership(request.user)
        client_id = request.data.get("client_id") if access.is_staff(request.user) else (m.client_id if m else None)
        client = access.get_client(request.user, client_id) if client_id else None
        industry = Industry.objects.filter(code=request.data.get("industry_code")).first()
        if not (name and client and industry):
            return Response({"detail": "name, client and industry are required"}, status=400)
        if Brand.objects.filter(client=client, name__iexact=name).exists():
            return Response({"detail": f"{client} already has a brand called '{name}'"}, status=400)
        b = Brand.objects.create(client=client, name=name, industry=industry)
        return Response(_brand_json(b), status=201)
    return Response([_brand_json(b) for b in access.brands_for(request.user).order_by("client__name", "name")])


@api_view(["GET", "PATCH"])
def brand_detail(request, brand_id):
    b = access.get_brand(request.user, brand_id, manage=request.method == "PATCH")
    if request.method == "PATCH":
        if "name" in request.data:
            name = (request.data["name"] or "").strip()
            if not name:
                return Response({"detail": "Brand name cannot be empty"}, status=400)
            if Brand.objects.filter(client=b.client, name__iexact=name).exclude(pk=b.pk).exists():
                return Response({"detail": f"{b.client} already has a brand called '{name}'"}, status=400)
            b.name = name
        if "industry_code" in request.data:
            b.industry = get_object_or_404(Industry, code=request.data["industry_code"])
        if "client_id" in request.data and int(request.data["client_id"]) != b.client_id:
            if not access.is_staff(request.user):
                raise PermissionDenied("Only Codeonto staff can move a brand to another client")
            if b.outlets.exclude(zomato=None, swiggy=None, google=None).exists():
                return Response({"detail": "Unmap this brand's ids before moving it to another client"}, status=400)
            b.client = access.get_client(request.user, request.data["client_id"])
        b.save()
    return Response(_brand_json(b))


@api_view(["GET"])
def brand_config(request, brand_id):
    """What the dashboard renders for this brand: its industry's modules + KPIs, and mapped platforms."""
    b = access.get_brand(request.user, brand_id)
    modules = list(b.industry.modules.filter(is_active=True).order_by("sort_order"))
    kpis = Kpi.objects.filter(module__in=modules, is_active=True).select_related("module")
    counts = access.in_scope(b.outlets.all(), request.user, "id").aggregate(**{code: Count(f, filter=Q(**{f"{f}__isnull": False}))
                                    for code, f in BrandOutlet.PLATFORM_FIELDS.items()})
    mapped = Platform.objects.filter(code__in=[c for c, n in counts.items() if n])
    return Response({
        "brand": _brand_json(b),
        "modules": [{"code": m.code, "name": m.name, "scope": m.scope, "locked": not access.is_staff(request.user) and not unlocked(b.client, m.code)}
                    for m in modules],
        "kpis": [{"code": k.code, "name": k.name, "unit": k.unit, "higher_is_better": k.higher_is_better,
                  "module": k.module.code} for k in kpis],
        "connected_platforms": [{"code": p.code, "name": p.name} for p in mapped],
    })


@api_view(["GET", "PUT"])
def brand_outlets(request, brand_id):
    b = access.get_brand(request.user, brand_id, manage=request.method == "PUT")
    if request.method == "PUT":
        try:
            result = save_brand_outlets(b, request.data.get("outlets", []), request.data.get("delete_ids", []),
                                        bool(request.data.get("move_conflicts")),
                                        assign_unowned=access.is_staff(request.user))
        except MappingError as e:
            return Response({"detail": str(e)}, status=400)
        except MappingConflict as e:
            return Response({"detail": "Some ids are already used in another store", "conflicts": e.conflicts},
                            status=status.HTTP_409_CONFLICT)
        return Response(result)
    qs = access.in_scope(b.outlets.select_related("zomato", "swiggy", "google"), request.user, "id").order_by("city", "outlet_name")
    return Response({"platforms": list(BrandOutlet.PLATFORM_FIELDS), "outlets": [_outlet_json(o) for o in qs]})


@api_view(["GET"])
def catalog(request, platform):
    """Ids a picker may offer. Always limited to one client's ids:
    the brand's client (?brand_id=), else the user's own client; staff without brand_id see all.
    ?q=  &unmapped=1  &limit=  &offset="""
    access.require_whole_client(request.user)
    if platform not in CATALOGS:
        return Response({"detail": f"No catalog for '{platform}'"}, status=404)
    model, pk, _, _ = CATALOGS[platform]
    qs = model.objects.select_related("brand_outlet__brand", "client")
    qp = request.query_params
    if qp.get("brand_id"):
        client_id = access.get_brand(request.user, int(qp["brand_id"])).client_id
        # staff may also pick unassigned ids (they get assigned to this client on save)
        qs = qs.filter(Q(client_id=client_id) | Q(client__isnull=True)) if access.is_staff(request.user) \
            else qs.filter(client_id=client_id)
    else:
        ids = access.visible_client_ids(request.user)
        if ids is not None:
            qs = qs.filter(client_id__in=ids)
    q = (qp.get("q") or "").strip()
    order = ["-is_active", "name", pk]
    if q:
        # every word is matched on its own (id, name, area, city); stores matching more words come first
        def hit(tok):
            cond = Q(**{f"{pk}__icontains": tok}) | Q(name__icontains=tok) | Q(city__icontains=tok)
            return cond | Q(area__icontains=tok) if hasattr(model, "area") else cond
        tokens = q.replace(",", " ").split()[:6]
        qs = qs.filter(reduce(or_, (hit(t) for t in tokens)))
        score = sum((Case(When(hit(t), then=1), default=0, output_field=IntegerField()) for t in tokens), Value(0))
        # ?boost= (the brand name) only ranks, it does not filter
        boosts = (qp.get("boost") or "").split()[:4]
        score = sum((Case(When(hit(t), then=1), default=0, output_field=IntegerField()) for t in boosts), score)
        qs = qs.annotate(match_score=score)
        order = ["-match_score", *order]
    if qp.get("unmapped") == "1":
        qs = qs.filter(brand_outlet__isnull=True, is_active=True)
    limit = min(int(qp.get("limit", 30)), 500)
    rows = []
    offset = max(int(qp.get("offset", 0)), 0)
    for o in qs.order_by(*order)[offset:offset + limit]:
        bo = getattr(o, "brand_outlet", None)
        rows.append({"id": getattr(o, pk), "name": o.name, "area": getattr(o, "area", ""), "city": o.city,
                     "is_active": o.is_active, "client": o.client.name if o.client else None,
                     "mapped_to": f"{bo.brand} · {bo.outlet_name}" if bo else None,
                     "mapped_outlet_id": bo.id if bo else None})
    return Response({"total": qs.count(), "results": rows})


@api_view(["POST"])
def import_outlets(request, brand_id):
    """Bulk CSV: {"csv": "<file text>", "commit": false} -> per-row preview; commit=true saves if no errors."""
    from .bulk import import_csv

    b = access.get_brand(request.user, brand_id, manage=True)
    text = request.data.get("csv") or ""
    if not text.strip():
        return Response({"detail": "Upload a CSV file"}, status=400)
    return Response(import_csv(b, text, bool(request.data.get("commit")), assign_unowned=access.is_staff(request.user)))


@api_view(["GET"])
def link_suggestions(request, brand_id):
    """Zomato-only and Swiggy-only rows of a brand that are probably the same kitchen, for someone to confirm."""
    from .linking import suggest

    b = access.get_brand(request.user, brand_id, manage=True)
    rows = list(access.in_scope(b.outlets.filter(is_active=True), request.user, "id")
                .values("id", "outlet_name", "area", "city", "zomato_id", "swiggy_id"))
    z = [r for r in rows if r["zomato_id"] and not r["swiggy_id"]]
    s = [r for r in rows if r["swiggy_id"] and not r["zomato_id"]]
    pairs = suggest(z, s)
    return Response({"zomato_only": len(z), "swiggy_only": len(s), "pairs": [
        {"zomato": p["zomato"], "swiggy": p["swiggy"], "score": p["score"], "sure": p["sure"]} for p in pairs]})
