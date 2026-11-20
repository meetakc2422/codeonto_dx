"""Make (or remove) a sample client with made-up outlets and made-up data, for demos and load tests.

    python manage.py seed_demo_client                  # "Demo Client 1": one brand, 200 outlets, 45 days of data
    python manage.py seed_demo_client --outlets 500 --days 60
    python manage.py seed_demo_client --reset          # delete the sample client first, then make it again (also moves the dates up to today)
    python manage.py seed_demo_client --login client1 --password '...'   # a read-only customer-style login to show people (--role admin for more)
    python manage.py seed_demo_client --remove         # delete the sample client and everything made for it

Nothing here touches a real client. Safety:
- the client is marked is_demo, the dashboard says SAMPLE DATA next to the brand, and the collector's data-health email skips it;
- its platform ids are written DEMO-Z-0001 / DEMO-S-0001 and stored as inactive catalog rows, so no collector job ever tries to
  fetch them, and no real id can collide with them;
- it has no alert recipients, so no message is ever sent for it;
- all names, reviews, orders and figures are invented.
"""

import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.billing.models import Plan, Subscription
from apps.insights.models import ItemSalesDaily
from apps.listings.models import ListingProfile
from apps.masters.models import Industry, Kpi
from apps.metrics.models import MetricDaily
from apps.orders.models import OrderLine
from apps.outlets.models import Brand, BrandOutlet, Client, ClientUser, SwiggyOutlet, ZomatoOutlet
from apps.payouts.models import PayoutCycle
from apps.reviews.models import Review
from apps.stockouts.models import StockOut
from apps.uptime.models import OfflineEpisode, UptimeDaily

IST = timezone(timedelta(hours=5, minutes=30))
CLIENT_NAME = "Demo Client 1"
BRAND_NAME = "Sample Kitchen Co"
Z_PREFIX, S_PREFIX = "DEMO-Z-", "DEMO-S-"

CITIES = {
    "Delhi NCR": ["Rajouri Garden", "Saket", "Connaught Place", "Dwarka", "Rohini", "Lajpat Nagar", "Vasant Kunj", "Pitampura", "Janakpuri", "Karol Bagh",
                  "Sector 15 Noida", "Sector 62 Noida", "DLF Phase 3", "Sohna Road", "Golf Course Road", "Indirapuram", "Vaishali", "Mayur Vihar"],
    "Mumbai": ["Andheri West", "Bandra Kurla Complex", "Powai", "Borivali West", "Thane West", "Navi Mumbai Vashi", "Dadar", "Lower Parel", "Malad", "Goregaon"],
    "Bengaluru": ["Indiranagar", "Koramangala", "HSR Layout", "Whitefield", "Jayanagar", "Marathahalli", "Bellandur", "Electronic City", "Hebbal", "JP Nagar"],
    "Hyderabad": ["Banjara Hills", "Gachibowli", "Madhapur", "Kukatpally", "LB Nagar", "Secunderabad", "Jubilee Hills", "Manikonda"],
    "Pune": ["Baner", "Kothrud", "Viman Nagar", "Hinjewadi", "Wakad", "Koregaon Park", "Aundh"],
    "Chennai": ["Anna Nagar", "T Nagar", "Velachery", "Porur", "Adyar", "OMR Perungudi", "Tambaram"],
    "Kolkata": ["Salt Lake", "Park Street", "New Town", "Howrah", "Ballygunge"],
    "Ahmedabad": ["Satellite", "Navrangpura", "Bopal", "Prahlad Nagar"],
}
ITEMS = [("Classic Burger", "Burgers", 179), ("Cheese Burger", "Burgers", 219), ("Peri Peri Fries", "Sides", 129), ("Chicken Wings", "Starters", 249),
         ("Veg Wrap", "Wraps", 159), ("Paneer Tikka Wrap", "Wraps", 189), ("Chocolate Shake", "Beverages", 169), ("Cold Coffee", "Beverages", 149),
         ("Loaded Nachos", "Sides", 199), ("Chicken Biryani", "Rice", 289), ("Veg Pizza", "Pizza", 299), ("Brownie", "Desserts", 119)]
