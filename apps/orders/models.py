from django.db import models


class OrderLine(models.Model):
    """One item of one order, from the platform's order history (the collector fills it; no customer details are kept).
    Used to learn what an outlet normally sells at each mealtime, so a stock-out can be valued. unit_price is only known
    for single-item orders (subtotal / quantity); for the rest use the item's menu price."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="order_lines")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    order_id = models.CharField(max_length=32)
    placed_at = models.DateTimeField()
    order_date = models.DateField(help_text="The service day (5 am to 5 am), in India time")
    mealtime = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=40, blank=True, help_text="Delivered, Rejected, Cancelled...")
    rejection_reason = models.CharField(max_length=255, blank=True)
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    order_subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    order_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_lines"
        constraints = [models.UniqueConstraint(fields=["platform", "order_id", "item_name"], name="uniq_order_line")]
        indexes = [models.Index(fields=["outlet", "placed_at"]), models.Index(fields=["outlet", "item_name", "order_date"])]

    def __str__(self):
        return f"{self.quantity} x {self.item_name} · {self.order_id}"
