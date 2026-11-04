"""Collector's access to the Codeonto database (CODEONTO_DATABASE_URL).

The collector writes catalog rows (zomato_outlets, swiggy_outlets, google_locations) and
account sync times; Django owns the schema (migrations) and everything else.
"""

import json
from contextlib import contextmanager
from pathlib import Path

from .common import PROJECT_DIR, ConfigError, require_env


@contextmanager
def transaction():
    """One connection + transaction; commits on success, rolls back on any error."""
    import psycopg
    from psycopg.rows import dict_row

    url = require_env("CODEONTO_DATABASE_URL")["CODEONTO_DATABASE_URL"]
    with psycopg.connect(url, row_factory=dict_row) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                yield cur


def get_account(cur, platform: str, label: str) -> dict:
    """The platform_accounts row for a collector account (label = the account name, e.g. 'mn')."""
    cur.execute(
        "SELECT id, label, credentials_ref, is_active, client_id, only_ids FROM platform_accounts WHERE platform_id = %s AND label = %s",
        (platform, label),
    )
    row = cur.fetchone()
    if not row:
        raise ConfigError(f"No platform account '{label}' for {platform}. Add it in Codeonto admin → Platform accounts.")
    if not row["is_active"]:
        raise ConfigError(f"Platform account {platform}/{label} is inactive")
    return row


def load_credentials(account: dict) -> dict:
    """The login behind a platform account: a session/cookie file (file:/path, or file:sessions/x.json relative to
    the collector folder) or, for clients who connected Google from
    the dashboard, an encrypted token in the database (db:google:<connection id>)."""
    ref = account["credentials_ref"] or ""
    if ref.startswith("db:google:"):
        return _google_connection(account, int(ref.rsplit(":", 1)[1]))
    if not ref.startswith("file:"):
        raise ConfigError(f"Account {account['label']}: credentials_ref must be file:/path or db:google:<id> (got '{ref or 'empty'}')")
    path = Path(ref[5:]).expanduser()
    if not path.is_absolute():  # file:sessions/x.json: relative to the collector folder, so one database row works on any machine
        path = PROJECT_DIR / path
    if not path.exists():
        raise ConfigError(f"Account {account['label']}: session file not found: {path}")
    return json.loads(path.read_text())


def _google_connection(account: dict, connection_id: int) -> dict:
    """Decrypt a connected client's Google refresh token into the dict the Google collectors expect."""
    from cryptography.fernet import Fernet, InvalidToken

    cfg = require_env("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_TOKEN_KEY")
    with transaction() as cur:
        cur.execute("SELECT refresh_token_enc, status, scopes FROM google_connections WHERE id = %s", (connection_id,))
        row = cur.fetchone()
    if not row or row["status"] != "connected" or not row["refresh_token_enc"]:
        raise ConfigError(f"Account {account['label']}: the client disconnected Google or must reconnect it in the dashboard")
    try:
        token = Fernet(cfg["GOOGLE_TOKEN_KEY"].encode()).decrypt(row["refresh_token_enc"].encode()).decode()
    except InvalidToken:
        raise ConfigError(f"Account {account['label']}: stored Google token cannot be decrypted; GOOGLE_TOKEN_KEY differs from the dashboard's")
    return {"refresh_token": token, "client_id": cfg["GOOGLE_CLIENT_ID"], "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
            "token_uri": "https://oauth2.googleapis.com/token", "scopes": row["scopes"].split()}


def active_account_ids(cur, platform: str) -> set[int]:
    cur.execute("SELECT id FROM platform_accounts WHERE platform_id = %s AND is_active", (platform,))
    return {r["id"] for r in cur.fetchall()}


def mark_account_synced(cur, account_id: int) -> None:
    cur.execute("UPDATE platform_accounts SET last_synced_at = now(), updated_at = now() WHERE id = %s", (account_id,))
