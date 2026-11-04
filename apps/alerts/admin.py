from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "outlet", "kind", "severity", "is_open", "first_seen_at", "resolved_at")
    list_filter = ("kind", "severity", "is_open")
