"""The sidebar names for two modules: Store Uptime becomes Offline hours, Stock-outs becomes Out of stock."""

from django.db import migrations

NAMES = {"store_uptime": ("Store Uptime", "Offline hours"), "stock_outs": ("Stock-outs", "Out of stock")}


def rename(apps, schema_editor):
    Module = apps.get_model("masters", "Module")
    for code, (_, new) in NAMES.items():
        Module.objects.filter(code=code).update(name=new)


def undo(apps, schema_editor):
    Module = apps.get_model("masters", "Module")
    for code, (old, _) in NAMES.items():
        Module.objects.filter(code=code).update(name=old)


class Migration(migrations.Migration):
    dependencies = [("masters", "0006_district_platform")]
    operations = [migrations.RunPython(rename, undo)]
