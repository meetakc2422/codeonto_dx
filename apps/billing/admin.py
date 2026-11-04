from django.contrib import admin

from .models import Invoice, Plan, PlanRequest, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_per_outlet", "max_logins", "all_modules", "is_active", "sort_order")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("client", "plan", "status", "cycle", "outlet_limit", "trial_ends_on", "current_period_end")
    list_filter = ("plan", "status")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "period_start", "period_end", "total", "status", "issued_on", "paid_on")
    list_filter = ("status",)


@admin.register(PlanRequest)
class PlanRequestAdmin(admin.ModelAdmin):
    list_display = ("client", "plan", "cycle", "outlets", "quoted_total", "requested_by", "is_open", "created_at")
    list_filter = ("is_open", "plan")
