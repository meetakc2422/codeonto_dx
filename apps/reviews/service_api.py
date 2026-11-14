"""Staff page: which Zomato outlets (by res ID) get review replies sent to Zomato for them. Staff only; no row means no replies."""
import re

from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.outlets.access import is_staff
from apps.outlets.models import BrandOutlet

from .models import ReplyService


def _staff(request):
    if not is_staff(request.user):
        raise PermissionDenied("Only Codeonto staff can manage the reply service.")


def _outlets() -> dict[str, dict]:
    """Every mapped Zomato outlet by res ID, so a row can show which outlet it is (for reading only)."""
    rows = BrandOutlet.objects.filter(is_active=True, zomato__isnull=False).select_related("brand__client")
    return {o.zomato_id: {"name": f"{o.brand.name} · {o.area or o.outlet_name}", "city": o.city, "client": o.brand.client.name} for o in rows}


def _row(r: ReplyService, outlets: dict) -> dict:
    o = outlets.get(r.res_id)
    return {"id": r.id, "res_id": r.res_id, "outlet": o["name"] if o else "Not mapped to an outlet", "city": o["city"] if o else "",
            "client": o["client"] if o else "", "mapped": bool(o), "mode": r.mode, "hold_risky": r.hold_risky,
            "instructions": r.instructions, "max_per_day": r.max_per_day, "is_active": r.is_active, "enabled_by": r.enabled_by,
            "updated_at": r.updated_at}


@api_view(["GET", "POST"])
def reply_service(request):
    _staff(request)
    outlets = _outlets()
    if request.method == "POST":
        d = request.data
        raw = d.get("res_ids") if isinstance(d.get("res_ids"), list) else re.split(r"[\s,;]+", str(d.get("res_ids") or d.get("res_id") or ""))
        ids = list(dict.fromkeys(str(x).strip() for x in raw if str(x).strip()))
        if not ids:
            return Response({"detail": "Enter at least one Zomato res ID"}, status=400)
        unknown = [i for i in ids if i not in outlets]
        if unknown and not d.get("allow_unmapped"):
            return Response({"detail": f"Not mapped to any outlet: {', '.join(unknown[:15])}{' …' if len(unknown) > 15 else ''}. Map them on Brands & Outlets first.",
                             "unknown": unknown}, status=400)
        mode = d.get("mode") if d.get("mode") in dict(ReplyService.MODES) else "manual"
        saved = []
        for res_id in ids:
            row, _ = ReplyService.objects.update_or_create(platform="zomato", res_id=res_id, defaults={
                "mode": mode, "hold_risky": bool(d.get("hold_risky", True)), "instructions": str(d.get("instructions") or "")[:2000],
                "max_per_day": max(1, min(int(d.get("max_per_day") or 60), 500)), "is_active": bool(d.get("is_active", True)),
                "enabled_by": request.user.get_username()})
            saved.append(_row(row, outlets))
        return Response({"saved": saved}, status=201)
    return Response({"rows": [_row(r, outlets) for r in ReplyService.objects.all()]})


@api_view(["DELETE"])
def reply_service_delete(request, row_id: int):
    _staff(request)
    ReplyService.objects.filter(pk=row_id).delete()
    return Response({"ok": True})