REVIEWS = {  # rating band -> sentences (made up; the words are chosen so the dashboard's topic filters find them)
    5: ["Great taste and fresh food, delivered hot.", "Loved the burger, perfect portion and tasty.", "Quick delivery and neat packaging. Will order again.",
        "Best value in the area, really tasty.", "Fresh, hot and well packed. Five stars."],
    4: ["Good food, a little late but worth it.", "Tasty and fresh, packaging could be better.", "Nice taste, portion size is fair.", "Good value for the price."],
    3: ["Average taste, food was lukewarm.", "Okay food but the delivery took long.", "Portion was small for the price.", "Decent, nothing special."],
    2: ["Food was cold and the packaging had spilled.", "A burger was missing from the order.", "Very late delivery and the food was stale.", "Tasteless and oily, not worth the price."],
    1: ["Terrible taste, food was cold and stale.", "Item missing and delivery was very late.", "Raw and undercooked, packaging leaked everywhere.",
        "Worst order ever, bland and cold.", "Found a hair in the food, very upset."],
}
FIRST = ["Aarav", "Diya", "Rohan", "Isha", "Kabir", "Meera", "Vikram", "Anaya", "Arjun", "Sara", "Neel", "Tara", "Rahul", "Priya", "Karan", "Nisha"]
LAST = ["S.", "K.", "M.", "R.", "P.", "G.", "T.", "D."]
LISTING_ISSUES = [("no_description", "Add a business description"), ("few_photos", "Add more photos (fewer than 10 now)"),
                  ("no_recent_post", "Post an update (none in the last 30 days)"), ("no_website", "Add a website link"), ("one_category", "Add secondary categories")]


def d4(x):
    return Decimal(str(round(float(x), 4)))


def d2(x):
    return Decimal(str(round(float(x), 2)))


