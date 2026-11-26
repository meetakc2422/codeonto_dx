"""Show what Swiggy answers for a typed name from an outlet's delivery spot: the dropdown and the search page, to see where a nearer branch is.

    python manage.py inspect_swiggy_search "frozen" "milano ice cream"

Prints the dropdown's restaurants (id, name, area, rating), every kind of card the search page holds, and for each restaurant card its id, name,
area, distance and rating. Read-only: nothing is saved, and no session or token is printed."""
import collections

from django.db.models import Q

from django.core.management.base import BaseCommand, CommandError

from apps.competition import swiggy
from apps.competition.models import MarketSpot


class Command(BaseCommand):
    help = "Print what Swiggy's dropdown and search return for a name at an outlet's spot (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("outlet", help="the outlet's number, or part of its name (for example: frozen)")
        parser.add_argument("query")

    def handle(self, *args, outlet, query, **opts):
        spots = MarketSpot.objects.filter(platform="swiggy").select_related("outlet__brand")
        spots = spots.filter(outlet_id=int(outlet)) if outlet.isdigit() else spots.filter(
            Q(outlet__outlet_name__icontains=outlet) | Q(outlet__brand__name__icontains=outlet) | Q(outlet__area__icontains=outlet))
        found = list(spots[:10])
        if len(found) != 1:
            names = "\n".join(f"  {x.outlet_id}: {x.outlet.brand.name} - {x.outlet.outlet_name}" for x in found)
            raise CommandError(("No outlet with a Swiggy location matches that." if not found else "More than one matches, pass its number:\n" + names))
        a = found[0]
        spot = {**a.details, "lat": a.lat, "lng": a.lng, "city_id": a.city_id}
        self.stdout.write(f"spot: {a.title} ({a.lat:.4f}, {a.lng:.4f})\n\n== dropdown for {query!r}")
        for h in swiggy.suggest(spot, query):
            self.stdout.write(f"  {h['type'] or '?':12} id={h['res_id']} brand={h['brand_id']} {h['name']!r} area={h['area']!r} rating={h['rating']} {h['delivery_time']}")
        first = next((h for h in swiggy.suggest(spot, query) if h["res_id"] and h["metadata"]), None)
        if first:
            self.stdout.write(f"\n== opening {first['name']!r} from the dropdown, as tapping it does")
            try:
                for r in swiggy.search_restaurants(spot, first["name"], suggestion=first["metadata"])[:8]:
                    self.stdout.write(f"  id={r['res_id']} {r['name']!r} area={r['area']!r} {r['distance_km']} km rating={r['rating']} ratings={r['ratings']!r} {r['delivery_time']}")
            except swiggy.SwiggyAppError as e:
                self.stdout.write(f"  (failed: {e})")
        self.stdout.write(f"\n== search page for {query!r}")
        rows = swiggy.search_restaurants(spot, query)
        for r in rows:
            self.stdout.write(f"  id={r['res_id']} {r['name']!r} area={r['area']!r} {r['distance_km']} km rating={r['rating']} ratings={r['ratings']!r} serviceable={r['serviceable']}")
        if not rows:
            self.stdout.write("  (no restaurant cards read)")
        body = {"categoryPage": "FOOD", "query": query}
        kinds = collections.Counter()
        try:
            raw = swiggy.call("POST", "https://disc.swiggy.com/api/v3/search/", spot["lat"], spot["lng"], spot.get("city_id", ""), spot.get("city", ""),
                              params={"lat": spot["lat"], "lng": spot["lng"]},
                              body={**body, "marketplaces": [{"businessLineId": "FOOD", "marketplaceId": "SWIGGY"}], "queryUniqueId": "x", "redirection": 1,
                                    "submitAction": "ENTER", "supportedTabs": ["RESTAURANT", "DISH"], "deselectedFacets": {}, "secondaryFacets": {}})
            for c in swiggy._cards(raw):
                kinds[c["type_url"].rsplit(".", 1)[-1]] += 1
        except swiggy.SwiggyAppError as e:
            self.stdout.write(f"\n(second read failed: {e})")
        self.stdout.write("\n== kinds of card on the search page: " + ", ".join(f"{k} x{n}" for k, n in kinds.most_common()))
