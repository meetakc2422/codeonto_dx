"""Shared by the Zomato and Swiggy complaint collectors: one issue-type vocabulary and one upsert into complaints."""

import json
import re

# first match wins; Swiggy sends codes (MISSING_ITEMS), Zomato free text ("Items missing from my order")
ISSUE_TYPES = [
    ("missing_items", r"missing"),
    ("wrong_items", r"wrong|different item|incorrect"),
    ("quantity", r"quantity|portion|less food"),
    ("packaging", r"spill|packag|leak"),
    ("quality", r"quality|taste|stale|cold|undercook|burnt|hair|insect|foreign|raw|smell"),
]


def issue_type(*texts) -> str:
    text = " ".join(t for t in texts if t).lower().replace("_", " ")
    if not text:
        return ""
    return next((code for code, pattern in ISSUE_TYPES if re.search(pattern, text)), "other")


def save(cur, row: dict) -> bool:
    """Insert or refresh one complaint; True when it is new. Ticket fields (status, assigned_to, note) are left alone."""
    cur.execute("SELECT 1 FROM complaints WHERE platform = %(platform)s AND external_id = %(ext)s", row)
    new = cur.fetchone() is None
    cur.execute(
        """INSERT INTO complaints (outlet_id, platform, external_id, order_id, issue_type, issue_detail, items, customer_name,
                                   customer_context, platform_status, resolution, refund_amount, raised_at, expires_at,
                                   platform_resolved_at, status, note, raw, created_at, updated_at)
           VALUES (%(outlet)s, %(platform)s, %(ext)s, %(order)s, %(issue_type)s, %(detail)s, %(items)s, %(customer)s,
                   %(context)s, %(pstatus)s, %(resolution)s, %(refund)s, %(raised)s, %(expires)s,
                   %(presolved)s, 'open', '', %(raw)s::jsonb, now(), now())
           ON CONFLICT (platform, external_id) DO UPDATE SET
             outlet_id = EXCLUDED.outlet_id, issue_type = EXCLUDED.issue_type, issue_detail = EXCLUDED.issue_detail,
             items = EXCLUDED.items, customer_name = EXCLUDED.customer_name, customer_context = EXCLUDED.customer_context,
             platform_status = EXCLUDED.platform_status, resolution = EXCLUDED.resolution,
             refund_amount = EXCLUDED.refund_amount, expires_at = EXCLUDED.expires_at,
             platform_resolved_at = EXCLUDED.platform_resolved_at, raw = EXCLUDED.raw, updated_at = now()""",
        {**row, "raw": json.dumps(row["raw"], default=str)},
    )
    return new
