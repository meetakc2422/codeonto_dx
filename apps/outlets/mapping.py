"""Save a brand's outlets and their platform ids, with conflict detection and moves."""

from dataclasses import dataclass, field

from django.db import transaction

from apps.metrics.models import MetricDaily
from apps.reviews.models import Review

from .catalog import CATALOGS
from .models import Brand, BrandOutlet


class MappingError(Exception):
    pass


@dataclass
class MappingConflict(Exception):
    conflicts: list[dict] = field(default_factory=list)


def _clean(v) -> str:
    return (str(v) if v is not None else "").strip()


@transaction.atomic
def save_brand_outlets(brand: Brand, outlets: list[dict], delete_ids: list[int], move_conflicts: bool,
                       assign_unowned: bool = False) -> dict:
    """outlets: [{id?, outlet_name, area, city, address, zomato, swiggy, google}] where the platform
    values are catalog ids ('' = unmapped; key absent = leave as is).

    Raises MappingError for invalid input and MappingConflict (nothing saved) when an id
    belongs to another store, unless move_conflicts is set.
    """
    platforms = BrandOutlet.PLATFORM_FIELDS

    seen: dict[tuple, str] = {}
    for o in outlets:
        if not _clean(o.get("outlet_name")):
            raise MappingError("Every outlet needs a name")
        for code in platforms:
            ext = _clean(o.get(code))
            if ext and (code, ext) in seen:
                raise MappingError(f"{code} id {ext} is used for both '{seen[(code, ext)]}' and '{o['outlet_name']}'")
            if ext:
                seen[(code, ext)] = o["outlet_name"]

    conflicts, saved = [], 0
    for o in outlets:
        if o.get("id"):
            bo = BrandOutlet.objects.select_for_update().filter(pk=o["id"], brand=brand).first()
            if not bo:
                raise MappingError(f"Outlet {o['id']} does not belong to {brand}")
        else:
            bo = BrandOutlet(brand=brand)
        for f in ("outlet_name", "area", "city", "address"):
            if f in o:
                setattr(bo, f, _clean(o[f]))
        bo.save()
        saved += 1

        for code, fname in platforms.items():
            if code not in o:
                continue
            ext = _clean(o[code])
            if ext == (getattr(bo, f"{fname}_id") or ""):
                continue
            if not ext:
                setattr(bo, fname, None)
                continue
            model, pk, _, _ = CATALOGS[code]
            item = model.objects.filter(**{pk: ext}).first()
            if not item:
                raise MappingError(f"{code} id {ext} is not in the {code} catalog. Run the catalog sync or check the id.")
            if item.client_id is None and assign_unowned:
                # staff mapping an unassigned id: it becomes this client's
                item.client_id = brand.client_id
                item.save(update_fields=["client"])
            if item.client_id != brand.client_id:
                raise MappingError(f"{code} id {ext} is not in {brand.client}'s access"
                                   + ("" if item.client_id else " (no client assigned yet; ask Codeonto)"))
            owner = BrandOutlet.objects.filter(**{fname: item}).exclude(pk=bo.pk).select_related("brand").first()
            if owner and not move_conflicts:
                conflicts.append({"platform": code, "id": ext, "outlet": o["outlet_name"],
                                  "mapped_to": f"{owner.brand} · {owner.outlet_name}"})
                continue
            if owner:
                setattr(owner, fname, None)
                owner.save(update_fields=[fname, "updated_at"])
                # history recorded for that platform follows the id to its new store
                Review.objects.filter(outlet=owner, platform_id=code).update(outlet=bo)
                MetricDaily.objects.filter(outlet=owner, platform_id=code).update(outlet=bo)
            if not item.is_active and not owner:
                raise MappingError(f"{code} id {ext} is inactive (no longer in our accounts)")
            setattr(bo, fname, item)
        bo.save()

    if conflicts:
        raise MappingConflict(conflicts)

    deleted = 0
    if delete_ids:
        _, per_model = BrandOutlet.objects.filter(brand=brand, pk__in=delete_ids).delete()
        deleted = per_model.get(BrandOutlet._meta.label, 0)
    return {"saved": saved, "deleted": deleted}
