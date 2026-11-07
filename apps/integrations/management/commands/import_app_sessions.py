"""Copy the competitor-search app sessions (sessions/zomato_app.json, swiggy_app.json) into the database, where the
site reads them first and the Sessions page can refresh them. Safe to run again; the files stay as a fallback."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.integrations import sessions


class Command(BaseCommand):
    help = "Move the customer-app session files into the database"

    def handle(self, *args, **opts):
        for platform in ("zomato", "swiggy"):
            path = Path(getattr(settings, f"{platform.upper()}_APP_SESSION_FILE", ""))
            if not path.exists():
                self.stdout.write(f"{platform}: no file at {path}, skipped")
                continue
            headers = json.loads(path.read_text()).get("headers") or {}
            sessions.put(platform, "customer_app", {"headers": headers}, by="import_app_sessions")
            self.stdout.write(f"{platform}: {len(headers)} headers saved to the database")
