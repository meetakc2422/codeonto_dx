"""Turn a platform report into KPI rows. A report is {(section, metric): {day: number}}; the mapping file says which
figures are stored as-is ('direct') and how the rest are derived from them ('derived', evaluated in order).

Derived types:  pct    base x pct / 100               (counts the report only gives as a share)
                ratio  numerator / denominator x scale
                sum    the day's total of several figures
                share  numerator / (numerator + other) x 100
A reference 'kpi:<code>' means a KPI derived earlier in the list. Weight is 'one', 'orders' (the day's orders)
or 'denominator' (ratio only)."""

from datetime import date


def split(label: str) -> tuple[str, str]:
    section, metric = label.split("|", 1)
    return section, metric


def kpi_rows(report: dict, mapping: dict) -> list[tuple]:
    """(kpi code, day, value, weight) for one outlet's report."""
    orders = report.get(split(mapping["orders_metric"]), {})
    weight_of = lambda kind, day, den=None: orders.get(day, 1) if kind == "orders" else (den[day] if kind == "denominator" else 1)
    rows = []
    for label, (code, kind) in mapping["direct"].items():
        rows += [(code, day, v, weight_of(kind, day)) for day, v in report.get(split(label), {}).items()]

    derived: dict[str, dict[date, float]] = {}
    series = lambda ref: derived.get(ref[4:], {}) if ref.startswith("kpi:") else report.get(split(ref), {})
    for d in mapping["derived"]:
        t = d["type"]
        den = None
        if t == "pct":
            pct = series(d["pct"])
            out = {day: round(b * pct[day] / 100) for day, b in series(d["base"]).items() if day in pct}
        elif t == "ratio":
            den = series(d["denominator"])
            out = {day: n / den[day] * d.get("scale", 1) for day, n in series(d["numerator"]).items() if den.get(day)}
        elif t == "sum":
            terms = [series(r) for r in d["terms"]]
            out = {day: sum(s.get(day, 0) for s in terms) for day in set().union(*terms)}
        elif t == "share":
            other = series(d["other"])
            out = {day: n / (n + other.get(day, 0)) * 100 for day, n in series(d["numerator"]).items() if n + other.get(day, 0)}
        else:
            raise ValueError(f"Unknown derived type '{t}'")
        derived[d["kpi"]] = out
        kind = d.get("weight", "one")
        rows += [(d["kpi"], day, v, weight_of(kind, day, den)) for day, v in out.items()]
    return rows


def kpi_codes(mapping: dict) -> set[str]:
    return {code for code, _ in mapping["direct"].values()} | {d["kpi"] for d in mapping["derived"]}


def wanted(mapping: dict) -> set[tuple[str, str]]:
    """Every (section, metric) a parser needs to keep."""
    keys = {split(k) for k in mapping["direct"]} | {split(k) for k in mapping.get("needed", [])}
    return keys | {split(mapping["orders_metric"])}
