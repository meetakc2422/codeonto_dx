"""Which sections the report holds, and in what order: the Export page's drag-and-drop sends the list as ?modules=a,b,c."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.masters.models import Industry
from apps.outlets.models import Brand, Client

ALL = ["overview", "recommendations", "overall", "growth", "ads", "reputation", "complaints", "payouts", "months"]


class ReportModulesTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(client=Client.objects.create(name="T"), name="Report Brand", industry=Industry.objects.first())
        self.api = APIClient()
        self.api.force_authenticate(get_user_model().objects.create_user("ops", password="x", is_staff=True))

    def order(self, qs):
        r = self.api.get(f"/api/brands/{self.brand.id}/report?start=2026-11-10&end=2026-11-16{qs}")
        self.assertEqual(r.status_code, 200)
        return r.json()["module_order"]

    def test_no_modules_param_means_every_section(self):
        self.assertEqual(self.order(""), ALL)

    def test_the_order_asked_for_is_the_order_kept(self):
        self.assertEqual(self.order("&modules=payouts,overall,ads"), ["payouts", "overall", "ads"])

    def test_an_empty_list_means_none_not_all(self):
        self.assertEqual(self.order("&modules="), [])

    def test_unknown_and_repeated_names_are_dropped(self):
        self.assertEqual(self.order("&modules=ads,nonsense,ads,growth"), ["ads", "growth"])
