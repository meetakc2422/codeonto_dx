"""Opening hours: is a store open now, and how many of the minutes between two moments was it open.

Hours are rows (day, start, end, active) in local time. A slot whose end is at or before its start runs past
midnight (an end of 00:00 means midnight). A store with no saved hours counts as always open."""

from datetime import datetime, time, timedelta

from . import db

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def load(platform: str, service_type: str) -> dict[int, list[tuple]]:
    """{outlet id: [(day, active, start, end)]} for every outlet that has hours saved."""
    with db.transaction() as cur:
        cur.execute("""SELECT outlet_id, lower(day) AS day, is_active, start_time, end_time FROM outlet_hours
                       WHERE platform = %s AND service_type = %s""", (platform, service_type))
        out: dict[int, list[tuple]] = {}
        for r in cur.fetchall():
            out.setdefault(r["outlet_id"], []).append((r["day"], r["is_active"], r["start_time"], r["end_time"]))
    return out


def _intervals(slots: list[tuple], day: datetime) -> list[tuple[datetime, datetime]]:
    """Open intervals that START on this calendar day."""
    midnight = day.replace(hour=0, minute=0, second=0, microsecond=0)
    name = DAYS[day.weekday()]
    out = []
    for d, active, start, end in slots:
        if d != name or not active or start is None or end is None:
            continue
        s = midnight + timedelta(hours=start.hour, minutes=start.minute, seconds=start.second)
        e = midnight + timedelta(hours=end.hour, minutes=end.minute, seconds=end.second)
        if e <= s:
            e += timedelta(days=1)  # past midnight
        out.append((s, e))
    return out


def is_open(slots: list[tuple] | None, now: datetime) -> bool:
    if not slots:
        return True
    return any(s <= now < e for back in (1, 0) for s, e in _intervals(slots, now - timedelta(days=back)))


def open_minutes(slots: list[tuple] | None, start: datetime, end: datetime) -> float:
    """Minutes between start and end (local, same timezone) during which the store was open."""
    total = (end - start).total_seconds() / 60
    if not slots or end <= start:
        return max(total, 0)
    seconds = 0.0
    day = start - timedelta(days=1)
    while day.date() <= end.date():
        for s, e in _intervals(slots, day):
            lo, hi = max(s, start), min(e, end)
            if hi > lo:
                seconds += (hi - lo).total_seconds()
        day += timedelta(days=1)
    return seconds / 60
