from django.conf import settings
from django.db import models


class Complaint(models.Model):
    """One customer complaint on an order (missing item, wrong item, quality ...), from the Zomato or Swiggy partner
    dashboard. The collector owns the platform fields and keeps them current; status, assigned_to and note are the
    client's own ticket on it and the collector never touches them."""

    STATUS_CHOICES = [("open", "Open"), ("in_progress", "In progress"), ("resolved", "Resolved")]

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="complaints")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    external_id = models.CharField(max_length=255, help_text="Swiggy complaintId; Zomato <order id>:<issue number>")
    order_id = models.CharField(max_length=64, blank=True)
    issue_type = models.CharField(max_length=40, blank=True, help_text="missing_items, wrong_items, quality, quantity, packaging, other")
    issue_detail = models.TextField(blank=True, help_text="What the customer said, or the platform's sub-reason")
    items = models.TextField(blank=True)
    customer_name = models.CharField(max_length=255, blank=True)
    customer_context = models.CharField(max_length=255, blank=True, help_text="e.g. 'Repeat customer · 12 orders'")
    platform_status = models.CharField(max_length=100, blank=True, help_text="The complaint's state on the platform")
    resolution = models.TextField(blank=True, help_text="Refund decision / reason given on the platform")
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    raised_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Last moment the restaurant can respond on the platform")
    platform_resolved_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="open")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    raw = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "complaints"
        ordering = ["-raised_at"]
        constraints = [models.UniqueConstraint(fields=["platform", "external_id"], name="uniq_complaint_per_platform")]
        indexes = [models.Index(fields=["outlet", "-raised_at"]), models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.platform} {self.issue_type or 'complaint'} · {self.outlet}"
