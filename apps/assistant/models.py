from django.conf import settings
from django.db import models


class AssistantLog(models.Model):
    """Every question asked and every query the assistant ran, for audit and cost control."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    client_id = models.BigIntegerField(null=True, blank=True)
    question = models.TextField()
    answer = models.TextField(blank=True)
    queries = models.JSONField(default=list)
    error = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assistant_logs"
        ordering = ["-created_at"]
