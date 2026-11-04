from django.db import models


class Alert(models.Model):
    """Something a client should look at. One open row per (outlet, kind); the rules refresh it while the
    problem lasts and resolve it when it is gone."""

    SEVERITY_CHOICES = [("critical", "Critical"), ("warning", "Warning"), ("info", "Info")]

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="alerts")
    kind = models.SlugField(max_length=40)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="warning")
    title = models.CharField(max_length=200)
    detail = models.TextField(blank=True)
    is_open = models.BooleanField(default=True)
    notified = models.BooleanField(default=False)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts"
        ordering = ["-is_open", "severity", "-last_seen_at"]
        constraints = [models.UniqueConstraint(fields=["outlet", "kind"], condition=models.Q(is_open=True),
                                               name="uniq_open_alert")]
        indexes = [models.Index(fields=["is_open", "-last_seen_at"])]

    def __str__(self):
        return f"{self.kind} · {self.outlet}"
