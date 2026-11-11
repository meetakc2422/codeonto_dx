from datetime import date, timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import Floor
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, is_staff, membership, outlet_ids, require_outlet_edit

from .models import Review, ReviewContact, ReviewContactView, ReviewReply

RATING_BANDS = {"neg": (1, 2), "mid": (3, 3), "pos": (4, 5)}


def can_contact(user) -> bool:
    """Reviewers' shared numbers: staff and the client's admins / managers (not view-only logins)."""
    m = membership(user)
    return is_staff(user) or bool(m and m.can_edit)


def _contact_hint(r: Review, allowed: bool) -> dict | None:
    c = getattr(r, "contact", None) if allowed else None
    return {"hint": c.hint} if c and c.shared and c.hint else None


def _review_json(r: Review, allowed: bool = False) -> dict:
    latest = r.replies.all()[0].body if r.replies.all() else None
    return {"contact": _contact_hint(r, allowed), "order_id": (r.raw or {}).get("order_id") if allowed and isinstance(r.raw, dict) else None,
            "id": r.id, "rating": float(r.rating) if r.rating is not None else None, "title": r.title,
            "body": r.body, "author_name": r.author_name, "reviewed_at": r.reviewed_at, "sentiment": r.sentiment,
            "reply_status": r.reply_status, "platform": r.platform_id, "outlet_id": r.outlet_id,
            "outlet_name": r.outlet.display_name, "latest_reply": latest}


@api_view(["GET"])
def brand_reviews(request, brand_id):
    get_brand(request.user, brand_id)
    qp = request.query_params
    qs = (in_scope(Review.objects.filter(outlet__brand_id=brand_id), request.user)
          .select_related("outlet__brand", "contact").prefetch_related("replies"))
    if outlet_ids(qp.get("outlet_id")):
        qs = qs.filter(outlet_id__in=outlet_ids(qp.get("outlet_id")))
    if qp.get("platform"):
        qs = qs.filter(platform_id=qp["platform"])
    if qp.get("rating") in RATING_BANDS:
        lo, hi = RATING_BANDS[qp["rating"]]
        qs = qs.filter(rating__gte=lo, rating__lte=hi)
    if qp.get("reply_status"):
        qs = qs.filter(reply_status=qp["reply_status"])
    if qp.get("q"):
        qs = qs.filter(body__icontains=qp["q"])
    offset, limit = int(qp.get("offset", 0)), min(int(qp.get("limit", 25)), 200)
    if qp.get("contact") == "shared":
        qs = qs.filter(contact__shared=True)
    allowed = can_contact(request.user)
    return Response([_review_json(r, allowed) for r in qs[offset:offset + limit]])


@api_view(["GET"])
def reviews_summary(request, brand_id):
    get_brand(request.user, brand_id)
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)
    qs = in_scope(Review.objects.filter(outlet__brand_id=brand_id, reviewed_at__date__range=(start, end)), request.user)
    if outlet_ids(qp.get("outlet_id")):
        qs = qs.filter(outlet_id__in=outlet_ids(qp.get("outlet_id")))
    if qp.get("platform"):
        qs = qs.filter(platform_id=qp["platform"])
    totals = qs.aggregate(total=Count("id"), avg_rating=Avg("rating"),
                          replied=Count("id", filter=Q(reply_status="replied")),
                          pending=Count("id", filter=Q(reply_status="pending")),
                          negative=Count("id", filter=Q(rating__lte=2)))
    totals["avg_rating"] = round(float(totals["avg_rating"]), 2) if totals["avg_rating"] is not None else None
    return Response({
        **totals,
        "by_rating": list(qs.annotate(stars=Floor("rating")).values("stars").annotate(count=Count("id")).order_by("-stars")),
        "by_platform": [{"platform": r["platform_id"], "count": r["count"],
                         "avg_rating": round(float(r["avg"]), 2) if r["avg"] is not None else None}
                        for r in qs.values("platform_id").annotate(count=Count("id"), avg=Avg("rating")).order_by("-count")],
        "by_outlet": [{"outlet_id": r["outlet_id"], "count": r["count"], "negative": r["negative"], "pending": r["pending"],
                       "avg_rating": round(float(r["avg"]), 2) if r["avg"] is not None else None}
                      for r in qs.values("outlet_id").annotate(count=Count("id"), avg=Avg("rating"),
                                                               negative=Count("id", filter=Q(rating__lte=2)),
                                                               pending=Count("id", filter=Q(reply_status="pending")))
                                                     .order_by("-negative", "-count")[:30]],
    })


@api_view(["POST"])
def create_reply(request, review_id):
    review = get_object_or_404(Review.objects.select_related("outlet"), pk=review_id)
    get_brand(request.user, review.outlet.brand_id)
    require_outlet_edit(request.user, review.outlet_id)
    body = (request.data.get("body") or "").strip()
    if not body:
        return Response({"detail": "Reply text is required"}, status=400)
    reply = ReviewReply.objects.create(review=review, body=body, source=request.data.get("source", "manual"))
    if review.reply_status == "pending":
        review.reply_status = "drafted"
        review.save(update_fields=["reply_status", "updated_at"])
    return Response({"id": reply.id, "status": reply.status, "body": reply.body}, status=201)


@api_view(["POST"])
def reveal_contact(request, review_id):
    """The full number behind a review's hint. Every reveal is logged."""
    from apps.integrations.crypto import decrypt

    review = get_object_or_404(in_scope(Review.objects.select_related("outlet"), request.user), pk=review_id)
    get_brand(request.user, review.outlet.brand_id)
    if not can_contact(request.user):
        return Response({"detail": "Your role can't see customer numbers."}, status=403)
    contact = ReviewContact.objects.filter(review=review, shared=True).exclude(phone_enc="").first()
    if not contact:
        return Response({"detail": "This customer hasn't shared a number."}, status=404)
    action = request.data.get("action") if request.data.get("action") in ("view", "whatsapp") else "view"
    ReviewContactView.objects.create(contact=contact, user=request.user, action=action)
    return Response({"phone": decrypt(contact.phone_enc)})
