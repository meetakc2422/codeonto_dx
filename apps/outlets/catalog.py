"""Bootstrap the Zomato / Swiggy / Google catalogs from the pipeline database (read-only).

Live catalogs come from the collector (`collector/run.py <platform> outlets`), which asks
each master account directly; Django itself never calls the platforms for this."""

from django.db import transaction
from django.utils import timezone

from . import pipeline
from .models import GoogleLocation, SwiggyOutlet, ZomatoOutlet

# platform -> (model, primary key field, source rows, extra fields copied from source)
CATALOGS = {
    "zomato": (ZomatoOutlet, "res_id", lambda: pipeline.marketplace_outlets("zomato"), ["area"]),
    "swiggy": (SwiggyOutlet, "swiggy_id", lambda: pipeline.marketplace_outlets("swiggy"), ["area"]),
    "google": (GoogleLocation, "location_id", pipeline.google_locations, ["address"]),
}


def sync_catalog(platforms: list[str] | None = None) -> dict[str, dict]:
    """Upsert every outlet the pipeline knows; mark ones that disappeared as inactive.

    A platform whose source returns nothing is left untouched (no mass deactivation).
    """
    result = {}
    for code in platforms or CATALOGS:
        model, pk, fetch, extra = CATALOGS[code]
        rows = [r for r in fetch() if r["external_id"]]
        if not rows:
            result[code] = {"source_rows": 0, "skipped": True}
            continue
        now = timezone.now()
        existing = set(model.objects.values_list(pk, flat=True))
        objs = [
            model(**{pk: str(r["external_id"]), "name": r["name"] or str(r["external_id"]),
                     "city": r["city"] or "", "is_active": bool(r["is_active"]), "last_seen_at": now,
                     **{f: r.get(f) or "" for f in extra}})
            for r in rows
        ]
        with transaction.atomic():
            model.objects.bulk_create(
                objs, update_conflicts=True, unique_fields=[pk],
                update_fields=["name", "city", "is_active", "last_seen_at", *extra],
            )
            seen = {getattr(o, pk) for o in objs}
            gone = model.objects.filter(is_active=True).exclude(**{f"{pk}__in": seen}).update(is_active=False)
        result[code] = {"source_rows": len(rows), "new": len(seen - existing), "deactivated": gone}
    return result
