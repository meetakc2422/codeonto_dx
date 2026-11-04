from django.db import migrations

STARTER = ["overview", "reviews", "listings", "alerts", "store_uptime", "tickets"]
GROWTH = STARTER + ["ai_replies", "reports", "competitors", "marketplace_sales", "marketplace_ops", "marketplace_funnel", "marketplace_ads",
                    "marketplace_discounts", "stock_outs"]
PRO = GROWTH + ["reconciliation"]

# Placeholder prices: change them in admin -> Plans.
PLANS = [
    ("starter", "Starter", "For single outlets and small groups", "499", 3, STARTER, False, 1,
     ["Reviews and replies", "Google listings", "Store uptime and offline alerts", "Up to 3 logins"]),
    ("growth", "Growth", "For growing chains", "999", None, GROWTH, False, 2,
     ["Everything in Starter", "Sales and operations KPIs", "Stock-outs", "Outlet managers and unlimited logins", "Reports"]),
    ("pro", "Pro", "For multi-brand groups", "1499", None, PRO, False, 3,
     ["Everything in Growth", "Payout reconciliation", "AI review buckets and assistant", "Priority support"]),
    ("enterprise", "Enterprise", "For large groups with custom needs", None, None, [], True, 4,
     ["Everything in Pro", "Custom pricing", "Onboarding and a dedicated manager"]),
]


def add(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for code, name, desc, price, logins, modules, all_modules, order, features in PLANS:
        Plan.objects.update_or_create(code=code, defaults=dict(name=name, description=desc, price_per_outlet=price, max_logins=logins, modules=modules,
                                                               all_modules=all_modules, sort_order=order, features=features))


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]
    operations = [migrations.RunPython(add, migrations.RunPython.noop)]
