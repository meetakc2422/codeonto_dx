"""Starter master data. Lives in the database afterwards and is edited in admin;
existing rows are never overwritten by this migration."""

from django.db import migrations

PLATFORMS = [
    # code, name, category, reviews, replies, orders, store_status
    ("zomato", "Zomato", "marketplace", True, True, True, True),
    ("swiggy", "Swiggy", "marketplace", True, True, True, True),
    ("google", "Google Business Profile", "review", True, True, False, False),
    ("magicpin", "magicpin", "marketplace", True, False, True, True),
    ("eazydiner", "EazyDiner", "review", True, False, False, False),
    ("tripadvisor", "Tripadvisor", "review", True, True, False, False),
    ("booking", "Booking.com", "ota", True, True, False, False),
    ("makemytrip", "MakeMyTrip", "ota", True, True, False, False),
    ("practo", "Practo", "review", True, False, False, False),
    ("justdial", "Justdial", "listing", True, False, False, False),
    ("facebook", "Facebook", "social", True, True, False, False),
    ("instagram", "Instagram", "social", False, True, False, False),
    ("survey", "Codeonto Survey", "survey", True, False, False, False),
]

INDUSTRIES = {
    # code: (name, platforms)
    "restaurant": ("Restaurants & QSR", ["zomato", "swiggy", "google", "magicpin", "eazydiner", "facebook", "instagram", "survey"]),
    "cafe_bakery": ("Cafes & Bakeries", ["zomato", "swiggy", "google", "instagram", "survey"]),
    "cloud_kitchen": ("Cloud Kitchens", ["zomato", "swiggy", "google", "magicpin"]),
    "hotel": ("Hotels & Hospitality", ["google", "tripadvisor", "booking", "makemytrip", "facebook", "survey"]),
    "healthcare": ("Hospitals & Clinics", ["google", "practo", "justdial", "facebook", "survey"]),
    "retail": ("Retail Stores", ["google", "justdial", "facebook", "instagram", "survey"]),
    "salon_spa": ("Salons & Spas", ["google", "justdial", "instagram", "survey"]),
}

FOOD = ["restaurant", "cafe_bakery", "cloud_kitchen"]

MODULES = [
    # code, name, scope, industries (None = all)
    ("overview", "Overview", "common", None),
    ("reviews", "Reviews", "common", None),
    ("ai_replies", "AI Replies", "common", None),
    ("listings", "Listings", "common", None),
    ("reports", "Reports", "common", None),
    ("tickets", "Tickets", "common", None),
    ("competitors", "Competitors", "common", None),
    ("alerts", "Alerts", "common", None),
    ("marketplace_sales", "Sales Performance", "industry", FOOD),
    ("marketplace_ops", "Delivery & Operations", "industry", FOOD),
    ("marketplace_funnel", "Customer Funnel", "industry", FOOD),
    ("marketplace_ads", "Ads Performance", "industry", FOOD),
    ("marketplace_discounts", "Discounts & Offers", "industry", FOOD),
    ("store_uptime", "Store Uptime", "industry", FOOD),
    ("stock_outs", "Stock-outs", "industry", FOOD),
    ("reconciliation", "Reconciliation", "industry", FOOD),
]

