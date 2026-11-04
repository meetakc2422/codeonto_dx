from django.contrib import admin

from .models import OfflineEpisode, UptimeDaily


@admin.register(OfflineEpisode)
class OfflineEpisodeAdmin(admin.ModelAdmin):
    list_display = ("outlet", "platform", "is_active", "first_detected_at", "restored_at", "downtime_minutes")
    list_filter = ("platform", "is_active", "log_date")


@admin.register(UptimeDaily)
class UptimeDailyAdmin(admin.ModelAdmin):
    list_display = ("outlet", "platform", "day", "checks", "online_checks")
    list_filter = ("platform", "day")
