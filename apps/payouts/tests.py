"""Payout reconciliation numbers and who can see them."""

from datetime import date, timedelta
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.utils.timezone import now
from rest_framework.test import APIClient

from apps.assistant.db import scope_value
from apps.masters.models import Industry
from apps.outlets.models import Brand, BrandOutlet, Client, ClientUser

from .models import PayoutCycle, PayoutOrder

User = get_user_model()
SECRET = "test-scope-secret"


class PayoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        industry = Industry.objects.first()
        client = Client.objects.create(name="Acme")
        cls.brand = Brand.objects.create(client=client, name="Brand", industry=industry)
        cls.other_brand = Brand.objects.create(client=client, name="Other", industry=industry)
        cls.a = BrandOutlet.objects.create(brand=cls.brand, outlet_name="Brand", area="Rohini")
        cls.b = BrandOutlet.objects.create(brand=cls.brand, outlet_name="Brand", area="Saket")
        cls.client_id = client.pk
        def login(name, role, outlets=()):
            user = User.objects.create_user(name, password="x")
            ClientUser.objects.create(user=user, client=client, role=role).outlets.set(outlets)
            return user
        cls.owner, cls.manager = login("owner", "admin"), login("manager", "manager", [cls.a])
        cls.today = date.today()
        cls.good = cls.cycle(cls.a, 3, status="PAID", utr="UTR-A", net=D("1000"), expected=D("1000"), diff=D("0"), comm=D("2000"), fee=D("200"))
        cls.bad = cls.cycle(cls.b, 4, status="PAID", utr="UTR-B", net=D("900"), expected=D("1000"), diff=D("-100"), issues=["payout_mismatch"], comm=D("2000"), fee=D("400"))
        cls.upcoming = cls.cycle(cls.a, 1, status="TO BE PAID", net=D("500"), payout_in=2)
        cls.late = cls.cycle(cls.b, 8, status="TO BE PAID", net=D("700"), payout_in=-3)
        PayoutOrder.objects.create(cycle=cls.good, order_id="111", payout=D("1000"), net_order_value=D("1200"), status="DELIVERED")

    @classmethod
    def cycle(cls, outlet, days_ago, status, net, utr="", expected=None, diff=None, issues=(), comm=None, fee=None, payout_in=None):
        day = cls.today - timedelta(days=days_ago)
        return PayoutCycle.objects.create(
            outlet=outlet, platform_id="zomato", start_date=day, end_date=day, status=status, utr=utr, net_payout=net, expected_payout=expected,
            discrepancy=diff, issues=list(issues), commissionable_total=comm, service_fee_total=fee, order_count=1, fetched_at=now(),
            payout_date=cls.today + timedelta(days=payout_in) if payout_in is not None else day, reconciled_at=now() if expected is not None else None,
            breakdown=[{"id": "total_order_value", "label": "Net order value", "value": 1200.0, "items": []}])

    def get(self, user, tail, **q):
        c = APIClient()
        c.force_login(user)
        return c.get(f"/api/brands/{self.brand.pk}/payouts/{tail}", q)

    def test_owner_summary(self):
        s = self.get(self.owner, "summary").json()
        self.assertEqual((s["cycles"], s["reconciled"], s["paid_total"], s["to_be_paid_total"], s["to_be_paid_cycles"]), (4, 2, 1900.0, 1200.0, 2))
        self.assertEqual((s["with_issues"], s["discrepancy_total"], s["take_rate"]), (2, 100.0, 15.0))
        self.assertEqual({i["code"]: i["count"] for i in s["issues"]}, {"payout_mismatch": 1, "overdue": 1})

    def test_carried_forward_is_neither_due_nor_overdue(self):
        carried = self.cycle(self.a, 2, status="CARRIED FORWARD", net=D("-404.28"), payout_in=-5)
        s = self.get(self.owner, "summary").json()
        self.assertEqual((s["to_be_paid_total"], s["carried_forward_cycles"], s["carried_forward_total"]), (1200.0, 1, -404.28))
        rows = {r["id"]: r for r in self.get(self.owner, "cycles").json()["results"]}
        self.assertEqual(rows[carried.pk]["issues"], [])
        self.assertNotIn(carried.pk, {r["id"] for r in self.get(self.owner, "cycles", status="to_be_paid").json()["results"]})

    def test_only_past_due_unpaid_cycles_are_overdue(self):
        rows = {r["id"]: r for r in self.get(self.owner, "cycles").json()["results"]}
        self.assertEqual(rows[self.late.pk]["issues"], ["overdue"])
        self.assertEqual(rows[self.upcoming.pk]["issues"], [])
        self.assertEqual(rows[self.good.pk]["issues"], [])

    def test_filters_and_utr_search(self):
        ids = lambda **q: {r["id"] for r in self.get(self.owner, "cycles", **q).json()["results"]}
        self.assertEqual(ids(status="issues"), {self.bad.pk, self.late.pk})
        self.assertEqual(ids(status="paid"), {self.good.pk, self.bad.pk})
        self.assertEqual(ids(status="to_be_paid"), {self.upcoming.pk, self.late.pk})
        self.assertEqual(ids(q="utr-b"), {self.bad.pk})
        self.assertEqual(ids(q="rohini"), {self.good.pk, self.upcoming.pk})

    def test_cycles_needing_attention_come_first(self):
        rows = self.get(self.owner, "cycles").json()["results"]
        self.assertEqual({rows[0]["id"], rows[1]["id"]}, {self.bad.pk, self.late.pk})

    def test_date_range_uses_cycle_end(self):
        s = self.get(self.owner, "summary", start=self.today - timedelta(days=2), end=self.today).json()
        self.assertEqual(s["cycles"], 1)

    def test_detail_has_statement_and_orders_without_customer_data(self):
        d = self.get(self.owner, f"cycles/{self.good.pk}").json()
        self.assertEqual((d["utr"], d["breakdown"][0]["id"], d["orders"][0]["order_id"], d["orders"][0]["payout"]), ("UTR-A", "total_order_value", "111", 1000.0))
        self.assertNotIn("customer", str(d["orders"][0]).lower())

    def test_manager_sees_only_assigned_outlets(self):
        s = self.get(self.manager, "summary").json()
        self.assertEqual((s["cycles"], s["paid_total"], s["discrepancy_total"], s["take_rate"]), (2, 1000.0, 0.0, 10.0))
        self.assertEqual({r["id"] for r in self.get(self.manager, "cycles").json()["results"]}, {self.good.pk, self.upcoming.pk})
        self.assertEqual(self.get(self.manager, "cycles", outlet_id=self.b.pk).json()["results"], [])
        self.assertEqual(self.get(self.manager, f"cycles/{self.bad.pk}").status_code, 404)
        self.assertEqual(self.get(self.manager, f"cycles/{self.good.pk}").status_code, 200)

    def test_other_client_and_wrong_brand_get_nothing(self):
        stranger = User.objects.create_user("stranger", password="x")
        ClientUser.objects.create(user=stranger, client=Client.objects.create(name="Stranger"), role="admin")
        self.assertEqual(self.get(stranger, "summary").status_code, 404)
        self.assertEqual(self.get(stranger, f"cycles/{self.good.pk}").status_code, 404)
        c = APIClient()
        c.force_login(self.owner)
        self.assertEqual(c.get(f"/api/brands/{self.other_brand.pk}/payouts/cycles/{self.good.pk}").status_code, 404)

    def test_login_required(self):
        self.assertEqual(APIClient().get(f"/api/brands/{self.brand.pk}/payouts/summary").status_code, 401)

    @override_settings(ASSISTANT_SCOPE_SECRET=SECRET)
    def test_assistant_views_respect_outlet_limit(self):
        with connection.cursor() as cur:
            cur.execute("DELETE FROM assistant.scope_secret")
            cur.execute("INSERT INTO assistant.scope_secret (secret) VALUES (%s)", [SECRET])
            cur.execute("SELECT set_config('app.scope', %s, true)", [scope_value(self.client_id, [self.b.pk])])
            cur.execute("SELECT DISTINCT outlet_id FROM assistant.payout_cycles")
            self.assertEqual([r[0] for r in cur.fetchall()], [self.b.pk])
            cur.execute("SELECT count(*) FROM assistant.payout_orders")
            self.assertEqual(cur.fetchone()[0], 0)
            cur.execute("SELECT set_config('app.scope', %s, true)", [scope_value(self.client_id, [self.a.pk])])
            cur.execute("SELECT count(*) FROM assistant.payout_orders")
            self.assertEqual(cur.fetchone()[0], 1)


