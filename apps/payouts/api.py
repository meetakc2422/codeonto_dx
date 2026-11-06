from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets.access import get_brand, in_scope, outlet_ids
from apps.billing.access import require_module

from rest_framework.exceptions import PermissionDenied

from apps.outlets.access import is_staff

from .lines import guess_kind, lines
from .models import PayoutCycle, PayoutLineType

ISSUE_LABELS = {
    "payout_mismatch": "Payout doesn't match its orders",
    "order_count_mismatch": "Order count doesn't match the report",
    "unsettled_orders": "Paid, but orders are still unsettled",
    "order_payout_math": "An order's payout doesn't add up",
    "order_fee_math": "An order's service fee doesn't add up",
    "fee_rate_changed": "Base service fee % differs between orders",
    "paid_without_utr": "Paid, but has no UTR",
    "overdue": "Payout date has passed, not paid yet",
    "deductions_carried": "Deductions bigger than earnings, carried to next payout",
}


def _money(v):
    return float(v) if v is not None else None


def _is_paid(status: str) -> bool:
    return status.strip().upper() == "PAID"


def _is_due(status: str) -> bool:
    return status.strip().upper() == "TO BE PAID"


def _issues(c: PayoutCycle) -> list[str]:
    """The stored checks, plus overdue, which depends on today's date. A payout of ₹0 whose orders, less its deductions,
    come to less than nothing isn't a mismatch: the platform carries the shortfall into the next payout."""
    issues = list(c.issues)
    if "payout_mismatch" in issues and not c.net_payout and c.expected_payout is not None and c.expected_payout < 0:
        issues = [i for i in issues if i != "payout_mismatch"] + ["deductions_carried"]
    overdue = _is_due(c.status) and c.payout_date and c.payout_date < date.today()
    return [*issues, "overdue"] if overdue else issues


def _filtered(request, brand_id):
    require_module(request.user, get_brand(request.user, brand_id), "reconciliation")
    qp = request.query_params
    end = date.fromisoformat(qp["end"]) if qp.get("end") else date.today()
    start = date.fromisoformat(qp["start"]) if qp.get("start") else end - timedelta(days=29)
    qs = in_scope(PayoutCycle.objects.filter(outlet__brand_id=brand_id, end_date__range=(start, end)), request.user)
    if outlet_ids(qp.get("outlet_id")):
        qs = qs.filter(outlet_id__in=outlet_ids(qp.get("outlet_id")))
    if qp.get("platform"):
        qs = qs.filter(platform_id=qp["platform"])
    return qs, qp


def _cycle_json(c: PayoutCycle) -> dict:
    return {"id": c.id, "outlet_id": c.outlet_id, "outlet": c.outlet.area or c.outlet.outlet_name, "city": c.outlet.city,
            "res_id": c.outlet.swiggy_id if c.platform_id == "swiggy" else c.outlet.zomato_id, "platform": c.platform_id, "start_date": c.start_date, "end_date": c.end_date,
            "payout_date": c.payout_date, "status": c.status, "utr": c.utr, "net_payout": _money(c.net_payout),
            "order_count": c.order_count, "orders_total": _money(c.orders_total), "adjustments": _money(c.adjustments),
            "expected_payout": _money(c.expected_payout), "discrepancy": _money(c.discrepancy),
            "reconciled": c.reconciled_at is not None, "issues": _issues(c)}


