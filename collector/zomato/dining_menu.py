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

from .dining import _post, _session

UNIT = {"second": timedelta(seconds=1), "minute": timedelta(minutes=1), "hour": timedelta(hours=1), "day": timedelta(days=1),
        "week": timedelta(weeks=1), "month": timedelta(days=30), "year": timedelta(days=365)}


def menu_updated_text(headers: dict, res_id: str) -> str:
    """District's 'Updated a month ago' from the restaurant page's Menu header; empty if the page has none."""
    h = {**headers, "content-type": "application/json; charset=UTF-8"}
    data = _post(h, "restaurant/info?lang=en&city_id=-1", json={"res_id": res_id, "business_params": "{}", "postback_params": "{}"}).json()
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
    require_env("SOCIALSPORK_DATABASE_URL")
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
        try:
            text = menu_updated_text(headers, rid)
        except PermissionError:
            raise
        except Exception as e:
            log.warning("zomato dining menu %s: could not read the menu's update time: %s", rid, e)
            text = ""
        latest = latest_update(text, now) if text else None
        with db.transaction() as cur:
            cur.execute("SELECT synced_at FROM dining_menu_status WHERE res_id = %s", (rid,))
            prev = cur.fetchone()
            cur.execute("""INSERT INTO dining_menu_status (res_id, outlet_id, updated_text, updated_latest, checked_at) VALUES (%s,%s,%s,%s,%s)
                           ON CONFLICT (res_id) DO UPDATE SET outlet_id = EXCLUDED.outlet_id, updated_text = EXCLUDED.updated_text,
                           updated_latest = EXCLUDED.updated_latest, checked_at = EXCLUDED.checked_at""", (rid, s["outlet_id"], text, latest, now))
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
