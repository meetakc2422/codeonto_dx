from django.contrib import admin

from .models import Review, ReviewReply


class ReviewReplyInline(admin.TabularInline):
    model = ReviewReply
    extra = 0
    fields = ["body", "source", "status", "published_at"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["reviewed_at", "platform", "rating", "outlet", "reply_status", "sentiment"]
    list_filter = ["platform", "reply_status", "sentiment", "outlet__brand"]
    search_fields = ["body", "author_name", "external_review_id"]
    list_select_related = ["outlet__brand", "platform"]
    raw_id_fields = ["outlet"]
    inlines = [ReviewReplyInline]
