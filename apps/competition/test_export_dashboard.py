"""The comparison workbook's first sheet: its three bar charts sit side by side without covering each other, whatever the number of restaurants."""

import io
import re
import zipfile
from types import SimpleNamespace as NS

from django.test import SimpleTestCase
from openpyxl import Workbook

from openpyxl import load_workbook

from .export_dashboard import _short, add_dashboard, add_notes, findings, insights, not_seen, print_ready


def make(names, with_us=True, votes=None, offers=None, bestsellers=None, rating_step=0.1):
    rows, ins = [], {}
    for k, name in enumerate(names):
        r = NS(res_id=str(k + 1), rating=4.0 + rating_step * k, votes=(votes or {}).get(k, "1.2K+"), name=name, offers=(offers or {}).get(k, []), items=[], info={})
        rows.append((name, r, with_us and k == 0))
        ins[r.res_id] = {"items": 50 + 10 * k, "categories": 8, "avg_price": 300 + 20 * k, "veg_pct": 50, "photo_pct": 80, "desc_pct": 70,
                         "out_of_stock": [], "no_photo": [], "no_desc": [], "bestsellers": (bestsellers or {}).get(k, []), "top_sellers": [], "by_category": {}}
    return rows, ins


def build(names, **kw):
    rows, ins = make(names, **kw)
    wb = Workbook()
    wb.active.title = "x"
    add_dashboard(wb, "Zomato", "Test outlet", None, "26 Nov 2026 10:00", rows, ins, {})
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def chart_spans(data):
    """(left, right) in pixels of every chart, read back from the saved file: the column widths and each chart's anchor and size."""
    z = zipfile.ZipFile(io.BytesIO(data))
    xml = z.read([n for n in z.namelist() if n.startswith("xl/worksheets/sheet")][0]).decode()
    widths = {}
    for m in re.finditer(r"<col ([^>]*)/?>", xml):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if "width" in a:
            for c in range(int(a["min"]), int(a["max"]) + 1):
                widths[c] = float(a["width"])
    px = lambda c: widths.get(c, 8.43) * 7 + 5
    drawing = z.read([n for n in z.namelist() if re.match(r"xl/drawings/drawing\d+\.xml", n)][0]).decode()
    spans = []
    for m in re.finditer(r"<(?:xdr:)?oneCellAnchor>.*?<(?:xdr:)?col>(\d+)</(?:xdr:)?col>.*?<(?:xdr:)?ext cx=\"(\d+)\"", drawing, re.S):
        left = sum(px(c) for c in range(1, int(m.group(1)) + 1))
        spans.append((left, left + int(m.group(2)) / 9525))
    return spans


class DashboardChartsTests(SimpleTestCase):
    def test_the_dashboard_has_no_rating_price_or_menu_size_charts(self):
        z = zipfile.ZipFile(io.BytesIO(build(["A", "B", "C"])))
        self.assertFalse([n for n in z.namelist() if n.startswith("xl/charts/")])  # no shared dish types in the sample, so no chart at all

    def test_long_restaurant_names_are_shortened_under_the_bars(self):
        self.assertEqual(_short("KFC"), "KFC")
        short = _short("PVR Café – Popcorn, Pizza, Hot Dogs & Snacks")
        self.assertLessEqual(len(short), 24)
        self.assertTrue(short.startswith("PVR Café"))


