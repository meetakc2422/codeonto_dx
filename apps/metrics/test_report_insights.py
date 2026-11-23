"""The overview and recommendations written into the client report."""

from django.test import SimpleTestCase

from .report_insights import overview, recommendations


def cell(v, ch=None):
    return {"value": v, "prev": None, "change": ch}


def sample(**over):
    r = {"brand": "Demo", "outlets": 3, "period": {"start": "2026-11-10", "end": "2026-11-16", "days": 7},
         "headline": [{"name": "Sales", "value": 412000, "change": 8.2}, {"name": "Orders", "value": 1320, "change": -4}, {"name": "Average order value", "value": 312, "change": 3}, {"name": "Rating", "value": 4.2, "change": -1.2}],
         "platforms": [{"name": "Zomato", "sales": 250000, "share": 60.7}, {"name": "Swiggy", "sales": 162000, "share": 39.3}],
         "highlights": [{"name": "Ad Sales", "change": 73}, {"name": "Cancellation Rate", "change": -68}],
         "coverage": {"gaps": []}, "sections": []}
    r.update(over)
    return r


class OverviewTests(SimpleTestCase):
    def test_reads_like_a_summary_of_the_period(self):
        text = " ".join(overview(sample()))
        self.assertIn("Demo sold ₹4.12 L from 1,320 orders across 3 outlets between 10 Nov 2026 and 16 Nov 2026, up 8% on the previous 7 days", text)
        self.assertIn("Zomato brought 61% of the sales and Swiggy 39%.", text)
        self.assertIn("ad sales up 73%", text)

    def test_a_left_out_section_adds_nothing(self):
        self.assertNotIn("complaints", " ".join(overview(sample())).lower())
        comp = {"key": "complaints", "columns": [{"code": "total", "name": "Complaints"}, {"code": "per_100_orders", "name": "Per 100"}, {"code": "packaging", "name": "Packaging"}],
                "total": {"total": 40, "per_100_orders": 3.0, "packaging": 18}}
        self.assertIn("40 complaints (3.0 per 100 orders), mostly about packaging", " ".join(overview(sample(sections=[comp]))))

    def test_says_when_days_are_missing(self):
        self.assertIn("2 outlets had days with no sales data", " ".join(overview(sample(coverage={"gaps": [1, 2]}))))


class RecommendationTests(SimpleTestCase):
    def sections(self, **tot):
        return [{"key": "overall", "total": {k: cell(v) for k, v in tot.items()}, "rows": []}]

    def test_flags_cancellations_with_the_rupee_cost(self):
        recs = recommendations(sample(sections=self.sections(cancellation_loss=21000, cancellation_rate=3.1)))
        self.assertEqual(recs[0]["title"], "Cut cancellations")
        self.assertIn("₹21.0k (5.1% of sales)", recs[0]["detail"])

    def test_most_important_first_and_at_most_five(self):
        recs = recommendations(sample(sections=self.sections(delayed_orders_pct=12, online_pct=97)
                                      + [{"key": "reputation", "total": {"listing_rating": cell(3.6)}, "rows": []}]))
        self.assertEqual(recs[0]["title"], "Lift the rating")  # a low rating outranks lateness at this level
        self.assertLessEqual(len(recs), 5)
        big = recommendations(sample(sections=self.sections(cancellation_loss=30000, cancellation_rate=4, delayed_orders_pct=15, online_pct=80)))
        self.assertEqual(big[0]["title"], "Cut cancellations")  # 7% of sales lost to cancellations comes first
        self.assertLessEqual(len(big), 5)

    def test_a_healthy_period_still_says_something(self):
        recs = recommendations(sample(sections=self.sections(cancellation_rate=0.2, online_pct=99, delayed_orders_pct=3)))
        self.assertEqual(recs[0]["title"], "Nothing urgent this period")

    def test_good_ads_get_a_nudge_to_spend_more(self):
        ads = [{"key": "ads", "total": {"ad_roi": cell(7.0), "ad_spend": cell(20000)}, "rows": []}]
        self.assertIn("Put more behind ads", [x["title"] for x in recommendations(sample(sections=ads))])


class WordingTests(SimpleTestCase):
    def test_noise_on_tiny_numbers_is_not_news(self):
        hl = [{"name": "Cancellation Rate", "change": 120, "value": 0.2, "unit": "percent"}, {"name": "Ad ROI", "change": 34, "value": 5.1, "unit": "ratio"},
              {"name": "Revenue Lost to Cancellations", "change": 88, "value": 900, "unit": "currency"}]
        text = " ".join(overview(sample(highlights=hl)))
        self.assertIn("ad ROI up 34%", text)  # the acronym keeps its capitals
        self.assertNotIn("cancellation", text.lower())

    def test_discounts_are_worked_out_from_the_money(self):
        ads = [{"key": "ads", "total": {"discount_given": cell(100000)}, "rows": []}]
        rec = next(x for x in recommendations(sample(sections=ads)) if x["title"] == "Review discounts")
        self.assertIn("₹1.00 L, 24% of sales", rec["detail"])  # 1,00,000 of 4,12,000

    def test_deductions_are_not_counted_twice(self):
        pay = [{"key": "payouts", "total": {"net_order_value": 1000, "fees": 200, "deductions": 250, "payout": 750}, "rows": []}]
        titles = [x["title"] for x in recommendations(sample(sections=pay))]
        self.assertNotIn("Watch deductions", titles)  # 250 of 1,000 is 25%; adding the fees on top would have made it 45%
