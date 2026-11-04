from django.db import models


class ItemSalesDaily(models.Model):
    """One menu item's sales at one store on one day, from the platform's item sales report. Written by the collector;
    used to put a ₹ value on stock-outs."""

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="item_sales")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    item_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True)
    day = models.DateField()
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    orders = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "item_sales_daily"
        constraints = [models.UniqueConstraint(fields=["outlet", "platform", "item_name", "day"], name="uniq_item_sales_day")]
        indexes = [models.Index(fields=["outlet", "day"])]

    def __str__(self):
        return f"{self.item_name} · {self.outlet} · {self.day}"
