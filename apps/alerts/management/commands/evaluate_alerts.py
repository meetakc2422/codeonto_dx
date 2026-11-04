from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from apps.alerts.rules import evaluate
from apps.stockouts.models import AlertRecipient


class Command(BaseCommand):
    help = "Run the alert rules; email each client's recipients about alerts opened this run. Run every 30 minutes or so."

    def add_arguments(self, parser):
        parser.add_argument("--no-email", action="store_true")

    def handle(self, *args, no_email=False, **opts):
        result = evaluate()
        opened = result["opened"]
        self.stdout.write(f"opened {len(opened)}, refreshed {result['refreshed']}, resolved {result['resolved']}")
        if no_email or not opened:
            return
        by_client = {}
        for a in opened:
            by_client.setdefault(a.outlet.brand.client_id, []).append(a)
        for client_id, alerts in by_client.items():
            to = list(AlertRecipient.objects.filter(client_id=client_id, channel="email", is_active=True, performance_alerts=True)
                      .values_list("address", flat=True))
            if not to:
                continue
            lines = "\n".join(f"[{a.severity.upper()}] {a.outlet.display_name}: {a.title}\n    {a.detail}" for a in alerts)
            try:
                send_mail(f"Codeonto: {len(alerts)} new alert(s)", lines, None, to, fail_silently=False)
                for a in alerts:
                    a.notified = True
                    a.save(update_fields=["notified"])
            except Exception as e:  # mail not configured yet: the alerts still show in the dashboard
                self.stderr.write(f"email not sent: {e}")
