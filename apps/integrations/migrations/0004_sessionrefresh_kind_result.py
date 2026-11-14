from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0003_sessionrefresh")]
    operations = [
        migrations.AddField(model_name="sessionrefresh", name="kind",
                            field=models.CharField(choices=[("login", "Log in again"), ("outlets", "Sync outlets")], default="login",
                                                   help_text="what the worker should do for this account", max_length=10)),
        migrations.AddField(model_name="sessionrefresh", name="result",
                            field=models.CharField(blank=True, help_text="what a finished outlet sync found, e.g. '24 outlets, 3 new'", max_length=300)),
    ]
