"""Run a checked query as the read-only assistant role, scoped to one client (or all, for Codeonto staff)."""

import hashlib
import time

import psycopg
from django.conf import settings
from psycopg.rows import dict_row

from .guard import check


def scope_value(client_id, outlet_ids=None) -> str:
    """'<client id or *>[/<outlet ids>]:<signature>'. Only the server can sign; the database role cannot read the secret."""
    who = "*" if client_id is None else str(int(client_id))
    if client_id is not None and outlet_ids is not None:
        who += "/" + ",".join(str(int(i)) for i in sorted(outlet_ids))
    return f"{who}:{hashlib.md5(f'{settings.ASSISTANT_SCOPE_SECRET}:{who}'.encode()).hexdigest()}"


def _jsonable(v):
    from datetime import date, datetime, time as dtime
    from decimal import Decimal

    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date, dtime)):
        return v.isoformat()
    return v


_VIEWS: set[str] | None = None


def view_names() -> set[str]:
    global _VIEWS
    if _VIEWS is None:
        _VIEWS = {n.lower() for n in describe()}
    return _VIEWS


def run(sql: str, client_id, outlet_ids=None) -> dict:
    """{'columns': [...], 'rows': [...], 'truncated': bool, 'ms': int}. Raises UnsafeSQL or psycopg errors."""
    sql = check(sql, view_names())
    max_rows = settings.ASSISTANT_MAX_ROWS
    started = time.time()
    with psycopg.connect(settings.ASSISTANT_DATABASE_URL, row_factory=dict_row, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute("SELECT set_config('app.scope', %s, true)", [scope_value(client_id, outlet_ids)])
            cur.execute(sql)
            fetched = cur.fetchmany(max_rows + 1)
            columns = [c.name for c in cur.description or []]
        conn.rollback()
    rows = [{k: _jsonable(v) for k, v in r.items()} for r in fetched[:max_rows]]
    return {"columns": columns, "rows": rows, "truncated": len(fetched) > max_rows, "ms": int((time.time() - started) * 1000)}


def describe() -> dict:
    """Views and columns the assistant may use (names only, no data)."""
    with psycopg.connect(settings.ASSISTANT_DATABASE_URL, row_factory=dict_row) as conn:
        rows = conn.execute("""SELECT table_name, column_name, data_type FROM information_schema.columns
                               WHERE table_schema = 'assistant' ORDER BY table_name, ordinal_position""").fetchall()
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["table_name"], []).append(f"{r['column_name']} ({r['data_type']})")
    return out


_SCHEMA = {"at": 0.0, "text": ""}


def schema_text(max_age: float = 3600.0) -> str:
    """The views and columns as compact text for the prompt, read at most once an hour. Empty when the database can't be read:
    the model then falls back to the describe_schema tool."""
    if _SCHEMA["text"] and time.time() - _SCHEMA["at"] < max_age:
        return _SCHEMA["text"]
    try:
        from .prompt import compact_schema

        _SCHEMA.update(at=time.time(), text=compact_schema(describe()))
    except Exception:  # noqa: BLE001
        return _SCHEMA["text"]
    return _SCHEMA["text"]
