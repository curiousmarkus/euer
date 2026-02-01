import csv
import sys
from pathlib import Path

from ..db import get_db_connection
from ..utils import format_missing_fields


def cmd_incomplete_list(args):
    """Listet unvollständige Import-Einträge."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    query = """
        SELECT id, type, date, party, category_name, amount_eur,
               receipt_name, missing_fields, notes
        FROM incomplete_entries
        WHERE 1=1
    """
    params = []

    if args.type:
        query += " AND type = ?"
        params.append(args.type)
    if args.year:
        query += " AND date LIKE ?"
        params.append(f"{args.year}-%")

    query += " ORDER BY date DESC, id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Typ",
                "Datum",
                "Partei",
                "Kategorie",
                "EUR",
                "Beleg",
                "Fehlende Felder",
                "Notizen",
            ]
        )
        for r in rows:
            missing = format_missing_fields(r["missing_fields"])
            writer.writerow(
                [
                    r["id"],
                    r["type"],
                    r["date"] or "",
                    r["party"] or "",
                    r["category_name"] or "",
                    f"{r['amount_eur']:.2f}" if r["amount_eur"] is not None else "",
                    r["receipt_name"] or "",
                    missing,
                    r["notes"] or "",
                ]
            )
        return

    if not rows:
        print("Keine unvollständigen Einträge gefunden.")
        return

    print(
        f"{'ID':<5} {'Typ':<9} {'Datum':<12} {'Partei':<20} {'Kategorie':<25} {'EUR':>10} {'Fehlt':<20}"
    )
    print("-" * 105)
    for r in rows:
        missing = format_missing_fields(r["missing_fields"])
        amount_str = f"{r['amount_eur']:.2f}" if r["amount_eur"] is not None else ""
        print(
            f"{r['id']:<5} {r['type']:<9} {(r['date'] or ''):<12} {(r['party'] or '')[:20]:<20} {(r['category_name'] or '')[:25]:<25} {amount_str:>10} {missing[:20]:<20}"
        )
