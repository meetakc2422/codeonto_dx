"""Dining payouts for the Reconciliation page: what Zomato's consolidated dining report says each dining outlet earned,
what it kept as commission, and what is paid, pending or carried forward."""

from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Max, Min, Sum
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, outlet_ids
from apps.outlets.models import BrandOutlet

from .models import DiningPayoutTransaction as Tx

ZERO = Decimal("0")
PAID = {"SETTLED", "PAID", "PROCESSED", "COMPLETED"}


def _f(x) -> float:
    return float(x or ZERO)


@api_view(["GET"])
def brand_dining_payouts(request, brand_id):
    get_brand(request.user, brand_id)
    outlets = in_scope(BrandOutlet.objects.filter(brand_id=brand_id, is_active=True, zomato__is_dining=True), request.user, "id")
    ids = outlet_ids(request.query_params.get("outlet_id"))
    if ids:
        outlets = outlets.filter(id__in=ids)
    outlets = list(outlets.select_related("brand"))
    qs = Tx.objects.filter(outlet__in=outlets)
    start, end = request.query_params.get("start"), request.query_params.get("end")
    if start:
        qs = qs.filter(occurred_at__date__gte=start)
    if end:
        qs = qs.filter(occurred_at__date__lte=end)

    utr, status, of = request.query_params.get("utr"), request.query_params.get("status"), request.query_params.get("of")
    if utr or status or of:  # the bills behind one settlement (bank reference), one status (e.g. PENDING) or one outlet
        sel = qs.filter(utr_number=utr) if utr else qs.filter(settlement_status__iexact=status) if status else qs.filter(outlet_id=of)
        return Response({"bills": [{"id": t.transaction_id, "outlet": t.outlet.display_name if t.outlet else t.res_id, "at": t.occurred_at,
                                    "type": t.transaction_type, "discount_type": t.discount_type, "bill": _f(t.bill_amount), "cover_charge": _f(t.cover_charge),
                                    "commission": _f(t.commission_amount), "tax": _f(t.tax_on_commission), "adjustment": _f(t.adjustment),
                                    "net": _f(t.net_receivable), "status": t.settlement_status, "utr": t.utr_number, "remarks": t.remarks}
                                   for t in sel.select_related("outlet__brand").order_by("-occurred_at")[:500]],
                         "count": sel.count()})

    def totals(q):
        a = q.aggregate(n=Count("id"), bill=Sum("bill_amount"), commission=Sum("commission_amount"), tax=Sum("tax_on_commission"),
                        net=Sum("net_receivable"), first=Min("occurred_at"), last=Max("occurred_at"))
        return {"bills": a["n"], "bill_amount": _f(a["bill"]), "commission": _f(a["commission"]), "tax": _f(a["tax"]), "net_receivable": _f(a["net"]),
                "first": a["first"], "last": a["last"]}

    by_status = defaultdict(lambda: {"bills": 0, "net": 0.0})
    for r in qs.values("settlement_status").annotate(n=Count("id"), net=Sum("net_receivable")):
        s = (r["settlement_status"] or "UNKNOWN").upper()
        by_status[s]["bills"] += r["n"]; by_status[s]["net"] += _f(r["net"])
    rows = []
    for bo in outlets:
        o = qs.filter(outlet=bo)
        t = totals(o)
        paid = _f(o.filter(settlement_status__in=list(PAID) + [s.lower() for s in PAID]).aggregate(x=Sum("net_receivable"))["x"])
        rows.append({"outlet_id": bo.id, "name": bo.display_name, "res_id": bo.zomato_id, **t, "paid": paid, "unpaid": round(t["net_receivable"] - paid, 2)})
    settlements = [{"utr": r["utr_number"], "date": r["settlement_date"], "bills": r["n"], "amount": _f(r["net"])}
                   for r in qs.exclude(utr_number="").values("utr_number", "settlement_date").annotate(n=Count("id"), net=Sum("net_receivable")).order_by("-settlement_date")[:50]]
    recent = [{"id": t.transaction_id, "outlet": t.outlet.display_name if t.outlet else t.res_id, "at": t.occurred_at, "type": t.transaction_type,
               "bill": _f(t.bill_amount), "discount_type": t.discount_type, "commission": _f(t.commission_amount), "net": _f(t.net_receivable),
               "status": t.settlement_status, "utr": t.utr_number} for t in qs.select_related("outlet__brand").order_by("-occurred_at")[:100]]
    return Response({"has_dining": bool(outlets), "summary": totals(qs), "by_status": dict(by_status), "outlets": rows, "settlements": settlements, "recent": recent})
