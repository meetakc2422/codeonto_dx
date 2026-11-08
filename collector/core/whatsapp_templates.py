"""Create the WhatsApp message templates the alerts use, in this .env's Meta WhatsApp Business account.

    python -m core.whatsapp_templates            # show which templates exist and which would be created
    python -m core.whatsapp_templates --apply    # submit the missing ones to Meta for approval

Templates belong to one WhatsApp Business account, so every client with its own WhatsApp number needs its own copies.
The names and variable order match core/notify.py; a template that already exists is never changed.
Picture-card templates (image header) are not created here: they need a sample image uploaded first. Until they
exist, set WHATSAPP_IMAGE_CARDS=0 so alerts go out as text.

.env:
    WHATSAPP_BEARER_TOKEN           token with whatsapp_business_management (the one alerts already use)
    WHATSAPP_BUSINESS_ACCOUNT_ID    the WABA id: WhatsApp Manager -> Overview (not the phone number id); WHATSAPP_WABA_ID works too
    WHATSAPP_TEMPLATE_LANG          default en"""

import sys

import requests

from . import config as cfg
from .common import ConfigError, log, require_env, setup_logging

# name setting, default name, body, sample values ({{n}} in order; Meta needs one sample per variable)
TEMPLATES = [
    ("WHATSAPP_TEMPLATE_OOS", "zomato_item_oos_alert",
     "Stock alert for {{1}}: {{2}} item(s) are out of stock across {{3}} outlet(s) as of {{4}}.\n\n{{5}}\n\nOpen your dashboard for details.",
     ["Foodiness", "12", "2", "5:29 pm, 8 Nov", "Sector 63: Paneer Tikka, Dal Makhani"]),
    ("WHATSAPP_TEMPLATE_OOS_BACK", "zomato_item_recovery_alert",
     "Back in stock for {{1}}: {{2}} item(s) are available again across {{3}} outlet(s) as of {{4}}.\n\n{{5}}\n\nOpen your dashboard for details.",
     ["Foodiness", "5", "1", "6:10 pm, 8 Nov", "Sector 63: Paneer Tikka"]),
    ("WHATSAPP_TEMPLATE_OFFLINE", "zomato_outage_alert",
     "Outage alert for {{1}}: {{2}} outlet(s) went offline on Zomato at {{3}}.\n\n{{4}}\n\nPlease check the outlet or open your dashboard for details.",
     ["Foodiness", "1", "5:29 pm, 8 Nov", "Sector 63 (Noida)"]),
    ("WHATSAPP_TEMPLATE_ONLINE", "zomato_recovery_alert",
     "Good news for {{1}}: {{2}} outlet(s) are back online on Zomato as of {{3}}.\n\n{{4}}\n\nOpen your dashboard for details.",
     ["Foodiness", "1", "6:02 pm, 8 Nov", "Sector 63 (Noida), was offline 33 min"]),
    ("WHATSAPP_TEMPLATE_GENERIC", "restaurant_offline_alert",
     "Hello, this is an automated alert from your restaurant monitoring service. We noticed {{1}} for {{2}} "
     "at {{3}} on the {{4}} platform.\n\nHere are the details:\n{{5}}\n\n"
     "Please open your dashboard to review this alert and take action if needed. "
     "You will keep receiving these updates whenever something needs your attention.",
     ["Low reviews (3)", "Foodiness", "5:29 pm, 8 Nov", "Zomato", "Sector 63: 2 star review about late delivery"]),
]


def _api(path: str) -> str:
    return f"{cfg.text('WHATSAPP_API_BASE', 'https://graph.facebook.com/v20.0')}/{path}"


def existing(waba: str, token: str) -> dict:
    """name -> status of every template in the account."""
    out, url, params = {}, _api(f"{waba}/message_templates"), {"fields": "name,status,language", "limit": 200}
    while url:
        r = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if r.status_code != 200:
            raise ConfigError(f"Couldn't list templates (HTTP {r.status_code}): {r.text[:300]}")
        data = r.json()
        out |= {t["name"]: f"{t['status']} ({t.get('language', '?')})" for t in data.get("data", [])}
        url, params = (data.get("paging") or {}).get("next"), None
    return out


def create(waba: str, token: str, name: str, body: str, sample: list[str], lang: str) -> str:
    payload = {"name": name, "category": "UTILITY", "language": lang,
               "components": [{"type": "BODY", "text": body, "example": {"body_text": [sample]}}]}
    r = requests.post(_api(f"{waba}/message_templates"), json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code not in (200, 201):
        return f"FAILED (HTTP {r.status_code}): {r.text[:300]}"
    return f"submitted, status {r.json().get('status', '?')}"


def main(apply: bool) -> int:
    setup_logging()
    import os
    if not os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") and os.getenv("WHATSAPP_WABA_ID"):  # same id, shorter name
        os.environ["WHATSAPP_BUSINESS_ACCOUNT_ID"] = os.environ["WHATSAPP_WABA_ID"]
    try:
        env = require_env("WHATSAPP_BEARER_TOKEN", "WHATSAPP_BUSINESS_ACCOUNT_ID")
        have = existing(env["WHATSAPP_BUSINESS_ACCOUNT_ID"], env["WHATSAPP_BEARER_TOKEN"])
    except ConfigError as e:
        log.error("%s", e)
        return 2
    lang = cfg.text("WHATSAPP_TEMPLATE_LANG", "en")
    for setting, default, body, sample in TEMPLATES:
        name = cfg.text(setting, default)
        if name in have:
            log.info("%-28s already exists: %s", name, have[name])
        elif apply:
            log.info("%-28s %s", name, create(env["WHATSAPP_BUSINESS_ACCOUNT_ID"], env["WHATSAPP_BEARER_TOKEN"], name, body, sample, lang))
        else:
            log.info("%-28s missing: would create (run with --apply)", name)
    if apply:
        log.info("Meta reviews new templates, usually within minutes. Run this again to see their status (APPROVED / REJECTED).")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
