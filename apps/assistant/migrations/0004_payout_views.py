from django.db import migrations

from apps.assistant.views_sql import PAYOUTS_SQL


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0003_uptime_views"),
        ("payouts", "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(PAYOUTS_SQL, reverse_sql="DROP VIEW IF EXISTS assistant.payout_orders; DROP VIEW IF EXISTS assistant.payout_cycles;"),
    ]
