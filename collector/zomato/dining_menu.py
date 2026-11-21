"""Zomato dining menu pages -> dining_menu_pages.

The District app shows a dining outlet's menu as page images. For every Zomato id marked is_dining this job asks the app for
the menu (restaurant/menus), keeps the list of page images current, and leaves reading them to the server
(`manage.py read_dining_menus`), which turns each new image into dishes and prices. A page already read is not read again.

Run:  python run.py zomato dining_menu            (add --res-id to limit)
Uses the same District customer login as `zomato dining` (sessions/zomato_district.json).
"""

import os
import re
from datetime import datetime, timedelta, timezone

from core import db
from core.common import log, require_env

from .dining import IST, _post, _session

UNIT = {"second": timedelta(seconds=1), "minute": timedelta(minutes=1), "hour": timedelta(hours=1), "day": timedelta(days=1),
        "week": timedelta(weeks=1), "month": timedelta(days=30), "year": timedelta(days=365)}


def fetch_info(headers: dict, res_id: str) -> dict:
    """The restaurant page as the District app shows it."""
    h = {**headers, "content-type": "application/json; charset=UTF-8"}
    return _post(h, "restaurant/info?lang=en&city_id=-1", json={"res_id": res_id, "business_params": "{}", "postback_params": "{}"}).json()


def menu_updated_text(data: dict) -> str:
    """District's 'Updated a month ago' from the page's Menu header; empty if the page has none."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            hd = o.get("ed_header_snippet_type_5")
            if isinstance(hd, dict) and ((hd.get("title") or {}).get("text") or "").strip().lower() == "menu":
                t = (((hd.get("right_tag") or {}).get("title")) or {}).get("text")
                if t:
                    found.append(t.strip())
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    return found[0] if found else ""


def outlet_photo(data: dict) -> str:
    """The first photo in the page's header gallery (a square picture of the outlet), or ''."""
    for it in (((data.get("header_data") or {}).get("top_container") or {}).get("snippet") or {}).get("ed_media_snippet_type_1", {}).get("items") or []:
        u = (((it or {}).get("media") or {}).get("image") or {}).get("url")
        if u and u.startswith("https://"):
            return u.split("?")[0] + "?fit=around%7C200%3A200&crop=200%3A200%3B%2A%2C%2A"
    return ""


def _count(text: str) -> int | None:
    """'2.6K+' -> 2600, '720' -> 720."""
    m = re.match(r"\s*([\d.,]+)\s*([kKlLmM]?)", text or "")
    if not m:
        return None
    return round(float(m.group(1).replace(",", "")) * {"k": 1e3, "l": 1e5, "m": 1e6}.get(m.group(2).lower(), 1))


def store_profile(data: dict) -> dict:
    """{rating, ratings, cost_for_two} from the page header: '4.3' over '2.6K+', and 'Japanese · ₹2200 for two'."""
    hd = ((data.get("header_data") or {}).get("bottom_container")) or {}
    block = hd.get("right_block") or {}
    rating = ((block.get("top_container") or {}).get("title") or {}).get("text")
    ratings = ((block.get("bottom_container") or {}).get("title") or {}).get("text")
    sub = (hd.get("subtitle1") or {}).get("text") or ""
    cost = re.search(r"₹\s*([\d,]+)\s*for two", sub)
    try:
        rating = float(rating) if rating and 0 < float(rating) <= 5 else None
    except ValueError:
        rating = None
    return {"rating": rating, "ratings": _count(ratings), "cost_for_two": int(cost.group(1).replace(",", "")) if cost else None}


def save_profile(cur, outlet_id, prof: dict, day) -> None:
    """Today's District rating (weight = number of ratings, so a brand figure is a weighted average), rating count and cost for two."""
    if not outlet_id:
        return
    cur.execute("SELECT code, id FROM kpis WHERE code IN ('listing_rating', 'rating_count', 'cost_for_two')")
    kpi = {r["code"]: r["id"] for r in cur.fetchall()}
    for code, value, weight in (("listing_rating", prof["rating"], prof["ratings"] or 1), ("rating_count", prof["ratings"], 1),
                                ("cost_for_two", prof["cost_for_two"], 1)):
        if value is None or code not in kpi:
            continue
        cur.execute("""INSERT INTO metric_daily (outlet_id, platform, kpi_id, metric_date, value, weight, updated_at)
                       VALUES (%s, 'district', %s, %s, %s, %s, now())
                       ON CONFLICT (outlet_id, platform, kpi_id, metric_date)
                       DO UPDATE SET value = EXCLUDED.value, weight = EXCLUDED.weight, updated_at = now()""",
                    (outlet_id, kpi[code], day, value, weight))


