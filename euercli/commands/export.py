import csv
import sys
from datetime import datetime
from pathlib import Path

from ..config import get_export_dir, load_config
from ..constants import DEFAULT_EXPORT_DIR
from ..db import get_db_connection

# Optional: openpyxl für XLSX-Export
try:
    import openpyxl

    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def cmd_export(args):
    """Exportiert Daten als CSV oder XLSX."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    config = load_config()
    config_export_dir = get_export_dir(config)

    if args.output:
        output_dir = Path(args.output)
    elif config_export_dir:
        output_dir = Path(config_export_dir)
    else:
        output_dir = DEFAULT_EXPORT_DIR

    output_dir.mkdir(exist_ok=True)

    year = args.year or datetime.now().year

    # Ausgaben laden
    expenses = conn.execute(
        """SELECT e.receipt_name, e.date, e.vendor, c.name as category, c.eur_line,
                  e.amount_eur, e.account, e.foreign_amount, e.notes, e.is_rc, e.vat_input, e.vat_output
           FROM expenses e
           JOIN categories c ON e.category_id = c.id
           WHERE strftime('%Y', e.date) = ?
           ORDER BY e.date, e.id""",
        (str(year),),
    ).fetchall()

    # Einnahmen laden
    income = conn.execute(
        """SELECT i.receipt_name, i.date, i.source, c.name as category, c.eur_line,
                  i.amount_eur, i.foreign_amount, i.notes, i.vat_output
           FROM income i
           JOIN categories c ON i.category_id = c.id
           WHERE strftime('%Y', i.date) = ?
           ORDER BY i.date, i.id""",
        (str(year),),
    ).fetchall()

    conn.close()

    if args.format == "csv":
        # CSV Export
        exp_path = output_dir / f"EÜR_{year}_Ausgaben.csv"
        with open(exp_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Belegname",
                    "Datum",
                    "Lieferant",
                    "Kategorie",
                    "EUR",
                    "Konto",
                    "Fremdwährung",
                    "Bemerkung",
                    "RC",
                    "Vorsteuer",
                    "Umsatzsteuer",
                ]
            )
            for r in expenses:
                cat = (
                    f"{r['category']} ({r['eur_line']})"
                    if r["eur_line"]
                    else r["category"]
                )
                writer.writerow(
                    [
                        r["receipt_name"] or "",
                        r["date"],
                        r["vendor"],
                        cat,
                        f"{r['amount_eur']:.2f}",
                        r["account"] or "",
                        r["foreign_amount"] or "",
                        r["notes"] or "",
                        "X" if r["is_rc"] else "",
                        f"{r['vat_input']:.2f}" if r["vat_input"] else "",
                        f"{r['vat_output']:.2f}" if r["vat_output"] else "",
                    ]
                )
        print(f"Exportiert: {exp_path}")

        inc_path = output_dir / f"EÜR_{year}_Einnahmen.csv"
        with open(inc_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Belegname",
                    "Datum",
                    "Quelle",
                    "Kategorie",
                    "EUR",
                    "Fremdwährung",
                    "Bemerkung",
                    "Umsatzsteuer",
                ]
            )
            for r in income:
                cat = (
                    f"{r['category']} ({r['eur_line']})"
                    if r["eur_line"]
                    else r["category"]
                )
                writer.writerow(
                    [
                        r["receipt_name"] or "",
                        r["date"],
                        r["source"],
                        cat,
                        f"{r['amount_eur']:.2f}",
                        r["foreign_amount"] or "",
                        r["notes"] or "",
                        f"{r['vat_output']:.2f}" if r["vat_output"] else "",
                    ]
                )
        print(f"Exportiert: {inc_path}")

    else:
        # XLSX Export
        if not HAS_OPENPYXL:
            print(
                "Fehler: openpyxl nicht installiert. Bitte 'pip install openpyxl'.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Ausgaben
        exp_path = output_dir / f"EÜR_{year}_Ausgaben.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ausgaben"
        ws.append(
            [
                "Belegname",
                "Datum",
                "Lieferant",
                "Kategorie",
                "EUR",
                "Konto",
                "Fremdwährung",
                "Bemerkung",
                "RC",
                "USt-VA",
            ]
        )
        for r in expenses:
            cat = (
                f"{r['category']} ({r['eur_line']})" if r["eur_line"] else r["category"]
            )
            ws.append(
                [
                    r["receipt_name"] or "",
                    r["date"],
                    r["vendor"],
                    cat,
                    r["amount_eur"],
                    r["account"] or "",
                    r["foreign_amount"] or "",
                    r["notes"] or "",
                    "X" if r["is_rc"] else "",
                    r["vat_amount"] if r["vat_amount"] else None,
                ]
            )
        wb.save(exp_path)
        print(f"Exportiert: {exp_path}")

        # Einnahmen
        inc_path = output_dir / f"EÜR_{year}_Einnahmen.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Einnahmen"
        ws.append(
            [
                "Belegname",
                "Datum",
                "Quelle",
                "Kategorie",
                "EUR",
                "Fremdwährung",
                "Bemerkung",
            ]
        )
        for r in income:
            cat = (
                f"{r['category']} ({r['eur_line']})" if r["eur_line"] else r["category"]
            )
            ws.append(
                [
                    r["receipt_name"] or "",
                    r["date"],
                    r["source"],
                    cat,
                    r["amount_eur"],
                    r["foreign_amount"] or "",
                    r["notes"] or "",
                ]
            )
        wb.save(inc_path)
        print(f"Exportiert: {inc_path}")
