"""WhatsApp / email alerts, sent by the collector right after it finds something: outlets offline in opening hours
(and back online) from the uptime job, items out of stock (and back) from the stock-out job, and - via
`run.py alerts send` - new 1-2 star reviews, payouts overdue or not matching their orders, and ad spend well above an
outlet's usual.

Who gets what is set on the dashboard (Alerts settings -> alert_recipients): each recipient belongs to a client, can
be narrowed to brands or outlets, ticks the alert types they want and may set quiet hours. Everything of one type for
one recipient goes in one message, using the WhatsApp templates approved for the business account
(WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_BEARER_TOKEN in .env). Each (recipient, alert type, thing) is logged in
alert_deliveries, so nothing is sent twice; a failed send is retried on the next run, up to MAX_TRIES times. The
dashboard's "Send test" queues a test there, which this sends on its next run.
"""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import config as cfg, db
from .common import log

IST = timezone(timedelta(hours=5, minutes=30))
MAX_TRIES = 3
KIND_FIELD = {"offline": "offline_alerts", "online": "online_alerts", "oos": "stock_out_alerts", "oos_back": "stock_out_alerts",
              "review": "review_alerts", "payout": "payout_alerts", "ads": "ad_alerts"}
LABEL = {"offline": "Outlet offline", "online": "Back online", "oos": "Items out of stock", "oos_back": "Items back in stock",
         "review": "New low-star review", "payout": "Payout problem", "ads": "Ad spend spike"}
PLATFORM = {"zomato": "Zomato", "swiggy": "Swiggy", "google": "Google"}
OUTLET_SQL = """SELECT bo.id, bo.area, bo.outlet_name, bo.city, b.name AS brand, b.client_id FROM brand_outlets bo JOIN brands b ON b.id = bo.brand_id"""


def _ist(dt: datetime) -> str:
    return dt.astimezone(IST).strftime("%d %b %I:%M %p").replace(" 0", " ")


def _name(o: dict) -> str:
    return f"{o['brand']} · {o['area'] or o['outlet_name']}"


