"""Swiggy stock-outs -> stock_outs table (platform 'swiggy'), for every Swiggy id mapped to a store.

Same as the Zomato job (zomato/stockouts.py) and stored the same way: reads each store's menu from Swiggy's partner
menu API with the login's access token, and keeps one row per stock-out episode. An item counts as out of stock when it
is on the menu (enabled) but in_stock is 0; items the restaurant switched off the menu (enabled 0) are not stock-outs.
Meant to run every few minutes: `run.py swiggy stockouts --every 5`.
"""

import random
import time
from collections import Counter
from datetime import datetime, timezone

from core import alerts, config as cfg, db, hours, notify, retry
from core.common import ConfigError, log, require_env
from zomato.stockouts import IST, _save

MENU_URL = cfg.text("SWIGGY_MENU_URL", "https://vhc-composer.swiggy.com/api/cms/menu-revision/v1/restaurant-menu-wrapper/{id}")
ORIGIN = cfg.text("SWIGGY_FINANCE_ORIGIN", "https://partner.swiggy.com")
WORKERS = cfg.integer("SWIGGY_STOCKOUT_WORKERS", 3)
PACE_SEC = cfg.numbers("SWIGGY_STOCKOUT_PACE_SEC", "0.8,1.8")


class RateLimited(Exception):
    pass


class MenuError(RuntimeError):
    """Swiggy answered without a menu ("failed to fetch menu"): usually a hiccup on their side, so it is retried."""
    transient = True


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _fetch(token: str, swiggy_id: str) -> list[dict]:
    """Out-of-stock items on one store's Swiggy menu. Raises PermissionError when the login is dead."""
    import requests

    if not token:
        raise PermissionError("Swiggy login has no access token; run `run.py swiggy session` for this account")
    time.sleep(random.uniform(*PACE_SEC))
    resp = requests.get(MENU_URL.format(id=swiggy_id), params={"disabled": "true", "item_slots": "true", "tickets": "true"},
                        headers={"accesstoken": token, "Accept": "*/*", "Origin": ORIGIN, "Referer": ORIGIN + "/",
                                 "User-Agent": cfg.user_agent()},
                        timeout=cfg.integer("STOCKOUT_HTTP_TIMEOUT_SEC", 20))
    if resp.status_code in (401, 403):
        raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
    if resp.status_code == 429:
        raise RateLimited("Swiggy rate limit (429) on menu fetch")
    resp.raise_for_status()
    body = resp.json()
    menu = (body.get("data") or {}).get("menu")
    if body.get("statusCode") not in (0, None) or menu is None:
        msg = body.get("statusMessage") or "no menu in the answer"
        if any(w in msg.lower() for w in ("token", "unauthor", "login", "expired")):
            raise PermissionError(f"Swiggy session expired ({msg}); run `run.py swiggy session` for this account")
        raise MenuError(f"Swiggy menu {swiggy_id}: {msg}")

    return out_items(menu)


