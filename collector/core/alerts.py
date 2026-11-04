"""Email / WhatsApp alerts. Recipients come from the alert_recipients table (set in admin per client);
credentials come from collector/.env only. A channel with no credentials is skipped with a log line.

    EMAIL_HOST, EMAIL_PORT (465 = SSL), EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
    WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_BEARER_TOKEN, WHATSAPP_OOS_TEMPLATE (approved Meta template, 4 body params)
    ALERT_OPS_EMAILS   comma separated: who hears about collector problems (expired session, rate limit)
"""

import html
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import config as cfg, db
from .common import log

_incident_sent: dict[str, float] = {}
INCIDENT_COOLDOWN_SEC = cfg.integer("INCIDENT_COOLDOWN_SEC", 3600)


def _recipients(client_id: int, channel: str) -> list[str]:
    with db.transaction() as cur:
        cur.execute("""SELECT address FROM alert_recipients
                       WHERE client_id = %s AND channel = %s AND is_active AND stock_out_alerts""", (client_id, channel))
        return [r["address"] for r in cur.fetchall()]


def send_email(to: list[str], subject: str, body_html: str) -> bool:
    host, user, password = os.getenv("EMAIL_HOST"), os.getenv("EMAIL_HOST_USER"), os.getenv("EMAIL_HOST_PASSWORD")
    if not (to and host and user and password):
        log.info("Email not sent (%s): %s", "no recipients" if not to else "EMAIL_* not set in .env", subject)
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, user, ", ".join(to)
    msg.attach(MIMEText(body_html, "html"))
    try:
        port = int(os.getenv("EMAIL_PORT", "465"))
        smtp = smtplib.SMTP_SSL(host, port, timeout=cfg.integer("EMAIL_TIMEOUT_SEC", 20)) if port == 465 else smtplib.SMTP(host, port, timeout=cfg.integer("EMAIL_TIMEOUT_SEC", 20))
        with smtp as s:
            if port != 465:
                s.starttls()
            s.login(user, password)
            s.sendmail(user, to, msg.as_string())
        log.info("Email sent to %s: %s", ", ".join(to), subject)
        return True
    except Exception as e:  # an alert failing must never stop the collector
        log.error("Email failed (%s): %s", subject, e)
        return False


def send_whatsapp(phone: str, brand: str, count: str, when: str, details: str) -> bool:
    import requests

    pid, token, template = os.getenv("WHATSAPP_PHONE_NUMBER_ID"), os.getenv("WHATSAPP_BEARER_TOKEN"), os.getenv("WHATSAPP_OOS_TEMPLATE")
    if not (pid and token and template):
        log.info("WhatsApp not sent: WHATSAPP_* not set in .env")
        return False
    params = [brand[:60], count[:30], when[:30], details.replace("\n", "  |  ").strip()[:980]]
    try:
        r = requests.post(f"{cfg.text('WHATSAPP_API_BASE', 'https://graph.facebook.com/v20.0')}/{pid}/messages", timeout=cfg.integer("WHATSAPP_TIMEOUT_SEC", 12),
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                          json={"messaging_product": "whatsapp", "to": phone, "type": "template",
                                "template": {"name": template, "language": {"code": cfg.text("WHATSAPP_TEMPLATE_LANG", "en")},
                                             "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]}})
        if r.status_code != 200:
            log.warning("WhatsApp to %s failed: %s", phone, r.text[:300])
            return False
        return True
    except Exception as e:
        log.error("WhatsApp to %s failed: %s", phone, e)
        return False


def _table(rows: list[tuple], head: tuple, colour: str) -> str:
    th = "".join(f'<th style="text-align:left;padding:8px 10px;background:#f6f8fa;border:1px solid #d0d7de">{h}</th>' for h in head)
    body = "".join("<tr>" + "".join(f'<td style="padding:8px 10px;border:1px solid #d0d7de">{html.escape(str(c))}</td>' for c in r) + "</tr>" for r in rows)
    return f'<table style="border-collapse:collapse;font-size:13px;width:100%"><tr>{th}</tr>{body}</table>'


def stock_out_alert(client_id: int, client_name: str, new_items: list[dict], restored: list[dict]) -> None:
    """new_items: outlet, item_name, category, mealtime, back_at.  restored: outlet, item_name, downtime_minutes."""
    if not (new_items or restored):
        return
    when = time.strftime("%I:%M %p, %d %b %Y")
    parts = []
    if new_items:
        parts.append(f'<h3 style="color:#c9302c">{len(new_items)} item(s) out of stock</h3>' + _table(
            [(i["outlet"], i["item_name"], i["category"], i["mealtime"], i["back_at"] or "—") for i in new_items],
            ("Outlet", "Item", "Category", "Mealtime", "Back on"), "#c9302c"))
    if restored:
        parts.append(f'<h3 style="color:#12a150">{len(restored)} item(s) back in stock</h3>' + _table(
            [(i["outlet"], i["item_name"], f'{i["downtime_minutes"]} min') for i in restored],
            ("Outlet", "Item", "Was out for"), "#12a150"))
    page = (f'<div style="font-family:Arial,sans-serif;max-width:900px"><h2>Stock-out update · {html.escape(client_name)}</h2>'
            f'<p style="color:#57606a">{when}</p>{"".join(parts)}</div>')
    send_email(_recipients(client_id, "email"), f"[{client_name}] {len(new_items)} out of stock, {len(restored)} back", page)

    if new_items:
        by_outlet: dict[str, list[str]] = {}
        for i in new_items:
            by_outlet.setdefault(i["outlet"], []).append(i["item_name"])
        details = "  |  ".join(f'{o}: {", ".join(n[:3])}{f" +{len(n) - 3} more" if len(n) > 3 else ""}' for o, n in by_outlet.items())
        for phone in _recipients(client_id, "whatsapp"):
            send_whatsapp(phone, f"{client_name} (OOS)", f"{len(new_items)} items across {len(by_outlet)}", when, details)


def incident(kind: str, message: str, action: str = "") -> None:
    """Tell the ops team a collector is stuck. Same kind is sent at most once an hour."""
    now = time.time()
    if now - _incident_sent.get(kind, 0) < INCIDENT_COOLDOWN_SEC:
        return
    _incident_sent[kind] = now
    to = [e.strip() for e in os.getenv("ALERT_OPS_EMAILS", "").split(",") if e.strip()]
    send_email(to, f"[Codeonto collector] {kind}",
               f'<div style="font-family:Arial,sans-serif"><h2 style="color:#c9302c">{html.escape(kind)}</h2>'
               f"<p>{html.escape(message)}</p><p><b>What to do:</b> {html.escape(action)}</p></div>")
