from django.db import migrations, models


def drop_client_wide_rows(apps, schema_editor):
    """A row with no res ID meant 'every outlet of the client'. The table is now by res ID only, so those rows can't be kept
    (the service was only just added and nothing is sent without a row)."""
    apps.get_model("reviews", "ReplyService").objects.filter(res_id="").delete()


class Migration(migrations.Migration):
    dependencies = [("reviews", "0003_replyservice")]
    operations = [
        migrations.RunPython(drop_client_wide_rows, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name="replyservice", name="one_reply_service_per_scope"),
        migrations.RemoveField(model_name="replyservice", name="client"),
        migrations.AlterField(model_name="replyservice", name="res_id", field=models.CharField(help_text="The outlet's Zomato res ID", max_length=32)),
        migrations.AlterField(model_name="replyservice", name="max_per_day", field=models.PositiveSmallIntegerField(default=60, help_text="Most automatic replies for this outlet per day")),
        migrations.AlterModelOptions(name="replyservice", options={"ordering": ["res_id"]}),
        migrations.AddConstraint(model_name="replyservice", constraint=models.UniqueConstraint(fields=("platform", "res_id"), name="one_reply_service_per_outlet")),
    ]
