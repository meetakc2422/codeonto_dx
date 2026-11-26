"""The comparison workbook's first sheet: its three bar charts sit side by side without covering each other, whatever the number of restaurants."""

import io
import re
import zipfile
from types import SimpleNamespace as NS

from django.test import SimpleTestCase
from openpyxl import Workbook

from .export_dashboard import _short, add_dashboard


def build(names):
    rows, ins = [], {}
    for k, name in enumerate(names):
        r = NS(res_id=str(k + 1), rating=4.0 + 0.1 * k, votes="1.2K+", name=name, offers=[], items=[], info={})
        rows.append((name, r, k == 0))
        ins[r.res_id] = {"items": 50 + 10 * k, "categories": 8, "avg_price": 300 + 20 * k, "veg_pct": 50, "photo_pct": 80, "desc_pct": 70,
                         "out_of_stock": [], "no_photo": [], "no_desc": [], "bestsellers": [], "top_sellers": [], "by_category": {}}
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
    def test_the_three_charts_never_overlap(self):
        for names in (["PVR Café – Popcorn, Pizza, Hot Dogs & Snacks", "KFC"], ["A", "B", "C"], ["One", "Two", "Three", "Four", "Five", "Six"]):
            spans = chart_spans(build(names))
            self.assertEqual(len(spans), 3, names)
            for (_, right), (left, _) in zip(spans, spans[1:]):
                self.assertGreater(left, right, f"charts overlap for {len(names)} restaurants: {spans}")

    def test_long_restaurant_names_are_shortened_under_the_bars(self):
        self.assertEqual(_short("KFC"), "KFC")
        short = _short("PVR Café – Popcorn, Pizza, Hot Dogs & Snacks")
        self.assertLessEqual(len(short), 24)
        self.assertTrue(short.startswith("PVR Café"))
