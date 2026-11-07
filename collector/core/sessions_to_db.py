"""One-time move of this machine's Zomato / Swiggy session files into the database.

    python -m core.sessions_to_db          # show what would move, change nothing
    python -m core.sessions_to_db --apply  # copy each file into platform_sessions and point the account at it

After --apply, those accounts read their login from the database (credentials_ref = db:session), wherever a job
runs, and a refresh from the Sessions page or any machine reaches all of them. The files are left in place as a
backup; accounts whose file is missing are skipped and keep working as before."""

import sys

from . import db
from .common import ConfigError, PROJECT_DIR, log, session_path, setup_logging


def main(apply: bool) -> None:
    import json

    with db.transaction() as cur:
        cur.execute("""SELECT id, label, platform_id, credentials_ref, is_active, client_id, only_ids FROM platform_accounts
                       WHERE platform_id IN ('zomato', 'swiggy') ORDER BY platform_id, label""")
        accounts = cur.fetchall()
    for a in accounts:
        name = f"{a['platform_id']}/{a['label']}"
        ref = a["credentials_ref"] or ""
        if ref.startswith("db:session"):
            log.info("%s: already reads from the database", name)
        elif ref.startswith("file:"):
            try:
                data = db.load_credentials(a)
            except ConfigError as e:
                log.warning("%s: skipped (%s)", name, e)
                data = None
            if data is not None:
                if apply:
                    db.store_session(a, a["platform_id"], "merchant", data)
                    with db.transaction() as cur:
                        cur.execute("UPDATE platform_accounts SET credentials_ref = 'db:session', updated_at = now() WHERE id = %s", (a["id"],))
                log.info("%s: %s %s -> database", name, "moved" if apply else "would move", ref)
        else:
            log.info("%s: skipped (credentials_ref %r)", name, ref or "empty")
        app = session_path("zomato_app", a["label"])
        if a["platform_id"] == "zomato" and app.exists():
            if apply:
                db.store_session(a, "zomato", "merchant_app", json.loads(app.read_text()))
            log.info("%s: %s merchant-app session %s -> database", name, "moved" if apply else "would move", app.relative_to(PROJECT_DIR))
    if not apply:
        log.info("Nothing changed. Run with --apply to move them.")


if __name__ == "__main__":
    setup_logging()
    main("--apply" in sys.argv)
