"""Zomato's own offline hours against what our monitor measured, outlet by outlet and day by day. Read-only.

    python manage.py compare_offline_hours [--brand louis] [--days 14] [--detail 25]

Run `python run.py zomato offline_hours` on the collector first (with BACKFILL_FROM / BACKFILL_TO for older days).
Ours: the hours of the offline episodes that started that day (opening hours only). A day only counts as "covered" when
our monitor made at least MIN_CHECKS checks that day; on other days we have no basis to compare."""
from collections import defaultdict
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.uptime.models import OfflineEpisode, UptimeDaily, ZomatoOfflineHours

MIN_CHECKS = 20  # about 100 minutes of 5-minute checks


class Command(BaseCommand):
    help = "Compare Zomato's offline hours with our own uptime data"

    def add_arguments(self, parser):
        parser.add_argument("--brand", default="", help="part of a brand name")
        parser.add_argument("--days", type=int, default=14)
        parser.add_argument("--detail", type=int, default=20, help="how many of the biggest differences to list")

    def handle(self, *args, **o):
        since = date.today() - timedelta(days=o["days"])
        z = ZomatoOfflineHours.objects.filter(day__gte=since)
        if o["brand"]:
            z = z.filter(outlet__brand__name__icontains=o["brand"])
        z = {(r["outlet_id"], r["day"]): float(r["hours"]) for r in z.values("outlet_id", "day", "hours")}
        if not z:
            self.stdout.write("No Zomato offline hours stored yet. Run `python run.py zomato offline_hours` on the collector first.")
            return
        ids = {k[0] for k in z}
        ours = defaultdict(float)
        for r in OfflineEpisode.objects.filter(outlet_id__in=ids, platform_id="zomato", log_date__gte=since).values("outlet_id", "log_date").annotate(m=Sum("downtime_minutes")):
            ours[(r["outlet_id"], r["log_date"])] = r["m"] / 60
        checks = {(r["outlet_id"], r["day"]): r["checks"] for r in UptimeDaily.objects.filter(outlet_id__in=ids, platform_id="zomato", day__gte=since).values("outlet_id", "day", "checks")}
        names = dict(__import__("apps.outlets.models", fromlist=["BrandOutlet"]).BrandOutlet.objects.filter(id__in=ids).values_list("id", "outlet_name"))

        covered = [(k, zh, ours.get(k, 0.0)) for k, zh in z.items() if checks.get(k, 0) >= MIN_CHECKS]
        uncovered = [k for k in z if checks.get(k, 0) < MIN_CHECKS]
        gap_days = [k for k in uncovered if z[k] >= 0.5]
        self.stdout.write(f"Zomato offline hours stored: {len(z)} outlet-days (last {o['days']} days)")
        self.stdout.write(f"  our monitor covered : {len(covered)} outlet-days (at least {MIN_CHECKS} checks)")
        self.stdout.write(f"  not covered          : {len(uncovered)} outlet-days; Zomato reports 0.5 h or more offline on {len(gap_days)} of them ({sum(z[k] for k in gap_days):.0f} h we never saw)")
        if covered:
            tz, to = sum(c[1] for c in covered), sum(c[2] for c in covered)
            agree = sum(1 for _, a, b in covered if abs(a - b) <= 0.5)
            both0 = sum(1 for _, a, b in covered if a < 0.5 and b < 0.5)
            self.stdout.write(f"On covered days: Zomato {tz:.1f} h, ours {to:.1f} h ({(to / tz * 100 if tz else 0):.0f}% of Zomato's)")
            self.stdout.write(f"  within 0.5 h of each other: {agree} of {len(covered)} ({both0} of them both about zero)")
            self.stdout.write(f"  Zomato higher by over 1 h : {sum(1 for _, a, b in covered if a - b > 1)}   ours higher by over 1 h: {sum(1 for _, a, b in covered if b - a > 1)}")
            self.stdout.write(f"\nBiggest differences (outlet, day, Zomato h, our h, our checks):")
            for k, a, b in sorted(covered, key=lambda c: -abs(c[1] - c[2]))[: o["detail"]]:
                self.stdout.write(f"  {names.get(k[0], k[0])[:34]:34} {k[1]}  zomato {a:5.1f}  ours {b:5.1f}  checks {checks.get(k, 0)}")
