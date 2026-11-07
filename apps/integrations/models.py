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


class PlatformSession(models.Model):
    """A Zomato or Swiggy login session, stored encrypted (GOOGLE_TOKEN_KEY) so the Windows collector and this site
    read the same one and it can be refreshed from anywhere: the Sessions page, or a collector login on any machine.

    kind:  merchant      the merchant dashboard login a collector account uses (cookies; Swiggy also access_token)
           merchant_app  the merchant mobile app's headers for that account (Zomato ratings screen)
           customer_app  the customer app's headers for competitor search (one per platform, no account)"""

    KINDS = [("merchant", "Merchant dashboard"), ("merchant_app", "Merchant app"), ("customer_app", "Customer app")]

    platform = models.CharField(max_length=20)
    account = models.ForeignKey("outlets.PlatformAccount", on_delete=models.CASCADE, null=True, blank=True, related_name="sessions")
    kind = models.CharField(max_length=20, choices=KINDS)
    data_enc = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=150, blank=True, help_text="Who or what saved it: a user, or collector@<machine>")

    class Meta:
        db_table = "platform_sessions"
        constraints = [
            models.UniqueConstraint(fields=["account", "kind"], name="uniq_session_account_kind"),
            models.UniqueConstraint(fields=["platform", "kind"], condition=models.Q(account__isnull=True), name="uniq_session_platform_kind"),
        ]

    def __str__(self):
        return f"{self.platform} · {self.account.label if self.account else '-'} · {self.kind}"
