from django.contrib import admin

from .models import AssistantLog


@admin.register(AssistantLog)
class AssistantLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "client_id", "question", "duration_ms", "error")
    search_fields = ("question", "answer")
