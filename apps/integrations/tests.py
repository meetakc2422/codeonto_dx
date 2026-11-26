from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.masters.models import Industry
from apps.outlets.models import Brand, BrandOutlet, Client, PlatformAccount

from .models import BackfillRequest, SessionRefresh

User = get_user_model()


class SessionRefreshTests(TestCase):
    def setUp(self):
        self.account = PlatformAccount.objects.create(platform_id="zomato", label="main", credentials_ref="db:session")
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.client_user = User.objects.create_user("owner", password="x")

    def api(self, user):
        c = APIClient()
        c.force_login(user)
        return c

    def refresh(self, user):
        return self.api(user).post(f"/api/staff/sessions/{self.account.id}/refresh", {}, format="json")

    def test_staff_queue_once_and_second_click_is_refused(self):
        first = self.refresh(self.staff)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["refresh"]["status"], "queued")
        second = self.refresh(self.staff)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["refresh"]["id"], first.json()["refresh"]["id"])
        self.assertEqual(SessionRefresh.objects.filter(account=self.account).count(), 1)

    def test_clients_cannot_refresh(self):
        self.assertEqual(self.refresh(self.client_user).status_code, 403)
        self.assertFalse(SessionRefresh.objects.exists())

    def test_a_finished_refresh_allows_a_new_one(self):
        SessionRefresh.objects.create(account=self.account, requested_by="staff", status=SessionRefresh.DONE)
        self.assertEqual(self.refresh(self.staff).status_code, 201)

    def test_stale_requests_fail_and_unlock_the_button(self):
        r = SessionRefresh.objects.create(account=self.account, requested_by="staff")
        SessionRefresh.objects.filter(pk=r.pk).update(requested_at=timezone.now() - timedelta(minutes=20))
        self.assertEqual(self.refresh(self.staff).status_code, 201)
        r.refresh_from_db()
        self.assertEqual(r.status, SessionRefresh.FAILED)
        self.assertIn("worker", r.error)

    def test_sessions_page_shows_status_and_latest_refresh(self):
        self.account.session_expired_at, self.account.session_error = timezone.now(), "zomato reviews: 3 refusals in a row"
        self.account.save()
        self.refresh(self.staff)
        row = next(a for a in self.api(self.staff).get("/api/staff/sessions").json()["accounts"] if a["id"] == self.account.id)
        self.assertIsNotNone(row["expired_at"])
        self.assertEqual(row["refresh"]["status"], "queued")
        self.assertEqual(row["refresh"]["requested_by"], "staff")

    def test_banner_lists_expired_logins_for_staff_only(self):
        self.account.session_expired_at = timezone.now()
        self.account.save()
        self.assertEqual([a["label"] for a in self.api(self.staff).get("/api/staff/sessions/alerts").json()["expired"]], ["main"])
        self.assertEqual(self.api(self.client_user).get("/api/staff/sessions/alerts").json()["expired"], [])

    def test_pasting_a_merchant_session_clears_expired(self):
        self.account.session_expired_at = timezone.now()
        self.account.save()
        resp = self.api(self.staff).post("/api/staff/sessions", {"platform": "zomato", "kind": "merchant", "account_id": self.account.id,
                                                                  "text": '{"PHPSESSID": "abc", "zat": "x"}'}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.account.refresh_from_db()
        self.assertIsNone(self.account.session_expired_at)


class BackfillRequestTests(TestCase):
    def setUp(self):
        client = Client.objects.create(name="Acme")
        industry = Industry.objects.first() or Industry.objects.create(code="restaurant", name="Restaurants")
        self.brand = Brand.objects.create(client=client, name="Acme Burgers", industry=industry)
        self.other = Brand.objects.create(client=client, name="Acme Pizza", industry=industry)
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.owner = User.objects.create_user("owner", password="x")

    def api(self, user):
        c = APIClient()
        c.force_login(user)
        return c

    def post(self, user, brand=None, days=90):
        return self.api(user).post(f"/api/brands/{(brand or self.brand).id}/backfill", {"days": days}, format="json")

    def map_outlet(self, brand=None):
        from apps.outlets.models import ZomatoOutlet
        z = ZomatoOutlet.objects.create(res_id="111", name="Z")
        return BrandOutlet.objects.create(brand=brand or self.brand, outlet_name="Main", zomato=z)

    def test_only_staff_can_ask_or_look(self):
        self.map_outlet()
        self.assertEqual(self.post(self.owner).status_code, 403)
        self.assertEqual(self.api(self.owner).get(f"/api/brands/{self.brand.id}/backfill").status_code, 403)

    def test_needs_a_mapped_outlet_and_a_valid_period(self):
        self.assertEqual(self.post(self.staff).status_code, 400)  # nothing mapped yet
        self.map_outlet()
        self.assertEqual(self.post(self.staff, days=7).status_code, 400)
        self.assertEqual(self.post(self.staff, days=90).status_code, 201)

    def test_one_at_a_time_per_brand_and_a_new_one_after_it_finishes(self):
        self.map_outlet()
        first = self.post(self.staff)
        self.assertEqual(first.status_code, 201)
        second = self.post(self.staff)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["backfill"]["id"], first.json()["backfill"]["id"])
        BackfillRequest.objects.filter(pk=first.json()["backfill"]["id"]).update(status=BackfillRequest.DONE)
        self.assertEqual(self.post(self.staff).status_code, 201)

    def test_queue_position_counts_the_one_running_and_older_queued(self):
        self.map_outlet()
        BackfillRequest.objects.create(brand=self.other, requested_by="x", status=BackfillRequest.RUNNING)
        r = self.post(self.staff)
        self.assertEqual(r.json()["backfill"]["ahead"], 1)
        self.assertEqual(self.api(self.staff).get(f"/api/brands/{self.brand.id}/backfill").json()["backfill"]["status"], "queued")

    def test_a_silent_worker_does_not_lock_the_button_forever(self):
        self.map_outlet()
        r = BackfillRequest.objects.create(brand=self.brand, requested_by="staff", status=BackfillRequest.RUNNING)
        BackfillRequest.objects.filter(pk=r.pk).update(updated_at=timezone.now() - timedelta(minutes=60))
        got = self.api(self.staff).get(f"/api/brands/{self.brand.id}/backfill").json()["backfill"]
        self.assertEqual(got["status"], "failed")
        self.assertEqual(self.post(self.staff).status_code, 201)
