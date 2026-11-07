"""WhatsApp / email alerts, sent from one place (this site), for everything the collectors save to the database.

Every few minutes (`manage.py send_alerts`) it looks for what's new: outlets gone offline in opening hours (and back
online), items out of stock (and back), new 1-2 star reviews, payouts overdue or not matching their orders, and ad
spend well above an outlet's usual. For each alert recipient (stockouts.AlertRecipient) it keeps only their client's
outlets, narrowed to the brands / outlets they chose and the alert types they ticked, skips quiet hours, groups
everything of one type into one message and sends it with the WhatsApp templates approved for the business account.

Each (recipient, alert type, thing) is logged in alert_deliveries, so nothing is sent twice; a failed send is retried
on the next run, up to MAX_TRIES times.
"""

import logging
import statistics
from collections import defaultdict
from datetime import timedelta, timezone

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone as djtz

from apps.outlets.models import BrandOutlet
from apps.stockouts.models import AlertRecipient, StockOut
from apps.uptime.models import OfflineEpisode

from .models import AlertDelivery

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
MAX_TRIES = 3
KIND_FIELD = {"offline": "offline_alerts", "online": "online_alerts", "oos": "stock_out_alerts", "oos_back": "stock_out_alerts",
              "review": "review_alerts", "payout": "payout_alerts", "ads": "ad_alerts"}
LABEL = {"offline": "Outlet offline", "online": "Back online", "oos": "Items out of stock", "oos_back": "Items back in stock",
         "review": "New low-star review", "payout": "Payout problem", "ads": "Ad spend spike"}
PLATFORM = {"zomato": "Zomato", "swiggy": "Swiggy", "google": "Google"}


def _cfg(name, default=None):
    return getattr(settings, name, None) or default


def _outlet_name(o: BrandOutlet) -> str:
    return f"{o.brand.name} · {o.area or o.outlet_name}"


def _ist(dt) -> str:
    return dt.astimezone(IST).strftime("%d %b %I:%M %p").replace(" 0", " ")


# ---------- what's new ----------

def events(now=None) -> list[dict]:
    """[{kind, ref, outlet, platform, text, sort}] for everything worth an alert right now."""
    now = now or djtz.now()
    since = now - timedelta(hours=int(_cfg("ALERT_LOOKBACK_HOURS", 6)))
    out = []
    min_off = timedelta(minutes=int(_cfg("ALERT_OFFLINE_MIN_MINUTES", 10)))
    for e in OfflineEpisode.objects.filter(is_active=True, first_detected_at__gte=since, first_detected_at__lte=now - min_off).select_related("outlet__brand"):
        out.append({"kind": "offline", "ref": f"offline:{e.id}", "outlet": e.outlet, "platform": e.platform_id,
                    "text": f"{_outlet_name(e.outlet)} ({PLATFORM.get(e.platform_id, e.platform_id)}) offline since {_ist(e.first_detected_at)}"})
    alerted = set(AlertDelivery.objects.filter(kind="offline", status="sent").values_list("ref", flat=True))
    for e in OfflineEpisode.objects.filter(is_active=False, restored_at__gte=since).select_related("outlet__brand"):
        if f"offline:{e.id}" in alerted:
            out.append({"kind": "online", "ref": f"online:{e.id}", "outlet": e.outlet, "platform": e.platform_id,
                        "text": f"{_outlet_name(e.outlet)} back online at {_ist(e.restored_at)} (was off {e.downtime_minutes or 0} min)"})
    for s in StockOut.objects.filter(is_active=True, first_detected_at__gte=since).select_related("outlet__brand"):
        out.append({"kind": "oos", "ref": f"oos:{s.id}", "outlet": s.outlet, "platform": s.platform_id, "item": s.item_name, "text": s.item_name})
    alerted = set(AlertDelivery.objects.filter(kind="oos", status="sent").values_list("ref", flat=True))
    for s in StockOut.objects.filter(is_active=False, restored_at__gte=since).select_related("outlet__brand"):
        if f"oos:{s.id}" in alerted:
            out.append({"kind": "oos_back", "ref": f"oos_back:{s.id}", "outlet": s.outlet, "platform": s.platform_id, "item": s.item_name, "text": s.item_name})
    out += _review_events(since, now)
    out += _payout_events(now)
    out += _ad_events(now)
    return out


