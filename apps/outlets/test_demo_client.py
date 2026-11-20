"""The sample client: made with made-up data, flagged as a demo, safe for the collector, and removable."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.metrics.models import MetricDaily
from apps.outlets.models import BrandOutlet, Client, SwiggyOutlet, ZomatoOutlet
from apps.payouts.models import PayoutCycle
from apps.reviews.models import Review


def run(*args):
    call_command("seed_demo_client", *args, stdout=StringIO())


class DemoClientTests(TestCase):
    def test_it_makes_a_flagged_client_with_inactive_fake_platform_ids_and_data(self):
        run("--outlets", "6", "--days", "10")
        client = Client.objects.get(name="Demo Client 1")
        self.assertTrue(client.is_demo)
        self.assertEqual(BrandOutlet.objects.filter(brand__client=client).count(), 6)
        # fake ids that no collector will fetch: inactive catalog rows with a DEMO prefix
        self.assertFalse(ZomatoOutlet.objects.filter(res_id__startswith="DEMO-Z-", is_active=True).exists())
        self.assertFalse(SwiggyOutlet.objects.filter(swiggy_id__startswith="DEMO-S-", is_active=True).exists())
        self.assertTrue(MetricDaily.objects.filter(outlet__brand__client=client).exists())
        self.assertTrue(Review.objects.filter(outlet__brand__client=client).exists())
        cycle = PayoutCycle.objects.filter(outlet__brand__client=client).first()
        self.assertAlmostEqual(float(sum(s["value"] for s in cycle.breakdown)), float(cycle.expected_payout or cycle.net_payout), delta=0.05 + abs(float(cycle.discrepancy or 0)))

    def test_it_refuses_to_run_twice_and_remove_takes_everything_away(self):
        run("--outlets", "3", "--days", "5")
        with self.assertRaises(Exception):
            run("--outlets", "3", "--days", "5")
        run("--remove")
        self.assertFalse(Client.objects.filter(name="Demo Client 1").exists())
        self.assertFalse(ZomatoOutlet.objects.filter(res_id__startswith="DEMO-Z-").exists())
        self.assertFalse(MetricDaily.objects.exists() and MetricDaily.objects.filter(outlet__brand__client__is_demo=True).exists())

    def test_reset_makes_it_again(self):
        run("--outlets", "3", "--days", "5")
        run("--outlets", "4", "--days", "5", "--reset")
        self.assertEqual(BrandOutlet.objects.filter(brand__client__name="Demo Client 1").count(), 4)

    def test_a_demo_login_is_made_only_when_asked_and_needs_a_password(self):
        with self.assertRaises(Exception):
            run("--outlets", "2", "--days", "3", "--login", "demo.viewer")
        run("--outlets", "2", "--days", "3", "--login", "demo.viewer", "--password", "x-test-only")
        from django.contrib.auth import get_user_model
        self.assertTrue(get_user_model().objects.filter(username="demo.viewer", is_staff=False).exists())

    def test_the_demo_login_is_a_read_only_viewer_that_sees_only_the_sample_client(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        from apps.outlets.models import Brand

        other = Client.objects.create(name="A real client")
        Brand.objects.create(client=other, name="Real Brand", industry=Brand.objects.model._meta.get_field("industry").related_model.objects.get(code="restaurant"))
        run("--outlets", "3", "--days", "3", "--login", "client1", "--password", "1234")
        user = get_user_model().objects.get(username="client1")
        self.assertEqual(user.client_membership.role, "viewer")
        c = APIClient(HTTP_HOST="localhost")
        self.assertTrue(c.login(username="client1", password="1234"))
        names = {b["name"] for b in c.get("/api/brands").json()}
        self.assertEqual(names, {"Sample Kitchen Co"})