def latest_update(text: str, now: datetime) -> datetime | None:
    """The latest moment the menu can have been updated, from 'Updated 3 days ago' (it was at least 3 days ago, maybe up to 4)."""
    t = text.lower()
    if re.search(r"just now|moments? ago|today", t):
        return now
    if "yesterday" in t:
        return now - UNIT["day"]
    m = re.search(r"(an?|\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago", t)
    if not m:
        return None
    n = 1 if m.group(1) in ("a", "an") else int(m.group(1))
    return now - n * UNIT[m.group(2)]


def menu_images(headers: dict, res_id: str) -> list[str]:
    """The menu's page images in order, without repeats: every photo in the answer's `medias` groups (Food, Beverages...)."""
    h = {**headers, "content-type": "application/json; charset=UTF-8"}
    data = _post(h, "restaurant/menus?lang=en&city_id=-1", json={"res_id": res_id, "selected_category": "FOOD", "service_type": "edition_menus"}).json()
    seen, out = set(), []
    for group in data.get("medias") or []:
        for ph in group.get("photos") or []:
            u = ph.get("url") if isinstance(ph, dict) else None
            if u and u.startswith("https://") and u not in seen:
                seen.add(u); out.append(u)
    return out


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    require_env("CODEONTO_DATABASE_URL")
    headers = _session()
    only = {x for x in os.getenv("ONLY_RES_IDS", "").split(",") if x}
    with db.transaction() as cur:
        cur.execute("""SELECT z.res_id, bo.id AS outlet_id FROM zomato_outlets z LEFT JOIN brand_outlets bo ON bo.zomato_res_id = z.res_id
                       WHERE z.is_dining AND z.is_active""")
        stores = [s for s in cur.fetchall() if not only or s["res_id"] in only]
    if not stores:
        log.warning("zomato dining menu: no active Zomato ids are marked is_dining")
        return True
    ok = True
    for s in stores:
        rid = str(s["res_id"])
        now = datetime.now(timezone.utc)
        text, photo = "", ""
        try:
            info = fetch_info(headers, rid)
            text = menu_updated_text(info)
            photo = outlet_photo(info)
            prof = store_profile(info)
            if prof["rating"] is not None or prof["cost_for_two"] is not None:
                with db.transaction() as cur:
                    save_profile(cur, s["outlet_id"], prof, datetime.now(IST).date())
                log.info("zomato dining menu %s: District rating %s (%s ratings), cost for two %s", rid, prof["rating"], prof["ratings"], prof["cost_for_two"])
        except PermissionError:
            raise
        except Exception as e:
            log.warning("zomato dining menu %s: could not read the restaurant page: %s", rid, e)
        latest = latest_update(text, now) if text else None
        with db.transaction() as cur:
            cur.execute("SELECT synced_at FROM dining_menu_status WHERE res_id = %s", (rid,))
            prev = cur.fetchone()
            cur.execute("""INSERT INTO dining_menu_status (res_id, outlet_id, updated_text, updated_latest, checked_at, photo_url) VALUES (%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (res_id) DO UPDATE SET outlet_id = EXCLUDED.outlet_id, updated_text = EXCLUDED.updated_text,
                           updated_latest = EXCLUDED.updated_latest, checked_at = EXCLUDED.checked_at,
                           photo_url = CASE WHEN EXCLUDED.photo_url <> '' THEN EXCLUDED.photo_url ELSE dining_menu_status.photo_url END""",
                        (rid, s["outlet_id"], text, latest, now, photo))
        synced = prev["synced_at"] if prev else None
        if not force and synced and latest and synced > latest:
            log.info("zomato dining menu %s: %s, already synced after that: skipped", rid, text)
            continue
        try:
            urls = menu_images(headers, rid)
        except PermissionError:
            raise
        except Exception as e:
            ok = False
            log.warning("zomato dining menu %s: %s", rid, e)
            continue
        if not urls:
            log.info("zomato dining menu %s: no menu pages found", rid)
            continue
        with db.transaction() as cur:
            for i, u in enumerate(urls):
                cur.execute("""INSERT INTO dining_menu_pages (res_id, outlet_id, image_url, position, first_seen, read_error) VALUES (%s,%s,%s,%s, now(), '')
                               ON CONFLICT (res_id, image_url) DO UPDATE SET position = EXCLUDED.position, outlet_id = EXCLUDED.outlet_id""",
                            (rid, s["outlet_id"], u, i))
            # a page the restaurant took down: drop it and its dishes
            cur.execute("DELETE FROM dining_menu_pages WHERE res_id = %s AND NOT (image_url = ANY(%s))", (rid, urls))
            cur.execute("UPDATE dining_menu_status SET synced_at = %s WHERE res_id = %s", (now, rid))
        log.info("zomato dining menu %s: %d pages", rid, len(urls))
    return ok
