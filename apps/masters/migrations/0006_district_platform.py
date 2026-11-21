"""District, Zomato's dining app, as a platform of its own: a dine-in rating is not a delivery rating, so it is kept apart.
Its rating and review count reuse the Listings KPIs; cost for two is new."""

from django.db import migrations


def load(apps, schema_editor):
    Platform = apps.get_model("masters", "Platform")
    Module = apps.get_model("masters", "Module")
    Kpi = apps.get_model("masters", "Kpi")
    Platform.objects.get_or_create(code="district", defaults=dict(
        name="District", category="marketplace", supports_reviews=False, supports_replies=False, supports_orders=False,
        supports_store_status=False, sort_order=13, is_active=True))
    module = Module.objects.filter(code="listings").first()
    if module:
        Kpi.objects.get_or_create(code="cost_for_two", defaults=dict(
            name="Cost for Two", module=module, unit="currency", aggregation="last", higher_is_better=False, sort_order=73))


class Migration(migrations.Migration):
    dependencies = [("masters", "0005_rating_kpis")]
    operations = [migrations.RunPython(load, migrations.RunPython.noop)]