@api_view(["GET"])
def payout_summary(request, brand_id):
    qs, _ = _filtered(request, brand_id)
    cycles = list(qs.only("status", "net_payout", "discrepancy", "expected_payout", "issues", "payout_date", "commissionable_total", "service_fee_total", "reconciled_at"))
    paid = [c for c in cycles if _is_paid(c.status)]
    with_issues = [c for c in cycles if _issues(c)]
    commissionable = sum((c.commissionable_total or 0) for c in cycles)
    fees = sum((c.service_fee_total or 0) for c in cycles)
    counts: dict[str, int] = {}
    for c in cycles:
        for code in _issues(c):
            counts[code] = counts.get(code, 0) + 1
    return Response({
        "cycles": len(cycles),
        "paid_total": _money(sum((c.net_payout or 0) for c in paid)),
        "zero_payouts": sum(1 for c in paid if not c.net_payout),
        "to_be_paid_total": _money(sum((c.net_payout or 0) for c in cycles if _is_due(c.status))),
        "to_be_paid_cycles": sum(1 for c in cycles if _is_due(c.status)),
        "carried_forward_cycles": sum(1 for c in cycles if c.status.strip().upper() == "CARRIED FORWARD"),
        "carried_forward_total": _money(sum((c.net_payout or 0) for c in cycles if c.status.strip().upper() == "CARRIED FORWARD")),
        "reconciled": sum(1 for c in cycles if c.reconciled_at),
        "with_issues": len(with_issues),
        "discrepancy_total": _money(sum(abs(c.discrepancy or 0) for c in cycles if "deductions_carried" not in _issues(c))),
        "carried_total": _money(sum(-(c.expected_payout or 0) for c in cycles if "deductions_carried" in _issues(c))),
        "take_rate": round(float(fees) / float(commissionable) * 100, 2) if commissionable else None,
        "issues": [{"code": k, "label": ISSUE_LABELS.get(k, k), "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])],
        "new_lines": _new_lines(qs),
    })


def _listed(request, brand_id) -> list[tuple]:
    """[(cycle, its json)] for the payouts the list shows with these filters (dates, outlets, platform, status, issue,
    search), newest problems first. The list, the combined statement and the CSV all use this, so they always agree."""
    qs, qp = _filtered(request, brand_id)
    qs = qs.select_related("outlet")
    status = qp.get("status")
    if status == "paid":
        qs = qs.filter(status__iexact="PAID")
    elif status == "to_be_paid":
        qs = qs.filter(status__iexact="TO BE PAID")
    rows = [(c, _cycle_json(c)) for c in qs]
    if status == "issues":
        rows = [(c, r) for c, r in rows if r["issues"]]
    if qp.get("issue"):  # one problem type, e.g. from a "What needs checking" line
        rows = [(c, r) for c, r in rows if qp["issue"] in r["issues"]]
    if qp.get("q"):
        q = qp["q"].strip().lower()
        rows = [(c, r) for c, r in rows if q in (r["utr"] or "").lower() or q in r["outlet"].lower()]
    rows.sort(key=lambda cr: (not cr[1]["issues"], -cr[1]["end_date"].toordinal(), cr[1]["outlet"]))
    return rows


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v if v not in (None, "") else 0))
    except InvalidOperation:
        return Decimal(0)


def _combine(cycles, exact: bool = False) -> list[dict]:
    """One combined statement per platform: every section and line added up exactly (Decimal), in the order the
    platform shows them. Zomato and Swiggy statements are laid out differently, so they're never mixed."""
    out = {}
    for c in cycles:
        p = out.setdefault(c.platform_id, {"platform": c.platform_id, "payouts": 0, "outlets": set(), "orders": 0,
                                           "net_payout": Decimal(0), "paid": Decimal(0), "to_be_paid": Decimal(0), "sections": {}})
        p["payouts"] += 1
        p["outlets"].add(c.outlet_id)
        p["orders"] += c.order_count or 0
        net = _dec(c.net_payout)
        p["net_payout"] += net
        if _is_paid(c.status):
            p["paid"] += net
        elif _is_due(c.status):
            p["to_be_paid"] += net
        for sec in c.breakdown or []:
            key = sec.get("id") or sec.get("label")
            ps = p["sections"].setdefault(key, {"id": key, "label": sec.get("label") or key, "value": Decimal(0), "items": {}})
            ps["value"] += _dec(sec.get("value"))
            for it in sec.get("items") or []:
                pi = ps["items"].setdefault(it.get("label") or "", Decimal(0))
                ps["items"][it.get("label") or ""] = pi + _dec(it.get("value"))
    q = (lambda d: d.quantize(Decimal("0.01"))) if exact else (lambda d: float(d.quantize(Decimal("0.01"))))
    return [{"platform": p["platform"], "payouts": p["payouts"], "outlets": len(p["outlets"]), "orders": p["orders"],
             "net_payout": q(p["net_payout"]), "paid": q(p["paid"]), "to_be_paid": q(p["to_be_paid"]),
             "sections": [{"id": s["id"], "label": s["label"], "value": q(s["value"]),
                           "items": [{"label": k, "value": q(v)} for k, v in s["items"].items() if v]}
                          for s in p["sections"].values()]}
            for p in sorted(out.values(), key=lambda p: p["platform"])]


