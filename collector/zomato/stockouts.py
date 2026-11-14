"""Zomato stock-outs -> stock_outs table, for every Zomato id mapped to a store.

Reads each store's live delivery menu and keeps one row per item per day: a row is active while the
item is off the menu, and gets restored_at / downtime_minutes when it is back. Meant to run every few
minutes (`run.py zomato stockouts --every 5`).
"""

import random
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

from core import alerts, config as cfg, db, hours, notify, retry
from core.common import ConfigError, log, require_env

from .outlets import _cookies

ZOMATO_SITE = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
MENU_URL = cfg.text("ZOMATO_MENU_URL", f"{ZOMATO_SITE}/php/online_ordering/menu_edit")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
WORKERS = cfg.integer("STOCKOUT_WORKERS", 3)  # parallel stores; Zomato rate-limits aggressive polling
PACE_SEC = cfg.numbers("STOCKOUT_PACE_SEC", "0.8,1.8")  # each worker waits a random time in this range before every request


class RateLimited(Exception):
    pass


class Blocked(Exception):
    """Zomato's firewall (Akamai) refused the request: an "Access Denied" page, not a logged-out session."""


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
    if resp.status_code == 403 and ("access denied" in resp.text[:2000].lower() or "akamai" in resp.text[:2000].lower()
                                    or "json" not in resp.headers.get("content-type", "")):
        raise Blocked(f"Zomato blocked the menu request (403 Access Denied from {MENU_URL.split('/')[2]})")
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

    return out_items((body.get("data") or {}).get("menuResponse") or {})


def out_items(menu: dict) -> list[dict]:
    """The items customers cannot order, from the menu editor's answer. An item is out when it is switched off as a whole
    (it has an auto turn-on time) or when every one of its variants is out. One variant being out (a combo with a drink
    that is off, say) leaves the item orderable, so it does not count. A name listed twice is out only when every
    listing of it is."""
    category_of = {}
    for cw in menu.get("categoryWrappers") or []:
        name = (cw.get("category") or {}).get("name", "")
        for sub in cw.get("subCategoryWrappers") or []:
            for ent in sub.get("subCategoryEntities") or []:
                category_of[str(ent.get("entityId"))] = name

    listings: dict[str, list[dict]] = {}
    for w in menu.get("catalogueWrappers") or []:
        cat = w.get("catalogue") or {}
        name = (cat.get("name") or "").strip()
        if not name:
            continue
        out, back = "autoTurnOnTime" in cat, cat.get("autoTurnOnTime")
        if not out:
            variants = [vw.get("variant") or {} for vw in w.get("variantWrappers") or []]
            if variants and all(v.get("inStock") is False for v in variants):
                out, back = True, next((v.get("turnOnTime") for v in variants if v.get("turnOnTime")), None)
        listings.setdefault(name, []).append({"out": out, "back": back, "category": category_of.get(str(cat.get("catalogueId")), "")})
    items = []
    for name, ls in listings.items():
        if all(x["out"] for x in ls):
            back = next((x["back"] for x in ls if x["back"]), "")
            items.append({"item_name": name, "category": ls[0]["category"], "back_at": back or ""})
    return items


