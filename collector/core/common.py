"""Shared by every collector: config from .env, logging, safe session writes, optional server push."""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR") or PROJECT_DIR / "sessions").expanduser()
LOG_FILE = PROJECT_DIR / "logs" / "collector.log"


class ConfigError(Exception):
    pass


class _RecentLines(logging.Handler):
    """Keeps this process's last log lines (with tracebacks) in memory, so an alert mail can carry the log."""

    def __init__(self, size: int):
        from collections import deque

        super().__init__(logging.INFO)
        self.lines = deque(maxlen=size)

    def emit(self, record):
        try:
            self.lines.append(self.format(record))
        except Exception:
            pass


_recent = _RecentLines(int(os.getenv("ALERT_LOG_LINES") or 80))


def recent_log() -> str:
    """The last ALERT_LOG_LINES lines this job logged (newest last)."""
    return "\n".join(_recent.lines)


def setup_logging() -> logging.Logger:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8"), _recent],
    )
    return logging.getLogger("collector")


log = logging.getLogger("collector")


def require_env(*names: str) -> dict[str, str]:
    """Read required settings; fail with one message listing everything missing."""
    values = {n: os.getenv(n, "").strip() for n in names}
    missing = [n for n, v in values.items() if not v]
    if missing:
        raise ConfigError(f"Missing in collector/.env: {', '.join(missing)}")
    return values


def account_key(account: str) -> str:
    """'mn' -> 'MN', 'main-1' -> 'MAIN_1': used as the env var infix for that account."""
    key = "".join(c if c.isalnum() else "_" for c in account.strip()).upper()
    if not key:
        raise ConfigError("Account name is empty")
    return key


def session_path(platform: str, account: str) -> Path:
    return SESSIONS_DIR / f"{platform}_{account.lower()}.json"


def save_session(path: Path, data: dict, stamp: bool = True) -> None:
    """Write atomically (never leave a half-written file for readers) and readable by owner only.

    stamp=False keeps the file exactly as given (e.g. a flat cookie dict where any extra key
    would be sent as a cookie)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if stamp:
        data = {**data, "updated_at": datetime.now().isoformat(timespec="seconds")}
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    log.info("Session saved -> %s", path)


def push_to_server(url_env: str, data: dict) -> bool:
    """Optionally POST the session to the central server. Skipped unless both URL and secret are set."""
    url, secret = os.getenv(url_env, "").strip(), os.getenv("COOKIE_PUSH_SECRET", "").strip()
    if not url:
        log.info("Server push skipped (%s not set)", url_env)
        return False
    if not secret:
        log.warning("Server push skipped: COOKIE_PUSH_SECRET is empty (refusing to push unauthenticated)")
        return False
    import requests

    try:
        resp = requests.post(url, json=data, headers={"X-Secret": secret}, timeout=15)
        if resp.ok:
            log.info("Session pushed to server")
            return True
        log.error("Server push failed: HTTP %s", resp.status_code)
    except Exception as e:
        log.error("Server push error: %s", e)
    return False
