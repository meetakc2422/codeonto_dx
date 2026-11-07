"""Zomato partner dashboard session refresh (email OTP).

Logs in with Playwright, reads the OTP from the login mailbox over IMAP, and saves the
cookies to sessions/zomato_<account>.json as a flat {"name": "value"} dict (the format
Codeonto's Zomato connector and the pipeline scrapers read).

Per-account settings in .env (account "main" -> ZOMATO_MAIN_*):
    ZOMATO_MAIN_EMAIL            Zomato login email (OTP goes to this mailbox)
    ZOMATO_MAIN_IMAP_PASSWORD    mailbox password for IMAP
    ZOMATO_MAIN_IMAP_HOST        optional: this login's own mail server (e.g. imap.gmail.com), else the shared one
Shared: ZOMATO_IMAP_HOST (default imap.secureserver.net), ZOMATO_IMAP_PORT (993),
        ZOMATO_PUSH_URL + COOKIE_PUSH_SECRET (optional server push).
"""

import email
import imaplib
import os
import re
import time
from datetime import datetime

from core import db
from core.common import ConfigError, account_key, log, push_to_server, require_env, PROJECT_DIR

LOGIN_URL = "https://www.zomato.com/partners/o2-business/"
OTP_SUBJECT = "Log in to Zomato"
OTP_MAX_AGE_SECONDS = 360

# The login modal renders in a separate context where DOM selectors return no boxes,
# so these are screen coordinates for Playwright's default 1280x720 viewport.
CLICK_CONTINUE_WITH_EMAIL = (640, 405)
CLICK_EMAIL_INPUT = (640, 398)
CLICK_SEND_OTP = (640, 470)


def config(account: str) -> dict:
    k = account_key(account)
    cfg = require_env(f"ZOMATO_{k}_EMAIL", f"ZOMATO_{k}_IMAP_PASSWORD")
    return {
        "email": cfg[f"ZOMATO_{k}_EMAIL"],
        "imap_password": cfg[f"ZOMATO_{k}_IMAP_PASSWORD"],
        # each login may use its own mail server (e.g. a Gmail address: imap.gmail.com + an app password);
        # otherwise the shared ZOMATO_IMAP_HOST / ZOMATO_IMAP_PORT
        "imap_host": os.getenv(f"ZOMATO_{k}_IMAP_HOST") or os.getenv("ZOMATO_IMAP_HOST", "imap.secureserver.net"),
        "imap_port": int(os.getenv(f"ZOMATO_{k}_IMAP_PORT") or os.getenv("ZOMATO_IMAP_PORT", "993")),
    }


def _extract_otp(body: str) -> str | None:
    m = re.search(r"(?:OTP|one.time.password|code|password)[^a-zA-Z0-9]*([A-Z0-9]{6})\b", body, re.IGNORECASE)
    if not m:
        m = next((x for x in re.finditer(r"\b([A-Z0-9]{6})\b", body) if sum(c.isalpha() for c in x.group(1)) >= 2), None)
    if not m:
        m = re.search(r"\b(\d{6})\b", body)
    return m.group(1) if m else None


def _message_text(msg) -> str:
    plain, html = "", ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        ctype = part.get_content_type()
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        text = payload.decode(errors="ignore")
        if ctype == "text/plain" and not plain:
            plain = text
        elif ctype == "text/html" and not html:
            html = text
    return plain or re.sub(r"<[^>]+>", " ", html)


def fetch_otp(cfg: dict, attempts: int = 6, wait: int = 10) -> str | None:
    """Newest 'Log in to Zomato' email from the last few minutes. The OTP itself is never logged."""
    for attempt in range(1, attempts + 1):
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"])
            mail.login(cfg["email"], cfg["imap_password"])
            mail.select("inbox")
            status, found = mail.search(None, f'(UNSEEN SUBJECT "{OTP_SUBJECT}")')
            if status != "OK" or not found[0]:
                status, found = mail.search(None, f'(SUBJECT "{OTP_SUBJECT}")')
            candidates = []
            if status == "OK" and found[0]:
                for msg_id in reversed(found[0].split()[-5:]):
                    _, data = mail.fetch(msg_id, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    sent = email.utils.parsedate_tz(msg.get("Date"))
                    if not sent:
                        continue
                    age = (datetime.now() - datetime.fromtimestamp(email.utils.mktime_tz(sent))).total_seconds()
                    if age <= OTP_MAX_AGE_SECONDS:
                        candidates.append((age, msg))
            if candidates:
                otp = _extract_otp(_message_text(min(candidates, key=lambda c: c[0])[1]))
                if otp:
                    log.info("OTP received (attempt %s)", attempt)
                    return otp
            log.info("OTP not in mailbox yet, retrying in %ss (%s/%s)", wait, attempt, attempts)
        except Exception as e:
            log.warning("Mailbox read failed (attempt %s): %s", attempt, e)
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass
        time.sleep(wait)
    return None


def login(account: str, cfg: dict, headless: bool) -> dict | None:
    from playwright.sync_api import sync_playwright

    profile_dir = PROJECT_DIR / "playwright_data" / f"zomato_{account.lower()}"
    profile_dir.mkdir(parents=True, exist_ok=True)
    for lock in ("SingletonLock", "SingletonCookie", "SingletonSocket", "lock", "Parent.lock"):
        (profile_dir / lock).unlink(missing_ok=True)

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir), headless=headless,
            # Zomato's CDN returns ERR_HTTP2_PROTOCOL_ERROR without this
            args=["--disable-http2", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                log.warning("Page load warning: %s (continuing)", e)
            page.wait_for_timeout(5000)

            if "login" not in page.url and not page.get_by_role("button", name="Login").is_visible():
                log.info("Saved browser profile is still logged in")
                return {c["name"]: c["value"] for c in context.cookies()}

            log.info("Logging in as %s", cfg["email"])
            page.get_by_role("button", name="Login").click()
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(3000)
            page.mouse.click(*CLICK_CONTINUE_WITH_EMAIL)
            page.wait_for_timeout(3000)
            page.mouse.click(*CLICK_EMAIL_INPUT)
            page.wait_for_timeout(500)
            page.keyboard.type(cfg["email"], delay=80)
            page.wait_for_timeout(1000)
            page.mouse.click(*CLICK_SEND_OTP)
            page.wait_for_timeout(10000)

            otp = fetch_otp(cfg)
            if not otp:
                log.error("No OTP received within the time limit")
                return None
            for ch in otp.strip():
                page.keyboard.type(ch)
                page.wait_for_timeout(300)
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass
            page.wait_for_timeout(15000)
            log.info("Login complete")
            return {c["name"]: c["value"] for c in context.cookies()}
        finally:
            context.close()


def run(account: str, headless: bool = False) -> bool:
    try:
        cfg = config(account)
    except ConfigError as e:
        log.error("%s", e)
        return False
    log.info("Zomato session refresh: account '%s'", account)
    cookies = login(account, cfg, headless)
    if not cookies:
        log.error("Zomato refresh failed for '%s'", account)
        return False
    log.info("Zomato session for '%s' saved to the %s", account, db.save_account_session("zomato", account, cookies, stamp=False))
    push_to_server("ZOMATO_PUSH_URL", cookies)
    return True
