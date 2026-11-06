"""Platform rating details from the Zomato and Swiggy rating screens: how many ratings the platform rating is built on,
and this week's rating (Swiggy) so a slipping outlet shows before the overall rating moves."""

from django.db import migrations

KPIS = [
    ("rating_count", "Ratings on Platform", "count", "last", True),
    ("weekly_rating", "This Week's Rating", "rating", "last", True),
    ("weekly_rating_count", "Ratings This Week", "count", "last", True),
]


def load(apps, schema_editor):
    Module = apps.get_model("masters", "Module")
    Kpi = apps.get_model("masters", "Kpi")
    module = Module.objects.filter(code="listings").first()
    if not module:
        return
    for i, (code, name, unit, agg, hib) in enumerate(KPIS, start=70):
        Kpi.objects.get_or_create(code=code, defaults=dict(
            name=name, module=module, unit=unit, aggregation=agg, higher_is_better=hib, sort_order=i))


class Migration(migrations.Migration):
    dependencies = [("masters", "0004_menu_health_kpis")]
    operations = [migrations.RunPython(load, migrations.RunPython.noop)]
