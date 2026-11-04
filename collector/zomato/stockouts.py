"""Zomato stock-outs -> stock_outs table, for every Zomato id mapped to a store.

Reads each store's live delivery menu and keeps one row per item per day: a row is active while the
item is off the menu, and gets restored_at / downtime_minutes when it is back. Meant to run every few
minutes (`run.py zomato stockouts --every 5`).
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from core import alerts, config as cfg, db, hours
from core.common import ConfigError, log, require_env

from .outlets import _cookies

ZOMATO_SITE = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
MENU_URL = cfg.text("ZOMATO_MENU_URL", f"{ZOMATO_SITE}/php/online_ordering/menu_edit")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
WORKERS = cfg.integer("STOCKOUT_WORKERS", 3)  # parallel stores; Zomato rate-limits aggressive polling
PACE_SEC = cfg.numbers("STOCKOUT_PACE_SEC", "0.8,1.8")  # each worker waits a random time in this range before every request


class RateLimited(Exception):
    pass


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def mealtime(now: datetime) -> str:
    return cfg.mealtime(now.hour)


def _fetch(cookies: dict, res_id: str) -> list[dict]:
    """Out-of-stock items on one store's menu. Raises PermissionError when the session is dead."""
    import requests

    headers = {
        "Accept": "application/json, text/plain, */*", "Content-Type": "application/json",
        "User-Agent": cfg.user_agent(),
        "Referer": cfg.text("ZOMATO_MENU_REFERER", f"{ZOMATO_SITE}/partners/onlineordering/menu/editor"),
        "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
    }
    time.sleep(random.uniform(*PACE_SEC))  # pace requests so a 5-minute loop stays under Zomato's limit
    resp = requests.get(MENU_URL, params={"action": "get_content_menu", "res_id": res_id, "service_role": cfg.text("ZOMATO_SERVICE_ROLE", "DELIVERY_TAKEAWAY")},
                        headers=headers, timeout=cfg.integer("STOCKOUT_HTTP_TIMEOUT_SEC", 20))
    if resp.status_code in (401, 403):
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
    if resp.status_code == 429:
        raise RateLimited("Zomato rate limit (429) on menu fetch")
    resp.raise_for_status()
    try:
        body = resp.json()
    except ValueError:
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
    if not body.get("success", True) and "login" in (body.get("message") or "").lower():
        raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")

    menu = (body.get("data") or {}).get("menuResponse") or {}
    category_of = {}
    for cw in menu.get("categoryWrappers") or []:
        name = (cw.get("category") or {}).get("name", "")
        for sub in cw.get("subCategoryWrappers") or []:
            for ent in sub.get("subCategoryEntities") or []:
                category_of[str(ent.get("entityId"))] = name

    items: dict[str, dict] = {}
    for w in menu.get("catalogueWrappers") or []:
        cat = w.get("catalogue") or {}
        out, back = "autoTurnOnTime" in cat, cat.get("autoTurnOnTime")
        if not out:
            for vw in w.get("variantWrappers") or []:
                v = vw.get("variant") or {}
                if v.get("inStock") is False:
                    out, back = True, v.get("turnOnTime")
                    break
        name = (cat.get("name") or "").strip()
        if out and name and (name not in items or (back and not items[name]["back_at"])):
            items[name] = {"item_name": name, "category": category_of.get(str(cat.get("catalogueId")), ""), "back_at": back or ""}
    return list(items.values())


