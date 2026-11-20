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
