"""Bulk CSV upload of a brand's stores and their Zomato / Swiggy / Google ids.

Columns (header row required, any order, case-insensitive):
    store_name, area, city, zomato_res_id, swiggy_id, google_location_id

A row whose store_name matches an existing store of the brand updates it; otherwise a new
store is created. Every row is checked first (preview); saving is all-or-nothing and only
happens when no row has an error.
"""

import csv
import io

from .catalog import CATALOGS
from .mapping import MappingConflict, MappingError, save_brand_outlets
from .models import Brand, BrandOutlet

COLUMNS = {"store_name": "outlet_name", "area": "area", "city": "city",
           "zomato_res_id": "zomato", "swiggy_id": "swiggy", "google_location_id": "google"}
ALIASES = {"outlet_name": "store_name", "store": "store_name", "outlet": "store_name", "zomato": "zomato_res_id",
           "zomato_id": "zomato_res_id", "res_id": "zomato_res_id", "swiggy": "swiggy_id", "google": "google_location_id",
           "google_id": "google_location_id", "location_id": "google_location_id"}
MAX_ROWS = 2000


def _header(name: str) -> str:
    key = name.strip().lower().replace(" ", "_")
    return ALIASES.get(key, key)


def parse(text: str) -> tuple[list[dict], list[str]]:
    """CSV text -> rows keyed by our field names, plus file-level errors."""
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return [], ["The file is empty"]
    header = [_header(h) for h in rows[0]]
    if "store_name" not in header:
        return [], ["Header row must include store_name (columns: " + ", ".join(COLUMNS) + ")"]
    unknown = [h for h in header if h and h not in COLUMNS]
    if len(rows) - 1 > MAX_ROWS:
        return [], [f"At most {MAX_ROWS} rows per upload"]
    parsed = []
    for line_no, r in enumerate(rows[1:], start=2):
        values = {header[i]: (r[i].strip() if i < len(r) else "") for i in range(len(header)) if header[i] in COLUMNS}
        parsed.append({"line": line_no, **{COLUMNS[k]: v for k, v in values.items()}})
    return parsed, [f"Ignored unknown column(s): {', '.join(unknown)}"] if unknown else []


def check(brand: Brand, rows: list[dict], assign_unowned: bool = False) -> list[dict]:
    """Annotate each row with action (create/update) and its errors. No writes."""
    existing = {o.outlet_name.strip().lower(): o for o in brand.outlets.all()}
    seen_ids: dict[tuple, int] = {}
    seen_names: dict[str, int] = {}
    for row in rows:
        errors = []
        name = row.get("outlet_name", "")
        store = existing.get(name.lower()) if name else None
        row["action"] = "update" if store else "create"
        row["id"] = store.id if store else None
        if not name:
            errors.append("store_name is empty")
        elif name.lower() in seen_names:
            errors.append(f"store_name repeats line {seen_names[name.lower()]}")
        else:
            seen_names[name.lower()] = row["line"]
        for code, fname in BrandOutlet.PLATFORM_FIELDS.items():
            ext = row.get(code, "")
            if not ext:
                continue
            if (code, ext) in seen_ids:
                errors.append(f"{code} {ext} repeats line {seen_ids[(code, ext)]}")
                continue
            seen_ids[(code, ext)] = row["line"]
            model, pk, _, _ = CATALOGS[code]
            item = model.objects.select_related("brand_outlet__brand").filter(**{pk: ext}).first()
            if not item:
                errors.append(f"{code} {ext} not found in catalog")
            elif item.client_id != brand.client_id and not (assign_unowned and item.client_id is None):
                errors.append(f"{code} {ext} is not in {brand.client}'s access")
            elif not item.is_active:
                errors.append(f"{code} {ext} is inactive")
            else:
                bo = getattr(item, "brand_outlet", None)
                if bo and bo.id != row["id"]:
                    errors.append(f"{code} {ext} is already used by {bo.brand} · {bo.outlet_name}")
        row["errors"] = errors
    return rows


def import_csv(brand: Brand, text: str, commit: bool, assign_unowned: bool = False) -> dict:
    rows, file_errors = parse(text)
    rows = check(brand, rows, assign_unowned) if rows else []
    bad = [r for r in rows if r["errors"]]
    result = {"rows": rows, "file_errors": file_errors, "committed": False,
              "summary": {"rows": len(rows), "create": sum(r["action"] == "create" for r in rows),
                          "update": sum(r["action"] == "update" for r in rows), "errors": len(bad)}}
    blocking = [e for e in file_errors if not e.startswith("Ignored")]
    if not commit or bad or blocking or not rows:
        return result
    payload = [{"id": r["id"], **{k: r[k] for k in ("outlet_name", "area", "city", "zomato", "swiggy", "google") if k in r}}
               for r in rows]
    try:
        save_brand_outlets(brand, payload, [], move_conflicts=False, assign_unowned=assign_unowned)
    except (MappingError, MappingConflict) as e:  # something changed between check and save
        result["file_errors"].append(f"Not saved: {e if isinstance(e, MappingError) else e.conflicts}")
        return result
    result["committed"] = True
    return result
