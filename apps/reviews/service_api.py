"""Staff page: which clients and outlets get review replies sent to Zomato for them. Staff only; no row means no replies."""
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.outlets.access import is_staff
from apps.outlets.models import BrandOutlet, Client

from .models import ReplyService


def _staff(request):
    if not is_staff(request.user):
        raise PermissionDenied("Only Codeonto staff can manage the reply service.")


def _row(r: ReplyService, names: dict) -> dict:
    return {"id": r.id, "client_id": r.client_id, "client": r.client.name, "res_id": r.res_id,
            "outlet": names.get(r.res_id, "All Zomato outlets of this client") if r.res_id else "All Zomato outlets of this client",
            "mode": r.mode, "hold_risky": r.hold_risky, "instructions": r.instructions, "max_per_day": r.max_per_day,
            "is_active": r.is_active, "enabled_by": r.enabled_by, "updated_at": r.updated_at}


@api_view(["GET", "POST"])
def reply_service(request):
    _staff(request)
    outlets = list(BrandOutlet.objects.filter(is_active=True, zomato__isnull=False).select_related("brand")
                   .values("zomato_id", "outlet_name", "area", "city", "brand__client_id", "brand__name"))
    names = {o["zomato_id"]: f"{o['brand__name']} · {o['area'] or o['outlet_name']}" for o in outlets}
    if request.method == "POST":
        d = request.data
        client = Client.objects.filter(pk=d.get("client_id")).first()
        if not client:
            return Response({"detail": "Pick a client"}, status=400)
        res_id = str(d.get("res_id") or "").strip()
        if res_id and not any(o["zomato_id"] == res_id and o["brand__client_id"] == client.id for o in outlets):
            return Response({"detail": "That outlet doesn't belong to this client"}, status=400)
        mode = d.get("mode") if d.get("mode") in dict(ReplyService.MODES) else "manual"
        row, _ = ReplyService.objects.update_or_create(client=client, platform="zomato", res_id=res_id, defaults={
            "mode": mode, "hold_risky": bool(d.get("hold_risky", True)), "instructions": str(d.get("instructions") or "")[:2000],
            "max_per_day": max(1, min(int(d.get("max_per_day") or 60), 500)), "is_active": bool(d.get("is_active", True)),
            "enabled_by": request.user.get_username()})
        return Response(_row(row, names), status=201)
    rows = ReplyService.objects.select_related("client").all()
    clients = {}
    for o in outlets:
        clients.setdefault(o["brand__client_id"], []).append({"res_id": o["zomato_id"], "name": names[o["zomato_id"]]})
    return Response({"rows": [_row(r, names) for r in rows],
                     "clients": [{"id": c.id, "name": c.name, "outlets": clients.get(c.id, [])} for c in Client.objects.filter(is_active=True)]})


@api_view(["DELETE"])
def reply_service_delete(request, row_id: int):
    _staff(request)
    ReplyService.objects.filter(pk=row_id).delete()
    return Response({"ok": True})
