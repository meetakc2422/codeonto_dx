"""Swiggy customer complaints -> complaints table, for every Swiggy id mapped to a store.

One paged getComplaints query per account (up to SWIGGY_COMPLAINT_BATCH restaurant ids per query, default 20)
covering complaints raised in the last SWIGGY_COMPLAINT_DAYS days (default 30), resolved or not, so refund
decisions made after the first sync are picked up.
"""

import re
import time
from datetime import date, datetime, timedelta, timezone

from core import complaints, config as cfg, db
from core.common import ConfigError, log, require_env

from .reviews import _headers

COMPLAINTS_URL = cfg.text("SWIGGY_COMPLAINTS_URL", "https://vhc-composer.swiggy.com/query?query=Complaints")
ISSUE_TYPES = ["MISSING_ITEMS", "WRONG_ITEMS", "QUALITY_ISSUES", "QUANTITY_ISSUES", "SPILLAGE_ISSUES",
               "PACKAGING_AND_SPILLAGE_ISSUES", "PACKAGING_ISSUES"]
QUERY = """query Complaints($restaurantIds: [Int64!]!, $complaintStartDate: String, $complaintEndDate: String,
  $issueTypes: [String!], $complaintStates: [ComplaintState!], $complaintResolutionStates: [ResolutionStatus!],
  $limit: Int, $nextToken: String, $rating: [Int!], $sortBy: String) {
  getComplaints(restaurantIds: $restaurantIds, complaintStartDate: $complaintStartDate, complaintEndDate: $complaintEndDate,
    issueTypes: $issueTypes, complaintStates: $complaintStates, complaintResolutionStates: $complaintResolutionStates,
    limit: $limit, nextToken: $nextToken, ratings: $rating, sortBy: $sortBy) {
    complaints { restaurantId complaintId orderId customerContextDescription issueType issueDescription
      createTimestamp complaintExpiryTimestamp complaintItemDescription complaintItemDescriptionV2 issueL2Disposition
      complaintState restaurantDispositionType
      restaurantResolution { resolutionStatus amountRefunded reasonForNoRefund resolutionTimestamp approvedBy
        resolutionType couponAmountRefunded }
      ratings { latestRating oldestRating customerName } }
    nextToken } }"""


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _fetch(creds: dict, res_ids: list[str], start: date, end: date) -> list[dict]:
    import requests

    token = creds.get("access_token")
    if not token:
        raise ConfigError("Session file has no access_token; run `run.py swiggy session` for this account")
    out, next_token = [], None
    while True:
        variables = {"restaurantIds": [int(r) for r in res_ids], "rating": [], "sortBy": "RECENT_COMPLAINTS",
                     "complaintStartDate": start.isoformat(), "complaintEndDate": end.isoformat(),
                     "complaintStates": ["UNRESOLVED", "RESOLVED"], "complaintResolutionStates": [],
                     "issueTypes": ISSUE_TYPES, "limit": 50, "nextToken": next_token}
        for wait in cfg.retry_waits():
            time.sleep(wait)
            resp = requests.post(COMPLAINTS_URL, headers=_headers(token), timeout=cfg.http_timeout(),
                                 json={"query": QUERY, "variables": variables, "operationName": "Complaints"})
            if resp.status_code in (401, 403):
                raise PermissionError("Swiggy session expired; run `run.py swiggy session` for this account")
            if resp.status_code != 429 and resp.status_code < 500:
                break
            log.warning("Swiggy %s; backing off", resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            raise RuntimeError(f"Swiggy complaints: {data['errors'][0].get('message')}")
        result = (data.get("data") or {}).get("getComplaints") or {}
        page = result.get("complaints") or []
        out += page
        next_token = result.get("nextToken")
        if not next_token or not page:
            return out


def _ts(epoch) -> datetime | None:
    if not epoch:
        return None
    epoch = float(epoch)
    return datetime.fromtimestamp(epoch / 1000 if epoch > 1e12 else epoch, tz=timezone.utc)


def _row(c: dict, outlet_id: int) -> dict:
    res = c.get("restaurantResolution") or {}
    ratings = c.get("ratings") or {}
    items = c.get("complaintItemDescriptionV2") or c.get("complaintItemDescription") or ""
    refund = sum(float(x) for x in (res.get("amountRefunded"), res.get("couponAmountRefunded")) if x) or None
    return {
        "outlet": outlet_id, "platform": "swiggy", "ext": str(c["complaintId"]), "order": str(c.get("orderId") or ""),
        "issue_type": complaints.issue_type(c.get("issueType")),
        "detail": " · ".join(x for x in (c.get("issueDescription"), c.get("issueL2Disposition")) if x),
        "items": " | ".join(items) if isinstance(items, list) else str(items),
        "customer": (ratings.get("customerName") or "")[:255], "context": (c.get("customerContextDescription") or "")[:255],
        "pstatus": " · ".join(x for x in (c.get("complaintState"), res.get("resolutionStatus")) if x)[:100],
        "resolution": " · ".join(x for x in (res.get("resolutionType"), res.get("reasonForNoRefund")) if x),
        "refund": refund, "raised": _ts(c.get("createTimestamp")) or datetime.now(timezone.utc),
        "expires": _ts(c.get("complaintExpiryTimestamp")), "presolved": _ts(res.get("resolutionTimestamp")), "raw": c,
    }


def _fetch_skipping(creds: dict, batch: list[str], start, end, refused: list[str]) -> list[dict]:
    """_fetch, but one outlet this login may not read no longer sinks the whole batch: on "Invalid Outlet ID /
    Unauthorised" the batch is split in halves until the refused outlets are found; they're noted and skipped."""
    try:
        return _fetch(creds, batch, start, end)
    except RuntimeError as e:
        if not re.search(r"invalid outlet|unauthori", str(e), re.I):
            raise
        if len(batch) == 1:
            refused.append(batch[0])
            return []
        mid = len(batch) // 2
        return _fetch_skipping(creds, batch[:mid], start, end, refused) + _fetch_skipping(creds, batch[mid:], start, end, refused)


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("swiggy complaints: %s", e)
        return False
    end = date.today()
    start = end - timedelta(days=cfg.integer("SWIGGY_COMPLAINT_DAYS", 30))
    start, end = cfg.date_range(start, end)  # BACKFILL_FROM/TO
    size = cfg.integer("SWIGGY_COMPLAINT_BATCH", 20)

    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "swiggy", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.swiggy_id AS res_id, s.account_id
                       FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id
                       WHERE bo.is_active AND s.is_active""")
        stores = cur.fetchall()
        stores = cfg.keep_stores(stores)  # ONLY_RES_IDS (backfill)
    if not stores:
        log.info("swiggy complaints: no Swiggy ids are mapped to stores yet")
        return True

    creds = {a["id"]: db.load_credentials(a) for a in accs.values()}
    by_id = {a["id"]: a for a in accs.values()}
    groups: dict[int, dict[str, int]] = {}
    visible = {i: {str(x) for x in c.get("outlets") or []} for i, c in creds.items()}
    unreachable = []
    for s in stores:
        # the account whose restaurant list has this id; else, when no login lists its outlets, the catalog's owner
        acc_id = next((i for i, ids in visible.items() if str(s["res_id"]) in ids), None)
        if acc_id is None:
            if any(visible.values()):  # the logins do list their outlets and none has this one: asking would fail the batch
                unreachable.append(str(s["res_id"]))
                continue
            acc_id = s["account_id"] if s["account_id"] in by_id else next(iter(by_id))
        groups.setdefault(acc_id, {})[str(s["res_id"])] = s["outlet_id"]

    ok, new, total, refused = True, 0, 0, []
    for acc_id, outlets in groups.items():
        res_ids = list(outlets)
        for i in range(0, len(res_ids), size):
            batch = res_ids[i:i + size]
            try:
                rows = [_row(c, outlets[str(c.get("restaurantId"))]) for c in _fetch_skipping(creds[acc_id], batch, start, end, refused)
                        if c.get("complaintId") and str(c.get("restaurantId")) in outlets]
                with db.transaction() as cur:
                    new += sum(complaints.save(cur, r) for r in rows)
                total += len(rows)
                log.info("swiggy complaints %s: %s complaints for %s stores", by_id[acc_id]["label"], len(rows), len(batch))
            except PermissionError as e:
                log.error("swiggy complaints: %s", e)
                return False
            except Exception as e:
                log.exception("swiggy complaints %s failed: %s", by_id[acc_id]["label"], e)
                ok = False
    if unreachable:
        log.warning("swiggy complaints: %s mapped outlets aren't in any login's outlet list, skipped: %s", len(unreachable), ", ".join(unreachable))
    if refused:
        log.warning("swiggy complaints: Swiggy refused %s outlets, skipped: %s", len(refused), ", ".join(refused))
    log.info("swiggy complaints: %s saved, %s new", total, new)
    return ok