def _review_events(since, now) -> list[dict]:
    from apps.reviews.models import Review

    out = []
    for r in Review.objects.filter(rating__lte=2, created_at__gte=since, reviewed_at__gte=now - timedelta(days=3)).select_related("outlet__brand"):
        body = " ".join((r.body or "").split())[:140] or "rating only, no text"
        out.append({"kind": "review", "ref": f"review:{r.id}", "outlet": r.outlet, "platform": r.platform_id,
                    "text": f"{_outlet_name(r.outlet)} · {PLATFORM.get(r.platform_id, r.platform_id)} {int(r.rating)}★ by {r.author_name or 'a customer'}: \"{body}\""})
    return out


def _payout_events(now) -> list[dict]:
    from apps.payouts.api import _issues
    from apps.payouts.models import PayoutCycle

    out = []
    for c in PayoutCycle.objects.filter(end_date__gte=(now - timedelta(days=21)).date()).select_related("outlet__brand"):
        for issue in _issues(c):
            if issue == "overdue" and c.payout_date and c.payout_date > (now - timedelta(days=int(_cfg("ALERT_PAYOUT_GRACE_DAYS", 2)))).date():
                continue  # a day or so late is normal; alert once it's really overdue
            if issue in ("overdue", "payout_mismatch"):
                what = "overdue, not paid yet" if issue == "overdue" else f"doesn't match its orders (₹{abs(c.discrepancy or 0):,.0f} off)"
                out.append({"kind": "payout", "ref": f"payout:{c.id}:{issue}", "outlet": c.outlet, "platform": c.platform_id,
                            "text": f"{_outlet_name(c.outlet)} · {PLATFORM.get(c.platform_id)} payout {c.start_date:%d %b}–{c.end_date:%d %b} ₹{float(c.net_payout or 0):,.0f} {what}"})
    return out


def _ad_events(now) -> list[dict]:
    """A payout period whose ad spend is at least ALERT_AD_SPIKE_X times the outlet's usual (median of its previous 28
    periods on that platform) and at least ALERT_AD_SPIKE_MIN rupees more."""
    from apps.payouts.ads import cycle_numbers
    from apps.payouts.models import PayoutCycle

    times, extra = float(_cfg("ALERT_AD_SPIKE_X", 2)), float(_cfg("ALERT_AD_SPIKE_MIN", 500))
    recent = PayoutCycle.objects.filter(end_date__gte=(now - timedelta(days=4)).date()).exclude(breakdown=[]).select_related("outlet__brand")
    out = []
    for c in recent:
        days = (c.end_date - c.start_date).days + 1
        ads = cycle_numbers(c)["ads"] / days
        history = PayoutCycle.objects.filter(outlet=c.outlet, platform_id=c.platform_id, end_date__lt=c.start_date).exclude(breakdown=[]).order_by("-end_date")[:28]
        past = [cycle_numbers(h)["ads"] / ((h.end_date - h.start_date).days + 1) for h in history]
        if len(past) < 7:
            continue
        usual = statistics.median(past)
        if ads >= times * max(usual, 1) and ads - usual >= extra:
            out.append({"kind": "ads", "ref": f"ads:{c.id}", "outlet": c.outlet, "platform": c.platform_id,
                        "text": f"{_outlet_name(c.outlet)} · {PLATFORM.get(c.platform_id)} ads ₹{ads:,.0f}/day on {c.end_date:%d %b}, usually ₹{usual:,.0f}/day"})
    return out


# ---------- who gets what ----------

def recipient_outlets(r: AlertRecipient) -> set[int]:
    qs = BrandOutlet.objects.filter(brand__client_id=r.client_id, is_active=True)
    picked = set(r.outlets.values_list("id", flat=True))
    if picked:
        return set(qs.filter(id__in=picked).values_list("id", flat=True))
    brands = set(r.brands.values_list("id", flat=True))
    if brands:
        qs = qs.filter(brand_id__in=brands)
    return set(qs.values_list("id", flat=True))


