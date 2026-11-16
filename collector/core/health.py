"""`run.py alerts health`: once a day, check that every outlet that normally has data still gets it, and email ops the gaps.

An outlet counts as a gap when it had data for a source in the last 14 days but nothing for yesterday: that is a
collector that stopped, an expired login, or an outlet that closed. Outlets that never had data are not nagged about
(that is a setup question, not a failure). Nothing is sent when there are no gaps."""
import html
import os
import time
from datetime import datetime, timedelta, timezone

from . import alerts, config as cfg, db
from .common import log

IST = timezone(timedelta(minutes=cfg.timezone_offset_minutes()))
LOOKBACK_DAYS = 14
# label, table, outlet column, date column, platform column, platforms that should have it
SOURCES = [
    ("Order history", "order_lines", "outlet_id", "order_date", "platform", ("zomato", "swiggy")),
    ("Sales & KPIs", "metric_daily", "outlet_id", "metric_date", "platform", ("zomato", "swiggy")),
    ("Item sales", "item_sales_daily", "outlet_id", "day", "platform", ("zomato",)),
    ("Store uptime", "outlet_uptime_daily", "outlet_id", "day", "platform", ("zomato",)),
]


def find_gaps(cur, yesterday) -> list[dict]:
    since = yesterday - timedelta(days=LOOKBACK_DAYS)
    gaps = []
    for label, table, outlet_col, date_col, plat_col, platforms in SOURCES:
        cur.execute(f"""SELECT t.{outlet_col} AS outlet_id, t.{plat_col} AS platform, max(t.{date_col}) AS last_day,
                               b.name AS brand, bo.outlet_name, bo.area
                        FROM {table} t JOIN brand_outlets bo ON bo.id = t.{outlet_col} JOIN brands b ON b.id = bo.brand_id
                        WHERE bo.is_active AND t.{date_col} >= %s AND t.{plat_col} = ANY(%s)
                        GROUP BY t.{outlet_col}, t.{plat_col}, b.name, bo.outlet_name, bo.area""", (since, list(platforms)))
        for r in cur.fetchall():
            if r["last_day"] < yesterday:
                gaps.append({"source": label, "platform": r["platform"], "brand": r["brand"],
                             "outlet": r["area"] or r["outlet_name"], "last_day": r["last_day"]})
    return gaps


def render(gaps: list[dict], yesterday) -> str:
    """One block per source and platform, brands grouped, worst (longest silent) first."""
    blocks = {}
    for g in gaps:
        blocks.setdefault((g["source"], g["platform"]), []).append(g)
    parts = []
    for (source, platform), rows in sorted(blocks.items(), key=lambda kv: -len(kv[1])):
        by_brand = {}
        for g in rows:
            by_brand.setdefault(g["brand"], []).append(g)
        lines = "".join(
            f'<tr><td style="padding:3px 10px">{html.escape(brand)}</td><td style="padding:3px 10px">{len(items)}</td>'
            f'<td style="padding:3px 10px;color:#667085">{html.escape(", ".join(i["outlet"] for i in items[:4]))}'
            f'{" …" if len(items) > 4 else ""} · last data {min(i["last_day"] for i in items):%d %b}</td></tr>'
            for brand, items in sorted(by_brand.items(), key=lambda kv: -len(kv[1])))
        parts.append(f'<h3 style="margin:18px 0 4px">{html.escape(source)} · {html.escape(platform)} · {len(rows)} outlet(s)</h3>'
                     f'<table style="border-collapse:collapse;font-size:13px">{lines}</table>')
    return (f'<div style="font-family:Arial,sans-serif;max-width:900px"><h2 style="color:#c9302c">Data gaps for {yesterday:%d %b}</h2>'
            f'<p>These outlets had data in the last {LOOKBACK_DAYS} days but nothing for yesterday.</p>{"".join(parts)}'
            f'<p style="color:#667085">Common causes: an expired login (Sessions page), a task that is not running on its server, or an outlet that closed.</p></div>')


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    yesterday = (datetime.now(IST) - timedelta(days=1)).date()
    with db.transaction() as cur:
        gaps = find_gaps(cur, yesterday)
    if not gaps:
        log.info("health: no data gaps for %s", yesterday)
        return True
    log.warning("health: %s data gap(s) for %s", len(gaps), yesterday)
    to = [e.strip() for e in os.getenv("ALERT_OPS_EMAILS", "").split(",") if e.strip()]
    if not to:
        log.warning("health: ALERT_OPS_EMAILS is empty, so the gap list was not emailed")
        return True
    return alerts.send_email(to, f"[Codeonto collector] {len(gaps)} data gap(s) for {yesterday:%d %b}", render(gaps, yesterday))
