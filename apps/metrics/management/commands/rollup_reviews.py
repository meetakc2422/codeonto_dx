from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.metrics.rollups import rollup_review_metrics
from apps.outlets.models import Brand


class Command(BaseCommand):
    help = "Recompute review KPIs (rating, counts, response rate) in metric_daily from the reviews table."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=120)

    def handle(self, *args, **opts):
        end = date.today()
        start = end - timedelta(days=opts["days"] - 1)
        total = sum(rollup_review_metrics(b.id, start, end) for b in Brand.objects.filter(is_active=True))
        self.stdout.write(f"{total} KPI rows written ({start} to {end})")
