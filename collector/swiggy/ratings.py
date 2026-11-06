"""Swiggy platform ratings -> metric_daily, from the partner app's restaurantRatings query (100 outlets per call).

Per mapped outlet, today:
    listing_rating        overall Swiggy rating (weight = number of ratings, so brand figures are weighted)
    rating_count          how many ratings that is built on
    weekly_rating         this week's rating (weight = this week's ratings), when there were any
    weekly_rating_count   how many ratings came in this week
Uses the access_token already in each Swiggy session file; no separate login.
"""

from datetime import datetime, timedelta, timezone

import requests

from core import config as cfg, db
from core.common import ConfigError, log, require_env

URL = cfg.text("SWIGGY_RATINGS_URL", "https://vhc-composer.swiggy.com/query?query=restaurantRatings")
BATCH = 100
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
QUERY = """query {
  restaurantRatings(input: {restaurantIds: [%s], period: "CURRENT_WEEK"}) {
    ratings { restaurantId globalRating globalRatingCount rating ratingCount ratingTrend }
    missingRatings { restaurantId globalRating globalRatingCount }
  }
}"""
KPIS = ("listing_rating", "rating_count", "weekly_rating", "weekly_rating_count")


def _headers(token: str) -> dict:
    return {"access_token": token, "x-swiggy-user-agent": "android", "x-swiggy-app-version-code": cfg.text("SWIGGY_APP_VERSION_CODE", "397"),
            "x-swiggy-app-version-name": cfg.text("SWIGGY_APP_VERSION_NAME", "19.8.0"), "x-app-type": "swiggy-partner",
            "content-type": "application/json", "user-agent": "okhttp/4.12.0"}


def fetch(token: str, ids: list[str]) -> list[dict]:
    """[{res_id, rating, count, week_rating, week_count}] for these outlets."""
    out = []
    for i in range(0, len(ids), BATCH):
        resp = requests.post(URL, headers=_headers(token), json={"query": QUERY % ",".join(ids[i:i + BATCH]), "variables": {}},
                             timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
        resp.raise_for_status()
        body = resp.json()
        if body.get("errors"):
            raise RuntimeError(f"Swiggy ratings query failed: {str(body['errors'])[:200]}")
        rr = (body.get("data") or {}).get("restaurantRatings") or {}
        for r in rr.get("ratings") or []:
            out.append({"res_id": str(r["restaurantId"]), "rating": r.get("globalRating"), "count": r.get("globalRatingCount"),
                        "week_rating": r.get("rating"), "week_count": r.get("ratingCount")})
        for r in rr.get("missingRatings") or []:  # no ratings this week, overall rating still known
            out.append({"res_id": str(r["restaurantId"]), "rating": r.get("globalRating"), "count": r.get("globalRatingCount"),
                        "week_rating": None, "week_count": 0})
    return out


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    require_env("CODEONTO_DATABASE_URL")
    today = datetime.now(IST).date()
    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "swiggy", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.swiggy_id AS res_id, s.account_id
                       FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id
                       WHERE bo.is_active AND s.is_active""")
        stores = cur.fetchall()
        cur.execute("SELECT code, id FROM kpis WHERE code = ANY(%s)", (list(KPIS),))
        kpi = {r["code"]: r["id"] for r in cur.fetchall()}
    if set(KPIS) - set(kpi):
        log.error("swiggy ratings: KPIs missing (%s); run `manage.py migrate`", ", ".join(sorted(set(KPIS) - set(kpi))))
        return False
    if not stores:
        log.info("swiggy ratings: no Swiggy ids are mapped to stores yet")
        return True
    outlet_of = {str(s["res_id"]): s["outlet_id"] for s in stores}
    by_id = {a["id"]: label for label, a in accs.items()}

    ok, saved, done = True, 0, set()
    for label, acc in accs.items():
        creds = db.load_credentials(acc)
        token = creds.get("access_token")
        if not token:
            log.error("swiggy ratings %s: session has no access_token; run `run.py swiggy session`", label)
            ok = False
            continue
        # this login's mapped outlets; outlets found under no known login go to the first login
        mine = [str(s["res_id"]) for s in stores if by_id.get(s["account_id"]) == label
                or (s["account_id"] not in by_id and label == next(iter(accs)))]
        visible = {str(x) for x in creds.get("outlets") or []}
        ids = [r for r in mine if not visible or r in visible] or mine
        if not ids:
            continue
        try:
            rows = fetch(token, ids)
        except (PermissionError, ConfigError) as e:
            log.error("swiggy ratings %s: %s", label, e)
            ok = False
            continue
        except Exception as e:
            log.exception("swiggy ratings %s failed: %s", label, e)
            ok = False
            continue
        n = 0
        with db.transaction() as cur:
            for r in rows:
                oid = outlet_of.get(r["res_id"])
                if not oid or r["res_id"] in done or not r["rating"]:
                    continue
                done.add(r["res_id"])
                values = [("listing_rating", r["rating"], r["count"] or 1), ("rating_count", r["count"] or 0, 1),
                          ("weekly_rating_count", r["week_count"] or 0, 1)]
                if r["week_count"] and r["week_rating"]:
                    values.append(("weekly_rating", r["week_rating"], r["week_count"]))
                for code, value, weight in values:
                    cur.execute("""INSERT INTO metric_daily (outlet_id, platform, kpi_id, metric_date, value, weight, updated_at)
                                   VALUES (%s, 'swiggy', %s, %s, %s, %s, now())
                                   ON CONFLICT (outlet_id, platform, kpi_id, metric_date)
                                   DO UPDATE SET value = EXCLUDED.value, weight = EXCLUDED.weight, updated_at = now()""",
                                (oid, kpi[code], today, value, weight))
                n += 1
        saved += n
        log.info("swiggy ratings %s: %s outlets asked, %s rated and saved", label, len(ids), n)
    log.info("swiggy ratings: %s outlets saved; %s mapped outlets without a rating", saved, len(set(outlet_of) - done))
    return ok
