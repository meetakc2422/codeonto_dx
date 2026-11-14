"""Staff page: see every Zomato / Swiggy session and refresh one by pasting a copied request (cURL) or session JSON.
Saving puts it in the database (encrypted); the Windows collector and this site both read it from there."""

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.outlets.access import is_staff
from apps.outlets.models import PlatformAccount

from . import sessions
from .models import PlatformSession, SessionRefresh

PLATFORMS = ("zomato", "swiggy")


def _staff(request):
    if not is_staff(request.user):
        raise PermissionDenied("Only Codeonto staff can manage platform sessions.")


def _row(s: PlatformSession | None) -> dict | None:
    return {"updated_at": s.updated_at, "updated_by": s.updated_by} if s else None


@api_view(["GET", "POST"])
def platform_sessions(request):
    _staff(request)
    if request.method == "POST":
        platform, kind = request.data.get("platform"), request.data.get("kind")
        if platform not in PLATFORMS or kind not in dict(PlatformSession.KINDS):
            return Response({"detail": "Unknown platform or kind"}, status=400)
        account = None
        if kind != "customer_app":
            account = PlatformAccount.objects.filter(pk=request.data.get("account_id"), platform_id=platform).first()
            if not account:
                return Response({"detail": "Pick the account this session belongs to"}, status=400)
        try:
            data = sessions.parse(platform, kind, request.data.get("text"), previous=sessions.get(platform, kind, account))
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        sessions.put(platform, kind, data, account=account, by=request.user.get_username())
        if kind == "merchant" and account.session_expired_at:  # a fresh login: no longer expired
            account.session_expired_at, account.session_error = None, ""
            account.save(update_fields=["session_expired_at", "session_error", "updated_at"])
        if kind == "merchant" and account.credentials_ref != "db:session":
            # from now on the collector reads this account's login from the database
            account.credentials_ref = "db:session"
            account.save(update_fields=["credentials_ref", "updated_at"])
        return Response({"ok": True})

    stored = {(s.platform, s.account_id, s.kind): s for s in PlatformSession.objects.all()}
    SessionRefresh.fail_stale()
    latest, latest_sync = {}, {}
    for r in SessionRefresh.objects.order_by("-requested_at"):
        (latest_sync if r.kind == SessionRefresh.OUTLETS else latest).setdefault(r.account_id, r)
    counts = _outlet_counts()
    accounts = []
    for a in PlatformAccount.objects.filter(platform_id__in=PLATFORMS, is_active=True).select_related("client").order_by("platform_id", "label"):
        accounts.append({"id": a.id, "platform": a.platform_id, "label": a.label, "client": str(a.client) if a.client else "Codeonto",
                         "is_active": a.is_active, "reads_from": "database" if a.credentials_ref.startswith("db:session") else "file" if a.credentials_ref else "—",
                         "merchant": _row(stored.get((a.platform_id, a.id, "merchant"))),
                         "merchant_app": _row(stored.get((a.platform_id, a.id, "merchant_app"))) if a.platform_id == "zomato" else None,
                         "expired_at": a.session_expired_at, "expired_reason": a.session_error,
                         "refresh": _refresh_row(latest.get(a.id)), "outlet_sync": _refresh_row(latest_sync.get(a.id)),
                         "outlets": counts.get((a.platform_id, a.id), 0), "last_synced_at": a.last_synced_at})
    from pathlib import Path
    customer = [{"platform": p, "session": _row(stored.get((p, None, "customer_app"))),
                 "file": Path(getattr(settings, f"{p.upper()}_APP_SESSION_FILE", "")).exists()} for p in PLATFORMS]
    return Response({"accounts": accounts, "customer_app": customer})


def _outlet_counts() -> dict:
    """How many active catalog outlets each login can see: {(platform, account_id): n}."""
    from django.db.models import Count

    from apps.outlets.models import SwiggyOutlet, ZomatoOutlet

    out = {}
    for platform, model in (("zomato", ZomatoOutlet), ("swiggy", SwiggyOutlet)):
        for row in model.objects.filter(is_active=True).values("account_id").annotate(n=Count("pk")):
            out[(platform, row["account_id"])] = row["n"]
    return out


def _refresh_row(r: SessionRefresh | None) -> dict | None:
    return {"id": r.id, "kind": r.kind, "result": r.result, "status": r.status, "requested_by": r.requested_by, "requested_at": r.requested_at, "started_at": r.started_at,
            "finished_at": r.finished_at, "worker": r.worker, "error": r.error} if r else None


@api_view(["POST"])
def refresh_session(request, account_id: int):
    """Queue a login refresh for one account; a collector worker on the Windows server runs it. Only one at a time per
    account: a second click while one is queued or running gets 409 with the one already in progress."""
    from django.db import IntegrityError, transaction

    _staff(request)
    account = PlatformAccount.objects.filter(pk=account_id, platform_id__in=PLATFORMS, is_active=True).first()
    if not account:
        return Response({"detail": "Unknown or inactive account"}, status=404)
    SessionRefresh.fail_stale()
    try:
        with transaction.atomic():
            r = SessionRefresh.objects.create(account=account, requested_by=request.user.get_username())
    except IntegrityError:
        active = SessionRefresh.objects.filter(account=account, status__in=SessionRefresh.ACTIVE).first()
        return Response({"detail": "A refresh for this login is already in progress", "refresh": _refresh_row(active)}, status=409)
    return Response({"ok": True, "refresh": _refresh_row(r)}, status=201)


@api_view(["POST"])
def sync_outlets(request, account_id: int):
    """Queue an outlet sync for one login: the collector worker asks Zomato / Swiggy which outlets it can access and updates the
    catalog (new ones appear under Add from catalog and Pick). Shares the one-at-a-time rule with login refreshes."""
    from django.db import IntegrityError, transaction

    _staff(request)
    account = PlatformAccount.objects.filter(pk=account_id, platform_id__in=PLATFORMS, is_active=True).first()
    if not account:
        return Response({"detail": "Unknown or inactive account"}, status=404)
    SessionRefresh.fail_stale()
    try:
        with transaction.atomic():
            r = SessionRefresh.objects.create(account=account, kind=SessionRefresh.OUTLETS, requested_by=request.user.get_username())
    except IntegrityError:
        active = SessionRefresh.objects.filter(account=account, status__in=SessionRefresh.ACTIVE).first()
        return Response({"detail": "A request for this login is already in progress", "refresh": _refresh_row(active)}, status=409)
    return Response({"ok": True, "refresh": _refresh_row(r)}, status=201)


@api_view(["GET"])
def session_alerts(request):
    """Expired logins, for the staff banner. Clients get an empty list."""
    if not is_staff(request.user):
        return Response({"expired": []})
    rows = PlatformAccount.objects.filter(platform_id__in=PLATFORMS, is_active=True, session_expired_at__isnull=False).order_by("session_expired_at")
    busy = set(SessionRefresh.objects.filter(status__in=SessionRefresh.ACTIVE).values_list("account_id", flat=True))
    return Response({"expired": [{"id": a.id, "platform": a.platform_id, "label": a.label, "expired_at": a.session_expired_at,
                                  "reason": a.session_error, "refreshing": a.id in busy} for a in rows]})