def _sync(cur, outlet_id: int, items: list[dict], now: datetime, slots=None, platform: str = "zomato") -> tuple[list[dict], list[dict]]:
    """Store the current state; returns (newly out of stock items, restored items with downtime).

    One row per episode: an item that is still out keeps its row (even across midnight); an item that left the
    list is closed with its downtime; an item that appears and has no open row starts a new one."""
    cur.execute("SELECT item_name FROM stock_outs WHERE outlet_id = %s AND platform = %s AND is_active", (outlet_id, platform))
    was_active = {r["item_name"] for r in cur.fetchall()}
    names = [i["item_name"] for i in items]
    # items no longer on the list are back: close them, counting only the hours the store was open as downtime
    cur.execute("""SELECT id, item_name, first_detected_at FROM stock_outs
                   WHERE outlet_id = %s AND platform = %s AND is_active AND NOT (item_name = ANY(%s))""", (outlet_id, platform, names))
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
                           WHERE outlet_id = %(o)s AND platform = %(p)s AND is_active AND item_name = %(item_name)s""",
                        {**it, "o": outlet_id, "now": now, "p": platform})
        else:
            cur.execute(
                """INSERT INTO stock_outs (outlet_id, platform, item_name, category, back_at, mealtime, is_active, log_date,
                                           first_detected_at, last_detected_at)
                   VALUES (%(o)s, %(p)s, %(item_name)s, %(category)s, %(back_at)s, %(meal)s, true, %(day)s, %(now)s, %(now)s)""",
                {**it, "o": outlet_id, "p": platform, "meal": mealtime(local), "day": cfg.business_date(local), "now": now})
            new.append(it | {"mealtime": mealtime(local)})
    return new, restored


def _save(outlet_id, items, now, slots, platform):
    """One store's result in its own transaction, so a dropped DB connection can be retried without half a save."""
    with db.transaction() as cur:
        return _sync(cur, outlet_id, items, now, slots, platform=platform)


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

    def login_of(s):
        return s["account_id"] if s["account_id"] in by_id else default

    t0 = time.time()
    log.info("zomato stockouts: fetching %s menus (%s at a time)", len(stores), WORKERS)
    results = retry.fetch_all(stores, lambda s: _fetch(creds[login_of(s)], s["res_id"]), WORKERS, "zomato stockouts",
                              slow=(RateLimited, Blocked))
    log.info("zomato stockouts: fetched %s menus in %.0fs; saving", len(stores), time.time() - t0)

    now, ok, out_total, new_total, back_total = datetime.now(timezone.utc), True, 0, 0, 0
    pending: dict[int, dict] = {}  # client_id -> what changed this run, sent as one alert per client
    expired: set = set()  # logins refused this pass: their stores are skipped, the other logins carry on
    failures: list[str] = []  # other errors (timeouts, 5xx, bad answers): a few are normal, many mean something broke
    blocked = limited = 0  # still refused after the retries: those stores are skipped, the rest are saved
    for s, items, err in results:
        if isinstance(err, PermissionError):
            acc_id = login_of(s)
            if acc_id not in expired:
                expired.add(acc_id)
                label = by_id[acc_id]["label"]
                log.error("zomato stockouts: login '%s' was refused (%s); its stores are skipped this pass", label, err)
                db.mark_session_expired(acc_id, f"zomato stockouts: {err}")
                alerts.incident(f"Zomato session expired: {label}", str(err),
                                f"Use Log in again on the Sessions page, or run `python run.py zomato session --account {label}`.")
            ok = False
            continue
        if isinstance(err, Blocked):
            blocked += 1; ok = False
            if blocked == 1:
                log.error("zomato stockouts: %s, even after retries; those stores wait for the next cycle", err)
                alerts.incident("Zomato blocked the stock-out checks (403)", str(err),
                            "This is usually Zomato's firewall refusing the server, not the login: check the menu proxy "
                            "(ZOMATO_MENU_PROXY_URL) is up, or slow the job down (--every 10). If it keeps happening "
                            "while the proxy is fine, log in again on the Sessions page.")
            continue
        if isinstance(err, RateLimited):
            limited += 1; ok = False
            if limited == 1:
                log.error("zomato stockouts: %s, even after retries; those stores wait for the next cycle", err)
                alerts.incident("Zomato rate limit (429)", str(err), "The job retried and backed off, but Zomato kept refusing. If it keeps happening, raise the interval (--every 10) or lower STOCKOUT_WORKERS.")
            continue
        if err:
            log.warning("zomato stockouts %s (%s) failed: %s", s["outlet_name"], s["res_id"], err)
            failures.append(f"{type(err).__name__}: {str(err)[:160]}")
            ok = False
            continue
        try:
            new, back = retry.call(lambda: _save(s["outlet_id"], items, now, store_hours.get(s["outlet_id"]), "zomato"),
                                   f"zomato stockouts save {s['res_id']}")
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
    if len(failures) >= max(3, len(stores) // 5):
        top, n = Counter(failures).most_common(1)[0]
        alerts.incident("Zomato stock-out checks failing", f"{len(failures)} of {len(stores)} menus failed this pass. "
                        f"Most common error ({n}×): {top}",
                        "Check the collector window on the Windows server and the menu proxy. Stock-outs for those stores are not up to date.")
    notify.send(("oos", "oos_back"))  # WhatsApp / email per Alerts settings (scope, alert types, quiet hours)
    log.info("zomato stockouts: %s out of stock across %s stores (%s new, %s back)", out_total, len(stores), new_total, back_total)
    return ok
