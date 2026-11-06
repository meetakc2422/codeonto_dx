from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, outlet_ids

from .models import ListingProfile


@api_view(["GET"])
def brand_listings(request, brand_id):
    get_brand(request.user, brand_id)
    qs = in_scope(ListingProfile.objects.filter(outlet__brand_id=brand_id), request.user).select_related("outlet__brand")
    if outlet_ids(request.query_params.get("outlet_id")):
        qs = qs.filter(outlet_id__in=outlet_ids(request.query_params.get("outlet_id")))
    if request.query_params.get("platform"):
        qs = qs.filter(platform_id=request.query_params["platform"])
    return Response([{
        "outlet_id": p.outlet_id, "outlet_name": p.outlet.display_name, "platform": p.platform_id, "title": p.title,
        "phone": p.phone, "website": p.website, "category": p.primary_category, "photo_count": p.photo_count,
        "last_post_at": p.last_post_at, "open_status": p.open_status, "health_score": p.health_score,
        "issues": p.issues, "fetched_at": p.fetched_at} for p in qs])
