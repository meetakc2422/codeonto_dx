"""Plans, locks, checkout totals and who can change what."""

from datetime import date, timedelta
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import now
from rest_framework.test import APIClient

from apps.masters.models import Industry
from apps.outlets.models import Brand, BrandOutlet, Client, ClientUser

from .models import Invoice, Plan, PlanRequest, Subscription

User = get_user_model()


class BillingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_obj = Client.objects.create(name="Acme")
        cls.other = Client.objects.create(name="Other")
        industry = Industry.objects.get(code="restaurant")
        cls.brand = Brand.objects.create(client=cls.client_obj, name="Brand", industry=industry)
        for i in range(3):
            BrandOutlet.objects.create(brand=cls.brand, outlet_name=f"O{i}")
        def login(name, client, role, outlets=()):
            u = User.objects.create_user(name, password="x")
            ClientUser.objects.create(user=u, client=client, role=role).outlets.set(outlets)
            return u
        cls.owner = login("owner", cls.client_obj, "admin")
        cls.manager = login("manager", cls.client_obj, "manager", [cls.brand.outlets.first()])
        cls.viewer = login("viewer", cls.client_obj, "viewer")
        cls.other_owner = login("other_owner", cls.other, "admin")
        cls.staff = User.objects.create_user("staff", password="x", is_staff=True)
        cls.starter, cls.growth, cls.pro = (Plan.objects.get(code=c) for c in ("starter", "growth", "pro"))

    def as_user(self, user):
        c = APIClient()
        c.force_login(user)
        return c

    def subscribe(self, plan, **over):
        return Subscription.objects.create(client=self.client_obj, plan=plan, **{"status": "active", **over})

    def locks(self, user):
        modules = self.as_user(user).get(f"/api/brands/{self.brand.pk}/config").json()["modules"]
        return {m["code"]: m["locked"] for m in modules}

    def test_seeded_plans_and_quote_with_gst(self):
        self.assertEqual([p["code"] for p in self.as_user(self.owner).get("/api/billing/plans").json()], ["starter", "growth", "pro", "enterprise"])
        q = self.as_user(self.owner).get("/api/billing/quote", {"plan": "growth", "cycle": "monthly", "outlets": 3}).json()
        self.assertEqual((q["subtotal"], q["gst"], q["total"]), (2997.0, 539.46, 3536.46))
        y = self.as_user(self.owner).get("/api/billing/quote", {"plan": "growth", "cycle": "annual", "outlets": 3}).json()
        self.assertEqual((y["months_billed"], y["covers_months"], y["subtotal"]), (10, 12, 29970.0))
        self.assertIsNone(self.as_user(self.owner).get("/api/billing/quote", {"plan": "enterprise", "outlets": 3}).json()["total"])

    def test_clients_without_a_plan_keep_everything(self):
        self.assertFalse(any(self.locks(self.owner).values()))

    def test_plan_locks_modules_in_config_and_api(self):
        self.subscribe(self.starter)
        locks = self.locks(self.owner)
        self.assertFalse(locks["reviews"])
        self.assertTrue(locks["stock_outs"])
        self.assertTrue(locks["reconciliation"])
        for tail in ("stock-outs", "payouts/summary"):
            self.assertEqual(self.as_user(self.owner).get(f"/api/brands/{self.brand.pk}/{tail}").status_code, 403, tail)
        self.assertEqual(self.as_user(self.owner).get(f"/api/brands/{self.brand.pk}/uptime/summary").status_code, 200)

    def test_staff_are_never_locked_out(self):
        self.subscribe(self.starter)
        self.assertFalse(any(self.locks(self.staff).values()))
        self.assertEqual(self.as_user(self.staff).get(f"/api/brands/{self.brand.pk}/stock-outs").status_code, 200)

    def test_trial_unlocks_until_it_ends_and_cancelled_keeps_only_overview(self):
        sub = self.subscribe(self.pro, status="trial", trial_ends_on=date.today() + timedelta(days=1))
        self.assertFalse(self.locks(self.owner)["reconciliation"])
        sub.trial_ends_on = date.today() - timedelta(days=1)
        sub.save()
        locks = self.locks(self.owner)
        self.assertTrue(locks["reconciliation"] and locks["reviews"])
        self.assertFalse(locks["overview"])
        sub.status = "cancelled"
        sub.save()
        self.assertTrue(self.locks(self.owner)["reviews"])

    def test_owner_sees_billing_others_dont(self):
        self.subscribe(self.growth, outlet_limit=2)
        Invoice.objects.create(client=self.client_obj, number="INV-1", period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
                               subtotal=D("100"), gst=D("18"), total=D("118"), issued_on=date(2026, 11, 1))
        Invoice.objects.create(client=self.other, number="INV-2", period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
                               subtotal=D("1"), gst=D("0"), total=D("1"), issued_on=date(2026, 11, 1))
        b = self.as_user(self.owner).get(f"/api/clients/{self.client_obj.pk}/billing").json()
        self.assertEqual((b["subscription"]["plan"], b["subscription"]["outlet_limit"], b["usage"]["outlets"], b["usage"]["logins"]), ("growth", 2, 3, 3))
        self.assertEqual([i["number"] for i in b["invoices"]], ["INV-1"])
        for user in (self.manager, self.viewer):
            self.assertEqual(self.as_user(user).get(f"/api/clients/{self.client_obj.pk}/billing").status_code, 403)
        self.assertEqual(self.as_user(self.other_owner).get(f"/api/clients/{self.client_obj.pk}/billing").status_code, 404)
        self.assertEqual(APIClient().get(f"/api/clients/{self.client_obj.pk}/billing").status_code, 401)

    def test_owner_can_request_but_not_set_a_plan(self):
        res = self.as_user(self.owner).post(f"/api/clients/{self.client_obj.pk}/billing/requests", {"plan": "pro", "cycle": "annual", "outlets": 3}, format="json")
        self.assertEqual(res.status_code, 201)
        r = PlanRequest.objects.get()
        self.assertEqual((r.plan.code, r.cycle, r.outlets, r.quoted_total, r.requested_by), ("pro", "annual", 3, D("53064.60"), self.owner))
        self.assertEqual(self.as_user(self.owner).patch(f"/api/clients/{self.client_obj.pk}/billing", {"plan": "pro", "status": "active"}, format="json").status_code, 403)
        self.assertEqual(self.as_user(self.manager).post(f"/api/clients/{self.client_obj.pk}/billing/requests", {"plan": "pro"}, format="json").status_code, 403)
        self.assertEqual(self.as_user(self.other_owner).post(f"/api/clients/{self.client_obj.pk}/billing/requests", {"plan": "pro"}, format="json").status_code, 404)

    def test_staff_sets_plan_and_closes_requests(self):
        PlanRequest.objects.create(client=self.client_obj, plan=self.pro, cycle="monthly", outlets=3)
        res = self.as_user(self.staff).patch(f"/api/clients/{self.client_obj.pk}/billing",
                                             {"plan": "pro", "status": "active", "cycle": "annual", "outlet_limit": "5", "current_period_end": "2027-11-01", "close_requests": True}, format="json")
        self.assertEqual(res.status_code, 200)
        sub = Subscription.objects.get(client=self.client_obj)
        self.assertEqual((sub.plan.code, sub.status, sub.cycle, sub.outlet_limit, sub.current_period_end), ("pro", "active", "annual", 5, date(2027, 11, 1)))
        self.assertFalse(PlanRequest.objects.filter(is_open=True).exists())
        self.assertEqual(self.as_user(self.staff).patch(f"/api/clients/{self.client_obj.pk}/billing", {"status": "bogus"}, format="json").status_code, 400)
        self.assertEqual(self.as_user(self.staff).patch(f"/api/clients/{self.client_obj.pk}/billing", {"trial_ends_on": "not a date"}, format="json").status_code, 400)

    def test_starter_login_limit(self):
        self.subscribe(self.starter)
        body = {"username": "fourth", "password": "Strong-pass-4821!", "role": "viewer"}
        res = self.as_user(self.owner).post(f"/api/clients/{self.client_obj.pk}/team", body, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("3 logins", res.json()["detail"])
        self.assertEqual(self.as_user(self.staff).post(f"/api/clients/{self.client_obj.pk}/team", body, format="json").status_code, 201)
