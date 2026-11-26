"""Compare one kitchen's Zomato and Swiggy menus as customers see them: which dishes are out of stock on one app and not the
other, and which dishes are only on one menu. Read-only: nothing is saved.

    python manage.py compare_menus <outlet_id>

<outlet_id> is a linked outlet (it has both a Zomato and a Swiggy ID) that has a delivery spot on each platform's
Competition page. Uses the sessions already stored for the competition feature."""
import re

from django.core.management.base import BaseCommand, CommandError

from apps.competition import swiggy, zomato
from apps.competition.models import MarketSpot
from apps.outlets.models import BrandOutlet


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def compare(z_items: list[dict], s_items: list[dict]) -> dict:
    """Group both menus' dishes by normalised name: out on one app only, out on both, listed on one app only."""
    z = {norm(i["name"]): i for i in z_items if norm(i["name"])}
    s = {norm(i["name"]): i for i in s_items if norm(i["name"])}
    both = z.keys() & s.keys()
    return {
        "common": len(both),
        "out_zomato_only": sorted(z[k]["name"] for k in both if not z[k]["in_stock"] and s[k]["in_stock"]),
        "out_swiggy_only": sorted(s[k]["name"] for k in both if z[k]["in_stock"] and not s[k]["in_stock"]),
        "out_both": sorted(z[k]["name"] for k in both if not z[k]["in_stock"] and not s[k]["in_stock"]),
        "only_zomato": sorted(z[k]["name"] for k in z.keys() - s.keys()),
        "only_swiggy": sorted(s[k]["name"] for k in s.keys() - z.keys()),
    }


class Command(BaseCommand):
    help = "Compare a linked outlet's Zomato and Swiggy menus (stock status and which dishes exist on each). Read-only."

    def add_arguments(self, parser):
        parser.add_argument("outlet_id", type=int)

    def handle(self, *args, **o):
        bo = BrandOutlet.objects.filter(pk=o["outlet_id"]).first()
        if not bo or not bo.zomato_id or not bo.swiggy_id:
            raise CommandError("That outlet needs both a Zomato and a Swiggy ID (link them on Brands & Outlets first).")
        menus = {}
        for platform, mod, res_id in (("zomato", zomato, bo.zomato_id), ("swiggy", swiggy, bo.swiggy_id)):
            spot = MarketSpot.objects.filter(outlet=bo, platform=platform).first()
            if not spot:
                raise CommandError(f"No {platform} delivery spot for this outlet: open it on the Competition page first.")
            place = {**(spot.details or {}), "lat": spot.lat, "lng": spot.lng, "city_id": spot.city_id}
            menus[platform] = mod.menu(place, str(res_id))["items"]
            self.stdout.write(f"{platform}: {len(menus[platform])} dishes, {sum(not i['in_stock'] for i in menus[platform])} out of stock")
        r = compare(menus["zomato"], menus["swiggy"])
        self.stdout.write(f"\nOn both menus: {r['common']} dishes")
        for key, label in (("out_zomato_only", "Out on Zomato, in stock on Swiggy"), ("out_swiggy_only", "Out on Swiggy, in stock on Zomato"),
                           ("out_both", "Out on both"), ("only_zomato", "Only on the Zomato menu"), ("only_swiggy", "Only on the Swiggy menu")):
            self.stdout.write(f"\n{label} ({len(r[key])}):")
            for n in r[key][:40]:
                self.stdout.write(f"  - {n}")
