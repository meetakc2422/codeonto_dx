from django.db import models


class MetricDaily(models.Model):
    """One KPI value for one outlet, platform and day. platform NULL = all platforms combined."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="metrics")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, null=True, blank=True,
                                 related_name="+", db_column="platform")
    kpi = models.ForeignKey("masters.Kpi", on_delete=models.PROTECT, related_name="values")
    metric_date = models.DateField()
    value = models.DecimalField(max_digits=18, decimal_places=4)
    weight = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True,
                                 help_text="For weighted averages, e.g. order count")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "metric_daily"
        constraints = [models.UniqueConstraint(fields=["outlet", "platform", "kpi", "metric_date"],
                                               name="uniq_metric_day", nulls_distinct=False)]
        indexes = [models.Index(fields=["kpi", "metric_date"])]


class DiningOfferSnapshot(models.Model):
    """One reading of a dining offer on Zomato's table-booking page: what the offer is and how many slots were left
    when we looked. Every collector run adds rows; comparing runs shows how fast an offer sells."""

    res_id = models.CharField(max_length=32)
    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    taken_at = models.DateTimeField()
    for_date = models.DateField()
    meal_time = models.CharField(max_length=20)
    offer = models.CharField(max_length=80)
    discount_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    window = models.CharField(max_length=60, blank=True, help_text="e.g. 'From 6:00 PM, today'")
    slots_left = models.IntegerField(null=True, blank=True)
    cover_charge = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "dining_offer_snapshots"
        indexes = [models.Index(fields=["res_id", "for_date", "taken_at"])]


class DiningSlotSnapshot(models.Model):
    """One bookable 15-minute slot seen on a run, with the discount on it. A slot that was there earlier and is gone
    later is full or closed."""

    res_id = models.CharField(max_length=32)
    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    taken_at = models.DateTimeField()
    for_date = models.DateField()
    meal_time = models.CharField(max_length=20, blank=True)
    slot_time = models.CharField(max_length=12)
    discount_pct = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "dining_slot_snapshots"
        indexes = [models.Index(fields=["res_id", "for_date", "taken_at"])]


class DiningMenuPage(models.Model):
    """One page of a dining outlet's menu as District shows it (an image). The collector keeps the list current; a page
    is read into items once, and again only if the restaurant replaces the image (a new file name)."""

    res_id = models.CharField(max_length=32)
    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    image_url = models.CharField(max_length=300)
    position = models.PositiveSmallIntegerField(default=0)
    first_seen = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True, help_text="When its items were read; empty = still to read")
    read_error = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "dining_menu_pages"
        constraints = [models.UniqueConstraint(fields=["res_id", "image_url"], name="uniq_dining_menu_page")]


class DiningMenuItem(models.Model):
    """A dish and its dining price, read from a menu page."""

    page = models.ForeignKey(DiningMenuPage, on_delete=models.CASCADE, related_name="items")
    res_id = models.CharField(max_length=32, db_index=True)
    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    section = models.CharField(max_length=120, blank=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    note = models.CharField(max_length=160, blank=True, help_text="Size or variant, e.g. 'Half' or '12 inch'")

    class Meta:
        db_table = "dining_menu_items"


class DiningMenuStatus(models.Model):
    """What District says about a dining outlet's menu ("Updated a month ago") and when we last looked, so a menu that has
    not changed since our last sync is not fetched again."""

    res_id = models.CharField(max_length=32, unique=True)
    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    updated_text = models.CharField(max_length=60, blank=True, help_text="District's own words, e.g. 'Updated a month ago'")
    updated_latest = models.DateTimeField(null=True, blank=True, help_text="The latest the menu can have been updated, worked out from the text")
    checked_at = models.DateTimeField(null=True, blank=True, help_text="Last time we asked District")
    synced_at = models.DateTimeField(null=True, blank=True, help_text="Last time we fetched the menu images")
    photo_url = models.CharField(max_length=500, blank=True, help_text="The outlet's first photo on District, used as its picture")

    class Meta:
        db_table = "dining_menu_status"
