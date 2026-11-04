"""Google Business Profile login (OAuth, business.manage scope).

First run opens a browser: log in with the Google account that manages the business
listings (your agency account, or a client's) and click Allow. The refreshable token is
saved to sessions/google_<account>.json; later runs only refresh it, no browser needed.

Settings in .env:
    GOOGLE_OAUTH_CLIENT_FILE   path to the OAuth client JSON from Google Cloud Console
                               (the client_secret_….apps.googleusercontent.com.json file)
"""

import json
import os
from pathlib import Path

from core.common import ConfigError, log, require_env, save_session, session_path

SCOPES = ["https://www.googleapis.com/auth/business.manage"]


def config(account: str) -> dict:
    path = Path(require_env("GOOGLE_OAUTH_CLIENT_FILE")["GOOGLE_OAUTH_CLIENT_FILE"]).expanduser()
    if not path.exists():
        raise ConfigError(f"GOOGLE_OAUTH_CLIENT_FILE not found: {path}")
    return {"client_file": path}


def credentials_from(data: dict):
    """Session file -> google Credentials, refreshed if expired. PermissionError if the login was revoked."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not data.get("refresh_token"):
        raise ConfigError("Google session has no refresh_token; run `run.py google session` for this account")
    creds = Credentials.from_authorized_user_info(data, SCOPES)
    if not creds.valid:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            raise PermissionError(f"Google login expired or was revoked; run `run.py google session` again ({e})") from e
    return creds


def run(account: str, headless: bool = False) -> bool:
    try:
        cfg = config(account)
    except ConfigError as e:
        log.error("%s", e)
        return False
    path = session_path("google", account)

    if path.exists():
        try:
            creds = credentials_from(json.loads(path.read_text()))
            save_session(path, json.loads(creds.to_json()))
            log.info("Google session '%s' refreshed", account)
            return True
        except PermissionError as e:
            log.warning("%s. Starting a new login.", e)

    if headless:
        log.error("Google account '%s' needs a browser login once; run without --headless on a machine with a display", account)
        return False

    from google_auth_oauthlib.flow import InstalledAppFlow

    log.info("Opening the browser for Google login (account '%s'). Use the Google account that manages the listings.", account)
    flow = InstalledAppFlow.from_client_secrets_file(str(cfg["client_file"]), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline", open_browser=True)
    save_session(path, json.loads(creds.to_json()))
    os.chmod(path, 0o600)
    log.info("Google login saved for '%s'", account)
    return True
