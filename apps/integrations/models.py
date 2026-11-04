from django.conf import settings
from django.db import models


class GoogleConnection(models.Model):
    """A client's Google login, connected through the dashboard's "Connect with Google" button. The refresh token is
    stored encrypted; the collector reads it through the platform account (credentials_ref = db:google:<id>)."""

    STATUS_CHOICES = [("connected", "Connected"), ("revoked", "Disconnected"), ("error", "Needs reconnecting")]

    client = models.ForeignKey("outlets.Client", on_delete=models.CASCADE, related_name="google_connections")
    account = models.OneToOneField("outlets.PlatformAccount", on_delete=models.SET_NULL, null=True, blank=True, related_name="google_connection")
    email = models.EmailField()
    refresh_token_enc = models.TextField(blank=True)
    scopes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="connected")
    connected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "google_connections"
        constraints = [models.UniqueConstraint(fields=["client", "email"], name="uniq_google_connection")]

    def __str__(self):
        return f"{self.client} · {self.email}"
