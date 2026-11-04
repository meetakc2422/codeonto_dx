"""The uptime rules, on the real database inside a transaction that is always rolled back. Run from collector/:
    ./.venv/bin/python -m unittest tests.test_uptime
"""

import os
import sys
import unittest
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from zomato.uptime import sync  # noqa: E402

IST = timezone(timedelta(minutes=330))
# 2026-11-02 is a Monday; open 11:00-23:00 every day
SLOTS = [(d, True, time(11), time(23)) for d in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")]


def at(hour, minute=0, day=2):
    return datetime(2026, 11, day, hour, minute, tzinfo=IST)


class Rollback(Exception):
    pass


class UptimeRules(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(os.environ["CODEONTO_DATABASE_URL"], row_factory=dict_row)
        self.addCleanup(self.conn.close)
        self.addCleanup(self.conn.rollback)
        self.cur = self.conn.cursor()
        self.cur.execute("SELECT id FROM industries LIMIT 1")
        industry = self.cur.fetchone()["id"]
        now = datetime.now(timezone.utc)
        self.cur.execute("""INSERT INTO clients (name, contact_name, contact_email, contact_phone, is_active, created_at, updated_at)
                            VALUES ('zz uptime test', '', '', '', true, %s, %s) RETURNING id""", (now, now))
        client = self.cur.fetchone()["id"]
        self.cur.execute("""INSERT INTO brands (client_id, name, logo_url, industry_id, is_active, created_at, updated_at)
                            VALUES (%s, 'zz', '', %s, true, %s, %s) RETURNING id""", (client, industry, now, now))
        brand = self.cur.fetchone()["id"]
        self.cur.execute("""INSERT INTO brand_outlets (brand_id, outlet_name, area, city, address, is_active, created_at, updated_at)
                            VALUES (%s, 'zz', '', '', '', true, %s, %s) RETURNING id""", (brand, now, now))
        self.outlet = self.cur.fetchone()["id"]

    def check(self, online, when, slots=SLOTS):
        return sync(self.cur, self.outlet, online, when, slots)

    def episodes(self):
        self.cur.execute("SELECT * FROM offline_episodes WHERE outlet_id = %s ORDER BY id", (self.outlet,))
        return self.cur.fetchall()

    def daily(self):
        self.cur.execute("SELECT day, checks, online_checks FROM outlet_uptime_daily WHERE outlet_id = %s ORDER BY day", (self.outlet,))
        return [(r["day"].isoformat(), r["checks"], r["online_checks"]) for r in self.cur.fetchall()]

    def test_online_store_has_no_episode_and_counts_as_up(self):
        self.assertIsNone(self.check(True, at(12)))
        self.assertIsNone(self.check(True, at(12, 5)))
        self.assertEqual(self.episodes(), [])
        self.assertEqual(self.daily(), [("2026-11-02", 2, 2)])

    def test_going_offline_and_back_is_one_episode(self):
        self.assertEqual(self.check(False, at(12)), "offline")
        self.assertIsNone(self.check(False, at(12, 5)))
        self.assertTrue(self.episodes()[0]["is_active"])
        self.assertEqual(self.episodes()[0]["downtime_minutes"], 5)  # keeps growing while it lasts
        self.assertEqual(self.check(True, at(12, 10)), "online")
        e = self.episodes()
        self.assertEqual(len(e), 1)
        self.assertFalse(e[0]["is_active"])
        self.assertEqual(e[0]["downtime_minutes"], 10)
        self.assertEqual(self.daily(), [("2026-11-02", 3, 1)])

    def test_offline_while_closed_is_not_an_episode_or_a_check(self):
        self.assertIsNone(self.check(False, at(2)))
        self.assertEqual(self.episodes(), [])
        self.assertEqual(self.daily(), [])

    def test_only_opening_hours_count_as_downtime(self):
        self.check(False, at(22, 50))
        for minutes in range(0, 60, 25):  # stays offline overnight; the checks keep going
            self.check(False, at(23, minutes))
        when = at(0, 20, day=3)
        while when < at(11, 10, day=3):
            self.check(False, when)
            when += timedelta(minutes=25)
        self.assertEqual(self.check(True, at(11, 10, day=3)), "online")
        self.assertEqual(self.episodes()[0]["downtime_minutes"], 20)  # 10 before closing, 10 after opening

    def test_collector_gap_is_not_downtime(self):
        self.check(False, at(12))
        self.check(False, at(12, 5))
        self.assertIsNone(self.check(True, at(18)))  # we don't know when it came back
        e = self.episodes()
        self.assertFalse(e[0]["is_active"])
        self.assertEqual(e[0]["downtime_minutes"], 5)
        self.assertEqual(e[0]["restored_at"], at(12, 5))

    def test_still_offline_after_gap_starts_a_new_episode(self):
        self.check(False, at(12))
        self.check(False, at(12, 5))
        self.assertEqual(self.check(False, at(18)), "offline")
        e = self.episodes()
        self.assertEqual([x["is_active"] for x in e], [False, True])
        self.assertEqual(e[0]["downtime_minutes"], 5)

    def test_no_saved_hours_counts_as_always_open(self):
        self.assertEqual(self.check(False, at(3), slots=None), "offline")

    def test_late_night_belongs_to_previous_service_day(self):
        self.check(True, at(2, day=3), slots=None)
        self.assertEqual(self.daily(), [("2026-11-02", 1, 1)])


if __name__ == "__main__":
    unittest.main()
