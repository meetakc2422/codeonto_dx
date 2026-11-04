from django.contrib import admin

from .models import GoogleConnection


@admin.register(GoogleConnection)
class GoogleConnectionAdmin(admin.ModelAdmin):
    list_display = ("client", "email", "status", "connected_at")
    list_filter = ("status",)
    exclude = ("refresh_token_enc",)  # never show tokens
    readonly_fields = ("client", "account", "email", "scopes", "connected_by")
