from django.contrib import admin

from .models import PayoutCycle, PayoutOrder


@admin.register(PayoutCycle)
class PayoutCycleAdmin(admin.ModelAdmin):
    list_display = ("outlet", "platform", "start_date", "end_date", "status", "net_payout", "expected_payout", "discrepancy")
    list_filter = ("platform", "status", "end_date")


@admin.register(PayoutOrder)
class PayoutOrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "cycle", "status", "payout", "settlement_status")
    search_fields = ("order_id",)
    raw_id_fields = ("cycle",)
