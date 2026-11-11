"""Read-only check: for stores on both Zomato and Swiggy, are the same dishes out of stock on both?

Only stores whose menus BOTH jobs checked in the last --fresh minutes are compared, so a job that stopped doesn't look
like a mismatch. Dish names are matched loosely (case, spaces and punctuation ignored), since the two menus are typed
separately.

    python manage.py compare_stockouts                 # every brand
    python manage.py compare_stockouts --brand shoyu   # one brand
    python manage.py compare_stockouts --fresh 30 --show 10
"""

import re
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.stockouts.models import StockOut


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


class Command(BaseCommand):
    help = "Compare Zomato and Swiggy stock-outs for stores on both apps (read-only)"

    def add_arguments(self, parser):
        parser.add_argument("--brand", help="brand name contains this")
        parser.add_argument("--fresh", type=int, default=30, help="only stores both jobs checked in the last N minutes (default 30)")
        parser.add_argument("--show", type=int, default=8, help="stores to list in detail (default 8)")

    def handle(self, *args, **o):
        since = timezone.now() - timedelta(minutes=o["fresh"])
        qs = StockOut.objects.filter(outlet__zomato__isnull=False, outlet__swiggy__isnull=False)
        if o["brand"]:
            qs = qs.filter(outlet__brand__name__icontains=o["brand"])
        # when each platform last looked at each store (any row of that store, active or not)
        seen = defaultdict(dict)
        for oid, plat, last in qs.values_list("outlet_id", "platform_id", "last_detected_at"):
            if last and (plat not in seen[oid] or last > seen[oid][plat]):
                seen[oid][plat] = last
        stores = {oid for oid, d in seen.items() if d.get("zomato") and d.get("swiggy")
                  and d["zomato"] >= since and d["swiggy"] >= since}
        out = defaultdict(lambda: {"zomato": {}, "swiggy": {}})
        names = {}
        for oid, plat, item, brand, outlet in qs.filter(is_active=True, outlet_id__in=stores).values_list(
                "outlet_id", "platform_id", "item_name", "outlet__brand__name", "outlet__outlet_name"):
            out[oid][plat][_norm(item)] = item
            names[oid] = f"{brand} · {outlet}"

        self.stdout.write(f"Stores on both apps with stock-out data: {len(seen)} · checked by both in the last {o['fresh']} min: {len(stores)}")
        if not stores:
            self.stdout.write("Nothing to compare: make sure both stock-out jobs are running.")
            return
        tz = ts = tb = 0
        rows = []
        for oid in stores:
            d = out[oid]
            z, s = set(d["zomato"]), set(d["swiggy"])
            tz, ts, tb = tz + len(z), ts + len(s), tb + len(z & s)
            rows.append((names.get(oid, str(oid)), z, s, d))
        self.stdout.write(f"Dishes out now: Zomato {tz} · Swiggy {ts} · out on both {tb} · "
                          f"only Zomato {tz - tb} · only Swiggy {ts - tb}")
        same = sum(1 for _, z, s, _ in rows if z == s)
        self.stdout.write(f"Stores where both apps agree exactly: {same} of {len(rows)}\n")
        for name, z, s, d in sorted(rows, key=lambda r: -len(r[1] ^ r[2]))[:o["show"]]:
            if z == s:
                continue
            self.stdout.write(f"{name}: Zomato {len(z)} · Swiggy {len(s)} · both {len(z & s)}")
            if z - s:
                self.stdout.write("   only on Zomato: " + " | ".join(sorted(d["zomato"][k] for k in z - s)[:6]))
            if s - z:
                self.stdout.write("   only on Swiggy: " + " | ".join(sorted(d["swiggy"][k] for k in s - z)[:6]))
