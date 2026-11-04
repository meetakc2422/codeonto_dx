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