class AnalyticsLayoutTests(TestCase):
    """Zomato changed its statement layout: the analytics shows one layout at a time, so no % mixes lines of both."""

    @classmethod
    def setUpTestData(cls):
        industry = Industry.objects.first()
        cls.client_org = Client.objects.create(name="Acme")
        cls.brand = Brand.objects.create(client=cls.client_org, name="Brand", industry=industry)
        cls.outlet = BrandOutlet.objects.create(brand=cls.brand, outlet_name="Brand", area="Rohini")
        cls.owner = User.objects.create_user("owner2", password="x")
        ClientUser.objects.create(user=cls.owner, client=cls.client_org, role="admin")
        today = date.today()
        old = [{"id": "total_order_value", "label": "Net order value (A)", "value": 1000.0, "items": []},
               {"id": "additions", "label": "Additions (B)", "value": 10.0, "items": []}]
        new = [{"id": "gross_order_value", "label": "Gross order value (A)", "value": 500.0, "items": []},
               {"id": "net_order_value_subtotal", "label": "Net order value (A+B)", "value": 400.0, "items": []}]
        for days, breakdown, orders in ((20, old, 7), (13, old, 5), (6, new, 3)):
            PayoutCycle.objects.create(outlet=cls.outlet, platform_id="zomato", start_date=today - timedelta(days=days + 6), end_date=today - timedelta(days=days),
                                       status="PAID", net_payout=D("100"), order_count=orders, breakdown=breakdown, fetched_at=now(), payout_date=today - timedelta(days=days))

    def get(self, **q):
        c = APIClient()
        c.force_login(self.owner)
        return c.get(f"/api/brands/{self.brand.pk}/payouts/analytics", q).json()

    def test_two_layouts_are_listed_newest_first_and_the_newest_is_shown(self):
        d = self.get()
        self.assertEqual([L["name"] for L in d["layouts"]], ["Gross order value", "Net order value"])
        self.assertEqual(d["layout"], "gross order value")
        self.assertEqual(d["total"]["orders"], 3)  # only the new layout's payouts
        self.assertEqual([s["label"] for s in d["sections"]], ["Gross order value (A)", "Net order value (A+B)"])

    def test_the_older_layout_adds_up_only_its_own_payouts(self):
        d = self.get(alayout="net order value")
        self.assertEqual(d["total"]["orders"], 12)
        self.assertEqual(d["total"]["cycles"], 2)
        self.assertEqual([s["label"] for s in d["sections"]], ["Net order value (A)", "Additions (B)"])

    def test_an_unknown_layout_falls_back_to_the_newest(self):
        self.assertEqual(self.get(alayout="nonsense")["layout"], "gross order value")

    def test_excel_export_follows_the_chosen_layout(self):
        c = APIClient()
        c.force_login(self.owner)
        res = c.get(f"/api/brands/{self.brand.pk}/payouts/analytics/xlsx", {"alayout": "net order value"})
        self.assertEqual(res.status_code, 200)
        import io

        from openpyxl import load_workbook

        ws = load_workbook(io.BytesIO(res.content)).active
        self.assertIn("Net order value format", ws["B2"].value)
        self.assertEqual(ws["C4"].value, 12)  # number of orders in that layout
