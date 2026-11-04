from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.billing.access import require_module
from apps.outlets.access import get_brand, in_scope, require_outlet_edit

from .models import Complaint

# the platform's response window ends within this many hours: shown as "expiring soon"
EXPIRING_HOURS = 6


def _json(c: Complaint) -> dict:
    return {"id": c.id, "platform": c.platform_id, "outlet_id": c.outlet_id, "outlet_name": c.outlet.display_name,
            "order_id": c.order_id, "issue_type": c.issue_type, "issue_detail": c.issue_detail, "items": c.items,
            "customer_name": c.customer_name, "customer_context": c.customer_context, "platform_status": c.platform_status,
            "resolution": c.resolution, "refund_amount": float(c.refund_amount) if c.refund_amount is not None else None,
            "raised_at": c.raised_at, "expires_at": c.expires_at, "status": c.status, "note": c.note,
            "assigned_to": (c.assigned_to.get_full_name() or c.assigned_to.username) if c.assigned_to else None,
            "resolved_at": c.resolved_at}


def _filtered(request, brand_id):
    require_module(request.user, get_brand(request.user, brand_id), "tickets")
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)
    qs = in_scope(Complaint.objects.filter(outlet__brand_id=brand_id, raised_at__date__range=(start, end)), request.user)
    if qp.get("outlet_id"):
        qs = qs.filter(outlet_id=qp["outlet_id"])
    if qp.get("platform"):
        qs = qs.filter(platform_id=qp["platform"])
    return qs, qp


@api_view(["GET"])
def brand_complaints(request, brand_id):
    qs, qp = _filtered(request, brand_id)
    if qp.get("status"):
        qs = qs.filter(status=qp["status"])
    if qp.get("issue_type"):
        qs = qs.filter(issue_type=qp["issue_type"])
    if qp.get("q"):
        q = qp["q"]
        qs = qs.filter(Q(issue_detail__icontains=q) | Q(items__icontains=q) | Q(order_id__icontains=q) | Q(customer_name__icontains=q))
    offset, limit = int(qp.get("offset", 0)), min(int(qp.get("limit", 25)), 200)
    return Response([_json(c) for c in qs.select_related("outlet__brand", "assigned_to")[offset:offset + limit]])


@api_view(["GET"])
def complaints_summary(request, brand_id):
    qs, _ = _filtered(request, brand_id)
    now = timezone.now()
    totals = qs.aggregate(total=Count("id"), open=Count("id", filter=Q(status="open")),
                          in_progress=Count("id", filter=Q(status="in_progress")),
                          resolved=Count("id", filter=Q(status="resolved")), refunds=Sum("refund_amount"),
                          expiring=Count("id", filter=~Q(status="resolved") & Q(expires_at__gt=now,
                                                                              expires_at__lte=now + timedelta(hours=EXPIRING_HOURS))))
    totals["refunds"] = float(totals["refunds"] or 0)
    return Response({
        **totals,
        "by_issue": [{"issue_type": r["issue_type"] or "other", "count": r["count"], "refunds": float(r["refunds"] or 0)}
                     for r in qs.values("issue_type").annotate(count=Count("id"), refunds=Sum("refund_amount")).order_by("-count")],
        "by_outlet": [{"outlet_id": r["outlet_id"], "count": r["count"], "open": r["open"], "refunds": float(r["refunds"] or 0)}
                      for r in qs.values("outlet_id").annotate(count=Count("id"), open=Count("id", filter=~Q(status="resolved")),
                                                               refunds=Sum("refund_amount")).order_by("-count")[:20]],
    })


@api_view(["PATCH"])
def update_complaint(request, complaint_id):
    """The client's ticket on a complaint: {status?, note?}. Moving it to in_progress assigns it to whoever did."""
    c = get_object_or_404(Complaint.objects.select_related("outlet__brand", "assigned_to"), pk=complaint_id)
    require_module(request.user, get_brand(request.user, c.outlet.brand_id), "tickets")
    require_outlet_edit(request.user, c.outlet_id)
    status = request.data.get("status")
    if status is not None:
        if status not in dict(Complaint.STATUS_CHOICES):
            return Response({"detail": "Unknown status"}, status=400)
        if status == "in_progress" and not c.assigned_to_id:
            c.assigned_to = request.user
        c.resolved_at = timezone.now() if status == "resolved" else None
        c.status = status
    if "note" in request.data:
        c.note = (request.data.get("note") or "").strip()[:5000]
    c.save()
    return Response(_json(c))
