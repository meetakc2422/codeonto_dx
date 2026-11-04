"""Zomato customer complaints -> complaints table, for every Zomato id mapped to a store.

customer-issues/get-all gives the order ids with a complaint raised in the last ZOMATO_COMPLAINT_DAYS days
(default 30), for up to 9 res_ids per call; orders/order-details (view=customer_complaints_v2) then gives each
order's issues. A batch that fails (one unmapped id fails the whole call) is retried id by id. Orders whose
complaints closed more than a day ago are not fetched again.
"""

import time
from datetime import date, datetime, timedelta

from core import complaints, config as cfg, db
from core.common import ConfigError, log, require_env

from .outlets import _cookies
from .reviews import _headers

ZOMATO_ORIGIN = cfg.text("ZOMATO_ORIGIN", "https://www.zomato.com")
ISSUES_URL = cfg.text("ZOMATO_COMPLAINTS_URL", f"{ZOMATO_ORIGIN}/merchant-api/customer-issues/get-all")
DETAILS_URL = cfg.text("ZOMATO_COMPLAINT_DETAILS_URL", f"{ZOMATO_ORIGIN}/merchant-api/orders/order-details")
BATCH = 9


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _get(cookies: dict, url: str, params: dict) -> dict:
    import requests

    # www.zomato.com sits behind Akamai, which answers 403 to requests without a browser User-Agent
    headers = {**_headers(cookies), "referer": f"{ZOMATO_ORIGIN}/partners/onlineordering/customerIssues/",
               "user-agent": cfg.user_agent()}
    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = requests.get(url, params=params, headers=headers, timeout=cfg.http_timeout())
        if resp.status_code == 403 and resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()  # {"status": false, "code": 715, "message": "User is not mapped to requested restaurants"}
        if resp.status_code in (401, 403):
            raise PermissionError("Zomato session expired; run `run.py zomato session` for this account")
        if resp.status_code != 429 and resp.status_code < 500:
            resp.raise_for_status()
            return resp.json()
        log.warning("Zomato %s; backing off", resp.status_code)
    resp.raise_for_status()


def _order_ids(cookies: dict, res_ids: list[str], start: date, end: date) -> set[str] | None:
    data = _get(cookies, ISSUES_URL, {"select": "order_id", "res_id": ",".join(res_ids), "tag": "sticky_banner_config",
                                      "created_at": f"{start.isoformat()},{end.isoformat()}"})
    if data.get("status") is False:
        return None
    return {str(i) for i in data.get("entities") or []}


def _ts(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def _refund(title: str | None):
    # "Refund requested; ₹150"
    if title and "₹" in title:
        try:
            return float(title.split("₹")[-1].strip().replace(",", ""))
        except ValueError:
            return None
    return None


def _rows(data: dict, order_id: str, outlets: dict[str, int]) -> list[dict]:
    order = data.get("order") or {}
    outlet = outlets.get(str(order.get("resId")))
    if outlet is None:
        return []
    creator = order.get("creator") or {}
    context = " · ".join(str(x) for x in (creator.get("customerSegmentationDisplay"),
                                          f"{creator['orderCount']} orders" if creator.get("orderCount") else None) if x)
    rows = []
    for n, issue in enumerate((order.get("serviceRecovery") or {}).get("customerIssues") or [], start=1):
        st = issue.get("issueStatus") or {}
        items = ", ".join(f"{i.get('quantity')} x {i.get('name')}" for i in issue.get("items") or [])
        message = issue.get("message") or ""
        rows.append({
            "outlet": outlet, "platform": "zomato", "ext": f"{order_id}:{n}", "order": order_id,
            "issue_type": complaints.issue_type(message, st.get("title")), "detail": message, "items": items,
            "customer": (creator.get("name") or "")[:255], "context": context[:255],
            "pstatus": (st.get("status") or "")[:100], "resolution": " · ".join(x for x in (st.get("title"), st.get("description")) if x),
            "refund": _refund(st.get("title")), "raised": _ts(issue.get("createdAt")) or datetime.now().astimezone(),
            "expires": _ts(issue.get("expireAt")), "presolved": None, "raw": issue,
        })
    return rows


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("zomato complaints: %s", e)
        return False
    end = date.today()
    start = end - timedelta(days=cfg.integer("ZOMATO_COMPLAINT_DAYS", 30))

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "zomato", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.zomato_res_id AS res_id, z.account_id
                       FROM brand_outlets bo JOIN zomato_outlets z ON z.res_id = bo.zomato_res_id
                       WHERE bo.is_active AND z.is_active""")
        stores = cur.fetchall()
        # orders whose complaints are all past their window by a day: nothing left to change
        cur.execute("""SELECT order_id FROM complaints WHERE platform = 'zomato' GROUP BY order_id
                       HAVING max(coalesce(expires_at, raised_at)) < now() - interval '1 day'""")
        settled = {r["order_id"] for r in cur.fetchall()}
    if not stores:
        log.info("zomato complaints: no Zomato ids are mapped to stores yet")
        return True

    by_id = {a["id"]: a for a in accs.values()}
    default = next(iter(by_id))
    groups: dict[int, list[dict]] = {}
    for s in stores:
        groups.setdefault(s["account_id"] if s["account_id"] in by_id else default, []).append(s)

    ok, new, total = True, 0, 0
    for acc_id, group in groups.items():
        cookies = _cookies(db.load_credentials(by_id[acc_id]))
        outlets = {str(s["res_id"]): s["outlet_id"] for s in group}
        res_ids = list(outlets)
        try:
            order_ids: set[str] = set()
            for i in range(0, len(res_ids), BATCH):
                batch = res_ids[i:i + BATCH]
                found = _order_ids(cookies, batch, start, end)
                if found is None:
                    for rid in batch:
                        found_one = _order_ids(cookies, [rid], start, end)
                        if found_one is None:
                            log.warning("zomato complaints: Zomato refused res_id %s", rid)
                        order_ids |= found_one or set()
                else:
                    order_ids |= found
            todo = sorted(order_ids - settled)
            log.info("zomato complaints %s: %s orders with complaints, %s to fetch", by_id[acc_id]["label"], len(order_ids), len(todo))
            for order_id in todo:
                try:
                    rows = _rows(_get(cookies, DETAILS_URL, {"tab_id": order_id, "view": "customer_complaints_v2"}), order_id, outlets)
                    with db.transaction() as cur:
                        new += sum(complaints.save(cur, r) for r in rows)
                    total += len(rows)
                except PermissionError:
                    raise
                except Exception as e:
                    log.exception("zomato complaints order %s failed: %s", order_id, e)
                    ok = False
        except PermissionError as e:
            log.error("zomato complaints: %s", e)
            return False
        except Exception as e:
            log.exception("zomato complaints %s failed: %s", by_id[acc_id]["label"], e)
            ok = False
    log.info("zomato complaints: %s saved, %s new", total, new)
    return ok
