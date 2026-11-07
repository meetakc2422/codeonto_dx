"""Alert settings for a client: who gets WhatsApp / email alerts, for which brands or outlets, which alert types, and
quiet hours. Client owners/managers and Codeonto staff can edit; a test button checks a number works."""

from datetime import time

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets import access
from apps.outlets.models import Brand, BrandOutlet
from apps.stockouts.models import AlertRecipient

from . import notify
from .models import AlertDelivery

TOGGLES = ["offline_alerts", "online_alerts", "stock_out_alerts", "review_alerts", "payout_alerts", "ad_alerts", "performance_alerts"]


def _client(request, client_id):
    client = access.get_client(request.user, client_id)
    access.require_manage(request.user)
    return client


def _json(r: AlertRecipient) -> dict:
    return {"id": r.id, "name": r.name, "channel": r.channel, "address": r.address, "is_active": r.is_active,
            **{t: getattr(r, t) for t in TOGGLES}, "brand_ids": list(r.brands.values_list("id", flat=True)),
            "outlet_ids": list(r.outlets.values_list("id", flat=True)),
            "quiet_start": r.quiet_start.strftime("%H:%M") if r.quiet_start else "", "quiet_end": r.quiet_end.strftime("%H:%M") if r.quiet_end else ""}


def _time(v):
    if not v:
        return None
    h, _, m = str(v).partition(":")
    return time(int(h), int(m or 0))


def _save(r: AlertRecipient, d: dict, client) -> AlertRecipient | Response:
    channel = d.get("channel", r.channel or "whatsapp")
    address = str(d.get("address", r.address or "")).strip()
    if channel not in ("whatsapp", "email"):
        return Response({"detail": "Channel must be whatsapp or email"}, status=400)
    if channel == "whatsapp":
        digits = "".join(ch for ch in address if ch.isdigit())
        address = "91" + digits if len(digits) == 10 else digits
        if not 11 <= len(address) <= 15:
            return Response({"detail": "Enter the WhatsApp number with country code, e.g. 919876543210"}, status=400)
    elif "@" not in address:
        return Response({"detail": "Enter a valid email address"}, status=400)
    r.client, r.channel, r.address = client, channel, address
    r.name = str(d.get("name", r.name or ""))[:120]
    r.is_active = bool(d.get("is_active", True if r.pk is None else r.is_active))
    for t in TOGGLES:
        if t in d:
            setattr(r, t, bool(d[t]))
    try:
        r.quiet_start, r.quiet_end = _time(d.get("quiet_start", r.quiet_start and r.quiet_start.strftime("%H:%M"))), _time(d.get("quiet_end", r.quiet_end and r.quiet_end.strftime("%H:%M")))
    except ValueError:
        return Response({"detail": "Quiet hours must look like 23:00"}, status=400)
    if AlertRecipient.objects.filter(client=client, channel=channel, address=address).exclude(pk=r.pk).exists():
        return Response({"detail": "That number or email is already on the list"}, status=400)
    r.save()
    if "brand_ids" in d:
        r.brands.set(Brand.objects.filter(client=client, id__in=d.get("brand_ids") or []))
    if "outlet_ids" in d:
        r.outlets.set(BrandOutlet.objects.filter(brand__client=client, id__in=d.get("outlet_ids") or []))
    return r


@api_view(["GET", "POST"])
def recipients(request, client_id):
    client = _client(request, client_id)
    if request.method == "POST":
        r = _save(AlertRecipient(), request.data, client)
        if isinstance(r, Response):
            return r
        notify.run(bootstrap=True, only=r)  # starts fresh: only what happens from now on
        return Response(_json(r), status=201)
    brands = Brand.objects.filter(client=client, is_active=True).order_by("name")
    outlets = BrandOutlet.objects.filter(brand__client=client, is_active=True).select_related("brand").order_by("brand__name", "city", "area")
    recent = AlertDelivery.objects.filter(client=client).exclude(status="skipped").order_by("-created_at")
    seen, log = set(), []
    for d in recent[:300]:  # one line per message (a grouped message logs one row per item)
        key = (d.address, d.kind, d.summary, d.created_at.replace(microsecond=0))
        if key not in seen:
            seen.add(key)
            log.append({"at": d.created_at, "to": d.address, "channel": d.channel, "kind": notify.LABEL.get(d.kind, d.kind), "summary": d.summary,
                        "status": d.status, "error": d.error[:200]})
        if len(log) >= 25:
            break
    return Response({"recipients": [_json(r) for r in AlertRecipient.objects.filter(client=client).order_by("channel", "name")],
                     "brands": [{"id": b.id, "name": b.name} for b in brands],
                     "outlets": [{"id": o.id, "brand_id": o.brand_id, "name": f"{o.brand.name} · {o.area or o.outlet_name}", "city": o.city} for o in outlets],
                     "toggles": [{"key": t, "label": label} for t, label in zip(TOGGLES, ["Outlet offline", "Back online", "Stock-outs", "1–2★ reviews",
                                                                                           "Payout problems", "Ad spend spikes", "Rating / listing drops"])],
                     "log": log})


@api_view(["PUT", "DELETE"])
def recipient(request, client_id, rid):
    client = _client(request, client_id)
    r = get_object_or_404(AlertRecipient, pk=rid, client=client)
    if request.method == "DELETE":
        r.delete()
        return Response({"ok": True})
    out = _save(r, request.data, client)
    if isinstance(out, Response):
        return out
    notify.run(bootstrap=True, only=out)  # newly ticked alerts or outlets start from now, not with a backlog
    return Response(_json(out))


@api_view(["POST"])
def recipient_test(request, client_id, rid):
    client = _client(request, client_id)
    r = get_object_or_404(AlertRecipient, pk=rid, client=client)
    err = notify.send_test(r)
    return Response({"detail": err}, status=400) if err else Response({"ok": True, "queued": True})
