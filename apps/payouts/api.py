from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope
from apps.billing.access import require_module

from .models import PayoutCycle

ISSUE_LABELS = {
    "payout_mismatch": "Payout doesn't match its orders",
    "order_count_mismatch": "Order count doesn't match the report",
    "unsettled_orders": "Paid, but orders are still unsettled",
    "order_payout_math": "An order's payout doesn't add up",
    "order_fee_math": "An order's service fee doesn't add up",
    "fee_rate_changed": "Base service fee % differs between orders",
    "paid_without_utr": "Paid, but has no UTR",
    "overdue": "Payout date has passed, not paid yet",
}


def _money(v):
    return float(v) if v is not None else None


def _is_paid(status: str) -> bool:
    return status.strip().upper() == "PAID"


def _is_due(status: str) -> bool:
    return status.strip().upper() == "TO BE PAID"


def _issues(c: PayoutCycle) -> list[str]:
    """The stored checks, plus overdue, which depends on today's date."""
    overdue = _is_due(c.status) and c.payout_date and c.payout_date < date.today()
    return [*c.issues, "overdue"] if overdue else list(c.issues)


def _filtered(request, brand_id):
    require_module(request.user, get_brand(request.user, brand_id), "reconciliation")
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)
    qs = in_scope(PayoutCycle.objects.filter(outlet__brand_id=brand_id, end_date__range=(start, end)), request.user)
    if qp.get("outlet_id"):
        qs = qs.filter(outlet_id=qp["outlet_id"])
    if qp.get("platform"):
        qs = qs.filter(platform_id=qp["platform"])
    return qs, qp


def _cycle_json(c: PayoutCycle) -> dict:
    return {"id": c.id, "outlet_id": c.outlet_id, "outlet": c.outlet.area or c.outlet.outlet_name, "city": c.outlet.city,
            "res_id": c.outlet.swiggy_id if c.platform_id == "swiggy" else c.outlet.zomato_id, "platform": c.platform_id, "start_date": c.start_date, "end_date": c.end_date,
            "payout_date": c.payout_date, "status": c.status, "utr": c.utr, "net_payout": _money(c.net_payout),
            "order_count": c.order_count, "orders_total": _money(c.orders_total), "adjustments": _money(c.adjustments),
            "expected_payout": _money(c.expected_payout), "discrepancy": _money(c.discrepancy),
            "reconciled": c.reconciled_at is not None, "issues": _issues(c)}


@api_view(["GET"])
def payout_summary(request, brand_id):
    qs, _ = _filtered(request, brand_id)
    cycles = list(qs.only("status", "net_payout", "discrepancy", "issues", "payout_date", "commissionable_total", "service_fee_total", "reconciled_at"))
    paid = [c for c in cycles if _is_paid(c.status)]
    with_issues = [c for c in cycles if _issues(c)]
    commissionable = sum((c.commissionable_total or 0) for c in cycles)
    fees = sum((c.service_fee_total or 0) for c in cycles)
    counts: dict[str, int] = {}
    for c in cycles:
        for code in _issues(c):
            counts[code] = counts.get(code, 0) + 1
    return Response({
        "cycles": len(cycles),
        "paid_total": _money(sum((c.net_payout or 0) for c in paid)),
        "zero_payouts": sum(1 for c in paid if not c.net_payout),
        "to_be_paid_total": _money(sum((c.net_payout or 0) for c in cycles if _is_due(c.status))),
        "to_be_paid_cycles": sum(1 for c in cycles if _is_due(c.status)),
        "carried_forward_cycles": sum(1 for c in cycles if c.status.strip().upper() == "CARRIED FORWARD"),
        "carried_forward_total": _money(sum((c.net_payout or 0) for c in cycles if c.status.strip().upper() == "CARRIED FORWARD")),
        "reconciled": sum(1 for c in cycles if c.reconciled_at),
        "with_issues": len(with_issues),
        "discrepancy_total": _money(sum(abs(c.discrepancy or 0) for c in cycles)),
        "take_rate": round(float(fees) / float(commissionable) * 100, 2) if commissionable else None,
        "issues": [{"code": k, "label": ISSUE_LABELS.get(k, k), "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])],
    })


@api_view(["GET"])
def payout_cycles(request, brand_id):
    qs, qp = _filtered(request, brand_id)
    qs = qs.select_related("outlet")
    status = qp.get("status")
    if status == "paid":
        qs = qs.filter(status__iexact="PAID")
    elif status == "to_be_paid":
        qs = qs.filter(status__iexact="TO BE PAID")
    rows = [_cycle_json(c) for c in qs]
    if status == "issues":
        rows = [r for r in rows if r["issues"]]
    if qp.get("q"):
        q = qp["q"].strip().lower()
        rows = [r for r in rows if q in (r["utr"] or "").lower() or q in r["outlet"].lower()]
    rows.sort(key=lambda r: (not r["issues"], -r["end_date"].toordinal(), r["outlet"]))
    offset, limit = int(qp.get("offset", 0)), min(int(qp.get("limit", 100)), 500)
    return Response({"total": len(rows), "results": rows[offset:offset + limit]})


@api_view(["GET"])
def payout_cycle_detail(request, brand_id, cycle_id):
    """What clicking a UTR opens: the platform's statement and every order in the payout."""
    require_module(request.user, get_brand(request.user, brand_id), "reconciliation")
    c = get_object_or_404(in_scope(PayoutCycle.objects.filter(outlet__brand_id=brand_id), request.user).select_related("outlet"), pk=cycle_id)
    return Response({
        **_cycle_json(c), "breakdown": c.breakdown, "delivered_orders": c.delivered_orders, "rejected_orders": c.rejected_orders,
        "issue_labels": ISSUE_LABELS,
        "orders": [{"order_id": o.order_id, "order_date": o.order_date, "status": o.status, "payment_mode": o.payment_mode,
                    "net_order_value": _money(o.net_order_value), "base_fee_pct": _money(o.base_fee_pct), "service_fee_pct": _money(o.service_fee_pct), "fees_total": _money(o.fees_total),
                    "government_charges": _money(o.government_charges), "other_deductions": _money(o.other_deductions), "net_deductions": _money(o.net_deductions),
                    "net_additions": _money(o.net_additions), "payout": _money(o.payout), "settlement_status": o.settlement_status,
                    "settlement_date": o.settlement_date, "unsettled_amount": _money(o.unsettled_amount), "issues": o.issues}
                   for o in c.orders.all()],
    })
