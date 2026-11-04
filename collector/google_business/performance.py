"""Google Business Profile performance -> metric_daily, for every Google location mapped to a store.

Daily counts of how people found and used each listing (views on Search and Maps, website clicks,
calls, direction requests, menu clicks, food orders). Google publishes these with a delay of a few
days. Window: GOOGLE_METRICS_DAYS (default 30); re-running just refreshes the same days.
"""

import os
import time
from datetime import date, timedelta

from core import config as cfg, db
from core.common import ConfigError, log, require_env

from .session import credentials_from

URL = cfg.text("GOOGLE_PERFORMANCE_URL", "https://businessprofileperformance.googleapis.com/v1/locations/{location_id}:fetchMultiDailyMetricsTimeSeries")
PUBLISH_LAG_DAYS = cfg.integer("GOOGLE_METRICS_LAG_DAYS", 2)  # the newest days are not published yet
# Google metric -> KPI code (several metrics can feed one KPI): mappings/google_performance_metrics.json
KPI_OF = cfg.mapping("google_performance_metrics")


def config(account: str) -> dict:
    return require_env("CODEONTO_DATABASE_URL")


def _fetch(session, location_id: str, start: date, end: date) -> dict[tuple[str, date], int]:
    """{(kpi code, day): value} summed over the metrics feeding each KPI."""
    params = [("dailyMetrics", m) for m in KPI_OF] + [
        ("dailyRange.startDate.year", start.year), ("dailyRange.startDate.month", start.month), ("dailyRange.startDate.day", start.day),
        ("dailyRange.endDate.year", end.year), ("dailyRange.endDate.month", end.month), ("dailyRange.endDate.day", end.day)]
    for wait in cfg.retry_waits():
        time.sleep(wait)
        resp = session.get(URL.format(location_id=location_id), params=params, timeout=cfg.http_timeout())
        if resp.status_code in (401, 403):
            detail = resp.json().get("error", {}).get("message", "") if resp.content else ""
            raise PermissionError(f"Google API refused access ({resp.status_code}): {detail}")
        if resp.status_code == 429 or resp.status_code >= 500:
            log.warning("Google %s; backing off", resp.status_code)
            continue
        resp.raise_for_status()
        break
    else:
        resp.raise_for_status()
    out: dict[tuple[str, date], int] = {}
    for group in resp.json().get("multiDailyMetricTimeSeries", []):
        for series in group.get("dailyMetricTimeSeries", []):
            code = KPI_OF.get(series.get("dailyMetric"))
            for dv in (series.get("timeSeries") or {}).get("datedValues") or []:
                d = dv.get("date") or {}
                if not code or not d:
                    continue
                key = (code, date(d["year"], d["month"], d["day"]))
                out[key] = out.get(key, 0) + int(dv.get("value") or 0)
    return out


def run_all(accounts: list[str], headless: bool = False, force: bool = False) -> bool:
    try:
        config("")
    except ConfigError as e:
        log.error("google performance: %s", e)
        return False
    from google.auth.transport.requests import AuthorizedSession

    days = cfg.integer("GOOGLE_METRICS_DAYS", 30)
    end = date.today() - timedelta(days=PUBLISH_LAG_DAYS)
    start = end - timedelta(days=days - 1)
    with db.transaction() as cur:
        accs = {a: db.get_account(cur, "google", a) for a in accounts}
        cur.execute("""SELECT bo.id AS outlet_id, bo.google_location_id AS location_id, g.account_id, b.name AS brand, bo.outlet_name
                       FROM brand_outlets bo JOIN google_locations g ON g.location_id = bo.google_location_id
                       JOIN brands b ON b.id = bo.brand_id WHERE bo.is_active AND g.is_active""")
        stores = cur.fetchall()
        cur.execute("SELECT code, id FROM kpis WHERE code = ANY(%s)", (list(set(KPI_OF.values())),))
        kpi_id = {r["code"]: r["id"] for r in cur.fetchall()}
    if not stores:
        log.info("google performance: no Google locations are mapped to stores yet")
        return True
    if len(kpi_id) < len(set(KPI_OF.values())):
        log.error("google performance: KPIs missing in the database; run `manage.py migrate`")
        return False

    by_id = {a["id"]: a for a in accs.values()}
    sessions = {}
    for a in accs.values():
        try:
            sessions[a["id"]] = AuthorizedSession(credentials_from(db.load_credentials(a)))
        except (PermissionError, ConfigError) as e:
            log.error("google performance: account %s: %s", a["label"], e)
            return False
    default = next(iter(by_id))
    # a location is only readable by the login that owns it: skip the others instead of trying them (404s)
    stores = [s for s in stores if s["account_id"] is None or s["account_id"] in by_id]
    ok = True
    for s in stores:
        try:
            data = _fetch(sessions[s["account_id"] if s["account_id"] in by_id else default], s["location_id"], start, end)
            with db.transaction() as cur:
                for (code, day), value in data.items():
                    cur.execute(
                        """INSERT INTO metric_daily (outlet_id, platform, kpi_id, metric_date, value, weight, updated_at)
                           VALUES (%s, 'google', %s, %s, %s, 1, now())
                           ON CONFLICT (outlet_id, platform, kpi_id, metric_date)
                           DO UPDATE SET value = EXCLUDED.value, updated_at = now()""",
                        (s["outlet_id"], kpi_id[code], day, value))
            log.info("google performance %s · %s: %s daily values (%s to %s)", s["brand"], s["outlet_name"], len(data), start, end)
        except PermissionError as e:
            log.error("google performance: %s", e)
            return False
        except Exception as e:
            log.exception("google performance %s failed: %s", s["location_id"], e)
            ok = False
    return ok
