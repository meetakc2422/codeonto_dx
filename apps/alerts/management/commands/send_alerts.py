"""Send WhatsApp / email alerts for what's new (offline, stock-outs, low reviews, payouts, ad spikes).

    (sending is done by the collector; this command only previews or bootstraps)
    manage.py send_alerts --dry-run     # show who would get what, send nothing
    manage.py send_alerts --bootstrap   # first switch-on: mark what's already pending as handled, send nothing
"""

import json

from django.core.management.base import BaseCommand

from apps.alerts import notify


class Command(BaseCommand):
    help = "Send WhatsApp / email alerts for new events"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--bootstrap", action="store_true")

    def handle(self, *args, **opts):
        if not (opts["dry_run"] or opts["bootstrap"]):
            self.stderr.write("Alerts are sent by the collector (uptime / stockouts jobs and `run.py alerts send`). "
                              "Here use --dry-run to preview or --bootstrap to mark pending events as handled.")
            return
        stats = notify.run(dry_run=opts["dry_run"], bootstrap=opts["bootstrap"])
        plans = stats.pop("plans")
        self.stdout.write(json.dumps(stats))
        for p in plans:
            self.stdout.write(f"  {p['status']:8} {p['to']:28} {p['kind']:9} {p['items']} item(s)  {p['template']}  {p['error'] or ''}")
            if opts["dry_run"]:
                self.stdout.write(f"           params: {p['params']}")