def out_items(menu: dict) -> list[dict]:
    """The items customers cannot order, from the partner menu. An item is out when it is on the menu (enabled) but
    in_stock is 0; one switched off on purpose (enabled 0 / active false) is not a stock-out. A name listed twice is
    out only when every listing of it is, so a second listing that is in stock keeps the dish orderable."""
    listings: dict[str, list[dict]] = {}
    for w in menu.get("items_vo") or []:
        it = w.get("item") or {}
        name = (it.get("name") or "").strip()
        if not name or not it.get("enabled") or it.get("active") is False:
            continue  # switched off the menu on purpose: not a stock-out
        back = ((it.get("availability") or {}).get("next_change_time_text") or "").strip()
        listings.setdefault(name, []).append({"out": it.get("in_stock") in (0, False), "category": w.get("main_category_name") or "",
                                              "back_at": "" if back.lower() == "unavailable" else back})
    return [{"item_name": name, "category": ls[0]["category"], "back_at": next((x["back_at"] for x in ls if x["back_at"]), "")}
            for name, ls in listings.items() if all(x["out"] for x in ls)]


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("swiggy stockouts: %s", e)
        return False

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "swiggy", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.swiggy_id AS res_id, s.account_id, b.name AS brand, bo.outlet_name,
                              b.client_id, c.name AS client
                       FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id
                       JOIN brands b ON b.id = bo.brand_id JOIN clients c ON c.id = b.client_id
                       WHERE bo.is_active AND s.is_active""")
        stores = cfg.keep_stores(cur.fetchall())
    if not stores:
        log.info("swiggy stockouts: no Swiggy ids are mapped to stores yet")
        return True
    by_id = {a["id"]: a for a in accs.values()}
    default = next(iter(by_id))
    tokens = {i: db.load_credentials(a).get("access_token") for i, a in by_id.items()}

    # Swiggy timings aren't collected; a store's Zomato hours are the same kitchen's hours, so use them
    store_hours = hours.load("swiggy", "delivery") or {}
    zomato_hours = hours.load("zomato", cfg.text("STOCKOUT_HOURS_SERVICE", "delivery"))
    slots_of = lambda oid: store_hours.get(oid) or zomato_hours.get(oid)  # noqa: E731
    local_now = datetime.now(IST).replace(tzinfo=None)
    open_stores = [s for s in stores if hours.is_open(slots_of(s["outlet_id"]), local_now)]
    if len(open_stores) < len(stores):
        log.info("swiggy stockouts: %s stores closed right now, skipped", len(stores) - len(open_stores))
    stores = open_stores
    if not stores:
        return True

    def login_of(s):
        return s["account_id"] if s["account_id"] in by_id else default

    t0 = time.time()
    log.info("swiggy stockouts: fetching %s menus (%s at a time)", len(stores), WORKERS)
    results = retry.fetch_all(stores, lambda s: _fetch(tokens[login_of(s)], s["res_id"]), WORKERS, "swiggy stockouts",
                              slow=(RateLimited,))
    log.info("swiggy stockouts: fetched %s menus in %.0fs; saving", len(stores), time.time() - t0)

    now, ok, out_total, new_total, back_total = datetime.now(timezone.utc), True, 0, 0, 0
    pending: dict[int, dict] = {}
    expired: set = set()
    failures: list[str] = []
    limited = 0
    for s, items, err in results:
        if isinstance(err, PermissionError):
            acc_id = login_of(s)
            if acc_id not in expired:
                expired.add(acc_id)
                label = by_id[acc_id]["label"]
                log.error("swiggy stockouts: login '%s' was refused (%s); its stores are skipped this pass", label, err)
                db.mark_session_expired(acc_id, f"swiggy stockouts: {err}")
                alerts.incident(f"Swiggy session expired: {label}", str(err),
                                f"Use Log in again on the Sessions page, or run `python run.py swiggy session --account {label}`.")
            ok = False
            continue
        if isinstance(err, RateLimited):
            limited += 1; ok = False
            if limited == 1:
                log.error("swiggy stockouts: %s, even after retries; those stores wait for the next cycle", err)
                alerts.incident("Swiggy rate limit (429)", str(err), "The job retried and backed off, but Swiggy kept refusing. If it keeps happening, raise the interval (--every 10) or lower SWIGGY_STOCKOUT_WORKERS.")
            continue
        if err:
            log.warning("swiggy stockouts %s (%s) failed: %s", s["outlet_name"], s["res_id"], err)
            failures.append(f"{type(err).__name__}: {str(err)[:160]}")
            ok = False
            continue
        try:
            new, back = retry.call(lambda: _save(s["outlet_id"], items, now, slots_of(s["outlet_id"]), "swiggy"),
                                   f"swiggy stockouts save {s['res_id']}")
        except Exception as e:
            log.exception("swiggy stockouts %s save failed: %s", s["res_id"], e)
            ok = False
            continue
        label = f"{s['brand']} · {s['outlet_name']}"
        p = pending.setdefault(s["client_id"], {"name": s["client"], "new": [], "back": []})
        p["new"] += [i | {"outlet": label} for i in new]
        p["back"] += [i | {"outlet": label} for i in back]
        out_total += len(items); new_total += len(new); back_total += len(back)
        log.info("swiggy stockouts %s · %s (%s): %s out of stock, %s new, %s back", s["brand"], s["outlet_name"],
                 s["res_id"], len(items), len(new), len(back))
    if len(failures) >= max(3, len(stores) // 5):
        top, n = Counter(failures).most_common(1)[0]
        alerts.incident("Swiggy stock-out checks failing", f"{len(failures)} of {len(stores)} menus failed this pass. "
                        f"Most common error ({n}×): {top}",
                        "Check the Swiggy stock-out window on the Windows server. Stock-outs for those stores are not up to date.")
    notify.send(("oos", "oos_back"))
    log.info("swiggy stockouts: %s out of stock across %s stores (%s new, %s back)", out_total, len(stores), new_total, back_total)
    return ok
