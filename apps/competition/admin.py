from django.contrib import admin

from .models import Competitor, OutletPlace, Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "rating", "rating_count", "refreshed_at")
    search_fields = ("name", "address", "place_id")


@admin.register(OutletPlace)
class OutletPlaceAdmin(admin.ModelAdmin):
    list_display = ("outlet", "place")


@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ("outlet", "place", "distance_m", "is_tracked")
    list_filter = ("is_tracked",)
