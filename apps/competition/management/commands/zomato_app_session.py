import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.competition import zomato


class Command(BaseCommand):
    help = ("Save the Zomato app session used for competitor lookup. Copy any request the Zomato app makes to "
            "api.zomato.com as cURL into a file and pass it here (or - to paste it on stdin).")

    def add_arguments(self, parser):
        parser.add_argument("file")

    def handle(self, file, **opts):
        text = sys.stdin.read() if file == "-" else Path(file).read_text()
        try:
            headers = zomato.import_curl(text)
        except zomato.ZomatoAppError as e:
            raise CommandError(str(e))
        self.stdout.write(f"Saved {len(headers)} headers to the Zomato app session.")