def _sync(cur, outlet_id: int, items: list[dict], now: datetime, slots=None) -> tuple[list[dict], list[dict]]:
    """Store the current state; returns (newly out of stock items, restored items with downtime).

    One row per episode: an item that is still out keeps its row (even across midnight); an item that left the
    list is closed with its downtime; an item that appears and has no open row starts a new one."""
    cur.execute("SELECT item_name FROM stock_outs WHERE outlet_id = %s AND platform = 'zomato' AND is_active", (outlet_id,))
    was_active = {r["item_name"] for r in cur.fetchall()}
    names = [i["item_name"] for i in items]
    # items no longer on the list are back: close them, counting only the hours the store was open as downtime
    cur.execute("""SELECT id, item_name, first_detected_at FROM stock_outs
                   WHERE outlet_id = %s AND platform = 'zomato' AND is_active AND NOT (item_name = ANY(%s))""", (outlet_id, names))
    restored = []
    local_now = now.astimezone(IST).replace(tzinfo=None)
    for r in cur.fetchall():
        minutes = max(1, round(hours.open_minutes(slots, r["first_detected_at"].astimezone(IST).replace(tzinfo=None), local_now)))
        cur.execute("UPDATE stock_outs SET is_active = false, restored_at = %s, downtime_minutes = %s WHERE id = %s", (now, minutes, r["id"]))
        restored.append({"item_name": r["item_name"], "downtime_minutes": minutes})
    local = now.astimezone(IST)
    new = []
    for it in items:
        if it["item_name"] in was_active:
            cur.execute("""UPDATE stock_outs SET category = %(category)s, back_at = %(back_at)s, last_detected_at = %(now)s
                           WHERE outlet_id = %(o)s AND platform = 'zomato' AND is_active AND item_name = %(item_name)s""",
                        {**it, "o": outlet_id, "now": now})
        else:
            cur.execute(
                """INSERT INTO stock_outs (outlet_id, platform, item_name, category, back_at, mealtime, is_active, log_date,
                                           first_detected_at, last_detected_at)
                   VALUES (%(o)s, 'zomato', %(item_name)s, %(category)s, %(back_at)s, %(meal)s, true, %(day)s, %(now)s, %(now)s)""",
                {**it, "o": outlet_id, "meal": mealtime(local), "day": cfg.business_date(local), "now": now})
            new.append(it | {"mealtime": mealtime(local)})
    return new, restored


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato stockouts: %s", e)
        return False

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id, b.name AS brand, bo.outlet_name,
                              b.client_id, c.name AS client
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       JOIN brands b ON b.id = bo.brand_id JOIN clients c ON c.id = b.client_id
                       WHERE bo.is_active AND z.is_active""")
        stores = cur.fetchall()
    if not stores:
        log.info("zomato stockouts: no Zomato ids are mapped to stores yet")
        return True

    by_id = {a["id"]: a for a in accs.values()}
    creds = {a["id"]: _cookies(db.load_credentials(a)) for a in accs.values()}
    default = next(iter(by_id))

    # closed stores are not checked: their menu is not meaningful, and closed hours must not count as downtime
    store_hours = hours.load("zomato", cfg.text("STOCKOUT_HOURS_SERVICE", "delivery"))
    local_now = datetime.now(IST).replace(tzinfo=None)
    open_stores = [s for s in stores if hours.is_open(store_hours.get(s["outlet_id"]), local_now)]
    if len(open_stores) < len(stores):
        log.info("zomato stockouts: %s stores closed right now, skipped", len(stores) - len(open_stores))
    stores = open_stores
    if not stores:
        return True

    def work(s):
        acc_id = s["account_id"] if s["account_id"] in by_id else default
        try:
            return s, _fetch(creds[acc_id], s["res_id"]), None
        except Exception as e:
            return s, None, e

    t0 = time.time()
    log.info("zomato stockouts: fetching %s menus (%s at a time)", len(stores), WORKERS)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(work, stores))
    log.info("zomato stockouts: fetched %s menus in %.0fs; saving", len(stores), time.time() - t0)

    now, ok, out_total, new_total, back_total = datetime.now(timezone.utc), True, 0, 0, 0
    pending: dict[int, dict] = {}  # client_id -> what changed this run, sent as one alert per client
    for s, items, err in results:
        if isinstance(err, PermissionError):
            log.error("zomato stockouts: %s", err)
            alerts.incident("Zomato session expired", str(err), "Run `python run.py zomato session`, then restart the stock-out job.")
            return False
        if isinstance(err, RateLimited):
            log.error("zomato stockouts: %s; stopping this pass, next cycle retries", err)
            alerts.incident("Zomato rate limit (429)", str(err), "The stock-out job backs off until its next cycle. If it keeps happening, raise the interval (--every 10).")
            return False
        if err:
            log.error("zomato stockouts %s (%s) failed: %s", s["outlet_name"], s["res_id"], err)
            ok = False
            continue
        try:
            with db.transaction() as cur:
                new, back = _sync(cur, s["outlet_id"], items, now, store_hours.get(s["outlet_id"]))
        except Exception as e:
            log.exception("zomato stockouts %s save failed: %s", s["res_id"], e)
            ok = False
            continue
        label = f"{s['brand']} · {s['outlet_name']}"
        p = pending.setdefault(s["client_id"], {"name": s["client"], "new": [], "back": []})
        p["new"] += [i | {"outlet": label} for i in new]
        p["back"] += [i | {"outlet": label} for i in back]
        new, back = len(new), len(back)
        out_total += len(items); new_total += new; back_total += back
        log.info("zomato stockouts %s · %s (%s): %s out of stock, %s new, %s back", s["brand"], s["outlet_name"],
                 s["res_id"], len(items), new, back)
    for client_id, p in pending.items():
        alerts.stock_out_alert(client_id, p["name"], p["new"], p["back"])
    log.info("zomato stockouts: %s out of stock across %s stores (%s new, %s back)", out_total, len(stores), new_total, back_total)
    return ok
