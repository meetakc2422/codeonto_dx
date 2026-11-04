from django.contrib import admin

from .models import MetricDaily


@admin.register(MetricDaily)
class MetricDailyAdmin(admin.ModelAdmin):
    list_display = ["metric_date", "kpi", "outlet", "platform", "value"]
    list_filter = ["kpi__module", "platform"]
    date_hierarchy = "metric_date"
    raw_id_fields = ["outlet"]
    list_select_related = ["kpi", "outlet__brand", "platform"]
