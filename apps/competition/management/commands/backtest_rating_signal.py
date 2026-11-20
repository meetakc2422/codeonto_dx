"""Can an outlet's public rating count predict its orders? A read-only test on our own outlets, where the true orders are known.

    python manage.py backtest_rating_signal                 # real outlets (sample clients are left out), 28-day windows over the last 120 days
    python manage.py backtest_rating_signal --window 14 --days 90

(With --min-windows 1 and one window per outlet, it is a first look across outlets: each outlet's window is predicted from the other
outlets' ratio, which is exactly what a competitor estimate would do.)

For every outlet and platform it takes the rise in the rating count over a window and the orders delivered in the same window. It then
predicts each outlet's orders from its rating rise using the median "orders per new rating" of the OTHER outlets only (an outlet is never
used to predict itself, just as a competitor's own ratio is never known) and reports how far off those predictions are. Nothing is written.

Rating counts: the daily rating_count figure of each platform (kept since 6 Nov 2026; both platforms round big counts, so a short window
on a big outlet shows no change and a longer window or smaller outlets measure better)."""

import statistics
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.metrics.models import MetricDaily


def spearman(xs, ys):
    """Rank correlation, -1 to 1 (no libraries needed)."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def windows_for(counts: dict, orders: dict, start, end, size: int, min_rise: int):
    """[(rating rise, orders)] for each non-overlapping window of `size` days with enough data on both sides."""
    out, d = [], start
    while d + timedelta(days=size) <= end:
        stop = d + timedelta(days=size)
        c0 = next((counts[x] for x in (d + timedelta(days=i) for i in range(0, 3)) if x in counts), None)
        c1 = next((counts[x] for x in (stop - timedelta(days=i) for i in range(0, 3)) if x in counts), None)
        days = [orders[x] for x in (d + timedelta(days=i) for i in range(size)) if x in orders]
        if c0 is not None and c1 is not None and len(days) >= 0.8 * size and c1 - c0 >= min_rise:
            out.append((c1 - c0, sum(days) * size / len(days)))  # fill the few missing days at the same daily pace
        d = stop
    return out


def predict_errors(per_outlet: list[list[tuple[float, float]]]):
    """The % error of predicting each window's orders as rating rise x the median orders-per-rating of OTHER outlets only. That is the real
    situation for a competitor: we never know its own ratio, only what outlets like it show. Needs 3 or more other outlets."""
    errs = []
    for i, samples in enumerate(per_outlet):
        others = [o / r for j, outlet in enumerate(per_outlet) if j != i for r, o in outlet if r > 0]
        if len(per_outlet) - 1 < 3 or len(others) < 3:
            continue
        ratio = statistics.median(others)
        errs += [abs(rise * ratio - orders) / orders * 100 for rise, orders in samples if orders > 0]
    return errs


class Command(BaseCommand):
    help = "Read-only: how well does the growth of the rating count predict an outlet's orders?"

    def add_arguments(self, p):
        p.add_argument("--window", type=int, default=28, help="days per window")
        p.add_argument("--days", type=int, default=120, help="how far back to look")
        p.add_argument("--min-rise", type=int, default=5, help="ignore windows where the count rose by fewer ratings than this")
        p.add_argument("--min-windows", type=int, default=4,
                       help="windows an outlet needs to be used; 1 gives a first look across outlets with just one window each (e.g. --window 7 --days 12 --min-windows 1)")

    def handle(self, *a, **o):
        end = timezone.localdate()
        start = end - timedelta(days=o["days"])
        counts, orders = defaultdict(dict), defaultdict(dict)
        rows = (MetricDaily.objects.filter(outlet__brand__client__is_demo=False, metric_date__gte=start, platform_id__in=("zomato", "swiggy"),
                                           kpi__code__in=("rating_count", "delivered_orders"))
                .values_list("outlet_id", "platform_id", "kpi__code", "metric_date", "value", "weight"))
        for outlet, platform, code, day, value, weight in rows:
            key = (outlet, platform)
            if code == "delivered_orders":
                orders[key][day] = float(value)
            elif code == "rating_count":
                counts[key][day] = float(value)  # the daily rating count, both platforms (Zomato's listing_rating weight is a placeholder before 6 Nov 2026)
        per_platform = defaultdict(list)
        usable = defaultdict(int)
        for key in counts:
            if key not in orders:
                continue
            samples = windows_for(counts[key], orders[key], start, end, o["window"], o["min_rise"])
            if len(samples) >= o["min_windows"]:
                usable[key[1]] += 1
                per_platform[key[1]].append(samples)
        self.stdout.write(f"Windows of {o['window']} days over the last {o['days']} days, to {end}. Sample clients are left out.\n")
        if not per_platform:
            self.stdout.write(f"Not enough history: need outlets with at least {o['min_windows']} window(s) of both rating counts and delivered orders.")
            return
        for platform, outlets in sorted(per_platform.items()):
            flat = [s for samples in outlets for s in samples]
            errs = predict_errors(outlets)
            rho = spearman([s[0] for s in flat], [s[1] for s in flat])
            self.stdout.write(f"\n{platform.title()}: {usable[platform]} outlets, {len(flat)} windows")
            self.stdout.write(f"  does a bigger rating rise go with more orders? rank correlation {rho:.2f}  (1 = always, 0 = no link)" if rho is not None else "  too few windows for a correlation")
            ratios = [o_ / r for r, o_ in flat if r > 0]
            if ratios:
                q = statistics.quantiles(ratios, n=4) if len(ratios) >= 4 else [min(ratios), statistics.median(ratios), max(ratios)]
                self.stdout.write(f"  orders per new rating: median {statistics.median(ratios):.1f}, middle half {q[0]:.1f} to {q[-1]:.1f}")
            if errs:
                within = lambda lim: sum(e <= lim for e in errs) / len(errs) * 100
                self.stdout.write(f"  predicting an outlet from the OTHER outlets: typical error {statistics.median(errs):.0f}%, "
                                  f"within 25%: {within(25):.0f}% of windows, within 50%: {within(50):.0f}%, within 100%: {within(100):.0f}%")
            else:
                self.stdout.write("  need at least 4 outlets to test a prediction from the others")
