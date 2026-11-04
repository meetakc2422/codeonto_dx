import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.competition import swiggy


class Command(BaseCommand):
    help = ("Save the Swiggy app session used for competitor lookup. Copy any request the Swiggy app makes as cURL "
            "into a file and pass it here (or - to paste it on stdin). Use a different account from the partner sessions.")

    def add_arguments(self, parser):
        parser.add_argument("file")

    def handle(self, file, **opts):
        text = sys.stdin.read() if file == "-" else Path(file).read_text()
        try:
            headers = swiggy.import_curl(text)
        except swiggy.SwiggyAppError as e:
            raise CommandError(str(e))
        self.stdout.write(f"Saved {len(headers)} headers to the Swiggy app session.")
