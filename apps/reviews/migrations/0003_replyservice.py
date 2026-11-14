import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("reviews", "0002_review_contacts"), ("outlets", "0008_platformaccount_session_error_and_more")]
    operations = [
        migrations.CreateModel(
            name="ReplyService",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(default="zomato", max_length=10)),
                ("res_id", models.CharField(blank=True, help_text="Empty = every Zomato outlet of this client", max_length=32)),
                ("mode", models.CharField(choices=[("manual", "Send button only"), ("ai", "Automatic AI replies")], default="manual", max_length=10)),
                ("hold_risky", models.BooleanField(default=True, help_text="AI mode: leave food-safety, refund and legal reviews for a person")),
                ("instructions", models.TextField(blank=True, help_text="AI mode: extra wording rules, e.g. a contact number or a signature")),
                ("max_per_day", models.PositiveSmallIntegerField(default=60, help_text="Most automatic replies per outlet per day")),
                ("is_active", models.BooleanField(default=True)),
                ("enabled_by", models.CharField(blank=True, max_length=150)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reply_services", to="outlets.client")),
            ],
            options={"db_table": "reply_service", "ordering": ["client_id", "res_id"],
                     "constraints": [models.UniqueConstraint(fields=("client", "platform", "res_id"), name="one_reply_service_per_scope")]},
        ),
    ]
