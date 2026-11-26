"""Show what one Zomato search card holds, to find where it keeps the restaurant's area or address.

    python manage.py inspect_zomato_search <outlet number or part of its name> "milano"

Prints, for the first three restaurants of the search, every plain-text field of the card and of its tracking data (name, texts, ids, locality
if there is one). Read-only: nothing is saved, and no session or token is printed."""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.competition import zomato
from apps.competition.models import MarketSpot


def plain(node, path="", out=None, depth=0):
    """Every short text or number in a card, with where it sits."""
    out = {} if out is None else out
    if depth > 6:
        return out
    if isinstance(node, dict):
        for k, v in node.items():
            plain(v, f"{path}.{k}" if path else k, out, depth + 1)
    elif isinstance(node, list):
        for v in node[:6]:
            plain(v, f"{path}[]", out, depth + 1)
    elif isinstance(node, (str, int, float)) and node != "" and len(str(node)) < 160 and not str(node).startswith(("http", "zomato://")):
        out.setdefault(path, node)
    return out


class Command(BaseCommand):
    help = "Print the plain fields of Zomato search cards (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("outlet", help="the outlet's number, or part of its name")
        parser.add_argument("query")

    def handle(self, *args, outlet, query, **opts):
        spots = MarketSpot.objects.filter(platform="zomato").select_related("outlet__brand")
        spots = spots.filter(outlet_id=int(outlet)) if outlet.isdigit() else spots.filter(
            Q(outlet__outlet_name__icontains=outlet) | Q(outlet__brand__name__icontains=outlet) | Q(outlet__area__icontains=outlet))
        found = list(spots[:10])
        if len(found) != 1:
            raise CommandError("Pass the outlet's number: " + "; ".join(f"{x.outlet_id} {x.outlet.outlet_name}" for x in found) if found else "No outlet with a Zomato location matches.")
        a = found[0]
        spot = {**a.details, "lat": a.lat, "lng": a.lng, "city_id": a.city_id}
        hint = next((h for h in zomato.suggest(spot, query) if h["search"] and not h["res_id"]), None)
        raw = []
        zomato.search_restaurants(spot, query, search=hint["search"] if hint else None, raw_out=raw)
        shown = 0
        for item in (raw[0].get("results") or []) if raw else []:
            for kind, snip in item.items():
                if kind.startswith("v2_res_snippet") and isinstance(snip, dict) and shown < 3:
                    shown += 1
                    tracking = [t for t in zomato._tracking(snip)]
                    fields = plain({k: v for k, v in snip.items() if k != "tracking_data"})
                    self.stdout.write(f"\n== card {shown}: {zomato._text(snip.get('title'))!r} ({kind})")
                    for k, v in fields.items():
                        self.stdout.write(f"  {k} = {v!r}")
                    for t in tracking:
                        self.stdout.write("  tracking: " + json.dumps(plain(t), ensure_ascii=False)[:1500])
