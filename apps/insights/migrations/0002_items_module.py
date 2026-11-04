from django.db import migrations


def add(apps, schema_editor):
    Module = apps.get_model("masters", "Module")
    stock = Module.objects.filter(code="stock_outs").first()
    mod, _ = Module.objects.update_or_create(code="items", defaults=dict(
        name="Item Scorecard", scope="industry", sort_order=15,
        description="Every menu item's sales, stock-outs, complaints and ratings, with the ones that need fixing first"))
    if stock:
        mod.industries.set(stock.industries.all())
    Module.objects.filter(code="reconciliation").update(sort_order=16)
    for plan in apps.get_model("billing", "Plan").objects.filter(code__in=["growth", "pro"]):
        if "items" not in plan.modules:
            plan.modules = plan.modules + ["items"]
            plan.save(update_fields=["modules"])


def remove(apps, schema_editor):
    apps.get_model("masters", "Module").objects.filter(code="items").delete()
    for plan in apps.get_model("billing", "Plan").objects.filter(code__in=["growth", "pro"]):
        plan.modules = [m for m in plan.modules if m != "items"]
        plan.save(update_fields=["modules"])


class Migration(migrations.Migration):
    dependencies = [("insights", "0001_initial"), ("masters", "0004_menu_health_kpis"), ("billing", "0002_starter_plans")]
    operations = [migrations.RunPython(add, remove)]
