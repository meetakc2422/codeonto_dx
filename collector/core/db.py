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
    if ref.startswith("db:session"):
        data = load_session(account, "merchant")
        if data is None:
            raise ConfigError(f"Account {account['label']}: no session saved in the database yet. Refresh it on the Sessions page or run `run.py <platform> session`")
        return data
    if not ref.startswith("file:"):
        raise ConfigError(f"Account {account['label']}: credentials_ref must be file:/path, db:session or db:google:<id> (got '{ref or 'empty'}')")
    path = Path(ref[5:]).expanduser()
    if not path.is_absolute():  # file:sessions/x.json: relative to the collector folder, so one database row works on any machine
        path = PROJECT_DIR / path
    if not path.exists():
        raise ConfigError(f"Account {account['label']}: session file not found: {path}")
    return json.loads(path.read_text())


def _fernet():
    from cryptography.fernet import Fernet
    return Fernet(require_env("GOOGLE_TOKEN_KEY")["GOOGLE_TOKEN_KEY"].encode())


def load_session(account: dict, kind: str) -> dict | None:
    """An account's session saved (encrypted) in platform_sessions by the Sessions page or a collector login."""
    from cryptography.fernet import InvalidToken

    with transaction() as cur:
        cur.execute("SELECT data_enc FROM platform_sessions WHERE account_id = %s AND kind = %s", (account["id"], kind))
        row = cur.fetchone()
    if not row:
        return None
    try:
        return json.loads(_fernet().decrypt(row["data_enc"].encode()).decode())
    except InvalidToken:
        raise ConfigError(f"Account {account['label']}: saved session cannot be decrypted; GOOGLE_TOKEN_KEY differs from the dashboard's")


def store_session(account: dict, platform: str, kind: str, data: dict) -> None:
    """Save (encrypted) an account's session to platform_sessions; the site and every collector read it from there."""
    import platform as _host

    enc, by = _fernet().encrypt(json.dumps(data).encode()).decode(), f"collector@{_host.node()}"[:150]
    with transaction() as cur:
        cur.execute("UPDATE platform_sessions SET data_enc = %s, updated_by = %s, updated_at = now() WHERE account_id = %s AND kind = %s",
                    (enc, by, account["id"], kind))
        if not cur.rowcount:
            cur.execute("INSERT INTO platform_sessions (platform, account_id, kind, data_enc, updated_by, updated_at) VALUES (%s, %s, %s, %s, %s, now())",
                        (platform, account["id"], kind, enc, by))
        if kind == "merchant":  # a fresh login: the account is no longer expired
            cur.execute("UPDATE platform_accounts SET session_expired_at = NULL, session_error = '' WHERE id = %s", (account["id"],))


def save_account_session(platform: str, label: str, data: dict, stamp: bool = True) -> str:
    """After a login: save the session where this account reads it from (the database for db:session accounts,
    otherwise its file, as before). Returns where it went."""
    from .common import save_session, session_path

    with transaction() as cur:
        account = get_account(cur, platform, label)
    if (account["credentials_ref"] or "").startswith("db:session"):
        store_session(account, platform, "merchant", data)
        return "database"
    save_session(session_path(platform, label), data, stamp=stamp)
    return "file"


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


def mark_session_expired(account_id: int, reason: str) -> None:
    """Flag a login the platform keeps refusing, so the site shows it to staff (banner + Sessions page). Never raises:
    a job reporting an expired session must not crash because of the report."""
    try:
        with transaction() as cur:
            cur.execute("""UPDATE platform_accounts SET session_expired_at = COALESCE(session_expired_at, now()), session_error = %s
                           WHERE id = %s""", (str(reason)[:300], account_id))
    except Exception as e:  # noqa: BLE001
        from .common import log
        log.warning("Couldn't mark account %s as expired: %s", account_id, e)


def mark_session_expired_by_label(platform: str, label: str, reason: str) -> None:
    try:
        with transaction() as cur:
            account = get_account(cur, platform, label)
        mark_session_expired(account["id"], reason)
    except Exception as e:  # noqa: BLE001
        from .common import log
        log.warning("Couldn't mark %s/%s as expired: %s", platform, label, e)
