import json
import os
from pathlib import Path

from dotenv import dotenv_values

from django.conf import settings
from apps.integrations.connectors.base import Connector
from apps.integrations.connectors.google import GoogleConnector
from apps.integrations.connectors.swiggy import SwiggyConnector
from apps.integrations.connectors.zomato import ZomatoConnector

_REGISTRY: dict[str, type[Connector]] = {
    c.platform_code: c for c in (GoogleConnector, ZomatoConnector, SwiggyConnector)
}


def resolve_credentials(credentials_ref: str | None) -> dict:
    """platform_connections.credentials_ref -> credentials dict.

    "env:VAR_NAME"  reads a JSON object from that env var (or .env).
    "file:/path"    reads a JSON file on every call, so sessions refreshed by an external
                    job (e.g. the pipeline's zomato_refresh_session.py) are picked up live.
    Replace with a secrets manager before production.
    """
    if not credentials_ref:
        return {}
    if credentials_ref.startswith("env:"):
        name = credentials_ref[4:]
        value = os.environ.get(name) or dotenv_values(settings.BASE_DIR / ".env").get(name) or "{}"
        return json.loads(value)
    if credentials_ref.startswith("file:"):
        path = Path(credentials_ref[5:]).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Credentials file not found: {path}")
        return json.loads(path.read_text())
    raise ValueError(f"Unsupported credentials_ref: {credentials_ref}")


def get_connector(platform_code: str, credentials_ref: str | None = None) -> Connector:
    cls = _REGISTRY.get(platform_code)
    if not cls:
        raise NotImplementedError(f"No connector for platform '{platform_code}'")
    return cls(resolve_credentials(credentials_ref))
