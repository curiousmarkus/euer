import csv
import sys
from pathlib import Path

from ..db import get_db_connection
from ..utils import format_missing_fields


def find_matching_booking_id(row, conn):
    """Sucht eine passende Buchung zu einem unvollständigen Eintrag."""
    row_type = row["type"]
    if row_type not in ("expense", "income"):
        return None
    if not row["date"] or not row["party"] or row["amount_eur"] is None:
        return None

    if row_type == "expense":
        table = "expenses"
        party_col = "vendor"
    else:
        table = "income"
        party_col = "source"

    if row["receipt_name"]:
        match = conn.execute(
            f"""SELECT id FROM {table}
                WHERE date = ?
                  AND amount_eur = ?
                  AND LOWER({party_col}) = LOWER(?)
                  AND receipt_name = ?
                ORDER BY id
                LIMIT 1""",
            (row["date"], row["amount_eur"], row["party"], row["receipt_name"]),
        ).fetchone()
    else:
        match = conn.execute(
            f"""SELECT id FROM {table}
                WHERE date = ?
                  AND amount_eur = ?
                  AND LOWER({party_col}) = LOWER(?)
                ORDER BY id
                LIMIT 1""",
            (row["date"], row["amount_eur"], row["party"]),
        ).fetchone()

    return match["id"] if match else None


def cmd_incomplete_list(args):
    """Listet unvollständige Import-Einträge."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    query = """
        SELECT id, type, date, party, category_name, amount_eur,
               receipt_name, missing_fields, notes
        FROM incomplete_entries
        WHERE 1=1
          AND (category_name IS NULL OR LOWER(category_name) NOT IN ('gezahlte ust', 'gezahlte ust (58)'))
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

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Typ",
                "Buchung-ID",
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
            booking_id = find_matching_booking_id(r, conn)
            writer.writerow(
                [
                    r["id"],
                    r["type"],
                    booking_id or "",
                    r["date"] or "",
                    r["party"] or "",
                    r["category_name"] or "",
                    f"{r['amount_eur']:.2f}" if r["amount_eur"] is not None else "",
                    r["receipt_name"] or "",
                    missing,
                    r["notes"] or "",
                ]
            )
        conn.close()
        return

    if not rows:
        print("Keine unvollständigen Einträge gefunden.")
        conn.close()
        return

    print(
        f"{'ID':<5} {'Typ':<9} {'Buchung':<8} {'Datum':<12} {'Partei':<20} {'Kategorie':<25} {'EUR':>10} {'Fehlt':<20}"
    )
    print("-" * 115)
    for r in rows:
        missing = format_missing_fields(r["missing_fields"])
        amount_str = f"{r['amount_eur']:.2f}" if r["amount_eur"] is not None else ""
        booking_id = find_matching_booking_id(r, conn)
        booking_str = str(booking_id) if booking_id is not None else ""
        print(
            f"{r['id']:<5} {r['type']:<9} {booking_str:<8} {(r['date'] or ''):<12} {(r['party'] or '')[:20]:<20} {(r['category_name'] or '')[:25]:<25} {amount_str:>10} {missing[:20]:<20}"
        )
    print()
    print(
        "Hinweis: Unvollständige Importzeilen werden automatisch aufgelöst, sobald die"
    )
    print(
        "zugehörige Buchung vollständig erfasst oder aktualisiert wird (z.B. via"
    )
    print(
        "`euer add`, `euer import` oder `euer update expense|income <ID>`)."
    )
    print("Matching: Datum, Partei, Betrag; optional Belegname.")
    conn.close()
