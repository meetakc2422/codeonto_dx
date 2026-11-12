"""Top-seller loss estimate from order history."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from apps.insights.models import ItemSalesDaily
from apps.orders.models import OrderLine
from apps.outlets.tests import Base as OutletsBase

from . import loss
from .models import StockOut

IST = loss.IST


class ExpectedLoss(SimpleTestCase):
    RATE = {"Lunch": 4.0, "Dinner": 8.0}

    def test_counts_only_hours_out_inside_each_meal(self):
        now = datetime(2026, 11, 11, 14, 0, tzinfo=IST)  # 2 pm: halfway through Lunch (12-4)
        out = loss.expected_loss(self.RATE, datetime(2026, 11, 11, 12, 0, tzinfo=IST), now, 500)
        self.assertEqual(out["units"], 2.0)  # 4 units x 2 of 4 hours
        self.assertEqual((out["high"], out["low"]), (1000, 400))  # low end = 40%

    def test_started_before_today_counts_only_today(self):
        now = datetime(2026, 11, 11, 20, 0, tzinfo=IST)
        out = loss.expected_loss(self.RATE, datetime(2026, 11, 8, 9, 0, tzinfo=IST), now, 100)
        self.assertEqual(out["units"], 4.0 + 2.0)  # all of Lunch, then 1 of Dinner's 4 hours (8 x 1/4 = 2)

    def test_no_price_gives_units_but_no_rupees(self):
        now = datetime(2026, 11, 11, 14, 0, tzinfo=IST)
        out = loss.expected_loss(self.RATE, datetime(2026, 11, 11, 12, 0, tzinfo=IST), now, None)
        self.assertEqual((out["units"], out["high"], out["low"]), (2.0, None, None))

    def test_after_midnight_belongs_to_the_previous_service_day(self):
        self.assertEqual(loss.service_day(datetime(2026, 11, 11, 1, 0, tzinfo=IST)), date(2026, 11, 10))
        self.assertEqual(loss.service_day(datetime(2026, 11, 11, 6, 0, tzinfo=IST)), date(2026, 11, 11))


class TopSellers(OutletsBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        o, today = cls.mine, loss.service_day(timezone.now())
        lines = []
        for i in range(1, 21):  # 20 days of a best seller (3 at dinner) and a rarely ordered item
            d = today - timedelta(days=i)
            placed = datetime.combine(d, datetime.min.time(), tzinfo=IST) + timedelta(hours=20)
            lines.append(OrderLine(outlet=o, platform=cls.platform, order_id=f"a{i}", placed_at=placed, order_date=d, mealtime="Dinner",
                                   status="Delivered", item_name="Hit Burger", quantity=3))
        lines.append(OrderLine(outlet=o, platform=cls.platform, order_id="r1", placed_at=timezone.now(), order_date=today - timedelta(days=2),
                               mealtime="Dinner", status="Delivered", item_name="Rare Dish", quantity=1))
        lines.append(OrderLine(outlet=o, platform=cls.platform, order_id="x1", placed_at=timezone.now(), order_date=today - timedelta(days=1),
                               mealtime="Dinner", status="Rejected", rejection_reason="Items out of stock", item_name="Hit Burger",
                               quantity=1, order_subtotal=Decimal("450")))
        OrderLine.objects.bulk_create(lines)
        ItemSalesDaily.objects.create(outlet=o, platform=cls.platform, item_name="Hit Burger", day=today - timedelta(days=1), quantity=3,
                                      unit_price=Decimal("400"))
        now = timezone.now()
        cls.out = StockOut.objects.create(outlet=o, platform=cls.platform, item_name="Hit Burger", log_date=today,
                                          first_detected_at=now - timedelta(hours=2), last_detected_at=now)
        cls.rare = StockOut.objects.create(outlet=o, platform=cls.platform, item_name="Rare Dish", log_date=today,
                                           first_detected_at=now - timedelta(hours=2), last_detected_at=now)

    def test_only_best_sellers_are_valued(self):
        res = loss.top_sellers_out([self.out, self.rare], timezone.now())
        self.assertEqual([i["item_name"] for i in res["items"]], ["Hit Burger"])  # the rare dish gets no figure
        item = res["items"][0]
        self.assertTrue(item["enough_history"])
        self.assertEqual(item["price"], 400.0)
        self.assertLessEqual(item["low"], item["high"])

    def test_rate_ignores_days_the_item_was_out(self):
        today = loss.service_day(timezone.now())
        rate, days = loss.meal_rates(self.mine.pk, "Hit Burger", today, set())
        self.assertEqual(round(rate["Dinner"], 3), round(60 / 30, 3))  # 20 days x 3 units over 30 days
        out_days = {today - timedelta(days=i) for i in range(1, 11)}  # out for 10 of those days
        rate2, days2 = loss.meal_rates(self.mine.pk, "Hit Burger", today, out_days)
        self.assertEqual(days2, days - 10)
        self.assertEqual(round(rate2["Dinner"], 3), 1.5)  # 30 units over the 20 in-stock days

    def test_not_enough_history_gives_no_rupees(self):
        res = loss.top_sellers_out([StockOut(outlet=self.sibling, platform=self.platform, item_name="Hit Burger", log_date=date.today(),
                                             first_detected_at=timezone.now(), last_detected_at=timezone.now())], timezone.now())
        self.assertEqual(res["items"], [])  # nothing sold at this outlet, so it is not a best seller

    def test_period_loss_counts_best_sellers_over_the_range(self):
        now = timezone.now()
        today = loss.service_day(now)
        dinner = datetime.combine(today - timedelta(days=2), datetime.min.time(), tzinfo=IST) + timedelta(hours=19)  # all of Dinner, 2 days ago
        old = StockOut.objects.create(outlet=self.mine, platform=self.platform, item_name="Hit Burger", log_date=today - timedelta(days=2),
                                      first_detected_at=dinner, last_detected_at=dinner, restored_at=dinner + timedelta(hours=4), is_active=False)
        res = loss.period_loss([old, self.out, self.rare], today - timedelta(days=29), today, now, now - timedelta(days=3))
        self.assertEqual([i["item_name"] for i in res["items"]], ["Hit Burger"])  # the rare dish gets no figure
        self.assertGreater(res["high"], 0)
        self.assertLessEqual(res["low"], res["high"])
        narrow = loss.period_loss([old, self.out], today, today, now, now - timedelta(days=3))  # a shorter period leaves the older stock-out out
        self.assertLess(narrow["high"], res["high"])

    def test_a_long_stock_out_counts_only_its_first_three_days(self):
        now = timezone.now()
        today = loss.service_day(now)
        start = datetime.combine(today - timedelta(days=15), datetime.min.time(), tzinfo=IST) + timedelta(hours=5)
        long_ep = StockOut.objects.create(outlet=self.mine, platform=self.platform, item_name="Hit Burger", log_date=today - timedelta(days=15),
                                          first_detected_at=start, last_detected_at=start, restored_at=start + timedelta(days=12), is_active=False)
        three = StockOut(outlet=self.mine, platform=self.platform, item_name="Hit Burger", log_date=today - timedelta(days=15),
                         first_detected_at=start, last_detected_at=start, restored_at=start + timedelta(days=3), is_active=False)
        a = loss.period_loss([long_ep], today - timedelta(days=29), today, now, now - timedelta(days=3))
        b = loss.period_loss([three], today - timedelta(days=29), today, now, now - timedelta(days=3))
        self.assertEqual(a["high"], b["high"])  # 12 days out is valued the same as 3

    def test_summary_has_the_period_loss(self):
        owner = self.as_user(self.owner).get(f"/api/brands/{self.brand_a.pk}/stock-outs/summary").json()
        self.assertIn("period_loss", owner)

    def test_rejections_for_stock_are_counted_once(self):
        today = loss.service_day(timezone.now())
        self.assertEqual(loss.rejected_for_stock([self.mine.pk], today - timedelta(days=30), today), {"orders": 1, "value": 450})
        self.assertEqual(loss.rejected_for_stock([self.sibling.pk], today - timedelta(days=30), today), {"orders": 0, "value": 0})

    def test_summary_carries_the_new_fields_and_respects_scope(self):
        url = f"/api/brands/{self.brand_a.pk}/stock-outs/summary"
        owner = self.as_user(self.owner).get(url).json()
        self.assertEqual(owner["stock_rejections"]["orders"], 1)
        self.assertEqual([i["item_name"] for i in owner["top_sellers_out"]["items"]], ["Hit Burger"])
        manager = self.as_user(self.manager).get(url).json()  # manager is assigned to "Mine" only: same outlet
        self.assertEqual(manager["stock_rejections"]["orders"], 1)
        other = self.as_user(self.other_owner).get(url)  # another client's login must not see this brand's figures
        self.assertNotEqual(other.status_code, 200)
        self.assertNotIn("stock_rejections", other.json() if other.status_code < 500 else {})
