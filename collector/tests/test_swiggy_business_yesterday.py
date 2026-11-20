"""Swiggy yesterday's business numbers: reading the response and turning it into KPIs. Made-up figures. Run from collector/:
    ./.venv/bin/python -m unittest tests.test_swiggy_business_yesterday
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swiggy import business_yesterday as by  # noqa: E402

DAY = date(2026, 11, 16)


def title(text):
    return {"attribute_values": {"date": {"value": text}}}


class YesterdayTests(unittest.TestCase):
    def test_title_day_reads_the_day_swiggy_answers_for(self):
        self.assertEqual(by._title_day(title("16th November"), 2026), DAY)
        self.assertEqual(by._title_day(title("2nd Nov"), 2026), date(2026, 11, 2))
        self.assertIsNone(by._title_day(None, 2026))
        self.assertIsNone(by._title_day(title("yesterday"), 2026))

    def test_report_keeps_only_wanted_metrics_and_converts_units(self):
        rows = [{"rid": "123", "metrics": {
            "NET_SALES": {"value": "₹1,438"}, "DELIVERED_ORDERS": {"value": "4"},
            "KITCHEN_PREPARATION_TIME": {"value": "17.5 min"}, "ONLINE_PERCENTAGE": {"value": "98.5%"},
            "BOLT_ORDERS": {"value": "9"}, "NET_AOV": {"value": "-"}}}]
        rep = by._report(rows, DAY)[123]
        self.assertEqual(rep[("SALES", "Net Sales")], {DAY: 1438.0})
        self.assertEqual(rep[("SALES", "Delivered Orders")], {DAY: 4.0})
        self.assertEqual(rep[("OPERATIONS", "Kitchen Prep Time")], {DAY: 1050.0})  # seconds, like the report job
        self.assertEqual(rep[("OPERATIONS", "Online Availability %")], {DAY: 98.5})
        self.assertNotIn(("SALES", "Net AOV"), rep)  # '-' is not a number

    def test_report_turns_into_the_same_kpis_as_the_report_job(self):
        from core import derive

        rows = [{"rid": 1, "metrics": {"NET_SALES": {"value": "₹1,000"}, "DELIVERED_ORDERS": {"value": "5"},
                                       "CANCELLED_ORDER": {"value": "1"}, "ADS_DRIVEN_SALES": {"value": "₹200"}, "CBA_DRIVEN_SALES": {"value": "₹50"}}}]
        kpis = {c: (v, w) for c, d, v, w in derive.kpi_rows(by._report(rows, DAY)[1], by._MAP)}
        self.assertEqual(kpis["net_revenue"], (1000.0, 1))
        self.assertEqual(kpis["delivered_orders"], (5.0, 1))
        self.assertAlmostEqual(kpis["cancellation_rate"][0], 100 / 6, places=2)
        self.assertEqual(kpis["ad_sales"][0], 250.0)


if __name__ == "__main__":
    unittest.main()
