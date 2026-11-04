from django.db import migrations, models


def managers_become_admins(apps, schema_editor):
    """Until now a manager could see and change everything under its client, which is what an admin does from here on.
    Keep existing logins working as they did; a manager now means someone limited to assigned outlets."""
    apps.get_model("outlets", "ClientUser").objects.filter(role="manager").update(role="admin")


class Migration(migrations.Migration):
    dependencies = [
        ("outlets", "0004_client_ownership"),
    ]
    operations = [
        migrations.AddField(
            model_name="clientuser",
            name="outlets",
            field=models.ManyToManyField(blank=True, db_table="client_user_outlets",
                                         help_text="The only outlets a manager can see. Admins and viewers see the whole client.",
                                         related_name="assigned_users", to="outlets.brandoutlet"),
        ),
        migrations.RunPython(managers_become_admins, migrations.RunPython.noop),
    ]
