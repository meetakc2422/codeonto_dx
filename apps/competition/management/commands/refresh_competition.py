from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.competition import places
from apps.competition.models import Competitor, OutletPlace, Place, PlaceSnapshot

KEEP_DAYS = 30  # Google's terms: Places content may be cached for at most 30 days


class Command(BaseCommand):
    help = ("Refresh the rating of every outlet's own Google listing and every tracked competitor, keep today's snapshot, "
            "and drop what Google doesn't let us keep: snapshots older than 30 days, and stale untracked suggestions.")

    def handle(self, *args, **opts):
        self.refresh_google()

    def refresh_google(self):
        if not places.configured():
            self.stderr.write("GOOGLE_API_KEY is not set; nothing refreshed.")
            return
        ids = set(OutletPlace.objects.values_list("place_id", flat=True)) | \
            set(Competitor.objects.filter(is_tracked=True).values_list("place_id", flat=True))
        ok = failed = 0
        for pid in sorted(ids):
            try:
                p = places.refresh(pid)
            except places.PlacesError as e:
                failed += 1
                self.stderr.write(f"{pid}: {e}")
                continue
            PlaceSnapshot.objects.update_or_create(place=p, day=date.today(), defaults={"rating": p.rating, "rating_count": p.rating_count})
            ok += 1
        cutoff = timezone.now() - timedelta(days=KEEP_DAYS)
        PlaceSnapshot.objects.filter(day__lt=date.today() - timedelta(days=KEEP_DAYS)).delete()
        Competitor.objects.filter(is_tracked=False, updated_at__lt=cutoff).delete()
        in_use = set(OutletPlace.objects.values_list("place_id", flat=True)) | set(Competitor.objects.values_list("place_id", flat=True))
        Place.objects.exclude(place_id__in=in_use).delete()
        Place.objects.filter(refreshed_at__lt=cutoff).update(rating=None, rating_count=None, price_level="")
        self.stdout.write(f"Refreshed {ok} places, {failed} failed.")
