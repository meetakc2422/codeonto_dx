"""Recheck stored Zomato payout cycles with the current rules, without calling Zomato.

Cycles in Zomato's newer statement layout were checked with rules that only knew the older one, so their "not tied to an
order" amount, expected payout, difference and payout_mismatch flag were wrong. This recomputes them from what is already
stored (the statement's breakdown and the cycle's orders). Cycles in the older layout are left alone.

    ./.venv/bin/python recheck_payouts.py            # shows what would change
    ./.venv/bin/python recheck_payouts.py --apply    # saves it
"""

import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from psycopg.types.json import Jsonb  # noqa: E402

from core import db  # noqa: E402
from zomato.payouts import PAYOUT_TOLERANCE, statement_adjustments, unknown_sections  # noqa: E402

NEWER_LAYOUT = {"gross_order_value", "discounts_and_promotions", "net_order_value_subtotal", "service_fee", "tax_deductions_v2",
                "investments_in_growth_v2", "refunds_and_additions", "food_delivery_statement_subtotal", "est_net_payout_soa_v2"}
CENTS = Decimal("0.01")


def main(apply: bool) -> None:
    changed = flipped = seen = 0
    with db.transaction() as cur:
        cur.execute("""SELECT c.id, c.net_payout, c.breakdown, c.issues, c.adjustments, c.expected_payout, c.discrepancy,
                              COALESCE(SUM(o.payout), 0) AS orders_total, COALESCE(SUM(o.net_additions), 0) AS order_additions, COUNT(o.id) AS n
                       FROM payout_cycles c LEFT JOIN payout_orders o ON o.cycle_id = c.id
                       WHERE c.platform = 'zomato' AND c.reconciled_at IS NOT NULL
                       GROUP BY c.id""")
        for c in cur.fetchall():
            if not c["n"] or not any(s.get("id") in NEWER_LAYOUT for s in (c["breakdown"] or [])):
                continue
            seen += 1
            adj = statement_adjustments(c["breakdown"], Decimal(c["order_additions"]))
            expected = (Decimal(c["orders_total"]) + adj).quantize(CENTS, ROUND_HALF_UP)
            net = c["net_payout"]
            disc = (Decimal(net) - expected) if net is not None else None
            issues = [i for i in (c["issues"] or []) if i not in ("payout_mismatch", "unknown_statement_section")]
            if unknown_sections(c["breakdown"]):
                issues.append("unknown_statement_section")
            if disc is None or abs(disc) > PAYOUT_TOLERANCE:
                issues.append("payout_mismatch")
            issues = sorted(issues)
            was_bad = "payout_mismatch" in (c["issues"] or [])
            if (c["expected_payout"], c["discrepancy"], sorted(c["issues"] or [])) == (expected, disc, issues):
                continue
            changed += 1
            flipped += was_bad and "payout_mismatch" not in issues
            print(f"cycle {c['id']}: expected {c['expected_payout']} -> {expected}, difference {c['discrepancy']} -> {disc}, "
                  f"mismatch {'yes' if was_bad else 'no'} -> {'yes' if 'payout_mismatch' in issues else 'no'}")
            if apply:
                cur.execute("UPDATE payout_cycles SET adjustments = %s, expected_payout = %s, discrepancy = %s, issues = %s WHERE id = %s",
                            (adj.quantize(CENTS, ROUND_HALF_UP), expected, disc, Jsonb(issues), c["id"]))
    print(f"\n{seen} cycles in the newer layout, {changed} {'updated' if apply else 'would change'}, {flipped} of them no longer flagged as a mismatch."
          + ("" if apply else "  Run again with --apply to save."))


if __name__ == "__main__":
    main("--apply" in sys.argv)
