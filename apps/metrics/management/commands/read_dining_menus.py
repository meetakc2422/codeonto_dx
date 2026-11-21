"""Read dining menu page images into dishes and prices (`dining_menu_items`).

The collector keeps `dining_menu_pages` current; this reads each page it has not read yet with a vision model. A page is read once:
when the restaurant replaces an image it gets a new file name and shows up as a new page.

    manage.py read_dining_menus              # all unread pages
    manage.py read_dining_menus --res-id 19635463 --limit 3 --dry-run
"""

import base64
import json
import re
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.metrics.models import DiningMenuItem, DiningMenuPage

PROMPT = """This is one page of a restaurant's dine-in menu. List every dish with its price.
Reply with ONLY a JSON array, no other text. Each element: {"section": "<heading the dish is under, e.g. Pizzas>", "name": "<dish name>", "price": <number in rupees, no symbol>, "note": "<size or variant such as Half, Full, 12 inch, or empty>"}.
If a dish has several prices (sizes), give one element per size with the size in "note". Skip taxes, notes, addresses and drinks-only lists with no prices. If the page has no dishes, reply []."""


def read_page(url: str) -> list[dict]:
    img = requests.get(url, timeout=60)
    img.raise_for_status()
    media = img.headers.get("content-type", "image/png").split(";")[0]
    if media not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        media = "image/jpeg" if url.lower().endswith((".jpg", ".jpeg")) else "image/png"
    body = {"model": settings.DINING_MENU_MODEL, "max_tokens": 4096, "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(img.content).decode()}},
        {"type": "text", "text": PROMPT}]}]}
    r = requests.post("https://api.anthropic.com/v1/messages", json=body, timeout=120,
                      headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
    m = re.search(r"\[.*\]", text, re.S)
    return json.loads(m.group(0)) if m else []


def _price(v):
    try:
        return Decimal(str(v).replace(",", "")) if v not in (None, "") else None
    except InvalidOperation:
        return None


class Command(BaseCommand):
    help = "Read unread dining menu page images into dishes and prices."

    def add_arguments(self, p):
        p.add_argument("--res-id")
        p.add_argument("--limit", type=int)
        p.add_argument("--dry-run", action="store_true", help="print what was read, save nothing")
        p.add_argument("--again", action="store_true", help="read pages that were already read")

    def handle(self, *a, **o):
        if not settings.ANTHROPIC_API_KEY:
            raise CommandError("ANTHROPIC_API_KEY is not set")
        pages = DiningMenuPage.objects.order_by("res_id", "position")
        if not o["again"]:
            pages = pages.filter(read_at__isnull=True)
        if o["res_id"]:
            pages = pages.filter(res_id=o["res_id"])
        if o["limit"]:
            pages = pages[: o["limit"]]
        done = 0
        for pg in pages:
            try:
                rows = read_page(pg.image_url)
            except Exception as e:
                pg.read_error = str(e)[:300]
                if not o["dry_run"]:
                    pg.save(update_fields=["read_error"])
                self.stderr.write(f"{pg.res_id} page {pg.position + 1}: {e}")
                continue
            items = [DiningMenuItem(page=pg, res_id=pg.res_id, outlet_id=pg.outlet_id, section=str(r.get("section") or "")[:120],
                                    name=str(r.get("name") or "")[:255], price=_price(r.get("price")), note=str(r.get("note") or "")[:160])
                     for r in rows if isinstance(r, dict) and r.get("name")]
            self.stdout.write(f"{pg.res_id} page {pg.position + 1}: {len(items)} dishes")
            if o["dry_run"]:
                for i in items[:40]:
                    self.stdout.write(f"   {i.section[:18]:18} {i.name[:42]:42} {i.price}  {i.note}")
                continue
            pg.items.all().delete()
            DiningMenuItem.objects.bulk_create(items)
            pg.read_at, pg.read_error = timezone.now(), ""
            pg.save(update_fields=["read_at", "read_error"])
            done += 1
        self.stdout.write(f"Read {done} pages.")
