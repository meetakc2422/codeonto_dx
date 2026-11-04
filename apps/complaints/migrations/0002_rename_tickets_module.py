from django.db import migrations


def rename(apps, schema_editor):
    apps.get_model("masters", "Module").objects.filter(code="tickets").update(
        name="Complaints", description="Order complaints from Zomato and Swiggy, tracked as tickets until resolved")


def undo(apps, schema_editor):
    apps.get_model("masters", "Module").objects.filter(code="tickets").update(name="Tickets")


class Migration(migrations.Migration):
    dependencies = [("complaints", "0001_initial"), ("masters", "0004_menu_health_kpis")]
    operations = [migrations.RunPython(rename, undo)]
