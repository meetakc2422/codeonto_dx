"""Read and write encrypted platform sessions, and turn what people paste (a copied cURL, cookie JSON) into one."""

import json
import re

from . import crypto
from .models import PlatformSession

# headers set per request, never stored
PER_REQUEST = {"content-length", "host", "x-request-id", "x-zomato-trace-id", "accept-encoding", "x-present-lat", "x-present-long",
               "x-user-defined-lat", "x-user-defined-long", "x-present-horizontal-accuracy", "x-city-id", "x-o2-city-id", "x-location-token",
               "traceparent", "tracestate", "newrelic"}


def get(platform: str, kind: str, account=None) -> dict | None:
    s = PlatformSession.objects.filter(platform=platform, kind=kind, account=account).first()
    return json.loads(crypto.decrypt(s.data_enc)) if s else None


def put(platform: str, kind: str, data: dict, account=None, by: str = "") -> PlatformSession:
    s = PlatformSession.objects.filter(platform=platform, kind=kind, account=account).first() or PlatformSession(platform=platform, kind=kind, account=account)
    s.data_enc, s.updated_by = crypto.encrypt(json.dumps(data)), by[:150]
    s.save()
    return s


def _curl_headers(text: str) -> dict:
    headers = {}
    for _, raw in re.findall(r"""-H\s+(['"])(.*?)\1""", text, re.S):
        name, _, value = raw.partition(":")
        if name.strip():
            headers[name.strip().lower()] = value.strip()
    m = re.search(r"""(?:-b|--cookie)\s+(['"])(.*?)\1""", text, re.S)
    if m:
        headers["cookie"] = m.group(2)
    return headers


def _cookie_dict(header: str) -> dict:
    out = {}
    for part in (header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k:
            out[k] = v
    return out


def parse(platform: str, kind: str, text: str, previous: dict | None = None) -> dict:
    """What someone pasted -> the session shape the collector and site expect. Raises ValueError with a reason."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Paste a copied request (cURL) or the session JSON.")
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"That JSON doesn't parse: {e}") from e
        if kind == "merchant" and platform == "swiggy" and isinstance(data, dict) and not data.get("access_token"):
            raise ValueError("A Swiggy session needs access_token.")
        return data if isinstance(data, dict) else {"cookies": data}  # a cookie list -> {"cookies": [...]}
    if "curl" not in text.lower():
        raise ValueError("Paste the whole request copied as cURL, or the session JSON.")
    h = _curl_headers(text)
    if kind == "merchant":
        if platform == "zomato":
            cookies = _cookie_dict(h.get("cookie", ""))
            if not cookies:
                raise ValueError("No cookies in that cURL: copy a request to zomato.com from the logged-in merchant dashboard.")
            return cookies
        token = h.get("access_token") or h.get("authorization", "").replace("Bearer", "").strip()
        if not token:
            raise ValueError("No access_token header in that cURL: copy a request from the logged-in Swiggy partner app or dashboard.")
        return {"cookies": _cookie_dict(h.get("cookie", "")), "access_token": token, "outlets": (previous or {}).get("outlets", [])}
    headers = {k: v for k, v in h.items() if k not in PER_REQUEST}
    if platform == "zomato" and "x-zomato-access-token" not in headers:
        raise ValueError("No x-zomato-access-token in that cURL: copy a request the Zomato app made to api.zomato.com.")
    out = {"headers": headers}
    if kind == "merchant_app":
        m = re.search(r'res_id\\?"\s*:\s*\\?"(\d+)', text)
        out["res_id"] = m.group(1) if m else (previous or {}).get("res_id")
    return out
