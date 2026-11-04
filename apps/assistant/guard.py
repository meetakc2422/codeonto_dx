"""Check a model-written query before it reaches the database. The database role is the real wall (read-only, only the
`assistant` views, signed per-client scope); this is a second layer that rejects anything that is not one plain SELECT."""

import sqlglot
from sqlglot import expressions as exp

# functions that read server state, files, or change settings
BLOCKED_FUNCTIONS = {"set_config", "current_setting", "pg_sleep", "pg_read_file", "pg_ls_dir", "lo_import", "lo_export",
                     "dblink", "query_to_xml", "pg_terminate_backend", "pg_cancel_backend", "nextval", "setval",
                     "pg_advisory_lock", "pg_stat_file", "copy", "set_role"}
ALLOWED_SCHEMAS = {"", "assistant"}


class UnsafeSQL(ValueError):
    pass


def check(sql: str, views: set[str] | None = None) -> str:
    """Return the query to run (one statement) or raise UnsafeSQL with a message the model can act on."""
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise UnsafeSQL("Empty query.")
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError as e:
        raise UnsafeSQL(f"Could not parse the query: {str(e)[:200]}")
    if len(statements) != 1 or statements[0] is None:
        raise UnsafeSQL("Send exactly one SELECT statement.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Subquery, exp.With)) and not tree.find(exp.Select):
        raise UnsafeSQL("Only SELECT queries are allowed.")
    for bad in (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command, exp.Into, exp.Lock,
                exp.TruncateTable, exp.Merge, exp.Set, exp.Use, exp.Copy, exp.Grant):
        if tree.find(bad):
            raise UnsafeSQL("Only read-only SELECT queries are allowed.")
    ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        schema = (t.args.get("db").name if t.args.get("db") else "").lower()
        if t.args.get("catalog") or schema not in ALLOWED_SCHEMAS:
            raise UnsafeSQL("Only the views listed by describe_schema can be queried (schema `assistant`).")
        name = t.name.lower()
        if name not in ctes and views is not None and name not in views:
            raise UnsafeSQL(f"`{t.name}` is not one of the assistant views. Call describe_schema to see them.")
    for f in tree.find_all(exp.Func):
        name = (f.sql_name() if hasattr(f, "sql_name") else type(f).__name__).lower()
        if name in BLOCKED_FUNCTIONS or name.startswith("pg_") or name.startswith("lo_"):
            raise UnsafeSQL(f"The function {name}() is not allowed.")
    for a in tree.find_all(exp.Anonymous):
        name = str(a.this).lower()
        if name in BLOCKED_FUNCTIONS or name.startswith("pg_") or name.startswith("lo_") or name.startswith("dblink"):
            raise UnsafeSQL(f"The function {name}() is not allowed.")
    return sql
