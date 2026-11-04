from django.db import migrations

from apps.assistant.views_sql import SQL


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0001_initial"),
        ("outlets", "0005_client_user_outlets"),
    ]
    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]
