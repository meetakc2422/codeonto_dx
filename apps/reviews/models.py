from django.db import models


class Review(models.Model):
    SENTIMENT_CHOICES = [("positive", "Positive"), ("neutral", "Neutral"), ("negative", "Negative")]
    REPLY_STATUS_CHOICES = [("pending", "Pending"), ("drafted", "Drafted"), ("replied", "Replied"), ("ignored", "Ignored")]

    outlet = models.ForeignKey("outlets.BrandOutlet", on_delete=models.CASCADE, related_name="reviews")
    platform = models.ForeignKey("masters.Platform", on_delete=models.PROTECT, related_name="+", db_column="platform")
    external_review_id = models.CharField(max_length=255)
    author_name = models.CharField(max_length=255, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    title = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, blank=True)
    reviewed_at = models.DateTimeField()
    reply_status = models.CharField(max_length=10, choices=REPLY_STATUS_CHOICES, default="pending")
    raw = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews"
        ordering = ["-reviewed_at"]
        constraints = [models.UniqueConstraint(fields=["platform", "external_review_id"], name="uniq_review_per_platform")]
        indexes = [models.Index(fields=["outlet", "-reviewed_at"]), models.Index(fields=["reply_status"])]

    def __str__(self):
        return f"{self.platform} {self.rating}★ · {self.outlet}"


class ReviewReply(models.Model):
    SOURCE_CHOICES = [("manual", "Manual"), ("template", "Template"), ("ai", "AI"), ("platform", "Platform")]
    STATUS_CHOICES = [("draft", "Draft"), ("approved", "Approved"), ("published", "Published"), ("failed", "Failed")]

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="replies")
    body = models.TextField()
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="manual")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    error = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review_replies"
        ordering = ["-created_at"]
        verbose_name_plural = "review replies"


class ReviewContact(models.Model):
    """The phone number a reviewer chose to share with the restaurant (Zomato's opt-in), for following up on their
    review. Written by the collector; the number is encrypted (GOOGLE_TOKEN_KEY) and only `hint` is ever listed.
    A row with shared=False means we asked and the customer hadn't shared, so we don't ask again."""

    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="contact", primary_key=True)
    order_id = models.CharField(max_length=100)
    shared = models.BooleanField(default=False)
    phone_enc = models.TextField(blank=True)
    hint = models.CharField(max_length=20, blank=True, help_text="e.g. 98•••••410")
    checked_at = models.DateTimeField()

    class Meta:
        db_table = "review_contacts"


class ReviewContactView(models.Model):
    """Who revealed a reviewer's number, and when."""

    contact = models.ForeignKey(ReviewContact, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, related_name="+")
    action = models.CharField(max_length=10, default="view")
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review_contact_views"
        ordering = ["-at"]


class ReplyService(models.Model):
    """Who gets review replies sent to Zomato for them, set by SocialSpork staff only. NO ROW = NO REPLIES: nothing is ever
    sent for a client or outlet that has no active row. A row with an empty res_id covers every Zomato outlet of the client;
    a row with a res_id covers just that outlet and wins over the client-wide row.

    mode "manual": a person writes the reply on the dashboard and clicks Send to Zomato.
    mode "ai":     the collector also writes and sends a reply (Gemini) for new reviews, every few hours.
    The collector (zomato/replies.py, on the Windows server) does the actual posting."""

    MODES = [("manual", "Send button only"), ("ai", "Automatic AI replies")]

    client = models.ForeignKey("outlets.Client", on_delete=models.CASCADE, related_name="reply_services")
    platform = models.CharField(max_length=10, default="zomato")
    res_id = models.CharField(max_length=32, blank=True, help_text="Empty = every Zomato outlet of this client")
    mode = models.CharField(max_length=10, choices=MODES, default="manual")
    hold_risky = models.BooleanField(default=True, help_text="AI mode: leave food-safety, refund and legal reviews for a person")
    instructions = models.TextField(blank=True, help_text="AI mode: extra wording rules, e.g. a contact number or a signature")
    max_per_day = models.PositiveSmallIntegerField(default=60, help_text="Most automatic replies per outlet per day")
    is_active = models.BooleanField(default=True)
    enabled_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reply_service"
        ordering = ["client_id", "res_id"]
        constraints = [models.UniqueConstraint(fields=["client", "platform", "res_id"], name="one_reply_service_per_scope")]

    def __str__(self):
        return f"{self.client} · {self.platform} · {self.res_id or 'all outlets'} · {self.mode}{'' if self.is_active else ' (off)'}"