@api_view(["GET"])
def payout_combined(request, brand_id):
    """The listed payouts added up: per platform statement, plus totals across platforms."""
    per = _combine(c for c, _ in _listed(request, brand_id))
    total = {k: round(sum(p[k] for p in per), 2) for k in ("net_payout", "paid", "to_be_paid")}
    return Response({"platforms": per, "total": {**total, "payouts": sum(p["payouts"] for p in per), "orders": sum(p["orders"] for p in per)}})


@api_view(["GET"])
def payout_combined_xlsx(request, brand_id):
    """The combined statement as Excel: one sheet per platform (every section and line, exact sums), then a sheet
    listing the payouts it adds up, with a total row that equals the statement's net payout."""
    import io

    from django.http import HttpResponse
    from django.utils import timezone
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    listed = _listed(request, brand_id)
    per = _combine((c for c, _ in listed), exact=True)
    wb = Workbook()
    wb.remove(wb.active)
    bold, fill, money = Font(bold=True), PatternFill("solid", fgColor="E8EEF6"), '#,##0.00;[Red]-#,##0.00'
    qp = request.query_params
    period = f"{qp.get('start') or ''} to {qp.get('end') or ''}".strip(" to")
    for p in per:
        name = "Swiggy" if p["platform"] == "swiggy" else "Zomato"
        ws = wb.create_sheet(f"{name} combined")
        ws.append([f"{name} combined statement", period])
        ws["A1"].font = Font(bold=True, size=12)
        ws.append([f"{p['payouts']} payouts · {p['outlets']} outlets · {p['orders']} orders"])
        ws.append([])
        for sec in p["sections"]:
            ws.append([sec["label"], sec["value"]])
            for cell in ws[ws.max_row]:
                cell.font = bold
            for it in sec["items"]:
                ws.append([f"    {it['label']}", it["value"]])
        ws.append(["Net payout", p["net_payout"]])
        for cell in ws[ws.max_row]:
            cell.font, cell.fill = bold, fill
        ws.append(["  of which paid", p["paid"]])
        ws.append(["  of which to be paid", p["to_be_paid"]])
        for row in ws.iter_rows(min_row=4, min_col=2, max_col=2):
            for cell in row:
                cell.number_format = money
        ws.column_dimensions["A"].width = 58
        ws.column_dimensions["B"].width = 18
    ws = wb.create_sheet("Payouts")
    ws.append(["Outlet", "City", "Platform", "Res ID", "Cycle start", "Cycle end", "Payout date", "Status", "UTR", "Orders", "Net payout"])
    for cell in ws[1]:
        cell.font, cell.fill = bold, fill
    total = Decimal(0)
    for c, r in listed:
        net = _dec(c.net_payout)
        total += net
        ws.append([r["outlet"], r["city"], "Swiggy" if c.platform_id == "swiggy" else "Zomato", r["res_id"] or "", c.start_date, c.end_date,
                   c.payout_date, c.status, c.utr, c.order_count or 0, net])
    ws.append(["TOTAL", "", "", "", "", "", "", "", "", sum(c.order_count or 0 for c, _ in listed), total])
    for cell in ws[ws.max_row]:
        cell.font = bold
    for row in ws.iter_rows(min_row=2, min_col=11, max_col=11):
        for cell in row:
            cell.number_format = money
    for col, width in zip("ABCDEFGHIJK", (28, 14, 9, 12, 12, 12, 12, 13, 22, 8, 15)):
        ws.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    brand = get_brand(request.user, brand_id)
    resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{brand.name.lower().replace(" ", "-")}-combined-statement-{timezone.localdate():%Y-%m-%d}.xlsx"'
    return resp


