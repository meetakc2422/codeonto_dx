from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.masters.models import Industry
from apps.outlets.models import Brand, Client


class TimeEndpointsTests(TestCase):
    def test_it_times_every_call_and_reads_only(self):
        brand = Brand.objects.create(client=Client.objects.create(name="T"), name="Timing Brand", industry=Industry.objects.first())
        get_user_model().objects.create_user("ops", password="x", is_staff=True)
        out = StringIO()
        call_command("time_endpoints", "--brand", "Timing Brand", stdout=out)
        text = out.getvalue()
        self.assertIn("kpis", text)
        self.assertIn("Total", text)
        self.assertEqual(brand.outlets.count(), 0)  # nothing was written

    def test_it_needs_a_brand_and_a_staff_login(self):
        with self.assertRaises(CommandError):
            call_command("time_endpoints", "--brand", "No Such Brand", stdout=StringIO())
