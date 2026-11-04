from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope

from .models import Alert


@api_view(["GET"])
def brand_alerts(request, brand_id):
    get_brand(request.user, brand_id)
    qs = in_scope(Alert.objects.filter(outlet__brand_id=brand_id), request.user).select_related("outlet__brand")
    qp = request.query_params
    if qp.get("outlet_id"):
        qs = qs.filter(outlet_id=qp["outlet_id"])
    if qp.get("status") == "resolved":
        qs = qs.filter(is_open=False)
    elif qp.get("status") != "all":
        qs = qs.filter(is_open=True)
    order = {"critical": 0, "warning": 1, "info": 2}
    rows = sorted(qs[:300], key=lambda a: (not a.is_open, order.get(a.severity, 3), -a.last_seen_at.timestamp()))
    return Response([{"id": a.id, "kind": a.kind, "severity": a.severity, "title": a.title, "detail": a.detail,
                      "is_open": a.is_open, "outlet_id": a.outlet_id, "outlet_name": a.outlet.display_name,
                      "first_seen_at": a.first_seen_at, "resolved_at": a.resolved_at} for a in rows])
