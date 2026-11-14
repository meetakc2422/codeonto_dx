"""Who can see and change what: owners, outlet managers, viewers and other clients."""

import re
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.alerts.models import Alert
from apps.assistant.db import scope_value
from apps.listings.models import ListingProfile
from apps.masters.models import Industry, Kpi, Platform
from apps.metrics.models import MetricDaily
from apps.reviews.models import Review
from apps.stockouts.models import StockOut

from .models import Brand, BrandOutlet, Client, ClientUser, ZomatoOutlet

User = get_user_model()
PASSWORD = "Strong-pass-4821!"
SECRET = "test-scope-secret"


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.industry = Industry.objects.first()
        cls.platform = Platform.objects.get(code="zomato")
        cls.kpi = Kpi.objects.filter(aggregation="sum").first()
        cls.acme, cls.other = Client.objects.create(name="Acme"), Client.objects.create(name="Other")
        cls.brand_a = Brand.objects.create(client=cls.acme, name="Brand A", industry=cls.industry)
        cls.brand_b = Brand.objects.create(client=cls.acme, name="Brand B", industry=cls.industry)
        cls.brand_z = Brand.objects.create(client=cls.other, name="Brand Z", industry=cls.industry)
        cls.mine = BrandOutlet.objects.create(brand=cls.brand_a, outlet_name="Mine")
        cls.sibling = BrandOutlet.objects.create(brand=cls.brand_a, outlet_name="Sibling")
        cls.far = BrandOutlet.objects.create(brand=cls.brand_b, outlet_name="Far")
        cls.foreign = BrandOutlet.objects.create(brand=cls.brand_z, outlet_name="Foreign")
        cls.owner = cls.login("owner", cls.acme, "admin")
        cls.manager = cls.login("manager", cls.acme, "manager", [cls.mine])
        cls.viewer = cls.login("viewer", cls.acme, "viewer")
        cls.other_owner = cls.login("other_owner", cls.other, "admin")
        cls.today = date.today()
        for value, o in enumerate((cls.mine, cls.sibling, cls.far, cls.foreign), start=1):
            cls.seed(o, value)

    @classmethod
    def login(cls, username, client, role, outlets=()):
        user = User.objects.create_user(username, password=PASSWORD)
        ClientUser.objects.create(user=user, client=client, role=role).outlets.set(outlets)
        return user

    @classmethod
    def seed(cls, o, value):
        now = timezone.now()
        Review.objects.create(outlet=o, platform=cls.platform, external_review_id=f"r{o.pk}", body=o.outlet_name, rating=4, reviewed_at=now)
        MetricDaily.objects.create(outlet=o, platform=cls.platform, kpi=cls.kpi, metric_date=cls.today, value=value)
        StockOut.objects.create(outlet=o, platform=cls.platform, item_name=f"Item {o.outlet_name}", category="Mains", log_date=cls.today,
                                first_detected_at=now, last_detected_at=now)
        Alert.objects.create(outlet=o, kind="test", title=o.outlet_name)
        ListingProfile.objects.create(outlet=o, platform=cls.platform, title=o.outlet_name, fetched_at=now)

    def as_user(self, user):
        c = APIClient()
        c.force_login(user)
        return c