def _flat(text: str, limit: int) -> str:
    """WhatsApp template values can't hold line breaks, tabs or long runs of spaces."""
    text = " | ".join(p.strip() for p in str(text).splitlines() if p.strip())
    text = " ".join(text.replace("\t", " ").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ---------- what's new ----------

def _outlets(cur, ids) -> dict:
    if not ids:
        return {}
    cur.execute(OUTLET_SQL + " WHERE bo.id = ANY(%s)", (list(ids),))
    return {r["id"]: r for r in cur.fetchall()}


def _events(cur, kinds, now: datetime) -> list[dict]:
    since = now - timedelta(hours=cfg.integer("ALERT_LOOKBACK_HOURS", 6))
    rows = []
    if "offline" in kinds:
        cur.execute("""SELECT id, outlet_id, platform, first_detected_at FROM offline_episodes
                       WHERE is_active AND first_detected_at >= %s AND first_detected_at <= %s""",
                    (since, now - timedelta(minutes=cfg.integer("ALERT_OFFLINE_MIN_MINUTES", 10))))
        rows += [{"kind": "offline", "ref": f"offline:{r['id']}", "outlet_id": r["outlet_id"], "platform": r["platform"],
                  "text": lambda o, r=r: f"{_name(o)} ({PLATFORM.get(r['platform'], r['platform'])}) offline since {_ist(r['first_detected_at'])}"} for r in cur.fetchall()]
    if "online" in kinds:
        cur.execute("""SELECT e.id, e.outlet_id, e.platform, e.restored_at, e.downtime_minutes FROM offline_episodes e
                       WHERE NOT e.is_active AND e.restored_at >= %s
                         AND EXISTS (SELECT 1 FROM alert_deliveries d WHERE d.kind = 'offline' AND d.status = 'sent' AND d.ref = 'offline:' || e.id)""", (since,))
        rows += [{"kind": "online", "ref": f"online:{r['id']}", "outlet_id": r["outlet_id"], "platform": r["platform"],
                  "text": lambda o, r=r: f"{_name(o)} back online at {_ist(r['restored_at'])} (was off {r['downtime_minutes'] or 0} min)"} for r in cur.fetchall()]
    if "oos" in kinds:
        cur.execute("SELECT id, outlet_id, platform, item_name FROM stock_outs WHERE is_active AND first_detected_at >= %s", (since,))
        rows += [{"kind": "oos", "ref": f"oos:{r['id']}", "outlet_id": r["outlet_id"], "platform": r["platform"], "item": r["item_name"]} for r in cur.fetchall()]
    if "oos_back" in kinds:
        cur.execute("""SELECT s.id, s.outlet_id, s.platform, s.item_name FROM stock_outs s WHERE NOT s.is_active AND s.restored_at >= %s
                         AND EXISTS (SELECT 1 FROM alert_deliveries d WHERE d.kind = 'oos' AND d.status = 'sent' AND d.ref = 'oos:' || s.id)""", (since,))
        rows += [{"kind": "oos_back", "ref": f"oos_back:{r['id']}", "outlet_id": r["outlet_id"], "platform": r["platform"], "item": r["item_name"]} for r in cur.fetchall()]
    if "review" in kinds:
        cur.execute("""SELECT id, outlet_id, platform, rating, author_name, body FROM reviews
                       WHERE rating <= 2 AND created_at >= %s AND reviewed_at >= %s""", (since, now - timedelta(days=3)))
        for r in cur.fetchall():
            body = " ".join((r["body"] or "").split())[:140] or "rating only, no text"
            rows.append({"kind": "review", "ref": f"review:{r['id']}", "outlet_id": r["outlet_id"], "platform": r["platform"],
                         "text": lambda o, r=r, body=body: f"{_name(o)} · {PLATFORM.get(r['platform'], r['platform'])} {int(r['rating'])}★ by {r['author_name'] or 'a customer'}: \"{body}\""})
    if "payout" in kinds:
        rows += _payout_events(cur, now)
    if "ads" in kinds:
        rows += _ad_events(cur, now)
    return rows


def _payout_events(cur, now: datetime) -> list[dict]:
    """Overdue (past the payout date by ALERT_PAYOUT_GRACE_DAYS, not paid) or not matching its orders. A ₹0 payout
    whose deductions were bigger than its orders is a carry-over, not a mismatch (same rule as the dashboard)."""
    today, grace = now.astimezone(IST).date(), cfg.integer("ALERT_PAYOUT_GRACE_DAYS", 2)
    cur.execute("""SELECT id, outlet_id, platform, start_date, end_date, payout_date, status, net_payout, expected_payout, discrepancy, issues
                   FROM payout_cycles WHERE end_date >= %s""", (today - timedelta(days=21),))
    out = []
    for c in cur.fetchall():
        issues = list(c["issues"] or [])
        if "payout_mismatch" in issues and not c["net_payout"] and c["expected_payout"] is not None and c["expected_payout"] < 0:
            issues.remove("payout_mismatch")
        if (c["status"] or "").strip().upper() == "TO BE PAID" and c["payout_date"] and c["payout_date"] <= today - timedelta(days=grace):
            issues.append("overdue")
        for issue in issues:
            if issue not in ("overdue", "payout_mismatch"):
                continue
            what = "overdue, not paid yet" if issue == "overdue" else f"doesn't match its orders (₹{abs(c['discrepancy'] or 0):,.0f} off)"
            out.append({"kind": "payout", "ref": f"payout:{c['id']}:{issue}", "outlet_id": c["outlet_id"], "platform": c["platform"],
                        "text": lambda o, c=c, what=what: f"{_name(o)} · {PLATFORM.get(c['platform'])} payout {c['start_date']:%d %b}–{c['end_date']:%d %b} ₹{float(c['net_payout'] or 0):,.0f} {what}"})
    return out


AD_SECTIONS = {"investments_in_growth", "growth_investments_in_ads"}


def _ads(breakdown) -> float:
    total = 0.0
    for s in breakdown or []:
        if s.get("id") in AD_SECTIONS:
            total += abs(float(s.get("value") or 0))
        elif s.get("id") == "other_charges_refunds":
            total += sum(abs(float(i.get("value") or 0)) for i in s.get("items") or [] if "display ads" in (i.get("label") or "").lower())
    return total


def _ad_events(cur, now: datetime) -> list[dict]:
    """A recent payout period whose ad spend a day is ALERT_AD_SPIKE_X times the outlet's usual (median of its previous
    28 periods on that platform) and at least ALERT_AD_SPIKE_MIN rupees more."""
    times, extra = float(cfg.text("ALERT_AD_SPIKE_X", "2")), float(cfg.text("ALERT_AD_SPIKE_MIN", "500"))
    cur.execute("""SELECT id, outlet_id, platform, start_date, end_date, breakdown FROM payout_cycles
                   WHERE end_date >= %s AND breakdown::text <> '[]'""", (now.astimezone(IST).date() - timedelta(days=4),))
    out = []
    for c in cur.fetchall():
        per_day = _ads(c["breakdown"]) / ((c["end_date"] - c["start_date"]).days + 1)
        cur.execute("""SELECT start_date, end_date, breakdown FROM payout_cycles WHERE outlet_id = %s AND platform = %s AND end_date < %s
                         AND breakdown::text <> '[]' ORDER BY end_date DESC LIMIT 28""", (c["outlet_id"], c["platform"], c["start_date"]))
        past = [_ads(h["breakdown"]) / ((h["end_date"] - h["start_date"]).days + 1) for h in cur.fetchall()]
        if len(past) < 7:
            continue
        usual = statistics.median(past)
        if per_day >= times * max(usual, 1) and per_day - usual >= extra:
            out.append({"kind": "ads", "ref": f"ads:{c['id']}", "outlet_id": c["outlet_id"], "platform": c["platform"],
                        "text": lambda o, c=c, per_day=per_day, usual=usual: f"{_name(o)} · {PLATFORM.get(c['platform'])} ads ₹{per_day:,.0f}/day on {c['end_date']:%d %b}, usually ₹{usual:,.0f}/day"})
    return out


# ---------- who gets what ----------

def _recipients(cur, client_ids) -> list[dict]:
    cur.execute("""SELECT r.*, c.name AS client_name,
                          ARRAY(SELECT brand_id FROM alert_recipients_brands WHERE alertrecipient_id = r.id) AS brand_ids,
                          ARRAY(SELECT brandoutlet_id FROM alert_recipients_outlets WHERE alertrecipient_id = r.id) AS outlet_ids
                   FROM alert_recipients r JOIN clients c ON c.id = r.client_id WHERE r.is_active AND r.client_id = ANY(%s)""", (list(client_ids),))
    return cur.fetchall()


def _scope(cur, r: dict) -> set[int]:
    if r["outlet_ids"]:
        cur.execute("SELECT bo.id FROM brand_outlets bo JOIN brands b ON b.id = bo.brand_id WHERE bo.is_active AND b.client_id = %s AND bo.id = ANY(%s)",
                    (r["client_id"], r["outlet_ids"]))
    elif r["brand_ids"]:
        cur.execute("SELECT bo.id FROM brand_outlets bo JOIN brands b ON b.id = bo.brand_id WHERE bo.is_active AND b.client_id = %s AND b.id = ANY(%s)",
                    (r["client_id"], r["brand_ids"]))
    else:
        cur.execute("SELECT bo.id FROM brand_outlets bo JOIN brands b ON b.id = bo.brand_id WHERE bo.is_active AND b.client_id = %s", (r["client_id"],))
    return {x["id"] for x in cur.fetchall()}


def _quiet(r: dict, now: datetime) -> bool:
    start, end = r["quiet_start"], r["quiet_end"]
    if not (start and end):
        return False
    t = now.astimezone(IST).time()
    return (start <= t < end) if start < end else (t >= start or t < end)


# ---------- messages ----------

def _fit(lines: list[str], budget: int) -> str:
    """As many whole lines as fit in budget characters, then "…and N more (see dashboard)". WhatsApp rejects a
    message whose template text plus values pass 1,024 characters, and the templates' own text takes ~250-450."""
    out, used = [], 0
    for i, line in enumerate(lines):
        line = _flat(line, 220)
        rest = len(lines) - i - 1
        tail = f" | …and {rest} more (see dashboard)" if rest else ""
        if used + len(line) + 3 + (len(tail) if rest else 0) > budget and out:
            out.append(f"…and {len(lines) - i} more (see dashboard)")
            break
        out.append(line)
        used += len(line) + 3
    return " | ".join(out)


def _compose(kind: str, items: list[dict], outlets: dict, who: str, now: datetime) -> dict:
    when = _ist(now)
    ids = {i["outlet_id"] for i in items}
    if kind in ("oos", "oos_back"):
        per = defaultdict(list)
        for i in items:
            per[_name(outlets[i["outlet_id"]])].append(i["item"])
        lines = [f"{o}: {', '.join(v[:8])}{f' +{len(v) - 8} more' if len(v) > 8 else ''}" for o, v in per.items()]
    else:
        lines = [i["text"](outlets[i["outlet_id"]]) for i in items]
    details = _fit(lines, cfg.integer("WHATSAPP_DETAILS_MAX", 560))
    platforms = ", ".join(sorted({PLATFORM.get(i["platform"], i["platform"]) for i in items}))
    t = lambda name, default: cfg.text(name, default)
    if kind == "offline":
        return {"template": t("WHATSAPP_TEMPLATE_OFFLINE", "zomato_outage_alert"), "params": [_flat(who, 60), str(len(ids)), when, details], "lines": lines,
                "subject": f"{len(ids)} outlet(s) offline · {who}"}
    if kind == "online":
        return {"template": t("WHATSAPP_TEMPLATE_ONLINE", "zomato_recovery_alert"), "params": [who, str(len(ids)), when, details], "lines": lines,
                "subject": f"{len(ids)} outlet(s) back online · {who}"}
    if kind == "oos":
        return {"template": t("WHATSAPP_TEMPLATE_OOS", "zomato_item_oos_alert"), "params": [who, str(len(items)), str(len(ids)), when, details], "lines": lines,
                "subject": f"{len(items)} item(s) out of stock across {len(ids)} outlet(s) · {who}"}
    if kind == "oos_back":
        return {"template": t("WHATSAPP_TEMPLATE_OOS_BACK", "zomato_item_recovery_alert"), "params": [who, str(len(items)), str(len(ids)), when, details], "lines": lines,
                "subject": f"{len(items)} item(s) back in stock · {who}"}
    scope = who if len(ids) > 1 else _name(outlets[items[0]["outlet_id"]])
    details = _fit(lines, cfg.integer("WHATSAPP_GENERIC_DETAILS_MAX", 420))  # this template's own text is longer
    return {"template": t("WHATSAPP_TEMPLATE_GENERIC", "restaurant_offline_alert"),
            "params": [f"{LABEL[kind]} ({len(items)})", _flat(scope, 80), when, platforms or "-", details], "lines": lines,
            "subject": f"{LABEL[kind]} · {len(items)} · {who}"}


def _whatsapp(to: str, template: str, params: list[str], image_id: str | None = None) -> str | None:
    """None when sent, else the error. image_id: an uploaded picture for templates with an image header."""
    import os

    import requests

    pid, token = os.getenv("WHATSAPP_PHONE_NUMBER_ID"), os.getenv("WHATSAPP_BEARER_TOKEN")
    if not (pid and token):
        return "WhatsApp isn't set up on the collector (WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_BEARER_TOKEN in .env)"
    to = "".join(ch for ch in to if ch.isdigit())
    if len(to) == 10:
        to = "91" + to
    body = {"messaging_product": "whatsapp", "to": to, "type": "template",
            "template": {"name": template, "language": {"code": cfg.text("WHATSAPP_TEMPLATE_LANG", "en")},
                         "components": ([{"type": "header", "parameters": [{"type": "image", "image": {"id": image_id}}]}] if image_id else [])
                                       + [{"type": "body", "parameters": [{"type": "text", "text": _flat(p, 1000) or "-"} for p in params]}]}}
    try:
        r = requests.post(f"{cfg.text('WHATSAPP_API_BASE', 'https://graph.facebook.com/v20.0')}/{pid}/messages", json=body,
                          timeout=cfg.integer("WHATSAPP_TIMEOUT_SEC", 15), headers={"Authorization": f"Bearer {token}"})
        return None if r.status_code == 200 else f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return str(e)


def _upload(png: bytes) -> str | None:
    """Upload a card to Meta; its media id, or None."""
    import os

    import requests

    pid, token = os.getenv("WHATSAPP_PHONE_NUMBER_ID"), os.getenv("WHATSAPP_BEARER_TOKEN")
    try:
        r = requests.post(f"{cfg.text('WHATSAPP_API_BASE', 'https://graph.facebook.com/v20.0')}/{pid}/media", headers={"Authorization": f"Bearer {token}"},
                          data={"messaging_product": "whatsapp", "type": "image/png"}, files={"file": ("alert.png", png, "image/png")},
                          timeout=cfg.integer("WHATSAPP_TIMEOUT_SEC", 15) + 15)
        return r.json().get("id") if r.status_code == 200 else (log.warning("card upload failed: HTTP %s %s", r.status_code, r.text[:200]) or None)
    except Exception as e:
        log.warning("card upload failed: %s", e)
        return None


_cards: dict = {}  # one upload per identical card within a run, shared by every recipient who gets it


def _image_message(kind: str, todo: list[dict], outlets: dict, who: str, now: datetime) -> tuple[str, list[str], str] | None:
    """(template, params, media id) for offline / stock-out alerts as picture cards, or None to send text."""
    import os

    if kind not in ("offline", "oos") or os.getenv("WHATSAPP_IMAGE_CARDS", "1") == "0":
        return None
    from . import cards

    ids = {e["outlet_id"] for e in todo}
    if kind == "offline":
        rows = [(_name(outlets[e["outlet_id"]]), f"{PLATFORM.get(e['platform'], e['platform'])} · not taking orders", e["text"](outlets[e["outlet_id"]]).rsplit("since ", 1)[-1])
                for e in todo]
        title, sub = f"{len(ids)} outlet{'s' if len(ids) != 1 else ''} offline", f"{who} · detected {_ist(now)}"
        template, params = cfg.text("WHATSAPP_TEMPLATE_OFFLINE_IMAGE", "zomato_outage_image_alert"), [_flat(who, 60), str(len(ids)), _ist(now)]
    else:
        per = defaultdict(list)
        for e in todo:
            per[e["outlet_id"]].append(e["item"])
        rows = [(_name(outlets[o]), ", ".join(v), f"{len(v)} item{'s' if len(v) != 1 else ''}") for o, v in sorted(per.items(), key=lambda kv: -len(kv[1]))]
        title, sub = f"{len(todo)} item{'s' if len(todo) != 1 else ''} out of stock", f"{who} · across {len(ids)} outlet{'s' if len(ids) != 1 else ''} · {_ist(now)}"
        template, params = cfg.text("WHATSAPP_TEMPLATE_OOS_IMAGE", "zomato_oos_image_alert"), [_flat(who, 60), str(len(todo)), str(len(ids)), _ist(now)]
    key = (kind, tuple(sorted(e["ref"] for e in todo)))
    if key not in _cards:
        png = cards.render(kind, title, sub, rows)
        _cards[key] = _upload(png) if png else None
    return (template, params, _cards[key]) if _cards[key] else None


def _email(to: str, subject: str, lines: list[str]) -> str | None:
    from . import alerts

    ok = alerts.send_email([to], f"Codeonto · {subject}", "<br>".join(lines) + "<br><br>See details on your Codeonto dashboard.")
    return None if ok else "email not sent (check EMAIL_* / SMTP settings in .env)"


def _log(cur, r: dict, kind: str, refs: list[str], status: str, summary: str, error: str = "") -> None:
    for ref in refs:
        cur.execute("""INSERT INTO alert_deliveries (recipient_id, client_id, kind, ref, channel, address, status, summary, error, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())""",
                    (r["id"], r["client_id"], kind, ref, r["channel"], r["address"], status, summary[:500], error[:1000]))


# ---------- one pass ----------

def _send_tests(cur, now: datetime) -> int:
    """Tests queued by the dashboard's Send test button."""
    cur.execute("""SELECT d.id, r.channel, r.address, c.name AS client_name FROM alert_deliveries d
                   JOIN alert_recipients r ON r.id = d.recipient_id JOIN clients c ON c.id = d.client_id
                   WHERE d.kind = 'test' AND d.status = 'queued'""")
    n = 0
    for t in cur.fetchall():
        text = "This is a test from Codeonto. Alerts for your outlets will arrive here."
        err = (_whatsapp(t["address"], cfg.text("WHATSAPP_TEMPLATE_GENERIC", "restaurant_offline_alert"), ["Test alert", t["client_name"], _ist(now), "Codeonto", text])
               if t["channel"] == "whatsapp" else _email(t["address"], "Test alert", [text]))
        cur.execute("UPDATE alert_deliveries SET status = %s, error = %s WHERE id = %s", ("failed" if err else "sent", err or "", t["id"]))
        n += 1
    return n


def send(kinds=tuple(KIND_FIELD), dry_run: bool = False) -> dict:
    """Send every new alert of these kinds to everyone who wants it. Safe to call after every job run."""
    now = datetime.now(timezone.utc)
    stats = {"events": 0, "messages": 0, "sent": 0, "failed": 0, "quiet": 0, "tests": 0}
    try:
        with db.transaction() as cur:
            if not dry_run:
                stats["tests"] = _send_tests(cur, now)
            evs = _events(cur, set(kinds), now)
            stats["events"] = len(evs)
            if not evs:
                return stats
            outlets = _outlets(cur, {e["outlet_id"] for e in evs})
            evs = [e for e in evs if e["outlet_id"] in outlets]
            by_client = defaultdict(list)
            for e in evs:
                by_client[outlets[e["outlet_id"]]["client_id"]].append(e)
            cur.execute("SELECT recipient_id, kind, ref, status, count(*) AS n FROM alert_deliveries WHERE ref = ANY(%s) GROUP BY 1, 2, 3, 4",
                        ([e["ref"] for e in evs],))
            done = {(x["recipient_id"], x["kind"], x["ref"], x["status"]): x["n"] for x in cur.fetchall()}
            for r in _recipients(cur, by_client):
                mine = _scope(cur, r)
                for kind in kinds:
                    if not r[KIND_FIELD[kind]]:
                        continue
                    todo = [e for e in by_client[r["client_id"]] if e["kind"] == kind and e["outlet_id"] in mine
                            and not done.get((r["id"], kind, e["ref"], "sent")) and not done.get((r["id"], kind, e["ref"], "skipped"))
                            and done.get((r["id"], kind, e["ref"], "failed"), 0) < MAX_TRIES]
                    if not todo:
                        continue
                    if _quiet(r, now):
                        stats["quiet"] += 1
                        continue
                    brands = {outlets[e["outlet_id"]]["brand"] for e in todo}
                    who = brands.pop() if len(brands) == 1 else r["client_name"]
                    msg = _compose(kind, todo, outlets, who, now)
                    stats["messages"] += 1
                    if dry_run:
                        log.info("alerts (dry run) %s %s: %s · %s", r["channel"], r["address"], msg["subject"], msg["params"])
                        continue
                    if r["channel"] == "whatsapp":
                        image = _image_message(kind, todo, outlets, who, now)
                        err = _whatsapp(r["address"], image[0], image[1], image[2]) if image else None
                        if not image or err:  # no card, or the image template failed: the text version still goes out
                            if err:
                                log.warning("alerts image %s to %s failed (%s); sending text", kind, r["address"], err)
                            err = _whatsapp(r["address"], msg["template"], msg["params"])
                    else:
                        err = _email(r["address"], msg["subject"], msg["lines"])
                    _log(cur, r, kind, [e["ref"] for e in todo], "failed" if err else "sent", msg["subject"], err or "")
                    stats["failed" if err else "sent"] += 1
                    log.info("alerts %s to %s %s: %s%s", kind, r["channel"], r["address"], msg["subject"], f" FAILED {err}" if err else "")
    except Exception as e:  # an alert problem must never stop the job that called it
        log.exception("alerts: %s", e)
    return stats


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    """`run.py alerts send`: reviews, payouts and ad spikes (offline and stock-outs go out from their own jobs)."""
    stats = send(("review", "payout", "ads"))
    log.info("alerts: %s", stats)
    return stats.get("failed", 0) == 0
