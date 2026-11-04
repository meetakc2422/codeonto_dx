"""Google listing health -> listing_profiles, for every Google location mapped to a store.

Reads the public profile (phone, website, categories, hours, description, open status), the photo
count and the latest post, then scores it out of 100 and lists what is missing.
"""

import json
import time
from datetime import datetime, timedelta, timezone

from core import config as cfg, db
from core.common import ConfigError, log, require_env

from .session import credentials_from

INFO_URL = cfg.text("GOOGLE_BUSINFO_URL", "https://mybusinessbusinessinformation.googleapis.com/v1/locations/{location_id}")
MEDIA_URL = cfg.text("GOOGLE_MEDIA_URL", "https://mybusiness.googleapis.com/v4/{business_account}/locations/{location_id}/media")
POSTS_URL = cfg.text("GOOGLE_POSTS_URL", "https://mybusiness.googleapis.com/v4/{business_account}/locations/{location_id}/localPosts")
READ_MASK = cfg.text("GOOGLE_PROFILE_READ_MASK", "name,title,phoneNumbers,categories,websiteUri,regularHours,openInfo,profile")
HEALTH = cfg.mapping("google_listing_health")  # mappings/google_listing_health.json: scoring checks and targets


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _get(session, url: str, params: dict) -> dict:
    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = session.get(url, params=params, timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            detail = resp.json().get("error", {}).get("message", "") if resp.content else ""
            raise PermissionError(f"Google API refused access ({resp.status_code}): {detail}")
        if resp.status_code == 404:
            return {}
        if resp.status_code == 429 or resp.status_code >= 500:
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return {}


def score(p: dict) -> tuple[int, list[dict]]:
    """Each check in the mapping file earns its points when passed; the rest become the fix list."""
    now = datetime.now(timezone.utc)
    passed = {
        "phone": bool(p["phone"]), "website": bool(p["website"]), "hours": p["has_hours"],
        "category": bool(p["primary_category"]), "extra_categories": p["extra_categories"] > 0,
        "description": p["has_description"], "photos": p["photo_count"] >= HEALTH["photos_target"],
        "posts": bool(p["last_post_at"]) and now - p["last_post_at"] < timedelta(days=HEALTH["post_max_age_days"]),
        "open": p["open_status"] in ("OPEN", ""),
    }
    checks = HEALTH["checks"]
    points = sum(c["points"] for c in checks if passed[c["key"]])
    return points, [{"code": c["key"], "label": c["fix"]} for c in checks if not passed[c["key"]]]


def _profile(session, loc: dict) -> dict:
    info = _get(session, INFO_URL.format(location_id=loc["location_id"]), {"readMask": READ_MASK})
    media = _get(session, MEDIA_URL.format(**loc), {"pageSize": 1})
    posts = _get(session, POSTS_URL.format(**loc), {"pageSize": 20})
    cats = info.get("categories") or {}
    times = [p.get("createTime") for p in posts.get("localPosts", []) if p.get("createTime")]
    p = {
        "title": info.get("title", ""), "phone": (info.get("phoneNumbers") or {}).get("primaryPhone", ""),
        "website": info.get("websiteUri", ""), "primary_category": (cats.get("primaryCategory") or {}).get("displayName", ""),
        "extra_categories": len(cats.get("additionalCategories") or []),
        "has_description": bool(((info.get("profile") or {}).get("description") or "").strip()),
        "has_hours": bool((info.get("regularHours") or {}).get("periods")),
        "open_status": (info.get("openInfo") or {}).get("status", ""),
        "photo_count": int(media.get("totalMediaItemCount") or 0),
        "last_post_at": max(datetime.fromisoformat(t.replace("Z", "+00:00")) for t in times) if times else None,
    }
    p["health_score"], p["issues"] = score(p)
    return p


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("google profile: %s", e)
        return False
    from google.auth.transport.requests import AuthorizedSession

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "google", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.google_location_id AS location_id, g.business_account, g.account_id,
                              b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN google_locations g ON g.location_id = bo.google_location_id
                       JOIN brands b ON b.id = bo.brand_id
                       WHERE bo.is_active AND g.is_active AND g.business_account <> ''""")
        stores = cur.fetchall()
    if not stores:
        log.info("google profile: no Google locations are mapped to stores yet")
        return True
    by_id = {a["id"]: a for a in accs.values()}
    sessions = {}
    for a in accs.values():
        try:
            sessions[a["id"]] = AuthorizedSession(credentials_from(db.load_credentials(a)))
        except (PermissionError, ConfigError) as e:
            log.error("google profile: account %s: %s", a["label"], e)
            return False
    default = next(iter(by_id))
    # a location is only readable by the login that owns it: skip the others instead of trying them (404s)
    stores = [s for s in stores if s["account_id"] is None or s["account_id"] in by_id]
    ok = True
    for s in stores:
        try:
            p = _profile(sessions[s["account_id"] if s["account_id"] in by_id else default], s)
            with db.transaction() as cur:
                cur.execute(
                    """INSERT INTO listing_profiles (outlet_id, platform, title, phone, website, primary_category, extra_categories,
                           has_description, has_hours, open_status, photo_count, last_post_at, health_score, issues, fetched_at)
                       VALUES (%(o)s, 'google', %(title)s, %(phone)s, %(website)s, %(primary_category)s, %(extra_categories)s,
                           %(has_description)s, %(has_hours)s, %(open_status)s, %(photo_count)s, %(last_post_at)s, %(health_score)s,
                           %(issues)s::jsonb, now())
                       ON CONFLICT (outlet_id, platform) DO UPDATE SET title = EXCLUDED.title, phone = EXCLUDED.phone,
                           website = EXCLUDED.website, primary_category = EXCLUDED.primary_category,
                           extra_categories = EXCLUDED.extra_categories, has_description = EXCLUDED.has_description,
                           has_hours = EXCLUDED.has_hours, open_status = EXCLUDED.open_status, photo_count = EXCLUDED.photo_count,
                           last_post_at = EXCLUDED.last_post_at, health_score = EXCLUDED.health_score, issues = EXCLUDED.issues,
                           fetched_at = now()""",
                    {**p, "o": s["outlet_id"], "issues": json.dumps(p["issues"])})
            log.info("google profile %s · %s: health %s/100, %s to fix", s["brand"], s["outlet_name"], p["health_score"], len(p["issues"]))
        except PermissionError as e:
            log.error("google profile: %s", e)
            return False
        except Exception as e:
            log.exception("google profile %s failed: %s", s["location_id"], e)
            ok = False
    return ok
