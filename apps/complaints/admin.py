from django.contrib import admin

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("order_id", "outlet", "platform", "issue_type", "refund_amount", "status", "raised_at")
    list_filter = ("platform", "status", "issue_type")
    search_fields = ("order_id", "issue_detail", "items", "customer_name")
    raw_id_fields = ("outlet", "assigned_to")
