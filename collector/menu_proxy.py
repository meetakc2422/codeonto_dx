"""Zomato menu proxy: fetches competitor menus for the site from this machine's (non-datacenter) IP.

Zomato's edge (Akamai) refuses /gw/menu from cloud servers like EC2, so the site posts menu requests here instead
(settings.ZOMATO_MENU_PROXY_URL, e.g. http://<this machine>:5000). The site sends the customer-app access token with
each request, so nothing secret is stored in this file or on this machine.

    python menu_proxy.py                 # listen on 0.0.0.0:5000

    GET  /health                         -> {"status": "online"}
    POST /fetch-menu  {"res_id", "lat", "lon", "city_id", "access_token"}  -> {"status": 200, "menu_json": {...}}
    POST /fetch-res-info  (same body)                                      -> {"status": 200, "res_info_json": {...}}

.env (optional):
    MENU_PROXY_PORT      port to listen on (default 5000)
    MENU_PROXY_SECRET    when set, requests must send it in the X-Proxy-Secret header (the site sends
                         ZOMATO_MENU_PROXY_SECRET). Also allow only the site's IP to this port in Windows Firewall."""

import hmac
import json
import os
import random
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from core.common import log, setup_logging

PORT = int(os.getenv("MENU_PROXY_PORT") or 5000)
SECRET = (os.getenv("MENU_PROXY_SECRET") or "").strip()
TRIES = 3

# Zomato Android app identifiers (the same in every copy of the app; not a login)
APP_HEADERS = {
    "user-agent": "&source=android_market&version=15&device_manufacturer=motorola&device_brand=motorola&device_model=moto+g45+5G&api_version=980&app_version=v19.8.0",
    "x-zomato-client-id": "5276d7f1-910b-4243-92ea-d27e758ad02b",
    "x-access-token": "1adb5f56-08dd-4a14-7458-90aabf55c6e9",
    "x-zomato-api-key": "7749b19667964b87a3efc739e254ada2",
    "x-client-id": "zomato_android_v2",
    "x-zomato-app-version-code": "1710019800",
    "x-zomato-app-version": "980",
    "x-device-language": "en-IN",
    "x-app-language": "&lang=en&android_language=en&android_country=IN",
    "x-network-type": "wifi",
    "x-perf-class": "PERFORMANCE_HIGH",
    "x-tab-type": "TAB_TYPE_HOME",
    "x-device-pixel-ratio": "1.75",
    "x-device-width": "720",
    "x-device-height": "1600",
    "x-installer-package-name": "com.android.vending",
    "x-vpn-active": "0",
    "accept": "image/webp",
    "content-type": "application/x-www-form-urlencoded",
}


def _app_headers(lat: float, lon: float, city_id: str, token: str) -> tuple[dict, str, str]:
    la, lo, city = f"{lat:.7f}", f"{lon:.7f}", str(city_id or "1")
    headers = {**APP_HEADERS,
               "x-zomato-access-token": token,
               "x-present-lat": la, "x-present-long": lo, "x-user-defined-lat": la, "x-user-defined-long": lo,
               "x-present-horizontal-accuracy": "27", "x-city-id": city, "x-o2-city-id": city,
               "x-android-id": "".join(random.choices("0123456789abcdef", k=16)),
               "x-firebase-instance-id": "".join(random.choices("0123456789abcdef", k=32)),
               "x-appsflyer-uid": f"{int(time.time() * 1000)}-{random.randint(10**18, 10**19 - 1)}",
               "x-jumbo-session-id": f"{uuid.uuid4()}{int(time.time() * 1000)}",
               "x-zomato-uuid": str(uuid.uuid4()), "x-request-id": str(uuid.uuid4()), "x-app-session-id": str(uuid.uuid4())}
    return headers, la, lo


def fetch_menu(res_id: int, lat: float, lon: float, city_id: str, token: str) -> tuple[int, dict | None]:
    headers, la, lo = _app_headers(lat, lon, city_id, token)
    params = {"user_defined_longitude": lo, "user_defined_latitude": la, "device_lat": la, "device_lon": lo,
              "mode": "delivery", "tabId": "menu", "res_id": str(res_id)}
    body = {"has_active_group_order": "false", "type": "all", "mode": "delivery", "is_order_location": "1",
            "user_defined_latitude": la, "user_defined_longitude": lo, "device_lat": la, "device_lon": lo,
            "tabId": "menu", "previous_search_id": str(uuid.uuid4()), "resID": str(res_id)}
    url = f"https://api.zomato.com/gw/menu/{res_id}?" + urllib.parse.urlencode(params)
    status = 0
    for attempt in range(1, TRIES + 1):
        try:
            r = requests.post(url, headers=headers, data=body, timeout=15)
            status = r.status_code
            if status == 200:
                return 200, r.json()
            log.warning("menu %s: Zomato returned %s (try %s/%s)", res_id, status, attempt, TRIES)
        except (requests.RequestException, ValueError) as e:
            log.warning("menu %s: %s (try %s/%s)", res_id, e, attempt, TRIES)
        time.sleep(1.0)
    return status, None


def fetch_res_info(res_id: int, lat: float, lon: float, city_id: str, token: str) -> tuple[int, dict | None]:
    """The restaurant's info page (cuisines, address, timings)."""
    headers, _, _ = _app_headers(lat, lon, city_id, token)
    headers["content-type"] = "application/json; charset=utf-8"
    status = 0
    for attempt in range(1, TRIES + 1):
        try:
            r = requests.post(f"https://api.zomato.com/gw/menu/res_info/{res_id}", headers=headers, json={"should_fetch_res_info_from_agg": True}, timeout=15)
            status = r.status_code
            if status == 200:
                return 200, r.json()
            log.warning("res_info %s: Zomato returned %s (try %s/%s)", res_id, status, attempt, TRIES)
        except (requests.RequestException, ValueError) as e:
            log.warning("res_info %s: %s (try %s/%s)", res_id, e, attempt, TRIES)
        time.sleep(1.0)
    return status, None


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, data: dict) -> None:
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):  # route http.server's access log through ours
        log.info("menu proxy %s %s", self.address_string(), fmt % args)

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            return self._send(200, {"status": "online", "service": "menu-proxy", "timestamp": time.time()})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        route = self.path.rstrip("/")
        if route not in ("/fetch-menu", "/fetch-res-info"):
            return self._send(404, {"error": "not found"})
        if SECRET and not hmac.compare_digest(self.headers.get("X-Proxy-Secret", ""), SECRET):
            return self._send(403, {"error": "bad or missing X-Proxy-Secret"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            res_id = int(body["res_id"])
        except (ValueError, KeyError, TypeError):
            return self._send(400, {"error": "send JSON with res_id"})
        token = str(body.get("access_token") or body.get("token") or "").strip()
        if not token:
            return self._send(400, {"error": "send the customer-app access_token"})
        fetch, key = (fetch_menu, "menu_json") if route == "/fetch-menu" else (fetch_res_info, "res_info_json")
        status, data = fetch(res_id, float(body.get("lat") or 28.605), float(body.get("lon") or 77.376), str(body.get("city_id") or "1"), token)
        self._send(200 if status == 200 else 502, {"status": status, "res_id": str(res_id), key: data})


def main() -> None:
    setup_logging()
    if not SECRET:
        log.warning("MENU_PROXY_SECRET is not set: anyone who can reach port %s can use this proxy. "
                    "Set it here and ZOMATO_MENU_PROXY_SECRET on the site, and firewall the port to the site's IP.", PORT)
    log.info("Zomato menu proxy listening on 0.0.0.0:%s", PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
