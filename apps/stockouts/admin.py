from django.contrib import admin

from .models import AlertRecipient, StockOut


@admin.register(StockOut)
class StockOutAdmin(admin.ModelAdmin):
    list_display = ("item_name", "outlet", "platform", "is_active", "first_detected_at", "downtime_minutes")
    list_filter = ("platform", "is_active", "log_date")
    search_fields = ("item_name",)


@admin.register(AlertRecipient)
class AlertRecipientAdmin(admin.ModelAdmin):
    list_display = ("client", "channel", "address", "name", "stock_out_alerts", "is_active")
    list_filter = ("client", "channel", "is_active")
    search_fields = ("address", "name")
