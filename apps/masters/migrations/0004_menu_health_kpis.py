"""Menu health KPIs (from Zomato's owner-hub report) under the Listings module."""

from django.db import migrations

KPIS = [
    ("menu_score", "Menu Score", "percent", "weighted_avg", True),
    ("menu_images_pct", "Items with Images", "percent", "weighted_avg", True),
    ("menu_description_pct", "Items with Description", "percent", "weighted_avg", True),
]


def load(apps, schema_editor):
    Module = apps.get_model("masters", "Module")
    Kpi = apps.get_model("masters", "Kpi")
    module = Module.objects.filter(code="listings").first()
    if not module:
        return
    for i, (code, name, unit, agg, hib) in enumerate(KPIS, start=60):
        Kpi.objects.get_or_create(code=code, defaults=dict(
            name=name, module=module, unit=unit, aggregation=agg, higher_is_better=hib, sort_order=i))


class Migration(migrations.Migration):
    dependencies = [("masters", "0003_google_profile_kpis")]
    operations = [migrations.RunPython(load, migrations.RunPython.noop)]