class Command(BaseCommand):
    help = "Make or remove a sample client with made-up outlets and data (for demos and load tests)"

    def add_arguments(self, p):
        p.add_argument("--outlets", type=int, default=200)
        p.add_argument("--days", type=int, default=45, help="days of daily data, ending yesterday")
        p.add_argument("--reset", action="store_true", help="remove the sample client first, then make it again")
        p.add_argument("--remove", action="store_true", help="remove the sample client and everything made for it, then stop")
        p.add_argument("--login", help="also make a login with this username for the sample client (read-only unless --role says otherwise)")
        p.add_argument("--password", help="its password (give it here; it is not kept in the code)")
        p.add_argument("--role", default="viewer", choices=["viewer", "manager", "admin"], help="what that login may do (default viewer: reads everything, changes nothing)")
        p.add_argument("--seed", type=int, default=7, help="same seed, same data")

    def handle(self, *a, **o):
        if o["remove"] or o["reset"]:
            self.remove()
            if o["remove"]:
                return
        if Client.objects.filter(name=CLIENT_NAME).exists():
            raise CommandError(f"'{CLIENT_NAME}' already exists. Use --reset to make it again, or --remove.")
        if o["login"] and not o["password"]:
            raise CommandError("--login needs --password")
        self.rng = random.Random(o["seed"])
        self.n, self.days = o["outlets"], o["days"]
        self.yesterday = datetime.now(IST).date() - timedelta(days=1)
        self.day_list = [self.yesterday - timedelta(days=i) for i in range(self.days - 1, -1, -1)]
        with transaction.atomic():
            client, brand, outlets = self.make_client(o)
            self.stdout.write(f"{len(outlets)} outlets made; making their data ...")
            self.make_metrics_and_reviews(outlets)
            self.make_stockouts_and_uptime(outlets)
            self.make_orders(outlets)
            self.make_payouts(outlets)
            self.make_item_sales(outlets)
            self.make_listings(outlets)
        self.stdout.write(self.style.SUCCESS(f"Done: '{CLIENT_NAME}', brand '{BRAND_NAME}', {len(outlets)} outlets, {self.days} days of data."))
        self.stdout.write("Open it by choosing the brand in the top bar (staff logins see every client).")

    # ---------- remove ----------
    def remove(self):
        with transaction.atomic():
            for client in Client.objects.filter(name=CLIENT_NAME, is_demo=True):
                User = get_user_model()
                user_ids = list(ClientUser.objects.filter(client=client).values_list("user_id", flat=True))
                for brand in client.brands.all():
                    brand.delete()  # its outlets and everything recorded for them go with it
                client.delete()
                User.objects.filter(pk__in=user_ids, is_staff=False, is_superuser=False).delete()
            ZomatoOutlet.objects.filter(res_id__startswith=Z_PREFIX).delete()
            SwiggyOutlet.objects.filter(swiggy_id__startswith=S_PREFIX).delete()
        self.stdout.write("Sample client removed.")

    # ---------- the client, brand, outlets ----------
    def make_client(self, o):
        rng = self.rng
        client = Client.objects.create(name=CLIENT_NAME, is_demo=True, contact_name="Sample Owner", contact_email="")
        industry = Industry.objects.get(code="restaurant")
        brand = Brand.objects.create(client=client, name=BRAND_NAME, industry=industry)
        plan = Plan.objects.filter(code="pro").first()
        if plan:
            Subscription.objects.create(client=client, plan=plan, status="active", cycle="monthly", outlet_limit=max(self.n, 250))
        if o["login"]:
            user = get_user_model().objects.create_user(o["login"], password=o["password"])
            ClientUser.objects.create(user=user, client=client, role=o["role"])
        pairs = [(city, area) for city, areas in CITIES.items() for area in areas]
        rng.shuffle(pairs)
        while len(pairs) < self.n:  # more outlets than areas: a second branch in the same area
            pairs += [(c, f"{a} 2") for c, a in pairs[:self.n - len(pairs)]]
        outlets = []
        for i in range(self.n):
            city, area = pairs[i]
            has_swiggy = rng.random() < 0.7
            z = ZomatoOutlet.objects.create(res_id=f"{Z_PREFIX}{i + 1:04d}", name=BRAND_NAME, city=city, area=area, client=client, is_active=False)
            s = SwiggyOutlet.objects.create(swiggy_id=f"{S_PREFIX}{i + 1:04d}", name=BRAND_NAME, city=city, area=area, client=client, is_active=False) if has_swiggy else None
            bo = BrandOutlet.objects.create(brand=brand, outlet_name=BRAND_NAME, area=area, city=city, zomato=z, swiggy=s)
            quality = min(1.0, max(0.05, rng.gauss(0.72, 0.18)))
            if rng.random() < 0.1:
                quality = rng.uniform(0.05, 0.35)  # the problem outlets every chain has
            outlets.append({"o": bo, "scale": min(2.2, max(0.4, rng.lognormvariate(0, 0.35))), "quality": quality, "swiggy": has_swiggy,
                            "ads": rng.random() < 0.6, "hyperpure": rng.random() < 0.4, "city": city, "area": area, "menu": self.make_menu()})
        return client, brand, outlets

    def make_menu(self):
        """7-10 dishes with popularity weights (a few sell most): [(name, category, price, weight)]. The same menu drives the item sales,
        the stock-outs and the orders, so a stock-out of a best seller has real sales to lose."""
        dishes = self.rng.sample(ITEMS, self.rng.randint(7, 10))
        return [(n, c, p, 1 / (i + 1) ** 0.9) for i, (n, c, p) in enumerate(dishes)]

    # ---------- daily KPIs and reviews ----------
    def make_metrics_and_reviews(self, outlets):
        rng = self.rng
        kpi = {k.code: k.id for k in Kpi.objects.all()}
        rows, reviews = [], []
        by_day = {}  # (outlet id, platform, day) -> [ratings]
        review_no = 0
        for og in outlets:
            for plat in ("zomato", "swiggy"):
                if plat == "swiggy" and not og["swiggy"]:
                    continue
                base = (24 if plat == "zomato" else 16) * og["scale"]
                for day in self.day_list:
                    wk = 1.25 if day.weekday() >= 4 else 0.9
                    trend = 1 + 0.004 * (day - self.day_list[0]).days  # a gentle climb over the period
                    orders = max(0, round(base * wk * trend * rng.uniform(0.75, 1.25)))
                    aov = rng.uniform(280, 380)
                    gross = orders * aov * 1.22
                    net = gross * 0.78
                    cancel = round(orders * rng.uniform(0.003, 0.05 + (0.04 if og["quality"] < 0.4 else 0)))
                    delayed = min(40, rng.uniform(3, 14) + (1 - og["quality"]) * 22)
                    prep = int((rng.uniform(8, 13) + (1 - og["quality"]) * 8) * 60)
                    online = min(100, rng.uniform(93, 100) - (1 - og["quality"]) * 8)
                    impressions = int(orders * rng.uniform(70, 110))
                    views = int(impressions * rng.uniform(0.12, 0.18))
                    carts = int(views * rng.uniform(0.3, 0.4))
                    f_orders = int(orders * rng.uniform(1.0, 1.08))
                    disc = gross * rng.uniform(0.10, 0.22 + (0.08 if og["quality"] < 0.4 else 0))
                    disc_orders = int(orders * rng.uniform(0.4, 0.7))
                    w = max(orders, 1)
                    vals = [("delivered_orders", orders, 1), ("avg_order_value", aov, w), ("net_revenue", net, 1),
                            ("online_pct", online, w), ("avg_prep_time", prep, w), ("mfr_accuracy", rng.uniform(72, 96), w),
                            ("delayed_orders_pct", delayed, w), ("cancellation_rate", cancel / w * 100, w), ("cancellation_loss", cancel * aov, 1),
                            ("impressions", impressions, 1), ("menu_views", views, 1), ("add_to_cart", carts, 1), ("funnel_orders", f_orders, 1),
                            ("menu_to_order_pct", f_orders / max(views, 1) * 100, max(views, 1)),
                            ("discount_given", disc, 1), ("discounted_orders", disc_orders, 1), ("discount_per_order", disc / max(disc_orders, 1), max(disc_orders, 1)),
                            ("discount_pct_revenue", disc / max(gross, 1) * 100, w)]
                    if plat == "zomato":
                        vals.append(("gross_revenue", gross, 1))
                    if og["ads"]:
                        spend = gross * rng.uniform(0.03, 0.07)
                        roi = rng.uniform(2.0, 7.5)
                        vals += [("ad_spend", spend, 1), ("ad_sales", spend * roi, 1), ("ad_orders", int(spend * roi / aov), 1),
                                 ("ad_impressions", int(spend * rng.uniform(60, 120)), 1), ("ad_roi", roi, max(spend, 1))]
                    for code, value, weight in vals:
                        if code in kpi:
                            rows.append(MetricDaily(outlet=og["o"], platform_id=plat, kpi_id=kpi[code], metric_date=day, value=d4(value), weight=d4(weight)))
                # reviews: about one every 3 days per outlet and platform, worse where the outlet is weak
                n_reviews = max(2, int(self.days / 3 * og["scale"] * rng.uniform(0.6, 1.2)))
                for _ in range(n_reviews):
                    r = rng.random()
                    q = og["quality"]
                    stars = 5 if r < q * 0.55 else 4 if r < q * 0.55 + 0.15 else 3 if r < 0.8 else 2 if r < 0.9 else 1
                    at = datetime.combine(rng.choice(self.day_list), time(rng.randint(10, 23), rng.randint(0, 59)), tzinfo=IST)
                    older = (self.yesterday - at.date()).days > 3
                    status = "replied" if older and rng.random() < 0.45 else "pending"
                    review_no += 1
                    reviews.append(Review(outlet=og["o"], platform_id=plat, external_review_id=f"demo-{plat[0]}-{review_no}",
                                          author_name=f"{rng.choice(FIRST)} {rng.choice(LAST)}", rating=Decimal(stars), title="",
                                          body=rng.choice(REVIEWS[stars]) if rng.random() > 0.2 else "",
                                          sentiment="positive" if stars >= 4 else "neutral" if stars == 3 else "negative",
                                          reviewed_at=at, reply_status=status, raw={}))
                    by_day.setdefault((og["o"].id, plat, at.date()), []).append((stars, status))
        # review KPIs follow the reviews
        for (oid, plat, day), items in by_day.items():
            n = len(items)
            stars = [s for s, _ in items]
            for code, value, weight in (("review_count", n, 1), ("avg_rating", sum(stars) / n, n), ("negative_review_count", sum(1 for s in stars if s <= 2), 1),
                                        ("positive_review_pct", sum(1 for s in stars if s >= 4) / n * 100, n),
                                        ("response_rate", sum(1 for _, st in items if st == "replied") / n * 100, n)):
                if code in kpi:
                    rows.append(MetricDaily(outlet_id=oid, platform_id=plat, kpi_id=kpi[code], metric_date=day, value=d4(value), weight=d4(weight)))
        MetricDaily.objects.bulk_create(rows, batch_size=5000)
        Review.objects.bulk_create(reviews, batch_size=2000)
        self.stdout.write(f"  {len(rows)} daily KPI rows, {len(reviews)} reviews")

    # ---------- stock-outs, offline time, uptime ----------
    def make_stockouts_and_uptime(self, outlets):
        rng = self.rng
        kpi = {k.code: k.id for k in Kpi.objects.all()}
        stock, episodes, uptime, kpis = [], [], [], []
        now = datetime.now(IST)
        self.eps = {}  # (outlet id, platform) -> [(item, from, until)], read by make_orders
        for og in outlets:
            for plat in ("zomato", "swiggy"):
                if plat == "swiggy" and not og["swiggy"]:
                    continue
                active_items = set()
                eps = self.eps.setdefault((og["o"].id, plat), [])
                for _ in range(rng.randint(2, 7) + (4 if og["quality"] < 0.4 else 0)):
                    name, cat, _price, _w = rng.choices(og["menu"], weights=[m[3] ** 0.5 for m in og["menu"]])[0]
                    day = rng.choice(self.day_list[-30:])
                    start = datetime.combine(day, time(rng.randint(9, 21), rng.randint(0, 59)), tzinfo=IST)
                    hour = start.hour
                    meal = "Breakfast" if hour < 12 else "Lunch" if hour < 16 else "Snacks" if hour < 19 else "Dinner" if hour < 23 else "Late Night"
                    still_out = day >= self.yesterday - timedelta(days=1) and name not in active_items and rng.random() < 0.5
                    if still_out:
                        active_items.add(name)
                        eps.append((name, start, now + timedelta(days=1)))
                        stock.append(StockOut(outlet=og["o"], platform_id=plat, item_name=name, category=cat, back_at="", mealtime=meal, is_active=True,
                                              log_date=day, first_detected_at=start, last_detected_at=now, restored_at=None, downtime_minutes=None))
                    else:
                        mins = rng.randint(25, 420)
                        eps.append((name, start, start + timedelta(minutes=mins)))
                        stock.append(StockOut(outlet=og["o"], platform_id=plat, item_name=name, category=cat, back_at="", mealtime=meal, is_active=False,
                                              log_date=day, first_detected_at=start, last_detected_at=start + timedelta(minutes=mins),
                                              restored_at=start + timedelta(minutes=mins), downtime_minutes=mins))
            # offline time is a Zomato monitor; weak outlets go offline more
            offline_days = {d: rng.randint(20, 240) for d in rng.sample(self.day_list, min(len(self.day_list), rng.randint(1, 3 + int((1 - og["quality"]) * 8))))}
            for day in self.day_list:
                checks = rng.randint(120, 150)
                down = offline_days.get(day, 0)
                online_checks = max(0, checks - int(checks * down / 720))
                uptime.append(UptimeDaily(outlet=og["o"], platform_id="zomato", day=day, checks=checks, online_checks=online_checks))
            for day, mins in offline_days.items():
                start = datetime.combine(day, time(rng.randint(11, 20), rng.randint(0, 59)), tzinfo=IST)
                episodes.append(OfflineEpisode(outlet=og["o"], platform_id="zomato", is_active=False, log_date=day, first_detected_at=start,
                                               last_detected_at=start + timedelta(minutes=mins), restored_at=start + timedelta(minutes=mins), downtime_minutes=mins))
                if "offline_events" in kpi:
                    kpis += [MetricDaily(outlet=og["o"], platform_id="zomato", kpi_id=kpi["offline_events"], metric_date=day, value=d4(1), weight=d4(1))]
            if og["quality"] < 0.3 and rng.random() < 0.6:  # a few outlets are offline right now
                start = now - timedelta(minutes=rng.randint(30, 300))
                episodes.append(OfflineEpisode(outlet=og["o"], platform_id="zomato", is_active=True, log_date=start.date(), first_detected_at=start,
                                               last_detected_at=now, restored_at=None, downtime_minutes=0))
        StockOut.objects.bulk_create(stock, batch_size=3000)
        OfflineEpisode.objects.bulk_create(episodes, batch_size=3000)
        UptimeDaily.objects.bulk_create(uptime, batch_size=5000)
        MetricDaily.objects.bulk_create(kpis, batch_size=5000, ignore_conflicts=True)
        self.stdout.write(f"  {len(stock)} stock-outs, {len(episodes)} offline stretches, {len(uptime)} uptime days")

    # ---------- order history: what the sales-lost figures are worked out from ----------
    def make_orders(self, outlets):
        """The last 30 service days of orders (one row per dish per order), with no sales of a dish while it was out of stock, and a few
        orders turned away 'because an item was out of stock'. The stock-outs page learns what each outlet normally sells from these."""
        rng = self.rng
        hours, weights = [11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22], [4, 8, 9, 6, 3, 3, 4, 7, 10, 9, 4]
        meal = lambda h: "Breakfast" if h < 12 else "Lunch" if h < 16 else "Evening Snacks" if h < 19 else "Dinner" if h < 23 else "Late Night Dinner"
        window = self.day_list[-30:]
        total = turned_away = counter = 0
        for og in outlets:
            menu, mw = og["menu"], [m[3] for m in og["menu"]]
            for plat in ("zomato", "swiggy"):
                if plat == "swiggy" and not og["swiggy"]:
                    continue
                eps = self.eps.get((og["o"].id, plat), [])
                lines = []
                base = (10 if plat == "zomato" else 7) * og["scale"]
                for day in window:
                    for _ in range(max(0, round(base * (1.25 if day.weekday() >= 4 else 0.9) * rng.uniform(0.75, 1.25)))):
                        hour = rng.choices(hours, weights)[0]
                        placed = datetime.combine(day, time(hour, rng.randint(0, 59)), tzinfo=IST)
                        picked, seen = [], set()
                        for _i in range(rng.choices([1, 2, 3], [55, 30, 15])[0]):
                            it = rng.choices(menu, mw)[0]
                            if it[0] in seen or any(e[0] == it[0] and e[1] <= placed < e[2] for e in eps):
                                continue  # nobody buys a dish that is out of stock
                            seen.add(it[0])
                            picked.append((it, 2 if rng.random() < 0.12 else 1))
                        if not picked:
                            continue
                        counter += 1
                        oid = f"DEMO{plat[0].upper()}{counter:07d}"
                        sub = sum(q * it[2] for it, q in picked)
                        status = "Delivered" if rng.random() < 0.95 else "Cancelled"
                        for it, q in picked:
                            lines.append(OrderLine(outlet=og["o"], platform_id=plat, order_id=oid, placed_at=placed, order_date=day, mealtime=meal(hour), status=status,
                                                   rejection_reason="", item_name=it[0], quantity=q, unit_price=d2(it[2]) if len(picked) == 1 else None,
                                                   order_subtotal=d2(sub), order_total=d2(sub * 1.05)))
                # orders turned away because an item was out of stock
                for name, a, b in eps:
                    price = next(m[2] for m in menu if m[0] == name)
                    for _ in range(rng.randint(0, 2)):
                        placed = a + (min(b, datetime.now(IST)) - a) * rng.random()
                        service_day = (placed - timedelta(hours=5)).date()
                        if service_day < window[0] or service_day > window[-1]:
                            continue
                        counter += 1
                        turned_away += 1
                        lines.append(OrderLine(outlet=og["o"], platform_id=plat, order_id=f"DEMO{plat[0].upper()}{counter:07d}", placed_at=placed, order_date=service_day,
                                               mealtime=meal(placed.astimezone(IST).hour), status="Rejected", rejection_reason="Item out of stock", item_name=name,
                                               quantity=1, unit_price=d2(price), order_subtotal=d2(price), order_total=d2(price * 1.05)))
                OrderLine.objects.bulk_create(lines, batch_size=3000)
                total += len(lines)
        self.stdout.write(f"  {total} order lines ({turned_away} turned away for stock)")

    # ---------- weekly payouts with a statement each ----------
    def make_payouts(self, outlets):
        rng = self.rng
        today = datetime.now(IST).date()
        monday = today - timedelta(days=today.weekday())
        cycles = []
        for og in outlets:
            for plat in ("zomato", "swiggy"):
                if plat == "swiggy" and not og["swiggy"]:
                    continue
                for w in range(1, 7):  # the six most recent whole weeks
                    start = monday - timedelta(days=7 * w)
                    end = start + timedelta(days=6)
                    orders = max(5, round((24 if plat == "zomato" else 16) * 7 * og["scale"] * rng.uniform(0.8, 1.2)))
                    value = orders * rng.uniform(270, 360)
                    fee_rate = rng.uniform(0.13, 0.15)
                    if plat == "zomato":
                        sections = [("total_order_value", "Net order value (A)", value, [("Item total", value * 0.92), ("Packaging", value * 0.08)]),
                                    ("additions", "Additions (B)", value * rng.uniform(0, 0.01), [("Compensations", None)]),
                                    ("order_level_deductions", "Order level deductions (C)", -value * (fee_rate + rng.uniform(0.05, 0.1)),
                                     [("Service fee", -value * fee_rate), ("Delivery and other charges", None)]),
                                    ("tax_deductions", "Tax deductions (D)", -value * rng.uniform(0.05, 0.09), [("GST on fees", None)]),
                                    ("investments_in_growth", "Investments in growth (E)", -value * (rng.uniform(0.03, 0.08) if og["ads"] else 0), [("Ads", None)]),
                                    ("hyperpure_deductions", "Hyperpure spend (F)", -value * (rng.uniform(0.05, 0.2) if og["hyperpure"] else 0), [("Hyperpure purchases", None)])]
                    else:
                        sections = [("total_customer_paid", "(A) Total Customer Paid", value, [("Item total", value)]),
                                    ("total_fees", "(B) Total Fees", -value * (fee_rate + rng.uniform(0.02, 0.05)), [("Commission", None)]),
                                    ("complaint_cancellation_charges", "(C) Complaint & Cancellation Charges", -value * rng.uniform(0, 0.02), [("Charges", None)]),
                                    ("total_taxes", "(D) Total Taxes", -value * rng.uniform(0.05, 0.08), [("Taxes", None)]),
                                    ("growth_investments_in_ads", "(E) Growth Investments in Ads", -value * (rng.uniform(0.03, 0.08) if og["ads"] else 0), [("Ads", None)]),
                                    ("other_charges_refunds", "(F) Other Charges & Refunds", 0.0, [("Refunds", None)])]
                    breakdown = []
                    for sid, label, total, items in sections:
                        known = sum(v for _, v in items if v is not None)
                        rest = [(l, total - known) for l, v in items if v is None]
                        lines = [{"label": l, "value": round(v, 2)} for l, v in items if v is not None] + [{"label": l, "value": round(v, 2)} for l, v in rest]
                        breakdown.append({"id": sid, "label": label, "value": round(total, 2), "items": lines})
                    net = round(sum(s["value"] for s in breakdown), 2)
                    paid = w >= 2 or rng.random() < 0.6
                    problem = rng.random() < (0.25 if og["quality"] < 0.4 else 0.05)
                    shortfall = round(net * rng.uniform(0.02, 0.06), 2) if problem and paid else 0
                    cycles.append(PayoutCycle(
                        outlet=og["o"], platform_id=plat, start_date=start, end_date=end, payout_date=end + timedelta(days=4), status="PAID" if paid else "TO BE PAID",
                        utr=f"DEMO{rng.randint(10**9, 10**10 - 1)}" if paid else "", net_payout=d2(net - shortfall) if paid else d2(net), order_count=orders,
                        delivered_orders=orders, rejected_orders=0, breakdown=breakdown, orders_total=d2(net), adjustments=d2(0), expected_payout=d2(net) if paid else None,
                        discrepancy=d2(-shortfall) if paid else None, commissionable_total=d2(value), service_fee_total=d2(value * fee_rate),
                        issues=["payout_mismatch"] if shortfall else [], reconciled_at=datetime.now(IST) if paid else None, fetched_at=datetime.now(IST)))
        PayoutCycle.objects.bulk_create(cycles, batch_size=1000)
        self.stdout.write(f"  {len(cycles)} payouts")

    # ---------- item sales (Zomato) ----------
    def make_item_sales(self, outlets):
        rng = self.rng
        rows = []
        for og in outlets:
            for day in self.day_list[-30:]:
                for name, cat, price, w in og["menu"]:
                    qty = max(0, round((2 + 14 * w) * og["scale"] * rng.uniform(0.3, 1.8) * (1.2 if day.weekday() >= 4 else 0.9)))
                    if qty:
                        rows.append(ItemSalesDaily(outlet=og["o"], platform_id="zomato", item_name=name, category=cat, day=day, quantity=d2(qty),
                                                   unit_price=d2(price * rng.uniform(0.97, 1.03)), orders=max(1, int(qty * 0.8)), rating=None))
        ItemSalesDaily.objects.bulk_create(rows, batch_size=5000)
        self.stdout.write(f"  {len(rows)} item-sales rows")

    # ---------- Google listing health ----------
    def make_listings(self, outlets):
        rng = self.rng
        rows = []
        for og in outlets:
            issues = [i for i in LISTING_ISSUES if rng.random() < (0.55 - og["quality"] * 0.4)]
            score = max(30, 100 - 12 * len(issues) - rng.randint(0, 6))
            rows.append(ListingProfile(outlet=og["o"], platform_id="google", title=f"{BRAND_NAME} {og['area']}", phone="", website="" if any(i[0] == "no_website" for i in issues) else "https://example.com",
                                       primary_category="Restaurant", extra_categories=0 if any(i[0] == "one_category" for i in issues) else 2,
                                       has_description=not any(i[0] == "no_description" for i in issues), has_hours=True, open_status="OPEN",
                                       photo_count=rng.randint(2, 9) if any(i[0] == "few_photos" for i in issues) else rng.randint(12, 80),
                                       last_post_at=None if any(i[0] == "no_recent_post" for i in issues) else datetime.now(IST) - timedelta(days=rng.randint(1, 20)),
                                       health_score=score, issues=[{"code": c, "label": l} for c, l in issues], fetched_at=datetime.now(IST)))
        ListingProfile.objects.bulk_create(rows, batch_size=1000)
        self.stdout.write(f"  {len(rows)} Google listing profiles")