class ManagerDataTests(Base):
    def setUp(self):
        self.c = self.as_user(self.manager)

    def brand_url(self, tail, brand=None):
        return f"/api/brands/{(brand or self.brand_a).pk}/{tail}"

    def test_sees_only_brands_with_assigned_outlets(self):
        self.assertEqual([b["name"] for b in self.c.get("/api/brands").json()], ["Brand A"])
        for tail in ("config", "outlets", "reviews", "kpis", "alerts", "listings", "stock-outs"):
            self.assertEqual(self.c.get(self.brand_url(tail, self.brand_b)).status_code, 404, tail)
            self.assertEqual(self.c.get(self.brand_url(tail, self.brand_z)).status_code, 404, tail)

    def test_every_list_contains_only_assigned_outlets(self):
        for tail in ("reviews", "alerts", "listings", "stock-outs"):
            rows = self.c.get(self.brand_url(tail)).json()
            self.assertEqual({r["outlet_id"] for r in rows}, {self.mine.pk}, tail)
        self.assertEqual([o["id"] for o in self.c.get(self.brand_url("outlets")).json()["outlets"]], [self.mine.pk])

    def test_asking_for_another_outlet_returns_nothing(self):
        q = {"outlet_id": self.sibling.pk}
        for tail in ("reviews", "alerts", "listings", "stock-outs"):
            self.assertEqual(self.c.get(self.brand_url(tail), q).json(), [], tail)
        self.assertEqual(self.c.get(self.brand_url("reviews/summary"), q).json()["total"], 0)
        self.assertEqual(self.c.get(self.brand_url("stock-outs/summary"), q).json()["events"], 0)
        self.assertEqual(self.c.get(self.brand_url("kpis"), q).json()["kpis"], [])
        self.assertEqual(self.c.get(self.brand_url(f"kpis/{self.kpi.code}/trend"), q).json(), [])

    def test_totals_count_only_assigned_outlets(self):
        self.assertEqual(self.c.get(self.brand_url("reviews/summary")).json()["total"], 1)
        summary = self.c.get(self.brand_url("stock-outs/summary")).json()
        self.assertEqual((summary["events"], [r["outlet"] for r in summary["by_outlet"]]), (1, ["Mine"]))
        kpi = next(k for k in self.c.get(self.brand_url("kpis")).json()["kpis"] if k["code"] == self.kpi.code)
        self.assertEqual(kpi["value"], 1.0)  # Mine's 1, not Sibling's 2 added on top
        trend = self.c.get(self.brand_url(f"kpis/{self.kpi.code}/trend")).json()
        self.assertEqual([r["value"] for r in trend], [1.0])
        board = self.c.get(self.brand_url(f"leaderboard/{self.kpi.code}")).json()
        self.assertEqual([r["id"] for r in board], [self.mine.pk])

    def test_export_contains_only_assigned_outlets(self):
        from openpyxl import load_workbook

        res = self.c.get(self.brand_url("stock-outs/export"))
        book = load_workbook(BytesIO(res.content))
        # the export is an insights workbook now: one row per dish and per outlet, only for the assigned outlets
        self.assertEqual([r[0] for r in book["By dish"].iter_rows(min_row=2, values_only=True)], ["Item Mine"])
        self.assertEqual(len(list(book["By outlet"].iter_rows(min_row=2, values_only=True))), 1)

    def test_config_platforms_come_from_assigned_outlets_only(self):
        self.assertEqual(self.c.get(self.brand_url("config")).json()["connected_platforms"], [])
        owner = self.as_user(self.owner)
        self.assertEqual(owner.get(self.brand_url("config")).json()["connected_platforms"], [])
        zomato = ZomatoOutlet.objects.create(res_id="z1", name="Sibling", client=self.acme)
        BrandOutlet.objects.filter(pk=self.sibling.pk).update(zomato=zomato)
        self.assertEqual(self.c.get(self.brand_url("config")).json()["connected_platforms"], [])
        self.assertEqual([p["code"] for p in owner.get(self.brand_url("config")).json()["connected_platforms"]], ["zomato"])

    def test_replies_only_on_assigned_outlets(self):
        mine = Review.objects.get(outlet=self.mine)
        self.assertEqual(self.c.post(f"/api/reviews/{mine.pk}/replies", {"body": "Thanks"}, format="json").status_code, 201)
        for o in (self.sibling, self.far, self.foreign):
            review = Review.objects.get(outlet=o)
            self.assertEqual(self.c.post(f"/api/reviews/{review.pk}/replies", {"body": "x"}, format="json").status_code, 404, o)

    def test_cannot_change_setup_or_read_client_wide_data(self):
        self.assertEqual(self.c.post("/api/brands", {"name": "New", "industry_code": self.industry.code}, format="json").status_code, 403)
        self.assertEqual(self.c.patch(self.brand_url("").rstrip("/"), {"name": "Renamed"}, format="json").status_code, 403)
        self.assertEqual(self.c.put(self.brand_url("outlets"), {"outlets": []}, format="json").status_code, 403)
        self.assertEqual(self.c.post(self.brand_url("outlets/import"), {"csv": "a"}, format="json").status_code, 403)
        self.assertEqual(self.c.post(self.brand_url("rollups/reviews")).status_code, 403)
        self.assertEqual(self.c.get("/api/catalog/zomato").status_code, 403)
        self.assertEqual(self.c.get(f"/api/clients/{self.acme.pk}/google").status_code, 403)
        self.assertEqual(self.c.get("/api/google/connect", {"client_id": self.acme.pk}).status_code, 403)
        self.assertEqual(self.c.get(f"/api/clients/{self.acme.pk}/team").status_code, 403)

    def test_no_assignments_sees_nothing(self):
        self.manager.client_membership.outlets.clear()
        self.assertEqual(self.c.get("/api/brands").json(), [])
        self.assertEqual(self.c.get(self.brand_url("reviews")).status_code, 404)

    def test_assignment_to_another_clients_outlet_gives_nothing(self):
        self.manager.client_membership.outlets.set([self.foreign])
        self.assertEqual(self.c.get("/api/brands").json(), [])
        self.assertEqual(self.c.get(self.brand_url("reviews", self.brand_z)).status_code, 404)


