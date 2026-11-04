from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.outlets import access
from apps.outlets.models import BrandOutlet

from .access import subscription, unlocked
from .models import Invoice, Plan, PlanRequest, Subscription

GST_RATE = Decimal(str(getattr(settings, "BILLING_GST_PERCENT", 18)))


def quote(plan: Plan, cycle: str, outlets: int) -> dict | None:
    """Price before and after GST. None when the plan has no list price (contact us)."""
    if plan.price_per_outlet is None:
        return None
    months = 12 - plan.annual_free_months if cycle == "annual" else 1
    cents = Decimal("0.01")
    subtotal = (plan.price_per_outlet * outlets * months).quantize(cents, ROUND_HALF_UP)
    gst = (subtotal * GST_RATE / 100).quantize(cents, ROUND_HALF_UP)
    return {"plan": plan.code, "cycle": cycle, "outlets": outlets, "months_billed": months, "covers_months": 12 if cycle == "annual" else 1,
            "price_per_outlet": float(plan.price_per_outlet), "subtotal": float(subtotal), "gst_percent": float(GST_RATE),
            "gst": float(gst), "total": float(subtotal + gst)}


def _plan_json(p: Plan) -> dict:
    return {"code": p.code, "name": p.name, "description": p.description,
            "price_per_outlet": float(p.price_per_outlet) if p.price_per_outlet is not None else None,
            "annual_free_months": p.annual_free_months, "max_logins": p.max_logins, "features": p.features}


def _client_for_billing(request, client_id):
    """Owners see their own billing; staff see any client's."""
    client = access.get_client(request.user, client_id)
    access.require_manage(request.user)
    return client


@api_view(["GET"])
def plans(request):
    return Response([_plan_json(p) for p in Plan.objects.filter(is_active=True)])


@api_view(["GET"])
def plan_quote(request):
    qp = request.query_params
    plan = get_object_or_404(Plan, code=qp.get("plan"), is_active=True)
    cycle = qp.get("cycle") if qp.get("cycle") in ("monthly", "annual") else "monthly"
    try:
        outlets = max(1, min(int(qp.get("outlets") or 1), 10000))
    except ValueError:
        return Response({"detail": "outlets must be a number"}, status=400)
    return Response(quote(plan, cycle, outlets) or {"plan": plan.code, "cycle": cycle, "outlets": outlets, "total": None})


@api_view(["GET", "PATCH"])
def client_billing(request, client_id):
    """GET the plan, usage, requests and invoices.  PATCH (staff only) {plan, status, cycle, outlet_limit, trial_ends_on, current_period_end, notes}."""
    client = _client_for_billing(request, client_id)
    if request.method == "PATCH":
        if not access.is_staff(request.user):
            raise PermissionDenied("Only Codeonto staff can change a plan. Use Choose plan to ask for one.")
        d = request.data
        sub = subscription(client)
        plan = get_object_or_404(Plan, code=d["plan"]) if d.get("plan") else (sub.plan if sub else None)
        if plan is None:
            return Response({"detail": "Pick a plan"}, status=400)
        sub = sub or Subscription(client=client, plan=plan)
        sub.plan = plan
        for field, choices in (("status", Subscription.STATUS_CHOICES), ("cycle", Subscription.CYCLE_CHOICES)):
            if field in d:
                if d[field] not in dict(choices):
                    return Response({"detail": f"Unknown {field} '{d[field]}'"}, status=400)
                setattr(sub, field, d[field])
        try:
            if "outlet_limit" in d:
                sub.outlet_limit = int(d["outlet_limit"]) if d["outlet_limit"] not in (None, "") else None
            for field in ("trial_ends_on", "current_period_end"):
                if field in d:
                    setattr(sub, field, date.fromisoformat(d[field]) if d[field] else None)
        except ValueError:
            return Response({"detail": "Check the outlet limit and dates"}, status=400)
        if "notes" in d:
            sub.notes = str(d["notes"])[:2000]
        sub.save()
        if d.get("close_requests"):
            client.plan_requests.filter(is_open=True).update(is_open=False)
        client.refresh_from_db()
    sub = subscription(client)
    outlets_used = BrandOutlet.objects.filter(brand__client=client, brand__is_active=True, is_active=True).count()
    logins_used = client.members.filter(user__is_active=True).count()
    return Response({
        "client": {"id": client.id, "name": client.name},
        "subscription": None if sub is None else {
            **_plan_json(sub.plan), "plan": sub.plan.code, "status": sub.status, "cycle": sub.cycle, "outlet_limit": sub.outlet_limit,
            "trial_ends_on": sub.trial_ends_on, "current_period_end": sub.current_period_end, "notes": sub.notes if access.is_staff(request.user) else "",
            "trial_expired": sub.status == "trial" and bool(sub.trial_ends_on) and sub.trial_ends_on < date.today()},
        "usage": {"outlets": outlets_used, "logins": logins_used},
        "requests": [{"id": r.id, "plan": r.plan.name, "cycle": r.cycle, "outlets": r.outlets, "quoted_total": float(r.quoted_total) if r.quoted_total is not None else None,
                      "requested_by": r.requested_by.get_username() if r.requested_by else None, "created_at": r.created_at}
                     for r in client.plan_requests.filter(is_open=True).select_related("plan", "requested_by")],
        "invoices": [{"number": i.number, "period_start": i.period_start, "period_end": i.period_end, "subtotal": float(i.subtotal), "gst": float(i.gst),
                      "total": float(i.total), "status": i.status, "issued_on": i.issued_on, "paid_on": i.paid_on}
                     for i in Invoice.objects.filter(client=client).exclude(status="void")],
        "gateway_connected": False,
    })


@api_view(["POST"])
def request_plan(request, client_id):
    """{plan, cycle, outlets}. Stands in for checkout until a payment gateway is connected."""
    client = _client_for_billing(request, client_id)
    d = request.data
    plan = get_object_or_404(Plan, code=d.get("plan"), is_active=True)
    cycle = d.get("cycle") if d.get("cycle") in ("monthly", "annual") else "monthly"
    try:
        outlets = max(1, min(int(d.get("outlets") or 1), 10000))
    except (TypeError, ValueError):
        return Response({"detail": "outlets must be a number"}, status=400)
    q = quote(plan, cycle, outlets)
    r = PlanRequest.objects.create(client=client, plan=plan, cycle=cycle, outlets=outlets, quoted_total=q["total"] if q else None, requested_by=request.user)
    return Response({"id": r.id, "quote": q}, status=201)


def module_locks(client, modules) -> dict[str, bool]:
    return {m.code: not unlocked(client, m.code) for m in modules}
