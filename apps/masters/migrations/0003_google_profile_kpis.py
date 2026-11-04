"""Google Business Profile performance KPIs (listing views and customer actions) under the Listings module."""

from django.db import migrations

KPIS = [
    # code, name, unit, aggregation, higher_is_better
    ("profile_views", "Profile Views (Search + Maps)", "count", "sum", True),
    ("website_clicks", "Website Clicks", "count", "sum", True),
    ("call_clicks", "Call Clicks", "count", "sum", True),
    ("direction_requests", "Direction Requests", "count", "sum", True),
    ("profile_menu_clicks", "Menu Clicks", "count", "sum", True),
    ("profile_food_orders", "Food Orders from Profile", "count", "sum", True),
]


def load(apps, schema_editor):
    Module = apps.get_model("masters", "Module")
    Kpi = apps.get_model("masters", "Kpi")
    module = Module.objects.filter(code="listings").first()
    if not module:
        return
    for i, (code, name, unit, agg, hib) in enumerate(KPIS, start=50):
        Kpi.objects.get_or_create(code=code, defaults=dict(
            name=name, module=module, unit=unit, aggregation=agg, higher_is_better=hib, sort_order=i))


class Migration(migrations.Migration):
    dependencies = [("masters", "0002_initial_data")]
    operations = [migrations.RunPython(load, migrations.RunPython.noop)]
