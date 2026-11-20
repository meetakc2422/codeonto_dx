"""Zomato dining offers and table-booking slots -> dining_offer_snapshots / dining_slot_snapshots.

For every Zomato id marked is_dining, each run asks the District consumer app (api.edition.in) what a diner sees on the
table-booking page: the offers (discount, cover charge, SLOTS LEFT) per meal time, and the bookable 15-minute slots with
their discount, for today and the next days. Each run adds a snapshot; comparing runs shows how fast offers sell.

The District app login is a customer login, saved once as sessions/zomato_district.json:
    {"headers": {"x-access-token": ..., "x-refresh-token": ..., ...}}
Run:  python run.py zomato dining            (add --res-id to limit, e.g. for a test)
Schedule it 4 times a day:  python run.py zomato dining --daily-at 08:00   (one process per time)
"""

import json
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import requests

from core import config as cfg, db
from core.common import ConfigError, log, require_env, session_path

BASE = cfg.text("DINING_BASE_URL", "https://api.edition.in/gw/consumer/dining")
IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
DAYS = cfg.integer("DINING_DAYS", 7)
MEALS = [m.strip() for m in cfg.text("DINING_MEALS", "Lunch,Dinner,All Day").split(",") if m.strip()]
PACE_SEC = cfg.numbers("DINING_PACE_SEC", "0.6,1.4")
COVERS = cfg.integer("DINING_COVERS", 2)
KEEP_DAYS = cfg.integer("DINING_KEEP_DAYS", 30)  # readings older than this are deleted at the end of a run


def _session() -> dict:
    path = session_path("zomato_district", "app")
    if not path.exists():
        raise ConfigError(f"No District app login. Save the customer app's headers in {path} as {{\"headers\": {{...}}}}")
    return json.loads(path.read_text(encoding="utf-8-sig"))["headers"]  # utf-8-sig: PowerShell writes a byte-order mark


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


# ---- offers (JSON) ----------------------------------------------------------------------------------------------

def _text(x) -> str:
    return (x.get("text") or "").strip() if isinstance(x, dict) else ""


