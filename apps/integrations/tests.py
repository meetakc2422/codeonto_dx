from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.outlets.models import PlatformAccount

from .models import SessionRefresh

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