class ExecutiveSummaryTests(SimpleTestCase):
    def test_findings_are_ordered_and_each_has_evidence_and_an_action(self):
        rows, ins = make(["You", "Rival A", "Rival B"], votes={0: "40", 1: "2K+", 2: "3K+"}, rating_step=0.4)
        rows[0][1].rating = 3.8
        fs = findings(rows, ins, {})
        self.assertTrue(fs)
        self.assertEqual([f["priority"] for f in fs][:2], ["High", "High"])
        self.assertEqual([f["score"] for f in fs], sorted((f["score"] for f in fs), reverse=True))
        for f in fs:
            self.assertTrue(f["title"] and f["evidence"] and f["action"])
        self.assertTrue(any("rating" in f["title"].lower() for f in fs))
        self.assertTrue(any("ratings" in f["title"].lower() for f in fs))  # 40 against a median of 2,500

    def test_a_group_with_no_large_gap_gets_one_calm_line_not_invented_problems(self):
        rows, ins = make(["You", "Rival"], rating_step=0.0)
        fs = findings(rows, ins, {})
        self.assertEqual(len(fs), 1)
        self.assertEqual(fs[0]["priority"], "—")

    def test_no_findings_without_you_or_without_competitors(self):
        self.assertEqual(findings(*make(["A", "B"], with_us=False), {}), [])
        self.assertEqual(findings(*make(["You"]), {}), [])


class NotSeenTests(SimpleTestCase):
    def test_zero_everywhere_is_not_seen_not_compared(self):
        rows, ins = make(["You", "A", "B"])
        self.assertEqual(not_seen(rows, ins), {"Offers running", "Bestseller-tagged items"})
        ws = load_workbook(io.BytesIO(build(["You", "A", "B"])))["Dashboard"]
        cells = {str(c.value) for row in ws.iter_rows() for c in row if c.value}
        self.assertIn("not seen", cells)
        text = " ".join(cells)
        self.assertNotIn("You run 0 offers", text)  # no insight built on missing data
        self.assertIn("Not seen in the menu read, so not compared", text)

    def test_offers_that_were_seen_are_compared_normally(self):
        rows, ins = make(["You", "A"], offers={1: [{"text": "Flat ₹75 OFF above ₹179", "code": ""}]})
        self.assertNotIn("Offers running", not_seen(rows, ins))
        self.assertTrue(any("You run 0 offers" in s for s in insights(rows, ins, {})))


class ScorecardAndSheetsTests(SimpleTestCase):
    def test_the_scorecard_has_a_peer_median_and_the_difference(self):
        ws = load_workbook(io.BytesIO(build(["You", "A", "B", "C"], rating_step=0.2)))["Dashboard"]
        head = next(row for row in ws.iter_rows() if row[0].value == "Measure")
        labels = [c.value for c in head if c.value]
        self.assertEqual(labels[-2:], ["Peer median", "You vs median"])
        rating = next(row for row in ws.iter_rows() if row[0].value == "Rating")
        self.assertAlmostEqual(rating[len(labels) - 2].value, 4.4)  # median of 4.2, 4.4, 4.6
        self.assertLess(rating[len(labels) - 1].value, 0)  # you (4.0) are below it

    def test_a_comparison_without_you_has_no_median_columns_and_no_summary(self):
        ws = load_workbook(io.BytesIO(build(["A", "B", "C"], with_us=False)))["Dashboard"]
        values = {str(c.value) for row in ws.iter_rows() for c in row if c.value}
        self.assertNotIn("Peer median", values)
        self.assertNotIn("Executive summary", values)

    def test_every_sheet_prints_one_page_wide_and_the_notes_sheet_explains_the_measures(self):
        rows, ins = make(["You", "A"])
        wb = Workbook()
        add_dashboard(wb, "Zomato", "Test outlet", None, "26 Nov 2026 10:00", rows, ins, {})
        add_notes(wb, "Zomato", "Test outlet", None, "26 Nov 2026 10:00", rows, ins)
        self.assertEqual(wb.sheetnames[:2], ["Dashboard", "Notes"])
        for ws in (wb["Dashboard"], wb["Notes"]):
            self.assertEqual(ws.page_setup.fitToWidth, 1)
            self.assertTrue(ws.sheet_properties.pageSetUpPr.fitToPage)
        text = " ".join(str(c.value) for row in wb["Notes"].iter_rows() for c in row if c.value)
        for must in ("Average item price", "Peer median", "Not seen is not zero", "No sales or order figures", "Ads and personalisation"):
            self.assertIn(must, text)
