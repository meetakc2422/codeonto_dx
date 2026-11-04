import secrets
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

ROLE = "assistant_ro"


class Command(BaseCommand):
    help = ("Create the read-only database role the AI assistant connects as, give it SELECT on the `assistant` views only, "
            "and store the scope-signing secret. Safe to run again. Writes ASSISTANT_DATABASE_URL and ASSISTANT_SCOPE_SECRET to .env.")

    def handle(self, *args, **opts):
        env_path = Path(settings.BASE_DIR) / ".env"
        lines = env_path.read_text().splitlines()
        have = {l.split("=", 1)[0]: l.split("=", 1)[1] for l in lines if "=" in l and not l.startswith("#")}
        scope_secret = have.get("ASSISTANT_SCOPE_SECRET") or secrets.token_urlsafe(32)
        url = have.get("ASSISTANT_DATABASE_URL", "")
        password = urlparse(url).password if url else None
        password = password or secrets.token_urlsafe(24)

        db = settings.DATABASES["default"]
        dbname, host, port = db["NAME"], db.get("HOST") or "localhost", db.get("PORT") or 5432
        with connection.cursor() as cur:
            cur.execute(f"""DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{ROLE}') THEN
                              CREATE ROLE {ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END $$""")
            cur.execute(f"ALTER ROLE {ROLE} WITH PASSWORD %s", [password])
            cur.execute(f'GRANT CONNECT ON DATABASE "{dbname}" TO {ROLE}')
            cur.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROLE}")
            cur.execute(f"GRANT USAGE ON SCHEMA assistant TO {ROLE}")
            cur.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA assistant TO {ROLE}")
            cur.execute(f"REVOKE ALL ON assistant.scope_secret FROM {ROLE}")  # the role must never read the signing secret
            for fn in ("scope_who()", "scope_ok(bigint)", "outlet_ok(bigint, bigint)", "brand_ok(bigint, bigint)"):
                cur.execute(f"GRANT EXECUTE ON FUNCTION assistant.{fn} TO {ROLE}")
            cur.execute(f"ALTER ROLE {ROLE} SET search_path = assistant")
            cur.execute(f"ALTER ROLE {ROLE} SET default_transaction_read_only = on")
            cur.execute(f"ALTER ROLE {ROLE} SET statement_timeout = '{settings.ASSISTANT_STATEMENT_TIMEOUT_MS}ms'")
            cur.execute(f"ALTER ROLE {ROLE} CONNECTION LIMIT 20")
            cur.execute("DELETE FROM assistant.scope_secret")
            cur.execute("INSERT INTO assistant.scope_secret (secret) VALUES (%s)", [scope_secret])

        new = {"ASSISTANT_DATABASE_URL": f"postgresql://{ROLE}:{password}@{host}:{port}/{dbname}",
               "ASSISTANT_SCOPE_SECRET": scope_secret}
        lines = [l for l in lines if l.split("=", 1)[0] not in new] + [f"{k}={v}" for k, v in new.items()]
        env_path.write_text("\n".join(lines) + "\n")
        env_path.chmod(0o600)
        self.stdout.write(self.style.SUCCESS(f"Role {ROLE} ready; ASSISTANT_DATABASE_URL and ASSISTANT_SCOPE_SECRET saved to .env"))