def parse_offers(resp: dict) -> list[dict]:
    """[{offer, discount_pct, window, slots_left, cover_charge}] from the offers answer. An offer card has a
    left_container title ('FLAT 15% OFF') and a right_container with the window and 'N slots left | Cover charge ₹25'."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            left, right = o.get("left_container"), o.get("right_container")
            if isinstance(left, dict) and isinstance(right, dict) and _text(left.get("title")):
                title = re.sub(r"\s+", " ", _text(left["title"]))
                sub = _text(right.get("subtitle"))
                pct = re.search(r"(\d+)\s*%", title)
                left_n = re.search(r"(\d+)\s*slots?\s*left", sub, re.I)
                cover = re.search(r"cover charge\s*[^\d]*([\d.]+)", sub, re.I)
                out.append({"offer": title, "discount_pct": int(pct.group(1)) if pct else None, "window": _text(right.get("title")),
                            "slots_left": int(left_n.group(1)) if left_n else None,
                            "cover_charge": Decimal(cover.group(1)) if cover else None})
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(resp)
    return out


# ---- slots (protobuf) -------------------------------------------------------------------------------------------

def _kv(key: str, value: str = "") -> bytes:
    k = key.encode()
    inner = b"\x0a" + bytes([len(k)]) + k
    if value:
        v = value.encode()
        inner += b"\x12" + bytes([len(v)]) + v
    return b"*" + bytes([len(inner)]) + inner


def slots_body(res_id: str, date: str, covers: int) -> bytes:
    return b"\x18\x01" + b"".join([
        _kv("res_id", res_id), _kv("ctx_date", date), _kv("ctx_covers", str(covers)), _kv("ctx_is_peak_hour", "false"),
        _kv("ctx_meal_time"), _kv("ctx_product_id"), _kv("ctx_start_time"), _kv("ctx_date_is_fallback", "1"),
        _kv("ctx_is_user_context_applicable", "1")])


def parse_slots(raw: bytes) -> list[dict]:
    """[{slot_time, meal_time, discount_pct}] read from the answer's text runs (it is protobuf; we don't need the schema).
    A slot appears as '<yyyymmdd>#<hhmm>', its label ('3:45 PM'), a 'top_details_update#<Meal>' marker, and
    'PREBOOK#<percent>#<cap>#<label>#...' carrying its discount."""
    runs = [m.decode() for m in re.findall(rb"[ -~]{3,}", raw)]
    slots, order, meal = {}, [], ""
    for r in runs:
        label = re.fullmatch(r"\d{1,2}:\d{2} [AP]M", r)
        if label and r not in slots:
            slots[r] = {"slot_time": r, "meal_time": "", "discount_pct": None}
            order.append(r)
            meal = ""
        m = re.search(r"top_details_update#(\w[\w ]*)", r)
        if m and order:
            slots[order[-1]]["meal_time"] = m.group(1)
        p = re.match(r"PREBOOK#(\d+)#\d+#(\d{1,2}:\d{2} [AP]M)", r)
        if p and p.group(2) in slots:
            slots[p.group(2)]["discount_pct"] = int(p.group(1))
    return [slots[k] for k in order]


# ---- calls ------------------------------------------------------------------------------------------------------

def _post(headers: dict, path: str, **kw):
    time.sleep(random.uniform(*PACE_SEC))
    resp = requests.post(f"{BASE}/{path}", headers=headers, timeout=cfg.http_timeout(), **kw)
    if resp.status_code in (401, 403):
        raise PermissionError("The District app login was refused; save a fresh customer login in sessions/zomato_district.json")
    resp.raise_for_status()
    return resp


def fetch_offers(headers: dict, res_id: str, date: str, meal: str) -> list[dict]:
    h = {**headers, "content-type": "application/json; charset=UTF-8"}
    r = _post(h, "restaurant/offers", json={"date": date, "res_id": res_id, "meal_time": meal, "postback_params": "", "ctx_covers": "0"})
    return parse_offers(r.json())


def fetch_slots(headers: dict, res_id: str, date: str) -> list[dict]:
    h = {**headers, "accept": "application/x-protobuf", "content-type": "application/x-protobuf"}
    return parse_slots(_post(h, "tr/v2/slots", data=slots_body(res_id, date, COVERS)).content)


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    require_env("CODEONTO_DATABASE_URL")
    headers = _session()
    only = {x for x in os.getenv("ONLY_RES_IDS", "").split(",") if x}
    with db.transaction() as cur:
        cur.execute("""SELECT z.res_id, bo.id AS outlet_id FROM zomato_outlets z LEFT JOIN brand_outlets bo ON bo.zomato_res_id = z.res_id
                       WHERE z.is_dining AND z.is_active""")
        stores = [s for s in cur.fetchall() if not only or s["res_id"] in only]
    if not stores:
        log.warning("zomato dining: no active Zomato ids are marked is_dining")
        return True
    now = datetime.now(timezone.utc)
    today = datetime.now(IST).date()
    ok, offers_saved, slots_saved = True, 0, 0
    for s in stores:
        rid, offers, slots = str(s["res_id"]), [], []
        try:
            for d in range(DAYS):
                day = (today + timedelta(days=d)).isoformat()
                seen = set()
                for meal in MEALS:
                    for o in fetch_offers(headers, rid, day, meal):
                        key = (o["offer"], o["window"])
                        if key in seen and meal != MEALS[0]:  # the same offer repeats across meals; keep it once with the first meal that has it
                            continue
                        seen.add(key)
                        offers.append((rid, s["outlet_id"], now, day, meal, o["offer"], o["discount_pct"], o["window"], o["slots_left"], o["cover_charge"]))
                for sl in fetch_slots(headers, rid, day):
                    slots.append((rid, s["outlet_id"], now, day, sl["meal_time"], sl["slot_time"], sl["discount_pct"]))
        except PermissionError:
            raise
        except Exception as e:
            ok = False
            log.warning("zomato dining %s: %s", rid, e)
            continue
        with db.transaction() as cur:
            cur.executemany("""INSERT INTO dining_offer_snapshots (res_id, outlet_id, taken_at, for_date, meal_time, offer, discount_pct, "window", slots_left, cover_charge)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", offers)
            cur.executemany("""INSERT INTO dining_slot_snapshots (res_id, outlet_id, taken_at, for_date, meal_time, slot_time, discount_pct)
                               VALUES (%s,%s,%s,%s,%s,%s,%s)""", slots)
        offers_saved += len(offers); slots_saved += len(slots)
        log.info("zomato dining %s: %d offers, %d slots over %d days", rid, len(offers), len(slots), DAYS)
    log.info("zomato dining: %d offer rows and %d slot rows saved for %d stores", offers_saved, slots_saved, len(stores))
    if KEEP_DAYS > 0:
        try:
            with db.transaction() as cur:
                cur.execute("DELETE FROM dining_slot_snapshots WHERE taken_at < now() - make_interval(days => %s)", (KEEP_DAYS,))
                gone_slots = cur.rowcount
                cur.execute("DELETE FROM dining_offer_snapshots WHERE taken_at < now() - make_interval(days => %s)", (KEEP_DAYS,))
                gone_offers = cur.rowcount
            if gone_slots or gone_offers:
                log.info("zomato dining: removed readings older than %d days (%d slot rows, %d offer rows)", KEEP_DAYS, gone_slots, gone_offers)
        except Exception as e:
            log.warning("zomato dining: could not clean old readings: %s", e)
    return ok
