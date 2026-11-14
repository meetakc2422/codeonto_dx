from datetime import date, timedelta

from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.masters.models import Kpi
from apps.outlets.access import get_brand, in_scope, outlet_limit, outlet_ids

from .rollups import rollup_review_metrics

# Aggregates metric_daily by each KPI's own rule. 'last' takes each outlet/platform's
# latest value in the window, then sums counts or averages everything else, weighted by each row's weight (1 unless
# set, so a plain average; listing_rating carries its number of ratings so the brand rating is a weighted average).
_AGG_SQL = """
WITH base AS (
  SELECT k.code, k.name, k.unit, k.aggregation, k.higher_is_better, m.code AS module, k.sort_order, md.outlet_id,
         md.metric_date, md.value, COALESCE(md.weight, 1) AS w,
         ROW_NUMBER() OVER (PARTITION BY k.id, md.outlet_id, md.platform {date_part}
                            ORDER BY md.metric_date DESC) AS rn
  FROM metric_daily md
  JOIN kpis k ON k.id = md.kpi_id
  JOIN modules m ON m.id = k.module_id
  JOIN brand_outlets bo ON bo.id = md.outlet_id
  WHERE bo.brand_id = %(brand_id)s
    AND md.metric_date BETWEEN %(start)s AND %(end)s
    AND (%(outlet_id)s::bigint[] IS NULL OR md.outlet_id = ANY(%(outlet_id)s::bigint[]))
    AND (%(allowed)s::bigint[] IS NULL OR md.outlet_id = ANY(%(allowed)s::bigint[]))
    AND (%(platform)s::text IS NULL OR md.platform = %(platform)s)
    AND (%(module)s::text IS NULL OR m.code = %(module)s)
    AND (%(kpi)s::text IS NULL OR k.code = %(kpi)s)
)
SELECT code, name, unit, higher_is_better, module {date_select}{outlet_select},
  CASE aggregation
    WHEN 'sum'          THEN SUM(value)
    WHEN 'avg'          THEN AVG(value)
    WHEN 'weighted_avg' THEN SUM(value * w) / NULLIF(SUM(w), 0)
    WHEN 'max'          THEN MAX(value)
    WHEN 'min'          THEN MIN(value)
    WHEN 'last'         THEN CASE WHEN unit = 'count' THEN SUM(value) FILTER (WHERE rn = 1)
                                  ELSE SUM(value * w) FILTER (WHERE rn = 1) / NULLIF(SUM(w) FILTER (WHERE rn = 1), 0) END
  END AS value
FROM base
GROUP BY code, name, unit, aggregation, higher_is_better, module, sort_order {date_select}{outlet_select}
ORDER BY module, sort_order {date_select}{outlet_select}
"""


