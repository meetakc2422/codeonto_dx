from django.core.management.base import BaseCommand

from apps.outlets.catalog import CATALOGS, sync_catalog


class Command(BaseCommand):
    help = ("Bootstrap zomato_outlets / swiggy_outlets / google_locations from the pipeline database "
            "(read-only). For live data from the master accounts use the collector: "
            "`collector/run.py all outlets`.")

    def add_arguments(self, parser):
        parser.add_argument("--platform", choices=list(CATALOGS), action="append",
                            help="Only these platforms (repeatable). Default: all.")

    def handle(self, *args, **opts):
        for platform, stats in sync_catalog(opts["platform"]).items():
            self.stdout.write(f"{platform:7} {stats}")
