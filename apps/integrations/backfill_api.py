"""Staff: load a brand's past reviews, business reports and payouts. The site only queues the request; a collector worker runs it
(collector/core/worker.py -> run_backfill.py), one backfill at a time, and reports progress back."""

from django.db import IntegrityError, transaction
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.outlets.access import get_brand, is_staff
from apps.outlets.models import BrandOutlet

from .models import BackfillRequest


def _staff(request):
    if not is_staff(request.user):
        raise PermissionDenied("Only SocialSpork staff can sync a brand's past data.")


def _row(r: BackfillRequest | None) -> dict | None:
    if not r:
        return None
    ahead = None
    if r.status == BackfillRequest.QUEUED:  # how many are in front: the one running now plus the older queued ones
        ahead = BackfillRequest.objects.filter(status=BackfillRequest.RUNNING).count() + BackfillRequest.objects.filter(
            status=BackfillRequest.QUEUED, requested_at__lt=r.requested_at).count()
    return {"id": r.id, "days": r.days, "status": r.status, "progress": r.progress, "result": r.result, "error": r.error, "requested_by": r.requested_by,
            "requested_at": r.requested_at, "started_at": r.started_at, "finished_at": r.finished_at, "ahead": ahead}


@api_view(["GET", "POST"])
def brand_backfill(request, brand_id: int):
    """GET: the latest request for this brand. POST {days: 30|90|180}: queue one; a second click while one is queued or running gets 409."""
    _staff(request)
    brand = get_brand(request.user, brand_id)
    BackfillRequest.fail_stale()
    if request.method == "GET":
        return Response({"backfill": _row(BackfillRequest.objects.filter(brand=brand).first())})
    try:
        days = int(request.data.get("days") or 90)
    except (TypeError, ValueError):
        days = 0
    if days not in BackfillRequest.DAYS:
        return Response({"detail": f"Choose {', '.join(str(d) for d in BackfillRequest.DAYS)} days."}, status=400)
    if not BrandOutlet.objects.filter(brand=brand, is_active=True).filter(zomato__isnull=False).exists() and \
            not BrandOutlet.objects.filter(brand=brand, is_active=True).filter(swiggy__isnull=False).exists():
        return Response({"detail": "This brand has no outlet with a Zomato or Swiggy ID yet. Map the outlets first."}, status=400)
    try:
        with transaction.atomic():
            r = BackfillRequest.objects.create(brand=brand, days=days, requested_by=request.user.get_username())
    except IntegrityError:
        active = BackfillRequest.objects.filter(brand=brand, status__in=BackfillRequest.ACTIVE).first()
        return Response({"detail": "A sync for this brand is already in progress", "backfill": _row(active)}, status=409)
    return Response({"ok": True, "backfill": _row(r)}, status=201)
