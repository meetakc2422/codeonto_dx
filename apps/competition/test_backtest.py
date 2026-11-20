from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.masters.models import Industry, Kpi
from apps.metrics.models import MetricDaily
from apps.outlets.models import Brand, BrandOutlet, Client

from .management.commands.backtest_rating_signal import predict_errors, spearman, windows_for


class BacktestMath(SimpleTestCase):
    def test_spearman_sees_a_link_and_no_link(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]), -1.0)

    def test_outlets_with_one_ratio_predict_each_other_exactly_and_unlike_outlets_do_not(self):
        same = [[(10, 100), (20, 200)], [(5, 50), (8, 80)], [(30, 300)], [(7, 70)]]
        self.assertTrue(all(e < 1e-9 for e in predict_errors(same)))
        unlike = [[(10, 100)], [(10, 200)], [(10, 50)], [(10, 400)]]
        self.assertTrue(all(e > 10 for e in predict_errors(unlike)))

    def test_it_needs_three_other_outlets(self):
        self.assertEqual(predict_errors([[(10, 100)], [(10, 100)], [(10, 100)]]), [])

    def test_windows_need_data_on_both_sides(self):
        from datetime import date
        d0 = date(2026, 1, 1)
        counts = {d0 + timedelta(days=i): 100 + i for i in range(0, 60)}
        orders = {d0 + timedelta(days=i): 7.0 for i in range(0, 60)}
        w = windows_for(counts, orders, d0, d0 + timedelta(days=56), 28, 5)
        self.assertEqual(len(w), 2)
        self.assertEqual(round(w[0][0]), 28)
        self.assertEqual(w[0][1], 196.0)
        self.assertEqual(windows_for({}, orders, d0, d0 + timedelta(days=56), 28, 5), [])


class BacktestCommand(TestCase):
    def test_it_reads_real_outlets_only_and_reports_the_error(self):
        client = Client.objects.create(name="Real", is_demo=False)
        demo = Client.objects.create(name="Sample", is_demo=True)
        ind = Industry.objects.first()
        today = timezone.localdate()
        kpi_orders = Kpi.objects.get(code="delivered_orders")
        kpi_rating = Kpi.objects.get(code="rating_count")
        outlets = [(client, f"R{n}") for n in range(5)] + [(demo, "S0")]
        for cl, name in outlets:
            outlet = BrandOutlet.objects.create(brand=Brand.objects.get_or_create(client=cl, name=f"B{cl.name}", industry=ind)[0], outlet_name=name)
            for i in range(0, 130):
                day = today - timedelta(days=129 - i)
                MetricDaily.objects.create(outlet=outlet, platform_id="zomato", kpi=kpi_orders, metric_date=day, value=10, weight=1)
                MetricDaily.objects.create(outlet=outlet, platform_id="zomato", kpi=kpi_rating, metric_date=day, value=500 + i * 1.5, weight=1)
        out = StringIO()
        call_command("backtest_rating_signal", stdout=out)
        text = out.getvalue()
        self.assertIn("Zomato: 5 outlets", text)  # the sample client is not counted
        self.assertIn("typical error", text)


class OneWindowPerOutlet(TestCase):
    def test_a_first_look_across_outlets_needs_only_one_window_each(self):
        from django.utils import timezone as tz
        ind = Industry.objects.first()
        today = tz.localdate()
        kpi_orders, kpi_rating = Kpi.objects.get(code="delivered_orders"), Kpi.objects.get(code="rating_count")
        brand = Brand.objects.create(client=Client.objects.create(name="One window", is_demo=False), name="OW", industry=ind)
        for n in range(6):
            outlet = BrandOutlet.objects.create(brand=brand, outlet_name=f"O{n}")
            for i in range(0, 13):
                day = today - timedelta(days=12 - i)
                MetricDaily.objects.create(outlet=outlet, platform_id="swiggy", kpi=kpi_orders, metric_date=day, value=10 + n, weight=1)
                MetricDaily.objects.create(outlet=outlet, platform_id="swiggy", kpi=kpi_rating, metric_date=day, value=300 + i * (1 + n / 5), weight=1)
        default = StringIO(); call_command("backtest_rating_signal", "--window", "7", "--days", "12", stdout=default)
        self.assertIn("Not enough history", default.getvalue())
        first = StringIO(); call_command("backtest_rating_signal", "--window", "7", "--days", "12", "--min-windows", "1", stdout=first)
        self.assertIn("Swiggy: 6 outlets", first.getvalue())
        self.assertIn("typical error", first.getvalue())
