from django.db import models


class OfflineEpisode(models.Model):
    """One stretch of a store being offline on a platform while it should be open. The collector keeps it current:
    is_active until the store is seen online again, then restored_at. downtime_minutes counts only the store's opening
    hours and keeps growing while the episode is active. log_date is the service day the episode started."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="offline_episodes")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    is_active = models.BooleanField(default=True)
    log_date = models.DateField()
    first_detected_at = models.DateTimeField()
    last_detected_at = models.DateTimeField(help_text="The last check that saw it offline")
    restored_at = models.DateTimeField(null=True, blank=True)
    downtime_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "offline_episodes"
        ordering = ["-is_active", "-first_detected_at"]
        constraints = [models.UniqueConstraint(fields=["outlet", "platform"], condition=models.Q(is_active=True),
                                               name="uniq_active_offline_episode")]
        indexes = [models.Index(fields=["outlet", "is_active"]), models.Index(fields=["log_date"])]

    def __str__(self):
        return f"{self.outlet} offline since {self.first_detected_at:%Y-%m-%d %H:%M}"


class UptimeDaily(models.Model):
    """How many checks saw a store online during its opening hours, per service day. Uptime % is online_checks / checks,
    so time the collector wasn't running doesn't count for or against the store."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="uptime_days")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    day = models.DateField()
    checks = models.PositiveIntegerField(default=0)
    online_checks = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "outlet_uptime_daily"
        constraints = [models.UniqueConstraint(fields=["outlet", "platform", "day"], name="uniq_outlet_uptime_day")]
        indexes = [models.Index(fields=["day"])]

    def __str__(self):
        return f"{self.outlet} {self.day}: {self.online_checks}/{self.checks}"
