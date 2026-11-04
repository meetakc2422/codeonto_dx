"""Turn raw rows (reviews; later orders, store status) into daily KPI values in metric_daily."""

from datetime import date

from django.db import connection

# kpi code -> SQL expression over one outlet/platform/day group of reviews
_REVIEW_KPIS = {
    "avg_rating": "AVG(r.rating)",
    "review_count": "COUNT(*)",
    "positive_review_pct": "100.0 * COUNT(*) FILTER (WHERE r.rating >= 4) / COUNT(*)",
    "negative_review_count": "COUNT(*) FILTER (WHERE r.rating <= 2)",
    "response_rate": "100.0 * COUNT(*) FILTER (WHERE r.reply_status = 'replied') / COUNT(*)",
}


def rollup_review_metrics(brand_id: int, start: date, end: date) -> int:
    written = 0
    with connection.cursor() as cur:
        for code, expr in _REVIEW_KPIS.items():
            cur.execute(
                f"""
                INSERT INTO metric_daily (outlet_id, platform, kpi_id, metric_date, value, weight, updated_at)
                SELECT r.outlet_id, r.platform, k.id, (r.reviewed_at AT TIME ZONE 'Asia/Kolkata')::date AS d,
                       {expr}, COUNT(*), now()
                FROM reviews r
                JOIN brand_outlets bo ON bo.id = r.outlet_id
                CROSS JOIN (SELECT id FROM kpis WHERE code = %(code)s) k
                WHERE bo.brand_id = %(brand_id)s
                  AND (r.reviewed_at AT TIME ZONE 'Asia/Kolkata')::date BETWEEN %(start)s AND %(end)s
                GROUP BY r.outlet_id, r.platform, k.id, d
                ON CONFLICT (outlet_id, platform, kpi_id, metric_date)
                DO UPDATE SET value = EXCLUDED.value, weight = EXCLUDED.weight, updated_at = now()
                """,
                {"code": code, "brand_id": brand_id, "start": start, "end": end},
            )
            written += cur.rowcount
    return written
