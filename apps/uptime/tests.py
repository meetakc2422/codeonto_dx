"""Store uptime numbers and who can see them."""

from datetime import date, datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.utils.timezone import now as current_time
from rest_framework.test import APIClient

from apps.alerts.rules import store_offline
from apps.assistant.db import scope_value
from apps.masters.models import Industry, Platform
from apps.outlets.models import Brand, BrandOutlet, Client, ClientUser, ZomatoOutlet

from .models import OfflineEpisode, UptimeDaily

User = get_user_model()
NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
SECRET = "test-scope-secret"


class UptimeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        industry, zomato = Industry.objects.first(), Platform.objects.get(code="zomato")
        client = Client.objects.create(name="Acme")
        cls.brand = Brand.objects.create(client=client, name="Brand", industry=industry)
        cls.other_brand = Brand.objects.create(client=client, name="Other brand", industry=industry)
        cls.a = BrandOutlet.objects.create(brand=cls.brand, outlet_name="A")
        cls.b = BrandOutlet.objects.create(brand=cls.brand, outlet_name="B")
        cls.today = date(2026, 11, 1)
        cls.owner = User.objects.create_user("owner", password="x")
        ClientUser.objects.create(user=cls.owner, client=client, role="admin")
        cls.manager = User.objects.create_user("manager", password="x")
        ClientUser.objects.create(user=cls.manager, client=client, role="manager").outlets.set([cls.a])
        UptimeDaily.objects.create(outlet=cls.a, platform=zomato, day=cls.today, checks=100, online_checks=90)
        UptimeDaily.objects.create(outlet=cls.b, platform=zomato, day=cls.today, checks=100, online_checks=50)
        UptimeDaily.objects.create(outlet=cls.a, platform=zomato, day=cls.today - timedelta(days=60), checks=100, online_checks=0)
        def episode(outlet, active, minutes, day=cls.today):
            return OfflineEpisode.objects.create(outlet=outlet, platform=zomato, is_active=active, log_date=day, first_detected_at=NOW,
                                                 last_detected_at=NOW, downtime_minutes=minutes, restored_at=None if active else NOW)
        episode(cls.a, False, 10)
        episode(cls.a, False, 30)
        cls.b_open = episode(cls.b, True, 60, cls.today - timedelta(days=45))  # started before the period, still going

    def summary(self, user, **q):
        c = APIClient()
        c.force_login(user)
        return c.get(f"/api/brands/{self.brand.pk}/uptime/summary", {"start": self.today, "end": self.today, **q}).json()

    def test_owner_totals(self):
        s = self.summary(self.owner)
        self.assertEqual(s["uptime_pct"], 70.0)  # 140 online of 200 checks; the old day is outside the period
        self.assertEqual((s["offline_now"], s["events"], s["avg_downtime"], s["total_downtime"]), (1, 3, 20, 100))
        self.assertEqual(s["trend"], [{"date": "2026-11-01", "value": 70.0}])
        self.assertEqual([o["name"] for o in s["outlets"]], ["B", "A"])  # offline first
        self.assertIsNotNone(s["outlets"][0]["offline_since"])

    def test_outlets_are_named_by_area_and_id(self):
        zomato = ZomatoOutlet.objects.create(res_id="z9", name="Brand", client=self.brand.client)
        BrandOutlet.objects.filter(pk=self.a.pk).update(outlet_name="Brand", area="Rohini", zomato=zomato)
        s = self.summary(self.owner)
        a = next(o for o in s["outlets"] if o["id"] == self.a.pk)
        self.assertEqual((a["name"], a["zomato_id"]), ("Rohini", "z9"))

    def test_outlet_filter(self):
        s = self.summary(self.owner, outlet_id=self.a.pk)
        self.assertEqual((s["uptime_pct"], s["offline_now"], s["events"]), (90.0, 0, 2))

    def test_no_checks_means_unknown_not_zero(self):
        s = self.summary(self.owner, platform="swiggy")
        self.assertIsNone(s["uptime_pct"])
        self.assertEqual(s["outlets"], [])

    def test_manager_sees_only_assigned_outlets(self):
        s = self.summary(self.manager)
        self.assertEqual((s["uptime_pct"], s["offline_now"], s["events"]), (90.0, 0, 2))
        self.assertEqual([o["name"] for o in s["outlets"]], ["A"])
        self.assertEqual(self.summary(self.manager, outlet_id=self.b.pk)["uptime_pct"], None)
        c = APIClient()
        c.force_login(self.manager)
        rows = c.get(f"/api/brands/{self.brand.pk}/uptime/episodes", {"start": self.today, "end": self.today}).json()
        self.assertEqual({r["outlet_id"] for r in rows}, {self.a.pk})
        self.assertEqual(c.get(f"/api/brands/{self.other_brand.pk}/uptime/summary").status_code, 404)

    def changes(self, user, **q):
        c = APIClient()
        c.force_login(user)
        return c.get("/api/uptime/changes", q).json()

    def test_changes_cover_every_brand_the_login_can_see(self):
        far = BrandOutlet.objects.create(brand=self.other_brand, outlet_name="Brand", area="Rohini")
        episode = OfflineEpisode.objects.create(outlet=far, platform_id="zomato", log_date=self.today, first_detected_at=NOW, last_detected_at=NOW)
        rows = self.changes(self.owner)["offline"]
        self.assertEqual({r["id"] for r in rows}, {self.b_open.pk, episode.pk})
        row = next(r for r in rows if r["id"] == episode.pk)
        self.assertEqual((row["outlet"], row["brand"], row["platform"]), ("Rohini", "Other brand", "Zomato"))
        self.assertEqual({r["id"] for r in self.changes(self.owner, brand_id=self.brand.pk)["offline"]}, {self.b_open.pk})

    def back_episode(self, outlet, restored, last_seen_offline):
        return OfflineEpisode.objects.create(outlet=outlet, platform_id="zomato", is_active=False, log_date=self.today, first_detected_at=restored - timedelta(minutes=30),
                                             last_detected_at=last_seen_offline, restored_at=restored, downtime_minutes=30)

    def test_back_online_lists_recent_returns_only(self):
        now = current_time()
        recent = self.back_episode(self.a, now - timedelta(minutes=5), now - timedelta(minutes=10))
        self.back_episode(self.a, now - timedelta(hours=3), now - timedelta(hours=3, minutes=5))  # too old
        self.back_episode(self.b, now - timedelta(minutes=5), now - timedelta(minutes=5))  # collector stopped: not seen coming back
        rows = self.changes(self.owner)["back"]
        self.assertEqual([r["id"] for r in rows], [recent.pk])
        self.assertEqual(rows[0]["downtime_minutes"], 30)

    def test_changes_respect_outlet_limit_and_client(self):
        now = current_time()
        mine = self.back_episode(self.a, now - timedelta(minutes=5), now - timedelta(minutes=10))
        self.back_episode(self.b, now - timedelta(minutes=5), now - timedelta(minutes=10))
        data = self.changes(self.manager)
        self.assertEqual((data["offline"], [r["id"] for r in data["back"]]), ([], [mine.pk]))
        stranger = User.objects.create_user("stranger", password="x")
        ClientUser.objects.create(user=stranger, client=Client.objects.create(name="Stranger"), role="admin")
        self.assertEqual(self.changes(stranger), {"offline": [], "back": []})
        self.assertEqual(self.changes(stranger, brand_id=self.brand.pk), {"offline": [], "back": []})

    def test_ended_episode_leaves_offline_list_and_login_is_required(self):
        OfflineEpisode.objects.filter(pk=self.b_open.pk).update(is_active=False, restored_at=NOW)
        self.assertEqual(self.changes(self.owner)["offline"], [])
        self.assertEqual(APIClient().get("/api/uptime/changes").status_code, 401)

    def test_episode_status_filter(self):
        c = APIClient()
        c.force_login(self.owner)
        url = f"/api/brands/{self.brand.pk}/uptime/episodes"
        q = {"start": self.today, "end": self.today}
        self.assertEqual([r["outlet_id"] for r in c.get(url, {**q, "status": "active"}).json()], [self.b.pk])
        self.assertEqual(len(c.get(url, {**q, "status": "restored"}).json()), 2)

    def test_alert_opens_after_15_minutes_offline(self):
        self.assertIsNotNone(store_offline(self.b))
        self.assertIsNone(store_offline(self.a))
        OfflineEpisode.objects.filter(pk=self.b_open.pk).update(downtime_minutes=5)
        self.assertIsNone(store_offline(self.b))

    @override_settings(ASSISTANT_SCOPE_SECRET=SECRET)
    def test_assistant_views_respect_outlet_limit(self):
        with connection.cursor() as cur:
            cur.execute("DELETE FROM assistant.scope_secret")
            cur.execute("INSERT INTO assistant.scope_secret (secret) VALUES (%s)", [SECRET])
            cur.execute("SELECT set_config('app.scope', %s, true)", [scope_value(self.brand.client_id, [self.a.pk])])
            for view in ("offline_episodes", "uptime_daily"):
                cur.execute(f"SELECT DISTINCT outlet_id FROM assistant.{view}")
                self.assertEqual([r[0] for r in cur.fetchall()], [self.a.pk], view)
            cur.execute("SELECT set_config('app.scope', %s, true)", ["forged:nope"])
            cur.execute("SELECT count(*) FROM assistant.offline_episodes")
            self.assertEqual(cur.fetchone()[0], 0)
