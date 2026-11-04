"""Write outlet catalogs (zomato_outlets / swiggy_outlets / google_locations)."""

from dataclasses import dataclass

from .common import log

# platform -> (table, primary key column, optional text columns besides name/city)
CATALOG_TABLES = {
    "zomato": ("zomato_outlets", "res_id", ["area"]),
    "swiggy": ("swiggy_outlets", "swiggy_id", ["area"]),
    "google": ("google_locations", "location_id", ["address", "business_account"]),
}

# Refuse to deactivate more than this share of a catalog in one run (truncated / partial API responses)
MAX_DEACTIVATE_RATIO = 0.2


@dataclass
class Outlet:
    external_id: str
    name: str
    area: str = ""
    city: str = ""
    address: str = ""
    business_account: str = ""


def upsert(cur, platform: str, outlets: list[Outlet], account_id: int, client_id: int | None = None) -> dict:
    """Insert new ids, refresh existing ones, link all to the account.
    Empty values never overwrite known ones (e.g. Swiggy sends no city).

    client_id: the account is a client's own login, so every id it can access becomes that
    client's, unless another client already owns it (left as is and reported)."""
    table, pk, extra = CATALOG_TABLES[platform]
    cols = ["name", "city", *extra]
    cur.execute(f"SELECT {pk}, client_id FROM {table} WHERE {pk} = ANY(%s)", ([o.external_id for o in outlets],))
    owners = {r[pk]: r["client_id"] for r in cur.fetchall()}
    existing = set(owners)
    for o in outlets:
        values = {c: (getattr(o, c) or "").strip() for c in cols}
        cur.execute(
            f"""INSERT INTO {table} ({pk}, {", ".join(cols)}, account_id, is_active, first_seen_at, last_seen_at)
                VALUES (%(id)s, {", ".join(f"%({c})s" for c in cols)}, %(acc)s, true, now(), now())
                ON CONFLICT ({pk}) DO UPDATE SET
                  {", ".join(f"{c} = COALESCE(NULLIF(EXCLUDED.{c}, ''), {table}.{c})" for c in cols)},
                  account_id = EXCLUDED.account_id, is_active = true, last_seen_at = now()""",
            {"id": o.external_id, "acc": account_id, **values},
        )
    stats = {"outlets": len(outlets), "new": len({o.external_id for o in outlets} - existing)}
    if client_id:
        ids = [o.external_id for o in outlets]
        cur.execute(f"UPDATE {table} SET client_id = %s WHERE {pk} = ANY(%s) AND client_id IS NULL", (client_id, ids))
        stats["assigned_to_client"] = cur.rowcount
        taken = [i for i in ids if owners.get(i) not in (None, client_id)]
        if taken:
            stats["owned_by_other_client"] = len(taken)
            log.warning("%s: %s ids from this client's login already belong to another client (left unchanged): %s",
                        platform, len(taken), ", ".join(taken[:10]) + (" …" if len(taken) > 10 else ""))
    return stats


def deactivate_missing(cur, platform: str, seen: set[str], force: bool) -> dict:
    """Mark ids no account returned as inactive, within the safety limit unless forced."""
    table, pk, _ = CATALOG_TABLES[platform]
    cur.execute(f"SELECT count(*) AS n FROM {table} WHERE is_active", ())
    active = cur.fetchone()["n"]
    cur.execute(f"SELECT count(*) AS n FROM {table} WHERE is_active AND NOT ({pk} = ANY(%s))", (list(seen),))
    missing = cur.fetchone()["n"]
    if not missing:
        return {"deactivated": 0}
    if not force and missing > MAX_DEACTIVATE_RATIO * active:
        log.warning("%s: %s ids not returned by any account were left active (over %.0f%% of the catalog). "
                    "Check the accounts, then re-run with --force to deactivate them.",
                    platform, missing, MAX_DEACTIVATE_RATIO * 100)
        return {"deactivated": 0, "held_back": missing}
    cur.execute(f"UPDATE {table} SET is_active = false WHERE is_active AND NOT ({pk} = ANY(%s))", (list(seen),))
    return {"deactivated": cur.rowcount}