KPIS = [
    # code, name, module, unit, aggregation, higher_is_better
    ("avg_rating", "Average Rating", "reviews", "rating", "weighted_avg", True),
    ("review_count", "New Reviews", "reviews", "count", "sum", True),
    ("positive_review_pct", "Positive Reviews %", "reviews", "percent", "weighted_avg", True),
    ("negative_review_count", "Negative Reviews", "reviews", "count", "sum", False),
    ("response_rate", "Response Rate", "reviews", "percent", "weighted_avg", True),
    ("listing_rating", "Platform Rating", "listings", "rating", "last", True),
    ("total_reviews", "Total Reviews on Platform", "listings", "count", "last", True),
    ("open_tickets", "Open Tickets", "tickets", "count", "last", False),
    ("delivered_orders", "Delivered Orders", "marketplace_sales", "count", "sum", True),
    ("gross_revenue", "Gross Revenue", "marketplace_sales", "currency", "sum", True),
    ("net_revenue", "Net Revenue", "marketplace_sales", "currency", "sum", True),
    ("avg_order_value", "Avg Order Value", "marketplace_sales", "currency", "weighted_avg", True),
    ("online_pct", "Store Online %", "marketplace_ops", "percent", "weighted_avg", True),
    ("avg_prep_time", "Avg Kitchen Prep Time", "marketplace_ops", "seconds", "weighted_avg", False),
    ("mfr_accuracy", "Food Ready Accuracy (MFR)", "marketplace_ops", "percent", "weighted_avg", True),
    ("delayed_orders_pct", "Delayed Orders %", "marketplace_ops", "percent", "weighted_avg", False),
    ("cancellation_rate", "Cancellation Rate", "marketplace_ops", "percent", "weighted_avg", False),
    ("cancellation_loss", "Revenue Lost to Cancellations", "marketplace_ops", "currency", "sum", False),
    ("impressions", "Impressions", "marketplace_funnel", "count", "sum", True),
    ("menu_views", "Menu Views", "marketplace_funnel", "count", "sum", True),
    ("add_to_cart", "Add to Cart", "marketplace_funnel", "count", "sum", True),
    ("funnel_orders", "Orders Placed", "marketplace_funnel", "count", "sum", True),
    ("menu_to_order_pct", "Menu to Order Conversion", "marketplace_funnel", "percent", "weighted_avg", True),
    ("ad_spend", "Ad Spend", "marketplace_ads", "currency", "sum", False),
    ("ad_sales", "Ad Sales", "marketplace_ads", "currency", "sum", True),
    ("ad_impressions", "Ad Impressions", "marketplace_ads", "count", "sum", True),
    ("ad_orders", "Ad Orders", "marketplace_ads", "count", "sum", True),
    ("ad_roi", "Ad ROI", "marketplace_ads", "ratio", "weighted_avg", True),
    ("discount_given", "Discounts Given", "marketplace_discounts", "currency", "sum", False),
    ("discounted_orders", "Orders with Discounts", "marketplace_discounts", "count", "sum", True),
    ("discount_per_order", "Discount per Order", "marketplace_discounts", "currency", "weighted_avg", False),
    ("discount_pct_revenue", "Discount % of Revenue", "marketplace_discounts", "percent", "weighted_avg", False),
    ("offline_events", "Offline Events", "store_uptime", "count", "sum", False),
    ("avg_downtime", "Avg Downtime", "store_uptime", "minutes", "avg", False),
    ("downtime_revenue_loss", "Est. Revenue Loss (Downtime)", "store_uptime", "currency", "sum", False),
    ("stock_out_items", "Items Out of Stock", "stock_outs", "count", "sum", False),
    ("payout_discrepancy", "Payout Discrepancy", "reconciliation", "currency", "sum", False),
    ("take_rate", "Commission Take Rate", "reconciliation", "percent", "weighted_avg", False),
]


def load(apps, schema_editor):
    Platform = apps.get_model("masters", "Platform")
    Industry = apps.get_model("masters", "Industry")
    Module = apps.get_model("masters", "Module")
    Kpi = apps.get_model("masters", "Kpi")

    for i, (code, name, cat, rev, rep, orders, status) in enumerate(PLATFORMS):
        Platform.objects.get_or_create(code=code, defaults=dict(
            name=name, category=cat, supports_reviews=rev, supports_replies=rep,
            supports_orders=orders, supports_store_status=status, sort_order=i))

    industries = {}
    for code, (name, platforms) in INDUSTRIES.items():
        ind, created = Industry.objects.get_or_create(code=code, defaults={"name": name})
        if created:
            ind.platforms.set(Platform.objects.filter(code__in=platforms))
        industries[code] = ind

    modules = {}
    for i, (code, name, scope, inds) in enumerate(MODULES):
        mod, created = Module.objects.get_or_create(code=code, defaults=dict(name=name, scope=scope, sort_order=i))
        if created:
            mod.industries.set([industries[c] for c in (inds or industries)])
        modules[code] = mod

    for i, (code, name, module, unit, agg, hib) in enumerate(KPIS):
        Kpi.objects.get_or_create(code=code, defaults=dict(
            name=name, module=modules[module], unit=unit, aggregation=agg, higher_is_better=hib, sort_order=i))


class Migration(migrations.Migration):
    dependencies = [("masters", "0001_initial")]
    operations = [migrations.RunPython(load, migrations.RunPython.noop)]
