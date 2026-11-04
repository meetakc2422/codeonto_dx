from django.db import migrations

from apps.assistant.views_sql import UPTIME_SQL


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0002_outlet_scope"),
        ("uptime", "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(UPTIME_SQL, reverse_sql="DROP VIEW IF EXISTS assistant.offline_episodes; DROP VIEW IF EXISTS assistant.uptime_daily;"),
    ]
