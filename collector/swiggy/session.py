"""Swiggy partner portal session refresh (phone + password).

Logs in with Playwright, captures the access_token the portal sends on API calls, lists
the restaurants the account can access, and saves sessions/swiggy_<account>.json:
    {"access_token": ..., "cookies": {...}, "outlets": [{"rest_id", "rest_name", "area_name"}], "updated_at": ...}

Per-account settings in .env (account "mn" -> SWIGGY_MN_*):
    SWIGGY_MN_PHONE       login mobile number / restaurant id
    SWIGGY_MN_PASSWORD    login password
Shared: SWIGGY_PUSH_URL + COOKIE_PUSH_SECRET (optional server push).
"""

import tempfile

from core import db
from core.common import ConfigError, account_key, log, push_to_server, require_env

ORDERS_URL = "https://partner.swiggy.com/orders"
# Pages that make the portal call vhc-composer with a full-privilege token
TOKEN_PAGES = ["https://partner.swiggy.com/finance/payouts", "https://partner-self-client.swiggy.com/business-metrics"]
COMPOSER_URL = "https://vhc-composer.swiggy.com/query"


def config(account: str) -> dict:
    k = account_key(account)
    cfg = require_env(f"SWIGGY_{k}_PHONE", f"SWIGGY_{k}_PASSWORD")
    return {"phone": cfg[f"SWIGGY_{k}_PHONE"], "password": cfg[f"SWIGGY_{k}_PASSWORD"]}


def list_restaurants(token: str, cookies: dict) -> list[dict]:
    import requests

    resp = requests.post(
        COMPOSER_URL, params={"query": "GetUser"}, timeout=30,
        headers={"Content-Type": "application/json", "access_token": token},
        cookies=cookies,
        json={
            "query": "query GetUser($input: GetUserRequest) { get_user(input: $input) "
                     "{ restaurants { rest_id rest_name area_name } } }",
            "variables": {"input": {"include_dineout": True}},
            "operationName": "GetUser",
        },
    )
    resp.raise_for_status()
    rows = ((resp.json().get("data") or {}).get("get_user") or {}).get("restaurants") or []
    return [{"rest_id": str(r["rest_id"]), "rest_name": r.get("rest_name"), "area_name": r.get("area_name")}
            for r in rows if r.get("rest_id")]


def login(cfg: dict, headless: bool) -> dict | None:
    from playwright.sync_api import sync_playwright

    captured = {"token": None}
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=tempfile.mkdtemp(prefix="swiggy_session_"), headless=headless,
            viewport={"width": 1920, "height": 1080},
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()

            def sniff(request):
                token = request.headers.get("access_token")
                if token and len(token) > 10:
                    captured["token"] = token

            page.on("request", sniff)
            page.goto(ORDERS_URL)
            page.wait_for_timeout(8000)
            try:
                page.wait_for_selector('input[id="Enter Restaurant ID / Mobile number"]', timeout=5000)
                log.info("Logging in")
                page.fill('input[id="Enter Restaurant ID / Mobile number"]', cfg["phone"])
                page.click('button[data-testid="submit-phone-number"]')
                page.wait_for_selector('button[data-testid="login-with-password"]')
                page.click('button[data-testid="login-with-password"]')
                page.wait_for_selector('input[id="Enter your password"]')
                page.fill('input[id="Enter your password"]', cfg["password"])
                page.click('button[data-testid="Login-Button"]')
                page.wait_for_load_state("networkidle")
            except Exception as e:
                log.info("Login form not shown (already logged in?): %s", type(e).__name__)
            page.wait_for_timeout(5000)

            for url in TOKEN_PAGES:
                if captured["token"]:
                    break
                try:
                    page.goto(url)
                    page.wait_for_timeout(8000)
                except Exception as e:
                    log.warning("Could not open %s: %s", url, e)

            if not captured["token"]:
                log.error("access_token was not seen in any request")
                return None
            log.info("access_token captured")
            cookies = {c["name"]: c["value"] for c in context.cookies()}
            return {"access_token": captured["token"], "cookies": cookies}
        finally:
            context.close()


def run(account: str, headless: bool = False) -> bool:
    try:
        cfg = config(account)
    except ConfigError as e:
        log.error("%s", e)
        return False
    log.info("Swiggy session refresh: account '%s'", account)
    session = login(cfg, headless)
    if not session:
        log.error("Swiggy refresh failed for '%s'", account)
        return False
    try:
        session["outlets"] = list_restaurants(session["access_token"], session["cookies"])
        log.info("%s restaurants accessible", len(session["outlets"]))
    except Exception as e:
        log.warning("Session saved, but listing restaurants failed: %s", e)
        session["outlets"] = []
    log.info("Swiggy session for '%s' saved to the %s", account, db.save_account_session("swiggy", account, session))
    push_to_server("SWIGGY_PUSH_URL", session)
    return True
