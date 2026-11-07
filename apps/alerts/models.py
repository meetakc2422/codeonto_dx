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


class AlertDelivery(models.Model):
    """One alert message sent (or attempted) to one recipient. ref identifies what it was about, e.g. offline:123
    (an offline episode) or review:456, so the same thing is never sent twice to the same person."""

    recipient = models.ForeignKey("stockouts.AlertRecipient", on_delete=models.SET_NULL, null=True, related_name="deliveries")
    client = models.ForeignKey("outlets.Client", on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=30)
    ref = models.CharField(max_length=160)
    channel = models.CharField(max_length=10)
    address = models.CharField(max_length=255)
    status = models.CharField(max_length=10, help_text="sent, failed")
    summary = models.TextField(blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alert_deliveries"
        indexes = [models.Index(fields=["client", "created_at"]), models.Index(fields=["kind", "ref"])]
