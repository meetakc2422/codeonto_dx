"""A shared report link: short (/r/<code>), no login, the readable file name kept beside the file, an older long link still works, and it expires."""

import os
import tempfile
import time
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.masters.models import Industry
from apps.outlets.models import Brand, Client
from . import report


class SharedReportLinkTests(TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.brand = Brand.objects.create(client=Client.objects.create(name="T"), name="Report Brand", industry=Industry.objects.first())
        self.api = APIClient()
        self.api.force_authenticate(get_user_model().objects.create_user("ops", password="x", is_staff=True))

    def share(self, name="Report Brand - Performance report - 20 Nov to 26 Nov 2026.pdf"):
        with override_settings(SHARED_REPORTS_DIR=self.dir), mock.patch.object(report, "_pdf_bytes", return_value=(b"%PDF-1.4 test", "2026-11-20", "2026-11-26")):
            return self.api.post(f"/api/brands/{self.brand.id}/report/share?name={name}")

    def test_the_link_is_short_and_serves_the_pdf_under_the_readable_name(self):
        path = self.share().json()["path"]
        self.assertRegex(path, r"^/r/[A-Za-z0-9_-]{22}$")  # no file name in the address
        with override_settings(SHARED_REPORTS_DIR=self.dir):
            r = APIClient().get(path)  # no login
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"%PDF-1.4 test")
        self.assertIn('filename="Report Brand - Performance report - 20 Nov to 26 Nov 2026.pdf"', r["Content-Disposition"])
        self.assertIn("filename*=UTF-8''", r["Content-Disposition"])

    def test_an_unsafe_name_is_cleaned_and_a_missing_one_falls_back(self):
        path = self.share(name='a/../b"<x>.pdf').json()["path"]
        with override_settings(SHARED_REPORTS_DIR=self.dir):
            r = APIClient().get(path)
        self.assertNotIn("/", r["Content-Disposition"].split("filename=")[1].split(";")[0].strip('"'))
        with override_settings(SHARED_REPORTS_DIR=self.dir), mock.patch.object(report, "_pdf_bytes", return_value=(b"x", "2026-11-20", "2026-11-26")):
            path2 = self.api.post(f"/api/brands/{self.brand.id}/report/share").json()["path"]
            r2 = APIClient().get(path2)
        self.assertIn("report_2026-11-20_to_2026-11-26.pdf", r2["Content-Disposition"])

    def test_an_older_long_link_still_works(self):
        token = self.share().json()["path"].split("/")[2]
        with override_settings(SHARED_REPORTS_DIR=self.dir):
            self.assertEqual(APIClient().get(f"/r/{token}/anything.pdf").status_code, 200)

    def test_it_stops_working_after_the_days_are_up(self):
        token = self.share().json()["path"].split("/")[2]
        f = Path(self.dir) / f"{token}.pdf"
        old = time.time() - (report.SHARE_DAYS + 1) * 86400
        os.utime(f, (old, old))
        with override_settings(SHARED_REPORTS_DIR=self.dir):
            self.assertEqual(APIClient().get(f"/r/{token}").status_code, 404)
            self.assertEqual(APIClient().get("/r/not-a-real-code").status_code, 404)
