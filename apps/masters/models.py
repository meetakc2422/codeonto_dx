"""Global lookups shared by every client: platforms, industries, modules, KPIs.

All of these are data (editable in admin), loaded initially by a data migration.
"""

from django.db import models


class Platform(models.Model):
    """A source of reviews / orders / metrics. Keyed by a readable code, never a number."""

    CATEGORY_CHOICES = [(c, c.title()) for c in ("marketplace", "review", "ota", "social", "listing", "survey")]

    code = models.SlugField(primary_key=True, max_length=30, help_text="e.g. zomato, swiggy, google")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    supports_reviews = models.BooleanField(default=False)
    supports_replies = models.BooleanField(default=False)
    supports_orders = models.BooleanField(default=False)
    supports_store_status = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "platforms"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Industry(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    platforms = models.ManyToManyField(Platform, related_name="industries", db_table="industry_platforms", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "industries"
        ordering = ["name"]
        verbose_name_plural = "industries"

    def __str__(self):
        return self.name


class Module(models.Model):
    SCOPE_CHOICES = [("common", "Common"), ("industry", "Industry pack")]

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    industries = models.ManyToManyField(Industry, related_name="modules", db_table="industry_modules", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "modules"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class Kpi(models.Model):
    UNIT_CHOICES = [(u, u) for u in ("count", "currency", "percent", "seconds", "minutes", "rating", "ratio")]
    AGGREGATION_CHOICES = [(a, a) for a in ("sum", "avg", "weighted_avg", "last", "max", "min")]

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    module = models.ForeignKey(Module, on_delete=models.PROTECT, related_name="kpis")
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    aggregation = models.CharField(max_length=15, choices=AGGREGATION_CHOICES)
    higher_is_better = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "kpis"
        ordering = ["module__sort_order", "sort_order", "code"]
        verbose_name = "KPI"

    def __str__(self):
        return self.name
