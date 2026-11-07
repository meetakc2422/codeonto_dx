"""Staff page: see every Zomato / Swiggy session and refresh one by pasting a copied request (cURL) or session JSON.
Saving puts it in the database (encrypted); the Windows collector and this site both read it from there."""

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.outlets.access import is_staff
from apps.outlets.models import PlatformAccount

from . import sessions
from .models import PlatformSession

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
        if kind == "merchant" and account.credentials_ref != "db:session":
            # from now on the collector reads this account's login from the database
            account.credentials_ref = "db:session"
            account.save(update_fields=["credentials_ref", "updated_at"])
        return Response({"ok": True})

    stored = {(s.platform, s.account_id, s.kind): s for s in PlatformSession.objects.all()}
    accounts = []
    for a in PlatformAccount.objects.filter(platform_id__in=PLATFORMS, is_active=True).select_related("client").order_by("platform_id", "label"):
        accounts.append({"id": a.id, "platform": a.platform_id, "label": a.label, "client": str(a.client) if a.client else "Codeonto",
                         "is_active": a.is_active, "reads_from": "database" if a.credentials_ref.startswith("db:session") else "file" if a.credentials_ref else "—",
                         "merchant": _row(stored.get((a.platform_id, a.id, "merchant"))),
                         "merchant_app": _row(stored.get((a.platform_id, a.id, "merchant_app"))) if a.platform_id == "zomato" else None})
    from pathlib import Path
    customer = [{"platform": p, "session": _row(stored.get((p, None, "customer_app"))),
                 "file": Path(getattr(settings, f"{p.upper()}_APP_SESSION_FILE", "")).exists()} for p in PLATFORMS]
    return Response({"accounts": accounts, "customer_app": customer})