class OtherRolesTests(Base):
    def test_owner_sees_all_their_brands_and_outlets_but_no_other_client(self):
        c = self.as_user(self.owner)
        self.assertEqual({b["name"] for b in c.get("/api/brands").json()}, {"Brand A", "Brand B"})
        ids = {r["outlet_id"] for r in c.get(f"/api/brands/{self.brand_a.pk}/reviews").json()}
        self.assertEqual(ids, {self.mine.pk, self.sibling.pk})
        kpi = next(k for k in c.get(f"/api/brands/{self.brand_a.pk}/kpis").json()["kpis"] if k["code"] == self.kpi.code)
        self.assertEqual(kpi["value"], 3.0)
        self.assertEqual(c.get(f"/api/brands/{self.brand_z.pk}/reviews").status_code, 404)

    def test_owner_can_create_brands(self):
        res = self.as_user(self.owner).post("/api/brands", {"name": "New", "industry_code": self.industry.code}, format="json")
        self.assertEqual(res.status_code, 201)

    def test_viewer_reads_whole_client_but_changes_nothing(self):
        c = self.as_user(self.viewer)
        self.assertEqual({b["name"] for b in c.get("/api/brands").json()}, {"Brand A", "Brand B"})
        self.assertEqual(len(c.get(f"/api/brands/{self.brand_a.pk}/reviews").json()), 2)
        review = Review.objects.get(outlet=self.mine)
        self.assertEqual(c.post(f"/api/reviews/{review.pk}/replies", {"body": "x"}, format="json").status_code, 403)
        self.assertEqual(c.get(f"/api/clients/{self.acme.pk}/team").status_code, 403)

    def test_me_tells_the_dashboard_what_to_show(self):
        me = self.as_user(self.manager).get("/api/auth/me").json()
        self.assertEqual((me["can_edit"], me["can_manage"], me["outlet_limited"]), (True, False, True))
        me = self.as_user(self.owner).get("/api/auth/me").json()
        self.assertEqual((me["can_edit"], me["can_manage"], me["outlet_limited"]), (True, True, False))


