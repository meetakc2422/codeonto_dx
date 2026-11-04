"""Save a Zomato merchant-dashboard session into .env (never into git).

Takes the cookie export JSON ({"name": "value", ...}) on stdin, e.g. copied from a
cookie-editor extension, and writes ZOMATO_SESSION_<NAME>=... into .env.

    pbpaste | ./.venv/bin/python scripts/set_zomato_session.py MAIN

Then link listings to it with platform_connections.credentials_ref = 'env:ZOMATO_SESSION_MAIN'.
CSRF headers default to the `csrf` and `__Host-zmxcsrft` cookies; override with
--csrf / --mx-csrf using the x-zomato-csrft / x-zomato-mx-csrf-token values from a
"Copy as cURL" request if Zomato rejects the defaults.
"""

import argparse
import json
import sys
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="suffix for the env var, e.g. MAIN -> ZOMATO_SESSION_MAIN")
    parser.add_argument("--csrf", help="x-zomato-csrft header value")
    parser.add_argument("--mx-csrf", help="x-zomato-mx-csrf-token header value")
    args = parser.parse_args()

    cookies = json.load(sys.stdin)
    if not isinstance(cookies, dict) or not cookies:
        sys.exit("Expected a JSON object of cookie name -> value on stdin")
    session = {
        "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
        "csrf_token": args.csrf or cookies.get("csrf", ""),
        "mx_csrf_token": args.mx_csrf or cookies.get("__Host-zmxcsrft", ""),
    }

    var = f"ZOMATO_SESSION_{args.name.upper()}"
    line = f"{var}={json.dumps(session)}"
    lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    lines = [l for l in lines if not l.startswith(f"{var}=")] + [line]
    ENV_FILE.write_text("\n".join(lines) + "\n")
    ENV_FILE.chmod(0o600)
    print(f"Saved {var} to {ENV_FILE} ({len(cookies)} cookies). Values not printed.")


if __name__ == "__main__":
    main()