@api_view(["GET"])
def payout_export(request, brand_id):
    """CSV of the listed payouts: one row per payout with every statement line as a column, then a total row per
    platform and a grand total. Columns are 'Platform: Section' and 'Platform: Section > Line' so Zomato and Swiggy
    lines never land in the same column."""
    import csv
    import io

    from django.http import HttpResponse
    from django.utils import timezone

    listed = _listed(request, brand_id)
    cols, seen = [], set()
    for c, _ in listed:
        name = "Swiggy" if c.platform_id == "swiggy" else "Zomato"
        for sec in c.breakdown or []:
            for col in [f"{name}: {sec.get('label')}"] + [f"{name}: {sec.get('label')} > {it.get('label')}" for it in sec.get("items") or []]:
                if col not in seen:
                    seen.add(col)
                    cols.append(col)
    head = ["Outlet", "City", "Platform", "Res ID", "Cycle start", "Cycle end", "Payout date", "Status", "UTR", "Orders",
            "Net payout", "Expected payout", "Difference", "Issues"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(head + cols)
    totals = {}
    for c, r in listed:
        name = "Swiggy" if c.platform_id == "swiggy" else "Zomato"
        vals = {}
        for sec in c.breakdown or []:
            vals[f"{name}: {sec.get('label')}"] = _dec(sec.get("value"))
            for it in sec.get("items") or []:
                k = f"{name}: {sec.get('label')} > {it.get('label')}"
                vals[k] = vals.get(k, Decimal(0)) + _dec(it.get("value"))
        t = totals.setdefault(name, {"orders": 0, "net": Decimal(0), "cols": {}})
        t["orders"] += c.order_count or 0
        t["net"] += _dec(c.net_payout)
        for k, v in vals.items():
            t["cols"][k] = t["cols"].get(k, Decimal(0)) + v
        w.writerow([r["outlet"], r["city"], name, r["res_id"] or "", c.start_date, c.end_date, c.payout_date or "", c.status, c.utr,
                    c.order_count, _dec(c.net_payout), "" if c.expected_payout is None else _dec(c.expected_payout),
                    "" if c.discrepancy is None else _dec(c.discrepancy), "; ".join(ISSUE_LABELS.get(i, i) for i in r["issues"])]
                   + [vals.get(col, "") for col in cols])
    w.writerow([])
    for name, t in totals.items():
        w.writerow([f"TOTAL {name}", "", name, "", "", "", "", "", "", t["orders"], t["net"], "", "", ""] + [t["cols"].get(col, "") for col in cols])
    if len(totals) > 1:
        w.writerow(["TOTAL all platforms", "", "", "", "", "", "", "", "", sum(t["orders"] for t in totals.values()),
                    sum((t["net"] for t in totals.values()), Decimal(0)), "", "", ""])
    brand = get_brand(request.user, brand_id)
    resp = HttpResponse("\ufeff" + buf.getvalue(), content_type="text/csv; charset=utf-8")  # BOM so Excel reads ₹ and Hindi names
    resp["Content-Disposition"] = f'attachment; filename="{brand.name.lower().replace(" ", "-")}-payouts-{timezone.localdate():%Y-%m-%d}.csv"'
    return resp


CUSTOMER_PAID_SECTIONS = ("total_order_value", "total_customer_paid")  # Zomato, Swiggy: what customers paid for the orders


def _customer_paid(c) -> Decimal:
    return next((_dec(sec.get("value")) for sec in c.breakdown or [] if sec.get("id") in CUSTOMER_PAID_SECTIONS), Decimal(0))


def _statement_groups(cycles, only_ids: set | None = None) -> list[dict]:
    """Payouts grouped per outlet and platform, cycles oldest first, with every statement section and line as a row
    and each cycle's value in it. Values stay Decimal here; callers turn them into numbers or cells."""
    groups = {}
    for c in cycles:
        if only_ids and c.id not in only_ids:
            continue
        g = groups.setdefault((c.outlet_id, c.platform_id), {"outlet": c.outlet, "platform": c.platform_id, "cycles": [], "rows": {}})
        g["cycles"].append(c)
        for sec in c.breakdown or []:
            key = sec.get("id") or sec.get("label")
            row = g["rows"].setdefault(key, {"id": key, "label": sec.get("label") or key, "values": {}, "items": {}})
            row["values"][c.id] = _dec(sec.get("value"))
            for it in sec.get("items") or []:
                item = row["items"].setdefault(it.get("label") or "", {})
                item[c.id] = item.get(c.id, Decimal(0)) + _dec(it.get("value"))
    out = []
    for g in groups.values():
        g["cycles"].sort(key=lambda c: (c.start_date, c.end_date))
        out.append(g)
    out.sort(key=lambda g: ((g["outlet"].city or ""), g["outlet"].area or g["outlet"].outlet_name, g["platform"]))
    return out


def _margin(net: Decimal, paid: Decimal):
    return float((net / paid * 100).quantize(Decimal("0.01"))) if paid else None


@api_view(["GET"])
def payout_statements(request, brand_id):
    """Statement view: per outlet and platform, its payout cycles as columns and the statement lines as rows."""
    q = lambda d: float(d.quantize(Decimal("0.01")))
    out = []
    for g in _statement_groups(c for c, _ in _listed(request, brand_id)):
        o = g["outlet"]
        out.append({
            "outlet_id": o.id, "outlet": o.area or o.outlet_name, "brand_outlet": o.outlet_name, "city": o.city, "platform": g["platform"],
            "res_id": o.swiggy_id if g["platform"] == "swiggy" else o.zomato_id,
            "cycles": [{"id": c.id, "start_date": c.start_date, "end_date": c.end_date, "payout_date": c.payout_date, "status": c.status,
                        "utr": c.utr, "orders": c.order_count or 0, "net_payout": q(_dec(c.net_payout)),
                        "customer_paid": q(_customer_paid(c)), "margin": _margin(_dec(c.net_payout), _customer_paid(c)),
                        "issues": [ISSUE_LABELS.get(i, i) for i in _issues(c)]} for c in g["cycles"]],
            "rows": [{"id": r["id"], "label": r["label"], "values": {str(k): q(v) for k, v in r["values"].items()},
                      "items": [{"label": lbl, "values": {str(k): q(v) for k, v in vals.items()}} for lbl, vals in r["items"].items()
                                if any(vals.values())]} for r in g["rows"].values()],
        })
    return Response({"groups": out})


@api_view(["GET"])
def payout_book(request, brand_id):
    """Excel book of the statement view: a summary sheet, then one sheet per outlet and platform with its cycles as
    columns and a Combined column. ?cycles=1,2,3 keeps only the ticked cycles."""
    import io

    from django.http import HttpResponse
    from django.utils import timezone
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    only = {int(x) for x in str(request.query_params.get("cycles") or "").split(",") if x.strip().isdigit()} or None
    groups = _statement_groups((c for c, _ in _listed(request, brand_id)), only)
    wb = Workbook()
    summary = wb.active
    summary.title = "Summary"
    bold, head_fill = Font(bold=True), PatternFill("solid", fgColor="E8EEF6")
    money = '#,##0.00;[Red]-#,##0.00'
    summary.append(["Outlet", "City", "Platform", "Res ID", "Cycles", "Orders", "Customer paid", "Net payout", "Margin %"])
    for cell in summary[1]:
        cell.font, cell.fill = bold, head_fill
    used, grand = set(), {"orders": 0, "paid": Decimal(0), "net": Decimal(0)}
    for g in groups:
        o, cs = g["outlet"], g["cycles"]
        name = "Swiggy" if g["platform"] == "swiggy" else "Zomato"
        res_id = o.swiggy_id if g["platform"] == "swiggy" else o.zomato_id
        orders, paid, net = sum(c.order_count or 0 for c in cs), sum((_customer_paid(c) for c in cs), Decimal(0)), sum((_dec(c.net_payout) for c in cs), Decimal(0))
        grand["orders"] += orders
        grand["paid"] += paid
        grand["net"] += net
        summary.append([o.area or o.outlet_name, o.city, name, res_id, len(cs), orders, paid, net, _margin(net, paid)])
        base = f"{(o.area or o.outlet_name)[:22]} {name[:1]}".replace("/", "-").replace("\\", "-").replace("*", "").replace("?", "").replace("[", "(").replace("]", ")").replace(":", "-")
        title, n = base[:31], 2
        while title in used:
            title, n = f"{base[:28]} {n}"[:31], n + 1
        used.add(title)
        ws = wb.create_sheet(title)
        ws.append([f"{o.outlet_name} · {o.area or ''} · {o.city or ''}", f"{name} {res_id or ''}"])
        ws["A1"].font = Font(bold=True, size=12)
        ws.append(["Particulars"] + [f"{c.start_date:%d %b} – {c.end_date:%d %b %Y}" for c in cs] + ["Combined"])
        ws.append(["Status"] + [c.status for c in cs] + [""])
        ws.append(["Payout date"] + [c.payout_date for c in cs] + [""])
        ws.append(["UTR"] + [c.utr for c in cs] + [""])
        ws.append(["Margin %"] + [_margin(_dec(c.net_payout), _customer_paid(c)) for c in cs] + [_margin(net, paid)])
        for r in range(2, 7):
            for cell in ws[r]:
                cell.font = bold if r == 2 else Font(color="555555")
                if r == 2:
                    cell.fill = head_fill
        ws.append(["Total orders"] + [c.order_count or 0 for c in cs] + [orders])
        for row in g["rows"].values():
            vals = [row["values"].get(c.id, Decimal(0)) for c in cs]
            ws.append([row["label"]] + vals + [sum(vals, Decimal(0))])
            for cell in ws[ws.max_row]:
                cell.font = bold
            for lbl, per in row["items"].items():
                ivals = [per.get(c.id, Decimal(0)) for c in cs]
                if any(ivals):
                    ws.append([f"    {lbl}"] + ivals + [sum(ivals, Decimal(0))])
        ws.append(["Net payout"] + [_dec(c.net_payout) for c in cs] + [net])
        for cell in ws[ws.max_row]:
            cell.font, cell.fill = bold, head_fill
        for row in ws.iter_rows(min_row=7, min_col=2):
            for cell in row:
                if isinstance(cell.value, Decimal):
                    cell.number_format = money
        ws.column_dimensions["A"].width = 46
        for i in range(2, len(cs) + 3):
            ws.column_dimensions[get_column_letter(i)].width = 20
        ws.freeze_panes = "B3"
        for row in ws.iter_rows(min_row=2, max_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, horizontal="center")
    summary.append([])
    summary.append(["TOTAL", "", "", "", sum(len(g["cycles"]) for g in groups), grand["orders"], grand["paid"], grand["net"], _margin(grand["net"], grand["paid"])])
    for cell in summary[summary.max_row]:
        cell.font = bold
    for row in summary.iter_rows(min_row=2, min_col=7, max_col=8):
        for cell in row:
            cell.number_format = money
    for col, width in zip("ABCDEFGHI", (30, 16, 10, 12, 8, 10, 16, 16, 10)):
        summary.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    brand = get_brand(request.user, brand_id)
    resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{brand.name.lower().replace(" ", "-")}-payout-book-{timezone.localdate():%Y-%m-%d}.xlsx"'
    return resp


@api_view(["GET"])
def payout_cycles(request, brand_id):
    qp = request.query_params
    rows = [r for _, r in _listed(request, brand_id)]
    offset, limit = int(qp.get("offset", 0)), min(int(qp.get("limit", 100)), 500)
    return Response({"total": len(rows), "results": rows[offset:offset + limit]})


@api_view(["GET"])
def payout_cycle_detail(request, brand_id, cycle_id):
    """What clicking a UTR opens: the platform's statement and every order in the payout."""
    require_module(request.user, get_brand(request.user, brand_id), "reconciliation")
    c = get_object_or_404(in_scope(PayoutCycle.objects.filter(outlet__brand_id=brand_id), request.user).select_related("outlet"), pk=cycle_id)
    return Response({
        **_cycle_json(c), "breakdown": c.breakdown, "delivered_orders": c.delivered_orders, "rejected_orders": c.rejected_orders,
        "issue_labels": ISSUE_LABELS,
        "orders": [{"order_id": o.order_id, "order_date": o.order_date, "status": o.status, "payment_mode": o.payment_mode,
                    "net_order_value": _money(o.net_order_value), "base_fee_pct": _money(o.base_fee_pct), "service_fee_pct": _money(o.service_fee_pct), "fees_total": _money(o.fees_total),
                    "government_charges": _money(o.government_charges), "other_deductions": _money(o.other_deductions), "net_deductions": _money(o.net_deductions),
                    "net_additions": _money(o.net_additions), "payout": _money(o.payout), "settlement_status": o.settlement_status,
                    "settlement_date": o.settlement_date, "unsettled_amount": _money(o.unsettled_amount), "issues": o.issues}
                   for o in c.orders.all()],
    })


def _new_lines(qs) -> list[dict]:
    """Statement lines in these payouts that nobody has reviewed yet (a new fee, ad product, adjustment...).
    A line seen for the first time is recorded, so it stays listed until someone says what it is."""
    known = {(l.platform, l.section, l.label): l for l in PayoutLineType.objects.all()}
    agg = {}
    for c in qs.exclude(breakdown=[]).only("platform_id", "breakdown", "end_date"):
        for sec, sec_label, label, shown, value in lines(c):
            key = (c.platform_id, sec, label)
            if key not in known:
                known[key] = PayoutLineType.objects.get_or_create(platform=c.platform_id, section=sec, label=label,
                                                                  defaults={"kind": guess_kind(sec, label), "first_seen": c.end_date})[0]
            if known[key].reviewed:
                continue
            a = agg.setdefault(key, {"id": known[key].id, "platform": c.platform_id, "section": sec_label, "label": shown,
                                     "guess": known[key].kind, "payouts": 0, "total": 0.0, "last_seen": c.end_date})
            a["payouts"] += 1
            a["total"] += value
            a["last_seen"] = max(a["last_seen"], c.end_date)
    return sorted(agg.values(), key=lambda a: a["total"])


@api_view(["POST"])
def review_line(request, brand_id, line_id):
    """Say what a new statement line is: {"kind": "order" | "ad" | "deduction"}. Codeonto staff only."""
    require_module(request.user, get_brand(request.user, brand_id), "reconciliation")
    if not is_staff(request.user):
        raise PermissionDenied("Only Codeonto staff can classify statement lines.")
    kind = request.data.get("kind")
    if kind not in dict(PayoutLineType.KINDS):
        return Response({"detail": "kind must be order, ad or deduction"}, status=400)
    line = get_object_or_404(PayoutLineType, pk=line_id)
    line.kind, line.reviewed = kind, True
    line.save(update_fields=["kind", "reviewed"])
    return Response({"id": line.id, "kind": kind})
