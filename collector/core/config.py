"""Every tunable of the collectors lives in collector/.env (see .env.example) or in collector/mappings/*.json.
Scripts read them through these helpers, so nothing is baked into code: change the file, not the script."""

import json
import os

from .common import ConfigError, PROJECT_DIR  # importing common loads collector/.env


def text(name: str, default: str = "") -> str:
    return os.getenv(name, "").strip() or default


def integer(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        raise ConfigError(f"{name} must be a whole number, got '{raw}'")


def numbers(name: str, default: str) -> tuple[float, ...]:
    """'0.8,1.8' -> (0.8, 1.8)"""
    raw = text(name, default)
    try:
        return tuple(float(x) for x in raw.split(",") if x.strip())
    except ValueError:
        raise ConfigError(f"{name} must be comma separated numbers, got '{raw}'")


def mapping(name: str):
    """Load collector/mappings/<name>.json (label -> KPI maps, status maps, scoring checks ...)."""
    path = PROJECT_DIR / "mappings" / f"{name}.json"
    if not path.exists():
        raise ConfigError(f"Mapping file missing: {path}")
    return json.loads(path.read_text())


# ---- shared across platforms ----
def http_timeout() -> int:
    return integer("HTTP_TIMEOUT_SEC", 30)


def retry_waits() -> tuple[float, ...]:
    """Seconds to wait before each attempt; a 429 or 5xx moves on to the next wait."""
    return numbers("RETRY_WAITS", "0.5,15,45,90")


def user_agent() -> str:
    return text("HTTP_USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15")


def timezone_offset_minutes() -> int:
    return integer("TIMEZONE_OFFSET_MINUTES", 330)


def sentiment(rating) -> str:
    """Star rating -> positive / neutral / negative using SENTIMENT_POSITIVE_MIN (4) and SENTIMENT_NEUTRAL_MIN (3)."""
    if rating is None:
        return ""
    pos, neu = integer("SENTIMENT_POSITIVE_MIN", 4), integer("SENTIMENT_NEUTRAL_MIN", 3)
    return "positive" if rating >= pos else "neutral" if rating >= neu else "negative"


def mealtime(hour: int) -> str:
    """Hour of day -> meal name from mappings/meal_windows.json (the last window wraps past midnight)."""
    windows = mapping("meal_windows")["windows"]
    name = windows[-1]["name"]
    for w in windows:
        if hour >= w["from"]:
            name = w["name"]
    return name


def business_date(local):
    """The service day a moment belongs to: the day starts when the first meal window starts (Breakfast, 5 am), so
    12-5 am counts as the end of the previous day's late-night service, not the start of the new day."""
    from datetime import timedelta

    return (local - timedelta(hours=mapping("meal_windows")["windows"][0]["from"])).date()


# ---- backfill: limit a run to some outlets and a date range (set by run_backfill.py, or by hand) ----
def only_res_ids() -> set[str]:
    """ONLY_RES_IDS=123,456 -> {'123', '456'}; empty means every mapped outlet."""
    return {x.strip() for x in os.getenv("ONLY_RES_IDS", "").split(",") if x.strip()}


def keep_stores(stores: list) -> list:
    """Drop stores whose res_id isn't in ONLY_RES_IDS (no-op when it's unset)."""
    only = only_res_ids()
    return [s for s in stores if str(s["res_id"]) in only] if only else stores


def date_range(default_start, default_end):
    """(start, end) dates: BACKFILL_FROM / BACKFILL_TO (YYYY-MM-DD) when set, else the job's own window."""
    from datetime import date

    def parse(name, fallback):
        raw = text(name)
        try:
            return date.fromisoformat(raw) if raw else fallback
        except ValueError:
            raise ConfigError(f"{name} must be YYYY-MM-DD, got '{raw}'")

    return parse("BACKFILL_FROM", default_start), parse("BACKFILL_TO", default_end)


def date_range_ms(default_start_ms: int, default_end_ms: int) -> tuple[int, int]:
    """Same as date_range for jobs that ask in epoch milliseconds (IST days, end day inclusive)."""
    from datetime import datetime, time as clock, timedelta, timezone

    if not (text("BACKFILL_FROM") or text("BACKFILL_TO")):
        return default_start_ms, default_end_ms
    ist = timezone(timedelta(minutes=timezone_offset_minutes()))
    to_day = lambda ms: datetime.fromtimestamp(ms / 1000, ist).date()  # noqa: E731
    start, end = date_range(to_day(default_start_ms), to_day(default_end_ms))
    at = lambda d: int(datetime.combine(d, clock(), ist).timestamp() * 1000)  # noqa: E731
    return at(start), min(at(end + timedelta(days=1)) - 1, default_end_ms)
