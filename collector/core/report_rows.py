"""Keep every row of a platform's business report (see apps.metrics.models.ReportRow), mapped to a KPI or not."""


def save(cur, outlet_id: int, platform: str, rows: list[tuple]) -> int:
    """rows: (section, metric, day, text, value). One upsert per row; returns how many were written."""
    clean = [(outlet_id, platform, day, str(sec)[:120], str(met)[:200], (str(text) if text is not None else "")[:120], value)
             for sec, met, day, text, value in rows if sec is not None and met is not None]
    if clean:
        cur.executemany(
            """INSERT INTO report_rows (outlet_id, platform, metric_date, section, metric, text, value, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, now())
               ON CONFLICT (outlet_id, platform, section, metric, metric_date)
               DO UPDATE SET text = EXCLUDED.text, value = EXCLUDED.value, updated_at = now()""", clean)
    return len(clean)
