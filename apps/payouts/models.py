from django.db import models


class PayoutCycle(models.Model):
    """One payout from a platform to one store for one period. The collector fills it and, once the payout is paid,
    downloads its orders and checks the sums. expected_payout, discrepancy and issues stay empty until then."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="payout_cycles")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    start_date = models.DateField()
    end_date = models.DateField()
    payout_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, blank=True, help_text="As the platform words it, e.g. PAID, TO BE PAID")
    utr = models.CharField(max_length=255, blank=True)
    net_payout = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    order_count = models.PositiveIntegerField(default=0)
    delivered_orders = models.PositiveIntegerField(default=0)
    rejected_orders = models.PositiveIntegerField(default=0)
    breakdown = models.JSONField(default=list, help_text="The platform's own payout statement: [{id, label, value, items: [{label, value}]}]")
    orders_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Sum of the orders' payouts")
    adjustments = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Ads, Hyperpure and other items not tied to an order")
    expected_payout = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    discrepancy = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="net_payout minus expected_payout")
    commissionable_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    service_fee_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    issues = models.JSONField(default=list, help_text="Problem codes found when checking this cycle")
    reconciled_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField()

    class Meta:
        db_table = "payout_cycles"
        ordering = ["-end_date", "outlet_id"]
        constraints = [models.UniqueConstraint(fields=["outlet", "platform", "start_date", "end_date"], name="uniq_payout_cycle")]
        indexes = [models.Index(fields=["end_date"]), models.Index(fields=["outlet", "end_date"])]

    def __str__(self):
        return f"{self.outlet} {self.start_date} to {self.end_date}"


class PayoutOrder(models.Model):
    """One order in a payout cycle, from the platform's order-level report. Customer ids are deliberately not kept."""

    cycle = models.ForeignKey(PayoutCycle, on_delete=models.CASCADE, related_name="orders")
    order_id = models.CharField(max_length=100)
    order_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, blank=True)
    payment_mode = models.CharField(max_length=30, blank=True)
    discount_construct = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    packaging_charge = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    restaurant_discount = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    gst_collected = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    net_order_value = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    commissionable_value = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    base_fee_pct = models.DecimalField(max_digits=7, decimal_places=4, default=0, help_text="The contract rate, before any distance fee")
    service_fee_pct = models.DecimalField(max_digits=7, decimal_places=4, default=0, help_text="Base rate plus any distance fee")
    service_fee = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    payment_fee = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    fees_total = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    government_charges = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    net_deductions = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    net_additions = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    payout = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    settlement_status = models.CharField(max_length=30, blank=True)
    settlement_date = models.DateField(null=True, blank=True)
    bank_utr = models.CharField(max_length=255, blank=True)
    unsettled_amount = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    issues = models.JSONField(default=list)

    class Meta:
        db_table = "payout_orders"
        ordering = ["order_date", "order_id"]
        constraints = [models.UniqueConstraint(fields=["cycle", "order_id"], name="uniq_payout_order")]

    def __str__(self):
        return f"{self.order_id} ({self.cycle})"


class PayoutLineType(models.Model):
    """A line seen on the platforms' payout statements (section + item label). Lines we haven't reviewed yet are shown
    as "new deduction types" so a new fee, ad product or adjustment never slips into the numbers unnoticed.
    kind says what it is once reviewed: part of the orders, ad spend, or another deduction not tied to orders."""

    KINDS = [("order", "Part of the orders"), ("ad", "Ad spend"), ("deduction", "Other deduction")]

    platform = models.CharField(max_length=20)
    section = models.CharField(max_length=80)
    label = models.CharField(max_length=255, help_text="Item label with digits replaced by #, so dated labels count as one")
    kind = models.CharField(max_length=20, choices=KINDS, blank=True)
    reviewed = models.BooleanField(default=False)
    first_seen = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "payout_line_types"
        constraints = [models.UniqueConstraint(fields=["platform", "section", "label"], name="uniq_payout_line_type")]

    def __str__(self):
        return f"{self.platform} · {self.section} · {self.label}"
