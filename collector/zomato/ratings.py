"""Zomato platform ratings -> metric_daily (listing_rating, rating_count, total_reviews), one call per login.

The merchant app's "Restaurant ratings" screen (merchant-gw/app/reviews/get-restaurant-ratings) lists every outlet the
login can see with its rating, how many ratings that rating is built on, and how many written reviews it has. Each
mapped outlet gets today's listing_rating (weight = number of ratings, so the brand figure is a weighted average) and
total_reviews.

It speaks as the merchant app, so it needs that app's headers, saved per login:
    python -m zomato.ratings import <account> <file with the request copied as cURL>
Then:  python run.py zomato ratings
"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

from core import config as cfg, db
from core.common import ConfigError, log, require_env, save_session, session_path

URL = cfg.text("ZOMATO_RATINGS_URL", "https://api.zomato.com/merchant-gw/app/reviews/get-restaurant-ratings")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
SKIP_HEADERS = {"content-length", "host", "x-request-id", "x-zomato-trace-id", "accept-encoding"}


def _app_path(account: str):
    return session_path("zomato_app", account)


def import_curl(account: str, text: str) -> int:
    """Save the -H headers of a copied merchant-app request for one login."""
    headers = {}
    for _, raw in re.findall(r"""-H\s+(['"])(.*?)\1""", text, re.S):
        name, _, value = raw.partition(":")
        if name.strip() and name.strip().lower() not in SKIP_HEADERS:
            headers[name.strip().lower()] = value.strip()
    if "x-zomato-access-token" not in headers:
        raise ConfigError("No x-zomato-access-token in that cURL: copy a merchant-app request to api.zomato.com")
    m = re.search(r'res_id\\?"\s*:\s*\\?"(\d+)', text)
    data = {"headers": headers, "res_id": m.group(1) if m else None}
    try:  # the database copy is what every machine reads; the file stays as a fallback
        with db.transaction() as cur:
            acc = db.get_account(cur, "zomato", account)
        db.store_session(acc, "zomato", "merchant_app", data)
    except Exception as e:
        log.warning("zomato ratings: couldn't save %s's merchant-app session to the database (%s); saved to the file only", account, e)
    save_session(_app_path(account), data)
    return len(headers)


def _count(text: str) -> int | None:
    """'3.4k ratings' -> 3400, '720 reviews' -> 720, '1.2L' -> 120000."""
    m = re.match(r"\s*([\d.,]+)\s*([kKlLmM]?)", text or "")
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    return round(n * {"k": 1e3, "l": 1e5, "m": 1e6}.get(m.group(2).lower(), 1))


def _texts(o, out):
    if isinstance(o, dict):
        if isinstance(o.get("text"), str) and o["text"].strip():
            out.append(o["text"].strip())
        for v in o.values():
            _texts(v, out)
    elif isinstance(o, list):
        for v in o:
            _texts(v, out)
    return out


def parse(resp: dict) -> list[dict]:
    """[{res_id, name, rating, ratings, reviews}] from the ratings screen."""
    rows = []
    for item in resp.get("results") or []:
        t = _texts(item, [])
        rid = next((m.group(1) for x in t for m in [re.match(r"ID:\s*(\d+)", x)] if m), None)
        if not rid:
            continue
        ratings = next((_count(x) for x in t if re.search(r"\bratings?\b", x, re.I) and re.match(r"\s*[\d.]", x)), None)
        reviews = next((_count(x) for x in t if re.search(r"\breviews?\b", x, re.I) and re.match(r"\s*[\d.]", x)), None)
        rating = next((float(x) for x in t if re.fullmatch(r"[0-5](\.\d)?", x)), None)
        rows.append({"res_id": rid, "name": t[0], "rating": rating, "ratings": ratings, "reviews": reviews})
    return rows


def fetch(headers: dict, any_res_id: str) -> list[dict]:
    body = {"postback_params": json.dumps({"screen_name": "reviews_home_page"}, separators=(",", ":")), "input": {}, "res_id": str(any_res_id)}
    resp = requests.post(URL, headers={**headers, "content-type": "application/json; charset=utf-8"}, json=body, timeout=cfg.http_timeout())
    if resp.status_code in (401, 403):
        raise PermissionError("Zomato merchant-app session expired; copy a fresh request and run `python -m zomato.ratings import <account> <file>`")
    resp.raise_for_status()
    return parse(resp.json())


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    require_env("CODEONTO_DATABASE_URL")
    today = datetime.now(IST).date()
    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       WHERE bo.is_active AND z.is_active""")
        stores = cur.fetchall()
        cur.execute("SELECT code, id FROM kpis WHERE code IN ('listing_rating', 'total_reviews', 'rating_count')")
        kpi = {r["code"]: r["id"] for r in cur.fetchall()}
    if len(kpi) < 3:
        log.error("zomato ratings: KPIs listing_rating / total_reviews / rating_count missing; run `manage.py migrate`")
        return False
    outlet_of = {str(s["res_id"]): s["outlet_id"] for s in stores}

    ok, saved, seen = True, 0, set()
    for label, acc in accs.items():
        path = _app_path(label)
        saved_session = db.load_session(acc, "merchant_app") or (json.loads(path.read_text()) if path.exists() else None)
        if not saved_session:
            log.warning("zomato ratings %s: no merchant-app session (Sessions page, or %s); skipping. Import one with `python -m zomato.ratings import %s <curl file>`",
                        label, path.name, label)
            continue
        own = [str(s["res_id"]) for s in stores if s["account_id"] == acc["id"]] or list(outlet_of)
        headers = saved_session["headers"]
        if saved_session.get("res_id"):  # the outlet the copied request was made from: known to open for this login
            own = [saved_session["res_id"], *[r for r in own if r != saved_session["res_id"]]]
        try:
            # the screen is opened "from" one outlet; a refusal can mean this login can't open that outlet, so try a few
            for tries, rid in enumerate(own[:5], 1):
                try:
                    rows = fetch(headers, rid)
                    break
                except PermissionError:
                    if tries == min(5, len(own)):
                        raise
        except PermissionError as e:
            log.error("zomato ratings %s: %s", label, e)
            ok = False
            continue
        except Exception as e:
            log.exception("zomato ratings %s failed: %s", label, e)
            ok = False
            continue
        n = 0
        with db.transaction() as cur:
            for r in rows:
                oid = outlet_of.get(r["res_id"])
                if not oid or r["res_id"] in seen or r["rating"] is None:
                    continue
                seen.add(r["res_id"])
                for code, value, weight in (("listing_rating", r["rating"], r["ratings"] or 1), ("total_reviews", r["reviews"], 1),
                                            ("rating_count", r["ratings"], 1)):
                    if value is None:
                        continue
                    cur.execute("""INSERT INTO metric_daily (outlet_id, platform, kpi_id, metric_date, value, weight, updated_at)
                                   VALUES (%s, 'zomato', %s, %s, %s, %s, now())
                                   ON CONFLICT (outlet_id, platform, kpi_id, metric_date)
                                   DO UPDATE SET value = EXCLUDED.value, weight = EXCLUDED.weight, updated_at = now()""",
                                (oid, kpi[code], today, value, weight))
                n += 1
        saved += n
        log.info("zomato ratings %s: %s outlets listed, %s mapped and saved", label, len(rows), n)
    missing = len(set(outlet_of) - seen)
    log.info("zomato ratings: %s outlets saved; %s mapped outlets not listed by any login", saved, missing)
    return ok


if __name__ == "__main__":
    from core.common import setup_logging
    setup_logging()
    if len(sys.argv) == 4 and sys.argv[1] == "import":
        print(f"saved {import_curl(sys.argv[2], open(sys.argv[3]).read())} headers for {sys.argv[2]}")
    else:
        print("usage: python -m zomato.ratings import <account> <curl file>")