class TeamTests(Base):
    def setUp(self):
        self.c = self.as_user(self.owner)
        self.url = f"/api/clients/{self.acme.pk}/team"

    def body(self, **over):
        return {"username": "new_mgr", "name": "New Manager", "password": PASSWORD, "role": "manager",
                "outlet_ids": [self.sibling.pk], **over}

    def test_owner_creates_manager_who_can_log_in_and_sees_only_that_outlet(self):
        self.assertEqual(self.c.post(self.url, self.body(), format="json").status_code, 201)
        fresh = APIClient()
        self.assertEqual(fresh.post("/api/auth/login", {"username": "new_mgr", "password": PASSWORD}, format="json").status_code, 200)
        rows = fresh.get(f"/api/brands/{self.brand_a.pk}/reviews").json()
        self.assertEqual({r["outlet_id"] for r in rows}, {self.sibling.pk})

    def test_list_shows_own_client_only_with_outlets_across_brands(self):
        data = self.c.get(self.url).json()
        self.assertEqual({u["username"] for u in data["users"]}, {"owner", "manager", "viewer"})
        self.assertEqual({b["name"] for b in data["brands"]}, {"Brand A", "Brand B"})
        self.assertEqual(next(u for u in data["users"] if u["username"] == "manager")["outlet_ids"], [self.mine.pk])

    def test_outlet_picker_names_outlets_by_area(self):
        BrandOutlet.objects.filter(pk=self.mine.pk).update(area="Rohini")
        outlets = {o["id"]: o["name"] for b in self.c.get(self.url).json()["brands"] for o in b["outlets"]}
        self.assertEqual((outlets[self.mine.pk], outlets[self.sibling.pk]), ("Rohini", "Sibling"))

    def test_manager_needs_outlets_from_this_client(self):
        self.assertEqual(self.c.post(self.url, self.body(outlet_ids=[]), format="json").status_code, 400)
        self.assertEqual(self.c.post(self.url, self.body(outlet_ids=[self.foreign.pk]), format="json").status_code, 400)
        self.assertEqual(self.c.post(self.url, self.body(outlet_ids="1"), format="json").status_code, 400)
        self.assertFalse(User.objects.filter(username="new_mgr").exists())

    def test_weak_password_and_taken_username_rejected(self):
        self.assertEqual(self.c.post(self.url, self.body(password="12345"), format="json").status_code, 400)
        self.assertEqual(self.c.post(self.url, self.body(username="MANAGER"), format="json").status_code, 400)

    def test_can_move_manager_across_brands(self):
        res = self.c.patch(f"{self.url}/{self.manager.pk}", {"outlet_ids": [self.mine.pk, self.far.pk]}, format="json")
        self.assertEqual(res.status_code, 200)
        m = self.as_user(self.manager)
        self.assertEqual({b["name"] for b in m.get("/api/brands").json()}, {"Brand A", "Brand B"})

    def test_removing_all_outlets_from_manager_is_rejected(self):
        res = self.c.patch(f"{self.url}/{self.manager.pk}", {"outlet_ids": []}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_viewer_cannot_become_manager_without_outlets(self):
        res = self.c.patch(f"{self.url}/{self.viewer.pk}", {"role": "manager"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.viewer.client_membership.refresh_from_db()
        self.assertEqual(self.viewer.client_membership.role, "viewer")

    def test_failed_password_changes_nothing(self):
        res = self.c.patch(f"{self.url}/{self.manager.pk}", {"role": "viewer", "password": "12345"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.manager.client_membership.refresh_from_db()
        self.assertEqual(self.manager.client_membership.role, "manager")

    def test_disable_signs_out_and_password_reset_works(self):
        m = self.as_user(self.manager)
        self.assertEqual(self.c.patch(f"{self.url}/{self.manager.pk}", {"is_active": False}, format="json").status_code, 200)
        self.assertEqual(m.get("/api/brands").status_code, 401)
        self.assertEqual(self.c.patch(f"{self.url}/{self.manager.pk}", {"is_active": True, "password": "Another-pass-7395!"}, format="json").status_code, 200)
        self.assertEqual(APIClient().post("/api/auth/login", {"username": "manager", "password": "Another-pass-7395!"}, format="json").status_code, 200)

    def test_owner_cannot_change_own_login_here(self):
        for body in ({"role": "viewer"}, {"is_active": False}, {"password": "Another-pass-7395!"}):
            self.assertEqual(self.c.patch(f"{self.url}/{self.owner.pk}", body, format="json").status_code, 400)

    def test_cannot_reach_another_clients_team(self):
        other_url = f"/api/clients/{self.other.pk}/team"
        self.assertEqual(self.c.get(other_url).status_code, 404)
        self.assertEqual(self.c.post(other_url, self.body(), format="json").status_code, 404)
        self.assertEqual(self.c.patch(f"{other_url}/{self.other_owner.pk}", {"password": PASSWORD}, format="json").status_code, 404)
        self.assertEqual(self.c.patch(f"{self.url}/{self.other_owner.pk}", {"password": PASSWORD}, format="json").status_code, 404)

    def test_owner_cannot_take_over_a_linked_staff_login(self):
        boss = User.objects.create_superuser("boss", password=PASSWORD)
        ClientUser.objects.create(user=boss, client=self.acme, role="viewer")
        res = self.c.patch(f"{self.url}/{boss.pk}", {"password": "Another-pass-7395!"}, format="json")
        self.assertEqual(res.status_code, 403)
        boss.refresh_from_db()
        self.assertTrue(boss.check_password(PASSWORD))

    def test_staff_can_manage_any_clients_team(self):
        staff = self.as_user(User.objects.create_user("ss_staff", password=PASSWORD, is_staff=True))
        url = f"/api/clients/{self.other.pk}/team"
        self.assertEqual(staff.get(url).status_code, 200)
        self.assertEqual(staff.post(url, self.body(role="admin", outlet_ids=[]), format="json").status_code, 201)

    def test_staff_cannot_make_a_manager_without_outlets(self):
        staff = self.as_user(User.objects.create_user("ss_staff", password=PASSWORD, is_staff=True))
        res = staff.patch(f"/api/clients/{self.other.pk}/team/{self.other_owner.pk}", {"role": "manager"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.other_owner.client_membership.refresh_from_db()
        self.assertEqual(self.other_owner.client_membership.role, "admin")
        self.assertEqual(staff.post(f"/api/clients/{self.other.pk}/team", self.body(outlet_ids=[]), format="json").status_code, 400)

    def test_only_staff_can_delete_a_login(self):
        self.assertEqual(self.c.delete(f"{self.url}/{self.viewer.pk}").status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.viewer.pk).exists())
        staff = self.as_user(User.objects.create_user("ss_staff", password=PASSWORD, is_staff=True))
        self.assertEqual(staff.delete(f"{self.url}/{self.viewer.pk}").status_code, 200)
        self.assertFalse(User.objects.filter(pk=self.viewer.pk).exists())

    def test_old_staff_login_endpoints_are_gone(self):
        staff = self.as_user(User.objects.create_user("ss_staff", password=PASSWORD, is_staff=True))
        self.assertEqual(staff.post(f"/api/staff/clients/{self.acme.pk}/users", self.body(), format="json").status_code, 404)
        self.assertEqual(staff.patch(f"/api/staff/clients/{self.acme.pk}/users/{self.manager.pk}", {"role": "viewer"}, format="json").status_code, 404)

    def test_client_page_still_lists_logins(self):
        staff = self.as_user(User.objects.create_user("ss_staff", password=PASSWORD, is_staff=True))
        users = staff.get(f"/api/staff/clients/{self.acme.pk}").json()["user_list"]
        self.assertEqual({u["username"] for u in users}, {"owner", "manager", "viewer"})


@override_settings(ASSISTANT_SCOPE_SECRET=SECRET)
class AssistantScopeTests(Base):
    """The views the assistant reads, under the same signed scope the server sets."""

    VIEWS = ("outlets", "reviews", "metrics_daily", "stock_outs", "listing_profiles", "alerts")

    def setUp(self):
        with connection.cursor() as cur:
            cur.execute("DELETE FROM assistant.scope_secret")
            cur.execute("INSERT INTO assistant.scope_secret (secret) VALUES (%s)", [SECRET])

    def query(self, scope, sql):
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.scope', %s, true)", [scope])
            cur.execute(sql)
            return cur.fetchall()

    def outlets_in(self, scope, view):
        return {r[0] for r in self.query(scope, f"SELECT DISTINCT outlet_id FROM assistant.{view}")}

    def test_manager_scope_shows_only_assigned_outlets(self):
        scope = scope_value(self.acme.pk, [self.mine.pk])
        for view in self.VIEWS:
            self.assertEqual(self.outlets_in(scope, view), {self.mine.pk}, view)
        self.assertEqual([r[0] for r in self.query(scope, "SELECT brand FROM assistant.brands")], ["Brand A"])
        Review.objects.get(outlet=self.sibling).replies.create(body="hidden")
        self.assertEqual(self.query(scope, "SELECT reply_id FROM assistant.review_replies"), [])

    def test_owner_scope_shows_whole_client_and_empty_brands(self):
        Brand.objects.create(client=self.acme, name="Empty", industry=self.industry)
        scope = scope_value(self.acme.pk)
        for view in self.VIEWS:
            self.assertEqual(self.outlets_in(scope, view), {self.mine.pk, self.sibling.pk, self.far.pk}, view)
        self.assertEqual({r[0] for r in self.query(scope, "SELECT brand FROM assistant.brands")}, {"Brand A", "Brand B", "Empty"})

    def test_staff_scope_shows_everything(self):
        self.assertIn(self.foreign.pk, self.outlets_in(scope_value(None), "outlets"))

    def test_no_outlets_shows_nothing(self):
        scope = scope_value(self.acme.pk, [])
        for view in self.VIEWS:
            self.assertEqual(self.outlets_in(scope, view), set(), view)
        self.assertEqual(self.query(scope, "SELECT brand FROM assistant.brands"), [])

    def test_outlet_of_another_client_in_scope_is_ignored(self):
        self.assertEqual(self.outlets_in(scope_value(self.acme.pk, [self.foreign.pk]), "reviews"), set())

    def test_forged_scope_shows_nothing(self):
        real_sig = scope_value(self.acme.pk, [self.mine.pk]).split(":")[1]
        for forged in (f"{self.acme.pk}:{real_sig}", f"{self.acme.pk}/{self.mine.pk},{self.far.pk}:{real_sig}", f"*:{real_sig}", str(self.acme.pk)):
            for view in self.VIEWS:
                self.assertEqual(self.outlets_in(forged, view), set(), (forged, view))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DASHBOARD_URL="https://app.example.test")
class PasswordResetTests(Base):
    def setUp(self):
        from unittest import mock

        cache.clear()
        self.owner.email = "owner@example.test"
        self.owner.save()
        patcher = mock.patch("apps.outlets.auth_api._send_in_background", lambda message: message.send())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.c = APIClient()

    def forgot(self, identifier):
        res = self.c.post("/api/auth/password/forgot", {"identifier": identifier}, format="json")
        self.assertEqual((res.status_code, res.json()), (200, {"ok": True}))

    def link(self):
        match = re.search(r"https://app\.example\.test/#/reset\?uid=([\w-]+)&token=([\w-]+)", mail.outbox[-1].body)
        return match.group(1), match.group(2)

    def reset(self, uid, token, password="Another-pass-7395!"):
        return self.c.post("/api/auth/password/reset", {"uid": uid, "token": token, "new_password": password}, format="json")

    def can_log_in(self, password):
        return APIClient().post("/api/auth/login", {"username": "owner", "password": password}, format="json").status_code == 200

    def test_username_or_email_sends_link_to_the_saved_address(self):
        for identifier in ("owner", "OWNER@example.test"):
            self.forgot(identifier)
            self.assertEqual(mail.outbox[-1].to, ["owner@example.test"])
        self.assertEqual(len(mail.outbox), 2)

    def test_unknown_login_gets_same_answer_and_no_mail(self):
        self.forgot("nobody")
        self.forgot("")
        self.assertEqual(mail.outbox, [])

    def test_login_without_email_or_disabled_gets_no_mail(self):
        self.forgot("manager")  # no email saved
        self.owner.is_active = False
        self.owner.save()
        self.forgot("owner")
        self.assertEqual(mail.outbox, [])

    def test_blank_email_cannot_match_logins_without_email(self):
        self.forgot("   ")
        self.assertEqual(mail.outbox, [])

    def test_link_changes_password_once_and_signs_out_other_sessions(self):
        session = self.as_user(self.owner)
        self.forgot("owner")
        uid, token = self.link()
        self.assertEqual(self.reset(uid, token).status_code, 200)
        self.assertTrue(self.can_log_in("Another-pass-7395!"))
        self.assertFalse(self.can_log_in(PASSWORD))
        self.assertEqual(session.get("/api/brands").status_code, 401)
        self.assertEqual(self.reset(uid, token, "Third-pass-2846!").status_code, 400)
        self.assertTrue(self.can_log_in("Another-pass-7395!"))

    def test_bad_links_rejected(self):
        self.forgot("owner")
        uid, token = self.link()
        other_uid = urlsafe_base64_encode(force_bytes(self.manager.pk))
        for bad_uid, bad_token in ((uid, "nope"), (other_uid, token), ("!!!", token), ("", ""), (urlsafe_base64_encode(b"abc"), token)):
            self.assertEqual(self.reset(bad_uid, bad_token).status_code, 400, (bad_uid, bad_token))
        self.assertTrue(self.can_log_in(PASSWORD))

    def test_expired_link_rejected(self):
        self.forgot("owner")
        uid, token = self.link()
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            self.assertEqual(self.reset(uid, token).status_code, 400)

    def test_disabled_login_cannot_use_a_link(self):
        self.forgot("owner")
        uid, token = self.link()
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertEqual(self.reset(uid, token).status_code, 400)

    def test_weak_password_rejected_and_link_still_works(self):
        self.forgot("owner")
        uid, token = self.link()
        self.assertEqual(self.reset(uid, token, "12345").status_code, 400)
        self.assertEqual(self.reset(uid, token, "").status_code, 400)
        self.assertEqual(self.reset(uid, token).status_code, 200)

    def test_mails_limited_per_hour(self):
        for _ in range(6):
            self.forgot("owner")
        self.assertEqual(len(mail.outbox), 3)

    def test_works_while_logged_in_as_someone_else(self):
        self.forgot("owner")
        uid, token = self.link()
        self.c = self.as_user(self.manager)
        self.assertEqual(self.reset(uid, token).status_code, 200)


class PasswordRulesTests(Base):
    def test_password_may_resemble_the_username_but_weak_ones_are_still_refused(self):
        c = self.as_user(self.owner)
        url = f"/api/clients/{self.acme.pk}/team/{self.manager.pk}"
        self.assertEqual(c.patch(url, {"password": "manager_ss"}, format="json").status_code, 200)
        self.assertEqual(c.patch(url, {"password": "short"}, format="json").status_code, 400)
        self.assertEqual(c.patch(url, {"password": "password"}, format="json").status_code, 400)
        self.assertEqual(c.patch(url, {"password": "4829173650"}, format="json").status_code, 400)


class OtpLoginTests(TestCase):
    def setUp(self):
        from unittest import mock
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user("otpuser", email="otp@example.com", password="x-Strong-pass-1")
        self.c = APIClient()
        patcher = mock.patch("apps.outlets.auth_api._send_in_background", side_effect=lambda m: m.send())
        patcher.start()
        self.addCleanup(patcher.stop)

    def _code(self):
        import re
        from django.core import mail
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].subject).group(1)

    def test_code_signs_in_once(self):
        from django.core import mail
        self.assertEqual(self.c.post("/api/auth/otp/request", {"identifier": "OTP@example.com"}, format="json").status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        code = self._code()
        self.assertEqual(self.c.post("/api/auth/otp/verify", {"identifier": "otp@example.com", "code": "000000" if code != "000000" else "111111"}, format="json").status_code, 400)
        r = self.c.post("/api/auth/otp/verify", {"identifier": "otp@example.com", "code": code}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get("/api/auth/me").status_code, 200)
        self.assertEqual(APIClient().post("/api/auth/otp/verify", {"identifier": "otp@example.com", "code": code}, format="json").status_code, 400)

    def test_unknown_email_same_answer_no_mail(self):
        from django.core import mail
        self.assertEqual(self.c.post("/api/auth/otp/request", {"identifier": "nobody@example.com"}, format="json").status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_one_code_a_minute_and_dies_after_wrong_guesses(self):
        from django.core import mail
        self.c.post("/api/auth/otp/request", {"identifier": "otp@example.com"}, format="json")
        self.c.post("/api/auth/otp/request", {"identifier": "otp@example.com"}, format="json")
        self.assertEqual(len(mail.outbox), 1)
        code = self._code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.c.post("/api/auth/otp/verify", {"identifier": "otp@example.com", "code": wrong}, format="json")
        self.assertEqual(self.c.post("/api/auth/otp/verify", {"identifier": "otp@example.com", "code": code}, format="json").status_code, 400)
