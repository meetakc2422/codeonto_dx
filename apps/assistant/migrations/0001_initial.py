import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from apps.assistant.views_sql import SQL


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("outlets", "0004_client_ownership"), ("reviews", "0001_initial"), ("metrics", "0001_initial"),
        ("stockouts", "0004_stock_out_episodes"), ("listings", "0002_outlet_hours"), ("alerts", "0001_initial"),
        ("masters", "0004_menu_health_kpis"),
    ]
    operations = [
        migrations.CreateModel(
            name="AssistantLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_id", models.BigIntegerField(blank=True, null=True)),
                ("question", models.TextField()), ("answer", models.TextField(blank=True)),
                ("queries", models.JSONField(default=list)), ("error", models.TextField(blank=True)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "assistant_logs", "ordering": ["-created_at"]},
        ),
        migrations.RunSQL(SQL, reverse_sql="DROP SCHEMA IF EXISTS assistant CASCADE;"),
    ]
