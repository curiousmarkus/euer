import csv
import sys
from pathlib import Path

from ..config import load_config
from ..db import get_db_connection
from ..importers import get_tax_config
from ..utils import format_missing_fields


def is_gezahlte_ust(category_name: str | None, eur_line: int | None) -> bool:
    if category_name and category_name.strip().lower() == "gezahlte ust":
        return True
    return eur_line == 58


def collect_expense_missing(row: dict, tax_mode: str) -> list[str]:
    missing: list[str] = []

    if not row["payment_date"]:
        missing.append("payment_date")
    if not row["invoice_date"]:
        missing.append("invoice_date")

    if row["category_id"] is None:
        missing.append("category")

    receipt_required = not is_gezahlte_ust(row["category_name"], row["eur_line"])
    if receipt_required and not row["receipt_name"]:
        missing.append("receipt")

    if not row["account"]:
        missing.append("account")

    if tax_mode == "standard":
        if row["is_rc"]:
            if row["vat_input"] is None or row["vat_output"] is None:
                missing.append("vat")
        else:
            if row["vat_input"] is None:
                missing.append("vat")

    return missing


def collect_income_missing(row: dict, tax_mode: str) -> list[str]:
    missing: list[str] = []

    if not row["payment_date"]:
        missing.append("payment_date")
    if not row["invoice_date"]:
        missing.append("invoice_date")

    if row["category_id"] is None:
        missing.append("category")

    if not row["receipt_name"]:
        missing.append("receipt")

    if tax_mode == "standard" and row["vat_output"] is None:
        missing.append("vat")

    return missing


def cmd_incomplete_list(args):
    """Listet unvollständige Buchungen."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    tax_mode = get_tax_config(config)

    rows: list[dict] = []

    if args.type in (None, "expense"):
        query = """
            SELECT e.id, e.payment_date, e.invoice_date, e.vendor AS party,
                   e.category_id, c.name AS category_name,
                   c.eur_line, e.amount_eur, e.account, e.receipt_name, e.notes,
                   e.is_rc, e.vat_input, e.vat_output
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE 1=1
        """
        params: list[object] = []
        if args.year:
            query += " AND strftime('%Y', COALESCE(e.payment_date, e.invoice_date)) = ?"
            params.append(str(args.year))
        query += " ORDER BY COALESCE(e.payment_date, e.invoice_date) DESC, e.id DESC"
        expenses = conn.execute(query, params).fetchall()
        for row in expenses:
            missing = collect_expense_missing(row, tax_mode)
            if missing:
                rows.append(
                    {
                        "id": row["id"],
                        "type": "expense",
                        "payment_date": row["payment_date"],
                        "invoice_date": row["invoice_date"],
                        "date": row["payment_date"] or row["invoice_date"] or "",
                        "party": row["party"],
                        "category_name": row["category_name"],
                        "amount_eur": row["amount_eur"],
                        "account": row["account"],
                        "receipt_name": row["receipt_name"],
                        "missing_fields": missing,
                        "notes": row["notes"],
                    }
                )

    if args.type in (None, "income"):
        query = """
            SELECT i.id, i.payment_date, i.invoice_date, i.source AS party,
                   i.category_id, c.name AS category_name,
                   c.eur_line, i.amount_eur, i.receipt_name, i.notes, i.vat_output
            FROM income i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE 1=1
        """
        params = []
        if args.year:
            query += " AND strftime('%Y', COALESCE(i.payment_date, i.invoice_date)) = ?"
            params.append(str(args.year))
        query += " ORDER BY COALESCE(i.payment_date, i.invoice_date) DESC, i.id DESC"
        income = conn.execute(query, params).fetchall()
        for row in income:
            missing = collect_income_missing(row, tax_mode)
            if missing:
                rows.append(
                    {
                        "id": row["id"],
                        "type": "income",
                        "payment_date": row["payment_date"],
                        "invoice_date": row["invoice_date"],
                        "date": row["payment_date"] or row["invoice_date"] or "",
                        "party": row["party"],
                        "category_name": row["category_name"],
                        "amount_eur": row["amount_eur"],
                        "account": None,
                        "receipt_name": row["receipt_name"],
                        "missing_fields": missing,
                        "notes": row["notes"],
                    }
                )

    rows.sort(
        key=lambda r: (
            r["payment_date"] or r["invoice_date"] or "",
            r["id"],
        ),
        reverse=True,
    )

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Typ",
                "Wertstellung",
                "Rechnung",
                "Partei",
                "Kategorie",
                "EUR",
                "Konto",
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
                    r["payment_date"] or "",
                    r["invoice_date"] or "",
                    r["party"] or "",
                    r["category_name"] or "",
                    f"{r['amount_eur']:.2f}" if r["amount_eur"] is not None else "",
                    r["account"] or "",
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
        f"{'ID':<5} {'Typ':<9} {'Payment':<12} {'Invoice':<12} {'Partei':<18} {'Kategorie':<22} {'EUR':>10} {'Fehlt':<25}"
    )
    print("-" * 125)
    for r in rows:
        missing = format_missing_fields(r["missing_fields"])
        amount_str = f"{r['amount_eur']:.2f}" if r["amount_eur"] is not None else ""
        print(
            f"{r['id']:<5} {r['type']:<9} {(r['payment_date'] or ''):<12} {(r['invoice_date'] or ''):<12} {(r['party'] or '')[:18]:<18} {(r['category_name'] or '')[:22]:<22} {amount_str:>10} {missing[:25]:<25}"
        )
    print()
    print(
        "Hinweis: Unvollständige Buchungen bitte per `euer update expense|income <ID>` vervollständigen."
    )
    print(
        "Fehlende Felder: payment_date, invoice_date, category, receipt, vat, account."
    )
    conn.close()
