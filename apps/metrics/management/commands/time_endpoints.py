"""Time the dashboard's data calls for one brand, read-only (it only reads, nothing is written).

    python manage.py time_endpoints                      # the sample client's brand, the last 30 days
    python manage.py time_endpoints --brand "Louis Burger" --days 90

For each call it prints the seconds, the number of database queries and the size of the answer, so you can see what is slow on the
server you run it on. It signs in as the first staff user inside the program only; no login is sent anywhere."""

import time
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.outlets.models import Brand

CALLS = [("config", ""), ("outlets", ""), ("kpis", "kpis"), ("kpi drops", "kpi-drops"), ("trend", "kpis/gross_revenue/trend"),
         ("leaderboard", "leaderboard/gross_revenue"), ("reviews summary", "reviews/summary"), ("reviews list", "reviews?limit=50"),
         ("stock-outs summary", "stock-outs/summary"), ("stock-outs list", "stock-outs?limit=100"), ("uptime summary", "uptime/summary"),
         ("payouts summary", "payouts/summary"), ("payouts list", "payouts/cycles?limit=100"), ("payouts analytics", "payouts/analytics"),
         ("payout statements", "payouts/statements"), ("items scorecard", "items"), ("listings", "listings"), ("ads performance", "ads/performance"),
         ("freshness", "freshness"), ("alerts", "alerts")]


class Command(BaseCommand):
    help = "Time the dashboard's data calls for one brand (read-only)"

    def add_arguments(self, p):
        p.add_argument("--brand", default="Sample Kitchen Co", help="the brand's name")
        p.add_argument("--days", type=int, default=30)
        p.add_argument("--slow", type=float, default=0, help="for calls slower than this many seconds, also print their 3 slowest queries (e.g. 0.3)")

    def handle(self, *a, **o):
        brand = Brand.objects.filter(name__iexact=o["brand"]).first()
        user = get_user_model().objects.filter(is_staff=True, is_active=True).first()
        if not brand or not user:
            raise CommandError("Need the brand (--brand) and at least one staff user")
        host = next((h for h in settings.ALLOWED_HOSTS if h and h != "*"), "localhost")
        client = APIClient(HTTP_HOST=host)
        client.force_login(user)
        end = date.today() - timedelta(days=1)
        qs = f"start={(end - timedelta(days=o['days'] - 1)).isoformat()}&end={end.isoformat()}"
        self.stdout.write(f"{brand.name}: {brand.outlets.filter(is_active=True).count()} outlets, {o['days']} days to {end}\n")
        self.stdout.write(f"{'call':22} {'status':>6} {'seconds':>8} {'queries':>8} {'KB':>7}")
        total = 0.0
        for name, path in CALLS:
            cache.clear()  # every call cold, so the figure is the worst case
            url = f"/api/brands/{brand.id}" + (f"/{path}" if path else "")
            url += ("&" if "?" in url else "?") + qs
            with CaptureQueriesContext(connection) as q:
                t = time.time()
                r = client.get(url)
                dt = time.time() - t
            total += dt
            self.stdout.write(f"{name:22} {r.status_code:>6} {dt:8.2f} {len(q):>8} {len(r.content) / 1024:7.0f}")
            if o["slow"] and dt >= o["slow"]:
                for x in sorted(q.captured_queries, key=lambda x: -float(x["time"]))[:3]:
                    self.stdout.write(f"      {float(x['time']):.2f}s  {' '.join(x['sql'].split())[:110]}")
        self.stdout.write(f"\nTotal {total:.1f} s for {len(CALLS)} calls, one after another")
