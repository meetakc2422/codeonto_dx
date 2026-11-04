from django.contrib import admin

from .models import Industry, Kpi, Module, Platform


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "supports_reviews", "supports_orders", "supports_store_status", "is_active"]
    list_editable = ["is_active"]
    list_filter = ["category", "is_active"]


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    filter_horizontal = ["platforms"]
    search_fields = ["name", "code"]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "scope", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    list_filter = ["scope"]
    filter_horizontal = ["industries"]


@admin.register(Kpi)
class KpiAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "module", "unit", "aggregation", "higher_is_better", "is_active"]
    list_filter = ["module", "unit", "is_active"]
    search_fields = ["name", "code"]
