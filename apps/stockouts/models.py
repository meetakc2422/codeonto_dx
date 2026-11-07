from django.db import models


class StockOut(models.Model):
    """One stock-out episode: an item going off a store's menu until it is back. The collector keeps it current:
    is_active while the item is off the menu, restored_at / downtime_minutes once it is back. An item that stays
    out across checks or days is still one episode; going out again after being restored starts a new one.
    log_date is the day the episode started."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="stock_outs")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    item_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True)
    back_at = models.CharField(max_length=255, blank=True, help_text="When the platform says it comes back on")
    mealtime = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    log_date = models.DateField()
    first_detected_at = models.DateTimeField()
    last_detected_at = models.DateTimeField()
    restored_at = models.DateTimeField(null=True, blank=True)
    downtime_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "stock_outs"
        ordering = ["-is_active", "-first_detected_at"]
        constraints = [models.UniqueConstraint(fields=["outlet", "platform", "item_name"], condition=models.Q(is_active=True),
                                               name="uniq_active_stock_out")]
        indexes = [models.Index(fields=["outlet", "is_active"]), models.Index(fields=["log_date"])]

    def __str__(self):
        return f"{self.item_name} · {self.outlet}"


class AlertRecipient(models.Model):
    """Who a client wants stock-out alerts sent to. A client with no active row gets none."""

    CHANNEL_CHOICES = [("email", "Email"), ("whatsapp", "WhatsApp")]

    client = models.ForeignKey("outlets.Client", on_delete=models.CASCADE, related_name="alert_recipients")
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    address = models.CharField(max_length=255, help_text="Email address, or WhatsApp number with country code (919876543210)")
    name = models.CharField(max_length=120, blank=True)
    stock_out_alerts = models.BooleanField(default=True, help_text="New and restored stock-outs")
    performance_alerts = models.BooleanField(default=True, help_text="Rating drops, view drops, listing problems, review backlog")
    offline_alerts = models.BooleanField(default=True, help_text="An outlet went offline during opening hours")
    online_alerts = models.BooleanField(default=True, help_text="An outlet that was reported offline is back online")
    review_alerts = models.BooleanField(default=True, help_text="New 1-2 star reviews")
    payout_alerts = models.BooleanField(default=True, help_text="Payouts overdue or not matching their orders")
    ad_alerts = models.BooleanField(default=True, help_text="Ad spend well above the outlet's usual")
    brands = models.ManyToManyField("outlets.Brand", blank=True, related_name="+", help_text="Only these brands (empty = every brand)")
    outlets = models.ManyToManyField("outlets.BrandOutlet", blank=True, related_name="+", help_text="Only these outlets (empty = all of the brands above)")
    quiet_start = models.TimeField(null=True, blank=True, help_text="No messages from (IST), e.g. 23:00")
    quiet_end = models.TimeField(null=True, blank=True, help_text="until (IST), e.g. 08:00")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alert_recipients"
        constraints = [models.UniqueConstraint(fields=["client", "channel", "address"], name="uniq_alert_recipient")]

    def __str__(self):
        return f"{self.client} · {self.channel} · {self.address}"
