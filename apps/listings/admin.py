from django.contrib import admin

from .models import ListingProfile, OutletHours


@admin.register(ListingProfile)
class ListingProfileAdmin(admin.ModelAdmin):
    list_display = ("outlet", "platform", "health_score", "photo_count", "last_post_at", "open_status", "fetched_at")
    list_filter = ("platform", "open_status")


@admin.register(OutletHours)
class OutletHoursAdmin(admin.ModelAdmin):
    list_display = ("outlet", "platform", "service_type", "day", "is_active", "start_time", "end_time")
    list_filter = ("platform", "service_type", "day")
