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


from django.core.cache import cache  # noqa: E402
from django.test import override_settings  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from apps.metrics.http_cache import cached_get  # noqa: E402


@override_settings(RESPONSE_CACHE=True, CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "resp-cache-test"}})
class ResponseCacheTests(TestCase):
    """The short shared cache on heavy read-only calls keeps an answer per person and per exact address."""

    def setUp(self):
        cache.clear()
        self.calls = 0
        from rest_framework.decorators import api_view
        from rest_framework.response import Response

        @api_view(["GET"])
        @cached_get(60)
        def view(request):
            self.calls += 1
            return Response({"n": self.calls})
        self.view = view

    def get(self, user, path="/x"):
        from rest_framework.test import APIRequestFactory, force_authenticate
        req = APIRequestFactory().get(path)
        force_authenticate(req, user=user)
        return self.view(req).data

    def test_same_person_same_address_is_answered_from_the_cache(self):
        user = get_user_model().objects.create_user("a", password="x")
        self.assertEqual(self.get(user)["n"], 1)
        self.assertEqual(self.get(user)["n"], 1)
        self.assertEqual(self.calls, 1)

    def test_another_person_or_another_address_is_never_given_that_answer(self):
        a = get_user_model().objects.create_user("a", password="x")
        b = get_user_model().objects.create_user("b", password="x")
        self.get(a)
        self.assertEqual(self.get(b)["n"], 2)
        self.assertEqual(self.get(a, "/x?outlet_id=5")["n"], 3)
