"""Show how a Swiggy payout annexure (the Excel file behind a paid payout) is laid out now, to update the parser in
swiggy/payouts.py after "Swiggy payout annexure changed".

    .venv\\Scripts\\python inspect_swiggy_annexure.py <login> [swiggy_id] [days]

<login> is the Swiggy account name (for example mn). It takes the most recent PAID payout of that login's first store
(or of the given store) in the last <days> days (default 45), downloads its annexure and prints, for every sheet: its
name, its size, the header rows, and what KIND of value sits in each column of the first data row (text / number /
date). It does not print order ids, amounts or customer details. Read only: nothing is saved, no file is kept."""

import io
import sys
from datetime import datetime, timedelta, timezone

from core import config as cfg, db
from core.common import setup_logging
from swiggy import payouts

KIND = {int: "number", float: "number", str: "text", datetime: "date"}


def kind(v) -> str:
    if v is None or v == "":
        return "empty"
    for t, name in KIND.items():
        if isinstance(v, t):
            return name
    return type(v).__name__


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    label = sys.argv[1]
    only = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 45
    setup_logging()
    with db.transaction() as cur:
        acc = db.get_account(cur, "swiggy", label)
        cur.execute("""SELECT bo.swiggy_id AS res_id FROM brand_outlets bo JOIN swiggy_outlets s ON s.swiggy_id = bo.swiggy_id
                       WHERE bo.is_active AND s.is_active AND s.account_id = %s ORDER BY bo.id""", (acc["id"],))
        stores = [int(r["res_id"]) for r in cur.fetchall()]
    token = db.load_credentials(acc).get("access_token")
    if only:
        stores = [only]
    end = datetime.now(payouts.IST).date()
    start = end - timedelta(days=days)
    for res_id in stores[:15]:
        paid = [c for c in payouts.fetch_cycles(token, res_id, start, end) if c["status"] == "PAID"]
        for cycle in sorted(paid, key=lambda c: c["end_date"], reverse=True)[:3]:
            st = payouts.fetch_statement(token, res_id, cycle)
            if st and st["annexure"]:
                content = payouts.fetch_annexure(st["annexure"], token)
                if content:
                    print(f"store {res_id}, payout {cycle['start_date']} to {cycle['end_date']}, file {len(content):,} bytes")
                    return show(content)
    sys.exit("No PAID payout with an annexure was found. Pass a swiggy_id that has one, or more days.")


def show(content: bytes) -> None:
    from openpyxl import load_workbook

    book = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    print("sheets:", book.sheetnames)
    for name in book.sheetnames:
        rows = list(book[name].iter_rows(values_only=True))
        width = max((len(r) for r in rows), default=0)
        print(f"\n=== sheet '{name}': {len(rows)} rows x {width} columns")
        # the header row is the one with the most text cells near the top
        texts = [sum(isinstance(c, str) and c.strip() != "" for c in r) for r in rows[:30]]
        head = texts.index(max(texts)) if texts and max(texts) >= 3 else None
        for i, r in enumerate(rows[: (head if head is not None else 6) + 1]):
            cells = [str(c).strip()[:48] for c in r if c not in (None, "")]
            if cells:
                print(f"  row {i + 1}{' (header)' if i == head else ''}: {cells}")
        if head is not None and head + 1 < len(rows):
            first = rows[head + 1]
            print(f"  first data row, kind of value per column ({len(rows) - head - 1} data rows):")
            print("   ", [f"{j + 1}:{kind(c)}" for j, c in enumerate(first) if c not in (None, "")])


if __name__ == "__main__":
    main()
