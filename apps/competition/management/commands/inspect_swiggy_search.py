"""Show what Swiggy answers for a typed name from an outlet's delivery spot: the dropdown and the search page, to see where a nearer branch is.

    python manage.py inspect_swiggy_search <outlet_id> "milano ice cream"

Prints the dropdown's restaurants (id, name, area, rating), every kind of card the search page holds, and for each restaurant card its id, name,
area, distance and rating. Read-only: nothing is saved, and no session or token is printed."""
import collections

from django.core.management.base import BaseCommand, CommandError

from apps.competition import swiggy
from apps.competition.models import MarketSpot


class Command(BaseCommand):
    help = "Print what Swiggy's dropdown and search return for a name at an outlet's spot (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("outlet_id", type=int)
        parser.add_argument("query")

    def handle(self, *args, outlet_id, query, **opts):
        a = MarketSpot.objects.filter(outlet_id=outlet_id, platform="swiggy").first()
        if not a:
            raise CommandError("That outlet has no Swiggy location yet.")
        spot = {**a.details, "lat": a.lat, "lng": a.lng, "city_id": a.city_id}
        self.stdout.write(f"spot: {a.title} ({a.lat:.4f}, {a.lng:.4f})\n\n== dropdown for {query!r}")
        for h in swiggy.suggest(spot, query):
            self.stdout.write(f"  {h['type'] or '?':12} id={h['res_id']} brand={h['brand_id']} {h['name']!r} area={h['area']!r} rating={h['rating']} {h['delivery_time']}")
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
