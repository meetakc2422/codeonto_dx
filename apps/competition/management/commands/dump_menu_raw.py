"""Save one competitor's raw menu response and an outline of every field in it, to see what the apps return beyond what we read.

    python manage.py dump_menu_raw zomato <outlet_id> <res_id>
    python manage.py dump_menu_raw swiggy <outlet_id> <res_id>

<outlet_id> is the outlet whose delivery spot the menu is loaded from (it must already have one on the Competition page).
Writes <platform>_<res_id>_raw.json and <platform>_<res_id>_outline.txt to the current folder. Read-only: nothing is saved to the database."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.competition import swiggy, zomato
from apps.competition.models import MarketSpot

MAX_DEPTH = 9


def outline(node, path="", out=None):
    """Every distinct field path (lists collapsed to [], one example value each)."""
    out = {} if out is None else out
    if len(path.split(".")) > MAX_DEPTH:
        return out
    if isinstance(node, dict):
        for k, v in node.items():
            outline(v, f"{path}.{k}" if path else k, out)
    elif isinstance(node, list):
        for v in node[:60]:
            outline(v, f"{path}[]", out)
    else:
        out.setdefault(path, node)
    return out


class Command(BaseCommand):
    help = "Save one competitor's raw menu response and a field outline (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("platform", choices=["zomato", "swiggy"])
        parser.add_argument("outlet_id", type=int)
        parser.add_argument("res_id")

    def handle(self, *args, **o):
        spot = MarketSpot.objects.filter(outlet_id=o["outlet_id"], platform=o["platform"]).first()
        if not spot:
            raise CommandError("That outlet has no delivery spot for this platform yet: open it on the Competition page first.")
        place = {**(spot.details or {}), "lat": spot.lat, "lng": spot.lng, "city_id": spot.city_id}
        mod = zomato if o["platform"] == "zomato" else swiggy
        raw = mod.menu_raw(place, o["res_id"])
        base = f"{o['platform']}_{o['res_id']}"
        Path(f"{base}_raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1))
        lines = [f"{p}  =  {json.dumps(v, ensure_ascii=False)[:70]}" for p, v in sorted(outline(raw).items())]
        Path(f"{base}_outline.txt").write_text("\n".join(lines))
        self.stdout.write(f"Saved {base}_raw.json and {base}_outline.txt ({len(lines)} fields) in the current folder.")
