"""Every row of the Zomato and Swiggy business reports is kept, mapped to a KPI or not. Run from collector/:
    ./.venv/bin/python -m unittest tests.test_business_rows
"""

import io
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from openpyxl import Workbook  # noqa: E402

from swiggy import business as swiggy  # noqa: E402
from zomato import business as zomato  # noqa: E402


class FakeResponse:
    status_code = 200

    def __init__(self, payload=None, content=b""):
        self._payload, self.content = payload, content

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


class ZomatoRows(unittest.TestCase):
    PAYLOAD = {"data": {"sections": [
        {"heading": {"value": "Sales overview"}, "row_data": [{"metric": {"value": "Sales"}, "20261026": {"value": "₹30,164"}, "20261027": {"value": "₹1.2 L"}}]},
        {"heading": {"value": "Customer segmentation"}, "row_data": [
            {"metric": {"value": "New users"}, "20261026": {"value": "12"}, "20261027": {"value": "-"}},
            {"metric": {"value": "Repeat users"}, "20261026": {"value": "30"}, "child_rows": [{"metric": {"value": "Lapsed users"}, "20261026": {"value": "7"}}]}]}]}}

    def fetch(self, keep):
        with mock.patch("requests.post", return_value=FakeResponse(self.PAYLOAD)), mock.patch("time.sleep"):
            return zomato._fetch({"csrf": "x"}, "123", date(2026, 10, 26), date(2026, 10, 27), keep=keep)

    def test_unmapped_rows_are_kept(self):
        keep = []
        self.fetch(keep)
        rows = {(s, m, d): (text, v) for s, m, d, text, v in keep}
        self.assertEqual(rows[("Customer segmentation", "New users", date(2026, 10, 26))], ("12", 12.0))
        self.assertEqual(rows[("Customer segmentation", "New users", date(2026, 10, 27))], ("-", None))  # a dash stays a dash, with no number
        self.assertEqual(rows[("Customer segmentation", "Lapsed users", date(2026, 10, 26))], ("7", 7.0))  # a row inside another row is kept too
        self.assertEqual(rows[("Sales overview", "Sales", date(2026, 10, 27))], ("₹1.2 L", 120000.0))

    def test_mapped_figures_are_unchanged_and_keep_is_optional(self):
        keep = []
        with_keep, without = self.fetch(keep), self.fetch(None)
        self.assertEqual(with_keep, without)
        self.assertNotIn(("Customer segmentation", "New users"), without)  # the mapped result still holds only the mapped rows


class SwiggyRows(unittest.TestCase):
    def sheet(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Restaurant ID", "Overview", "Metric", "26th Oct 2026", "27th Oct 2026"])
        ws.append([385109, "SALES", "Net Sales", "₹2,000", "₹3,000"])
        ws.append([385109, "CUSTOMERS", "New Customers", "5", "6"])
        ws.append([1359553, "CUSTOMERS", "New Customers", "9", "-"])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def test_every_row_of_every_outlet_is_kept(self):
        keep = {}
        with mock.patch("requests.get", return_value=FakeResponse(content=self.sheet())):
            swiggy._read("http://x", keep=keep)
        rows = {(s, m, d): (text, v) for s, m, d, text, v in keep[385109]}
        self.assertEqual(rows[("CUSTOMERS", "New Customers", date(2026, 10, 27))], ("6", 6.0))
        self.assertEqual(rows[("SALES", "Net Sales", date(2026, 10, 26))], ("₹2,000", 2000.0))
        other = {(s, m, d): (text, v) for s, m, d, text, v in keep[1359553]}
        self.assertEqual(other[("CUSTOMERS", "New Customers", date(2026, 10, 27))], ("-", None))


if __name__ == "__main__":
    unittest.main()
