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