def _aggregate(by_date: bool, by_outlet: bool = False, **params) -> list[dict]:
    sql = _AGG_SQL.format(date_part=", md.metric_date" if by_date else "",
                          date_select=", metric_date" if by_date else "", outlet_select=", outlet_id" if by_outlet else "")
    params = {"outlet_id": None, "platform": None, "module": None, "kpi": None, "allowed": None, **params}
    if isinstance(params["outlet_id"], int):  # one outlet passed directly (leaderboard): the SQL takes a list
        params["outlet_id"] = [params["outlet_id"]]
    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [c.name for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    for r in rows:
        r["value"] = float(r["value"]) if r["value"] is not None else None
    return rows


def _range(request) -> tuple[date, date]:
    end = date.fromisoformat(request.query_params["end"]) if request.query_params.get("end") else date.today()
    start = (date.fromisoformat(request.query_params["start"]) if request.query_params.get("start")
             else end - timedelta(days=29))
    return start, end


def _filters(request) -> dict:
    qp = request.query_params
    limit = outlet_limit(request.user)
    return {"outlet_id": outlet_ids(qp.get("outlet_id")),
            "platform": qp.get("platform") or None, "module": qp.get("module") or None,
            "allowed": None if limit is None else sorted(limit)}


@api_view(["GET"])
def brand_kpis(request, brand_id):
    """KPI cards: value for the period and change vs the same-length previous period."""
    get_brand(request.user, brand_id)
    start, end = _range(request)
    if end < start:
        return Response({"detail": "end must be on or after start"}, status=400)
    span = end - start + timedelta(days=1)
    f = _filters(request)
    current = _aggregate(False, brand_id=brand_id, start=start, end=end, **f)
    previous = {r["code"]: r["value"] for r in
                _aggregate(False, brand_id=brand_id, start=start - span, end=start - timedelta(days=1), **f)}
    with connection.cursor() as cur:  # which platforms actually supply each KPI in this window
        cur.execute("""SELECT k.code, array_agg(DISTINCT md.platform ORDER BY md.platform)
                       FROM metric_daily md JOIN kpis k ON k.id = md.kpi_id JOIN brand_outlets bo ON bo.id = md.outlet_id
                       WHERE bo.brand_id = %(b)s AND md.metric_date BETWEEN %(s)s AND %(e)s
                         AND (%(o)s::bigint[] IS NULL OR md.outlet_id = ANY(%(o)s::bigint[])) AND (%(p)s::text IS NULL OR md.platform = %(p)s)
                         AND (%(a)s::bigint[] IS NULL OR md.outlet_id = ANY(%(a)s::bigint[]))
                       GROUP BY k.code""", {"b": brand_id, "s": start, "e": end, "o": f["outlet_id"], "p": f["platform"], "a": f["allowed"]})
        platforms = {code: [p for p in plats if p] for code, plats in cur.fetchall()}
    for r in current:
        r["platforms"] = platforms.get(r["code"], [])
        prev = previous.get(r["code"])
        r["previous_value"] = prev
        r["change_pct"] = (round((r["value"] - prev) / abs(prev) * 100, 2)
                           if prev not in (None, 0) and r["value"] is not None else None)
    return Response({"start": start, "end": end, "kpis": current})


# how far a KPI must move the wrong way before it counts as a drop, by unit: points for percentages, stars for ratings,
# a share of the earlier value for everything else (and a floor on that value, so 2 orders -> 1 isn't an alert)
_MIN_MOVE = {"percent": 5.0, "rating": 0.3}
_MIN_PCT = 20.0
_MIN_BASE = {"count": 20, "currency": 2000, "seconds": 60, "minutes": 2, "ratio": 0.0}


@api_view(["GET"])
def brand_drops(request, brand_id):
    """The biggest wrong-way moves of each outlet's KPIs against the previous period of the same length, worst first:
    [{outlet_id, outlet, city, code, name, module, unit, value, previous, change_pct, severity}]."""
    brand = get_brand(request.user, brand_id)
    start, end = _range(request)
    span = end - start + timedelta(days=1)
    f = _filters(request)
    cur = _aggregate(False, True, brand_id=brand_id, start=start, end=end, **f)
    prev = {(r["outlet_id"], r["code"]): r["value"] for r in
            _aggregate(False, True, brand_id=brand_id, start=start - span, end=start - timedelta(days=1), **f)}
    outlets = {o.id: o for o in in_scope(brand.outlets.filter(is_active=True), request.user, "id")}
    out = []
    for r in cur:
        o, v, p = outlets.get(r["outlet_id"]), r["value"], prev.get((r["outlet_id"], r["code"]))
        if o is None or v is None or p is None:
            continue
        move = (v - p) if r["higher_is_better"] else (p - v)  # negative = got worse
        if move >= 0:
            continue
        unit = r["unit"]
        if unit in _MIN_MOVE:
            if -move < _MIN_MOVE[unit]:
                continue
            pct = round(move / abs(p) * 100, 1) if p else None
            size = -move / _MIN_MOVE[unit]
        else:
            if not p or abs(p) < _MIN_BASE.get(unit, 0) or -move / abs(p) * 100 < _MIN_PCT:
                continue
            pct = round(move / abs(p) * 100, 1)
            size = -move / abs(p) * 100 / _MIN_PCT
        out.append({"outlet_id": o.id, "outlet": o.display_name.split(" · ", 1)[-1], "city": o.city, "code": r["code"], "name": r["name"],
                    "module": r["module"], "unit": unit, "higher_is_better": r["higher_is_better"], "value": v, "previous": p, "change_pct": pct,
                    "severity": "critical" if size >= 2.5 else "warning", "_size": size})
    out.sort(key=lambda x: -x["_size"])
    for x in out:
        del x["_size"]
    return Response({"start": start, "end": end, "drops": out[:200]})


@api_view(["GET"])
def kpi_trend(request, brand_id, kpi_code):
    get_brand(request.user, brand_id)
    start, end = _range(request)
    f = {**_filters(request), "module": None}
    rows = _aggregate(True, brand_id=brand_id, start=start, end=end, kpi=kpi_code, **f)
    return Response([{"date": r["metric_date"], "value": r["value"]} for r in rows])


@api_view(["GET"])
def leaderboard(request, brand_id, kpi_code):
    """Rank a brand's outlets on one KPI."""
    kpi = get_object_or_404(Kpi, code=kpi_code)
    brand = get_brand(request.user, brand_id)
    start, end = _range(request)
    rows = []
    for o in in_scope(brand.outlets.filter(is_active=True), request.user, "id"):
        agg = _aggregate(False, brand_id=brand_id, start=start, end=end, outlet_id=o.id, kpi=kpi_code)
        rows.append({"id": o.id, "name": o.display_name.split(" · ", 1)[-1], "city": o.city, "value": agg[0]["value"] if agg else None})
    sign = -1 if kpi.higher_is_better else 1
    rows.sort(key=lambda r: (r["value"] is None, sign * (r["value"] or 0)))
    return Response(rows)


@api_view(["POST"])
def run_review_rollup(request, brand_id):
    get_brand(request.user, brand_id, manage=True)
    start, end = _range(request)
    return Response({"rows_written": rollup_review_metrics(brand_id, start, end)})
