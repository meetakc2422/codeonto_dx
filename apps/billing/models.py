from django.conf import settings
from django.db import models


class Plan(models.Model):
    """What a client can buy. Priced per outlet per month; staff edit prices and contents in admin."""

    code = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=200, blank=True)
    price_per_outlet = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Per outlet per month, before GST. Empty = contact us")
    annual_free_months = models.PositiveSmallIntegerField(default=2, help_text="Months free when paying yearly")
    max_logins = models.PositiveIntegerField(null=True, blank=True, help_text="Empty = unlimited")
    modules = models.JSONField(default=list, help_text="Module codes this plan unlocks")
    all_modules = models.BooleanField(default=False, help_text="Unlocks every module, including future ones")
    features = models.JSONField(default=list, help_text="Bullet points shown on the plan card")
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "billing_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name

    def unlocks(self, module_code: str) -> bool:
        return self.all_modules or module_code in self.modules


class Subscription(models.Model):
    """A client's plan. A client without one keeps full access (clients from before billing existed)."""

    STATUS_CHOICES = [("trial", "Trial"), ("active", "Active"), ("past_due", "Payment overdue"), ("cancelled", "Cancelled")]
    CYCLE_CHOICES = [("monthly", "Monthly"), ("annual", "Annual")]

    client = models.OneToOneField("outlets.Client", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="trial")
    cycle = models.CharField(max_length=10, choices=CYCLE_CHOICES, default="monthly")
    outlet_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Outlets paid for. Empty = no limit")
    trial_ends_on = models.DateField(null=True, blank=True)
    current_period_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscriptions"

    def __str__(self):
        return f"{self.client} · {self.plan} ({self.status})"


class Invoice(models.Model):
    STATUS_CHOICES = [("due", "Due"), ("paid", "Paid"), ("void", "Void")]

    client = models.ForeignKey("outlets.Client", on_delete=models.CASCADE, related_name="invoices")
    number = models.CharField(max_length=40, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    gst = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="due")
    issued_on = models.DateField()
    paid_on = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "billing_invoices"
        ordering = ["-issued_on", "-id"]

    def __str__(self):
        return self.number


class PlanRequest(models.Model):
    """An owner asked for a plan. Until a payment gateway is connected, staff follow up and activate it by hand."""

    client = models.ForeignKey("outlets.Client", on_delete=models.CASCADE, related_name="plan_requests")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="+")
    cycle = models.CharField(max_length=10, choices=Subscription.CYCLE_CHOICES)
    outlets = models.PositiveIntegerField()
    quoted_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_plan_requests"
        ordering = ["-created_at"]
