from django.db import models


class ListingProfile(models.Model):
    """What a store's public listing looks like right now (one row per store and platform), written by
    the collector. health_score is 0-100; issues says what to fix."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="listing_profiles")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    title = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    website = models.CharField(max_length=500, blank=True)
    primary_category = models.CharField(max_length=120, blank=True)
    extra_categories = models.PositiveSmallIntegerField(default=0)
    has_description = models.BooleanField(default=False)
    has_hours = models.BooleanField(default=False)
    open_status = models.CharField(max_length=40, blank=True)
    photo_count = models.PositiveIntegerField(default=0)
    last_post_at = models.DateTimeField(null=True, blank=True)
    health_score = models.PositiveSmallIntegerField(default=0)
    issues = models.JSONField(default=list)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listing_profiles"
        constraints = [models.UniqueConstraint(fields=["outlet", "platform"], name="uniq_listing_profile")]
        ordering = ["health_score"]

    def __str__(self):
        return f"{self.outlet} · {self.platform_id} · {self.health_score}"


class OutletHours(models.Model):
    """Opening hours of a store on one platform and service (for example Zomato delivery), one row per day and
    time slot. An end time at or before the start time means the slot runs past midnight (00:00 = midnight).
    A day with is_active false and no times is a closed day. Written by the collector."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="hours")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    service_type = models.CharField(max_length=20, default="delivery")
    day = models.CharField(max_length=10)  # monday .. sunday
    is_active = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "outlet_hours"
        indexes = [models.Index(fields=["outlet", "platform", "service_type"])]
        verbose_name_plural = "outlet hours"

    def __str__(self):
        return f"{self.outlet} · {self.platform_id} {self.service_type} {self.day}"