def in_quiet_hours(r: AlertRecipient, now=None) -> bool:
    if not (r.quiet_start and r.quiet_end):
        return False
    t = (now or djtz.now()).astimezone(IST).time()
    start, end = r.quiet_start, r.quiet_end
    return (start <= t < end) if start < end else (t >= start or t < end)


# ---------- messages ----------

def _flat(text: str, limit: int) -> str:
    """WhatsApp template values can't hold line breaks, tabs or long runs of spaces."""
    text = " | ".join(part.strip() for part in text.splitlines() if part.strip())
    text = " ".join(text.replace("\t", " ").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _compose(kind: str, items: list[dict], who: str, now) -> dict:
    """{template, params, subject, lines} for one grouped message."""
    when = _ist(now)
    outlets = {i["outlet"].id for i in items}
    if kind in ("oos", "oos_back"):
        per = defaultdict(list)
        for i in items:
            per[_outlet_name(i["outlet"])].append(i["item"])
        lines = [f"{o}: {', '.join(v[:8])}{f' +{len(v) - 8} more' if len(v) > 8 else ''}" for o, v in per.items()]
    else:
        lines = [i["text"] for i in items]
    details = _flat("\n".join(lines), 900)
    platforms = ", ".join(sorted({PLATFORM.get(i["platform"], i["platform"]) for i in items}))
    if kind == "offline":
        return {"template": _cfg("WHATSAPP_TEMPLATE_OFFLINE", "zomato_outage_alert"), "params": [who, str(len(outlets)), when, details], "lines": lines,
                "subject": f"{len(outlets)} outlet(s) offline · {who}"}
    if kind == "online":
        return {"template": _cfg("WHATSAPP_TEMPLATE_ONLINE", "zomato_recovery_alert"), "params": [who, str(len(outlets)), when, details], "lines": lines,
                "subject": f"{len(outlets)} outlet(s) back online · {who}"}
    if kind == "oos":
        return {"template": _cfg("WHATSAPP_TEMPLATE_OOS", "zomato_item_oos_alert"), "params": [who, str(len(items)), str(len(outlets)), when, details], "lines": lines,
                "subject": f"{len(items)} item(s) out of stock across {len(outlets)} outlet(s) · {who}"}
    if kind == "oos_back":
        return {"template": _cfg("WHATSAPP_TEMPLATE_OOS_BACK", "zomato_item_recovery_alert"), "params": [who, str(len(items)), str(len(outlets)), when, details], "lines": lines,
                "subject": f"{len(items)} item(s) back in stock · {who}"}
    scope = who if len(outlets) > 1 else _outlet_name(items[0]["outlet"])
    return {"template": _cfg("WHATSAPP_TEMPLATE_GENERIC", "restaurant_offline_alert"),
            "params": [f"{LABEL[kind]} ({len(items)})", _flat(scope, 120), when, platforms or "-", details], "lines": lines,
            "subject": f"{LABEL[kind]} · {len(items)} · {who}"}


def _whatsapp(to: str, template: str, params: list[str]) -> str | None:
    """None when sent, else the error."""
    pid, token = _cfg("WHATSAPP_PHONE_NUMBER_ID"), _cfg("WHATSAPP_BEARER_TOKEN")
    if not (pid and token):
        return "WhatsApp isn't set up on this server (WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_BEARER_TOKEN)"
    to = "".join(ch for ch in to if ch.isdigit())
    if len(to) == 10:
        to = "91" + to
    body = {"messaging_product": "whatsapp", "to": to, "type": "template",
            "template": {"name": template, "language": {"code": _cfg("WHATSAPP_TEMPLATE_LANG", "en")},
                         "components": [{"type": "body", "parameters": [{"type": "text", "text": _flat(p, 1000) or "-"} for p in params]}]}}
    try:
        r = requests.post(f"{_cfg('WHATSAPP_API_BASE', 'https://graph.facebook.com/v20.0')}/{pid}/messages", json=body, timeout=15,
                          headers={"Authorization": f"Bearer {token}"})
        return None if r.status_code == 200 else f"HTTP {r.status_code}: {r.text[:300]}"
    except requests.RequestException as e:
        return str(e)


def _email(to: str, subject: str, lines: list[str]) -> str | None:
    try:
        send_mail(f"Codeonto · {subject}", "\n".join(lines) + "\n\nSee details on your Codeonto dashboard.", None, [to])
        return None
    except Exception as e:
        return str(e)


def deliver(r: AlertRecipient, kind: str, items: list[dict], now=None, dry_run: bool = False) -> dict:
    now = now or djtz.now()
    brands = {i["outlet"].brand.name for i in items}
    who = brands.pop() if len(brands) == 1 else r.client.name
    msg = _compose(kind, items, who, now)
    if dry_run:
        return {"status": "dry-run", **msg}
    err = _whatsapp(r.address, msg["template"], msg["params"]) if r.channel == "whatsapp" else _email(r.address, msg["subject"], msg["lines"])
    status = "failed" if err else "sent"
    AlertDelivery.objects.bulk_create([AlertDelivery(recipient=r, client_id=r.client_id, kind=kind, ref=i["ref"], channel=r.channel, address=r.address,
                                                     status=status, summary=msg["subject"], error=err or "") for i in items])
    if err:
        log.warning("Alert %s to %s failed: %s", kind, r.address, err)
    return {"status": status, "error": err, **msg}


# ---------- one run ----------

def run(dry_run: bool = False, bootstrap: bool = False, only: AlertRecipient | None = None) -> dict:
    """Send everything new. bootstrap=True records what's pending as handled without sending: at first switch-on,
    and for a recipient just added or changed (only=that recipient), so nobody gets a backlog of old events."""
    now = djtz.now()
    evs = events(now)
    by_client = defaultdict(list)
    for e in evs:
        by_client[e["outlet"].brand.client_id].append(e)
    done = defaultdict(int)
    for row in AlertDelivery.objects.filter(ref__in=[e["ref"] for e in evs]).values("recipient_id", "kind", "ref", "status"):
        done[(row["recipient_id"], row["kind"], row["ref"], row["status"])] += 1
    stats = {"events": len(evs), "messages": 0, "sent": 0, "failed": 0, "quiet": 0, "marked_handled": 0, "plans": []}
    recipients = AlertRecipient.objects.filter(is_active=True, client_id__in=list(by_client)).select_related("client")
    if only is not None:
        recipients = recipients.filter(pk=only.pk)
    for r in recipients:
        mine = recipient_outlets(r)
        for kind in KIND_FIELD:
            if not getattr(r, KIND_FIELD[kind]):
                continue
            todo = [e for e in by_client[r.client_id] if e["kind"] == kind and e["outlet"].id in mine
                    and not done[(r.id, kind, e["ref"], "sent")] and not done[(r.id, kind, e["ref"], "skipped")]
                    and done[(r.id, kind, e["ref"], "failed")] < MAX_TRIES]
            if not todo:
                continue
            if bootstrap:
                AlertDelivery.objects.bulk_create([AlertDelivery(recipient=r, client_id=r.client_id, kind=kind, ref=e["ref"], channel=r.channel,
                                                                 address=r.address, status="skipped", summary="already pending when alerts were switched on") for e in todo])
                stats["marked_handled"] += len(todo)
                continue
            if in_quiet_hours(r, now):
                stats["quiet"] += 1
                continue
            res = deliver(r, kind, todo, now, dry_run)
            stats["messages"] += 1
            stats[res["status"]] = stats.get(res["status"], 0) + 1
            stats["plans"].append({"to": f"{r.channel}:{r.address}", "kind": kind, "items": len(todo), "status": res["status"],
                                   "template": res["template"], "params": res["params"], "error": res.get("error")})
    return stats


def send_test(r: AlertRecipient) -> str | None:
    """Queue a test message for this recipient. The collector sends alerts (it holds the WhatsApp keys); it picks the
    test up on its next run, within a few minutes. None when queued, else the error."""
    import uuid

    AlertDelivery.objects.create(recipient=r, client_id=r.client_id, kind="test", ref=f"test:{uuid.uuid4().hex}", channel=r.channel,
                                 address=r.address, status="queued", summary="Test alert")
    return None
