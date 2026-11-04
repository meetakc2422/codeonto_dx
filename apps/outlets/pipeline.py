"""Read-only access to the restaurant-data-pipeline database (settings.PIPELINE_DATABASE_URL).

The pipeline numbers platforms 1 = Zomato, 2 = Swiggy; this module is the only place that knows it.
"""

import re
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from django.conf import settings

PIPELINE_PLATFORM_IDS = {"zomato": "1", "swiggy": "2"}


@contextmanager
def pipeline_cursor():
    with psycopg.connect(settings.PIPELINE_DATABASE_URL, row_factory=dict_row) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            yield cur


def marketplace_outlets(platform: str) -> list[dict]:
    with pipeline_cursor() as cur:
        cur.execute(
            """SELECT res_id AS external_id, name, subzone AS area, city, is_active
               FROM restaurants_restaurantmetadata WHERE platform_id = %s""",
            (PIPELINE_PLATFORM_IDS[platform],),
        )
        return cur.fetchall()


def google_locations() -> list[dict]:
    with pipeline_cursor() as cur:
        cur.execute(
            """SELECT location_id AS external_id, MAX(location_name) AS name, MAX(city) AS city,
                      MAX(address) AS address, bool_or(is_active) AS is_active
               FROM (SELECT location_id, location_name, city, address, true AS is_active FROM google_location_mapping
                     UNION ALL
                     SELECT location_id, location_name, city, address, is_active FROM google_client_location_mapping) g
               WHERE location_id IS NOT NULL GROUP BY location_id"""
        )
        return cur.fetchall()


def name_key(s: str | None) -> str:
    """Spelling-insensitive key: 'Mister Kiyoshi-Asia in a box' == 'Mister Kiyoshi - Asia In A Box'."""
    return re.sub(r"[^a-z0-9]+", "", re.sub(r"[’']", "", (s or "").lower()))


CITY_ALIASES = {"gurgaon": "gurugram", "delhincr": "delhi", "newdelhi": "delhi", "bangalore": "bengaluru", "bombay": "mumbai"}


def city_key(s: str | None) -> str:
    k = name_key(s)
    return CITY_ALIASES.get(k, k)
