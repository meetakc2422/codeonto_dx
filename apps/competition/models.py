from django.db import models

from apps.outlets.models import TimeStamped


class Place(models.Model):
    """A Google Maps listing we look at: an outlet's own, or a competitor's. The rating fields are a cache of the
    Places API, refreshed daily; Google's terms let us keep them for at most 30 days, so history lives only in
    PlaceSnapshot and is pruned. place_id may be kept indefinitely."""

    place_id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    primary_type = models.CharField(max_length=80, blank=True)
    rating = models.FloatField(null=True, blank=True)
    rating_count = models.IntegerField(null=True, blank=True)
    price_level = models.CharField(max_length=40, blank=True)
    price_range = models.CharField(max_length=60, blank=True, help_text="e.g. ₹400–600, as Google shows it")
    business_status = models.CharField(max_length=40, blank=True)
    hours = models.JSONField(null=True, blank=True, help_text="Google's regularOpeningHours: periods + weekday descriptions")
    services = models.JSONField(default=dict, blank=True, help_text="delivery / dineIn / takeout / reservable / servesVegetarianFood")
    refreshed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class PlaceSnapshot(models.Model):
    """One day's rating for a place, so the page can show movement over the last weeks. Pruned after 30 days."""

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="snapshots")
    day = models.DateField()
    rating = models.FloatField(null=True, blank=True)
    rating_count = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = [("place", "day")]
        ordering = ["day"]


class OutletPlace(TimeStamped):
    """Which Google Maps listing is this outlet's own: the anchor for 'nearby' and the row compared against."""

    outlet = models.OneToOneField("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="google_place")
    place = models.ForeignKey(Place, on_delete=models.PROTECT, related_name="+")


class Competitor(TimeStamped):
    """A place near an outlet. Suggestions start untracked; the client ticks the few they want compared."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="competitors")
    place = models.ForeignKey(Place, on_delete=models.PROTECT, related_name="+")
    distance_m = models.IntegerField(null=True, blank=True)
    is_tracked = models.BooleanField(default=False)

    class Meta:
        unique_together = [("outlet", "place")]


PLATFORMS = [("zomato", "Zomato"), ("swiggy", "Swiggy")]


class MarketSpot(TimeStamped):
    """Where the outlet stands in a delivery app (Zomato or Swiggy): the delivery location its searches and menus are
    loaded from. details holds the app's own ids for the spot, and the outlet's own listing when found by name."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="market_spots")
    platform = models.CharField(max_length=10, choices=PLATFORMS)
    title = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    lat = models.FloatField()
    lng = models.FloatField()
    city_id = models.CharField(max_length=20, blank=True)
    details = models.JSONField(default=dict)

    class Meta:
        unique_together = [("outlet", "platform")]


class MarketRestaurant(models.Model):
    """A restaurant as a delivery app shows it, with its menu as last read. Shared by every outlet that tracks it."""

    platform = models.CharField(max_length=10, choices=PLATFORMS)
    res_id = models.CharField(max_length=40)
    name = models.CharField(max_length=255)
    rating = models.FloatField(null=True, blank=True)
    votes = models.CharField(max_length=40, blank=True)
    offers = models.JSONField(default=list, blank=True)
    combos = models.JSONField(default=list, blank=True)
    items = models.JSONField(default=list, blank=True)
    insights = models.JSONField(default=dict, blank=True)
    info = models.JSONField(default=dict, blank=True, help_text="cost for two, cuisines, area: whatever else the app shows")
    menu_refreshed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("platform", "res_id")]

    def __str__(self):
        return f"{self.name} ({self.platform})"


class MarketSnapshot(models.Model):
    """A restaurant's day, each time its menu was read: rating, menu size, prices and stock-outs."""

    restaurant = models.ForeignKey(MarketRestaurant, on_delete=models.CASCADE, related_name="snapshots")
    day = models.DateField()
    rating = models.FloatField(null=True, blank=True)
    votes = models.CharField(max_length=40, blank=True)
    items = models.IntegerField(default=0)
    out_of_stock = models.IntegerField(default=0)
    avg_price = models.IntegerField(null=True, blank=True)
    offers = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = [("restaurant", "day")]
        ordering = ["day"]


class MarketCompetitor(TimeStamped):
    """A delivery-app restaurant an outlet compares itself with."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="market_competitors")
    restaurant = models.ForeignKey(MarketRestaurant, on_delete=models.PROTECT, related_name="+")
    distance_km = models.FloatField(null=True, blank=True)
    delivery_time = models.CharField(max_length=40, blank=True)

    class Meta:
        unique_together = [("outlet", "restaurant")]
