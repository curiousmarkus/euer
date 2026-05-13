import json
import sys
from pathlib import Path

from ..config import get_audit_user, get_ledger_accounts, get_private_accounts, load_config
from ..db import get_category_id, get_db_connection
from ..importers import get_tax_config, iter_import_rows, normalize_import_row
from ..services.duplicates import DuplicateAction
from ..services.errors import ValidationError
from ..services.expenses import create_expense
from ..services.income import create_income
from ..utils import parse_bool


def print_import_schema() -> None:
    """Gibt Schema, Beispiele und Alias-Keys für den Import aus."""
    print("Import-Schema (CSV/JSONL)")
    print()
    print("Pflichtfelder:")
    print("  - type: expense|income (oder aus Vorzeichen von amount_eur abgeleitet)")
    print("  - payment_date oder invoice_date: YYYY-MM-DD (mindestens eins)")
    print("  - party: Lieferant/Quelle")
    print("  - amount_eur: Betrag in EUR (Ausgaben negativ, Einnahmen positiv)")
    print()
    print("Optionale Felder:")
    print(
        "  category, account, ledger_account, foreign_amount, receipt_name, notes, rc, "
        "private_paid, vat_input, vat_output, vat_rate, vat_code, tax_free"
    )
    print()
    print("Minimaler JSONL-Datensatz (Ausgabe):")
    print(
        '  {"type":"expense","date":"2025-03-19","party":"1und1",'
        '"category":"Telekommunikation","amount_eur":-39.99}'
    )
    print("Minimaler JSONL-Datensatz (Einnahme):")
    print(
        '  {"type":"income","date":"2025-03-19","party":"Kunde GmbH",'
        '"category":"Umsatzsteuerpflichtige Betriebseinnahmen","amount_eur":2500.00}'
    )
    print()
    print("Alias-Keys (werden akzeptiert):")
    print("  party: party, vendor, source, counterparty, Lieferant, Quelle, Partei")
    print("  category: category, category_name, Kategorie")
    print("  amount_eur: amount_eur, amount, EUR, Betrag, Betrag in EUR")
    print("  receipt_name: receipt_name, receipt, Belegname, Beleg")
    print("  rc: rc, rc_type, is_rc, RC")
    print("  rc_jurisdiction (Legacy): rc_jurisdiction, rc-jurisdiction, RC-Jurisdiktion")
    print("  private_paid: private_paid, Privat bezahlt")
    print("  vat_input: vat_input, Vorsteuer, USt-VA")
    print("  vat_output: vat_output, Umsatzsteuer")
    print("  vat_rate: vat_rate, vat-rate, Steuersatz")
    print("  vat_code: vat_code, vat-code, Steuerklasse")
    print("  tax_free: tax_free, tax-free, Steuerfrei")
    print("  notes: notes, Bemerkung, Notiz")
    print("  account: account, Konto")
    print("  ledger_account: ledger_account, Buchungskonto, konto")
    print("  foreign_amount: foreign_amount, foreign, Fremdwährung")
    print("  payment_date: payment_date, date, Datum, Wertstellung")
    print("  invoice_date: invoice_date, Rechnungsdatum")
    print()
    print("Hinweis:")
    print("  - CSV-Exporte von 'euer export' können direkt re-importiert werden.")
    print("  - Kategorien mit '(NN)' werden automatisch bereinigt.")
    print("  - private_paid=true|1|yes|X markiert manuell als Sacheinlage.")
    print("  - rc akzeptiert leer, eu oder third-country.")
    print("  - Legacy rc=true|X erfordert rc_jurisdiction=eu|third-country.")
    print("  - vat_rate akzeptiert 19, 7, 0 sowie Werte mit %-Zeichen.")
    print("  - Unbekannte Kategorien werden als fehlend behandelt.")
    print("  - Unvollständige Felder (category/receipt/vat/account) werden später per")
    print("    `euer incomplete list` angezeigt.")


def cmd_import(args):
    """Bulk-Import von Transaktionen."""
    if args.schema:
        print_import_schema()
        return

    if not args.file or not args.format:
        print(
            "Fehler: --file und --format sind erforderlich (oder --schema).",
            file=sys.stderr,
        )
        sys.exit(1)

    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    private_accounts = get_private_accounts(config)
    tax_mode = get_tax_config(config)
    try:
        ledger_accounts = get_ledger_accounts(config)
    except ValidationError as exc:
        conn.close()
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)

    try:
        rows = iter_import_rows(args.file, args.format)
    except (OSError, json.JSONDecodeError) as exc:
        conn.close()
        print(f"Fehler: Importdatei konnte nicht gelesen werden: {exc}", file=sys.stderr)
        sys.exit(1)

    total = 0
    inserted_expenses = 0
    inserted_income = 0
    duplicates = 0

    normalized_rows: list[dict] = []
    errors: list[tuple[int, list[str]]] = []

    for idx, row in enumerate(rows, start=1):
        total += 1
        normalized = normalize_import_row(row)
        missing_fields = []
        if not normalized["type"]:
            missing_fields.append("type")
        if not normalized["payment_date"] and not normalized["invoice_date"]:
            missing_fields.append("payment_date|invoice_date")
        if normalized["amount_eur"] is None:
            missing_fields.append("amount_eur")
        if not normalized["party"]:
            missing_fields.append("party")
        if normalized["vat_rate_raw"] is not None and normalized["vat_rate"] is None:
            missing_fields.append("invalid_vat_rate")
        rc_type = normalized["rc_type"]
        rc_raw = normalized["rc_raw"]
        rc_jurisdiction_raw = normalized["rc_jurisdiction_raw"]
        if normalized["type"] == "expense":
            if rc_type is None:
                missing_fields.append("invalid_rc_type")
            if parse_bool(rc_raw) and rc_type == "none":
                if rc_jurisdiction_raw is None:
                    missing_fields.append("rc_type")
                else:
                    missing_fields.append("invalid_rc_type")
            if rc_type == "unclassified":
                missing_fields.append("unclassified_rc_type_not_allowed")
        elif rc_raw is not None or rc_jurisdiction_raw is not None:
            missing_fields.append("rc_type_without_expense")
        if missing_fields:
            errors.append((idx, missing_fields))
        else:
            resolved_category_name = normalized["category"]
            if resolved_category_name:
                cat_id = get_category_id(
                    conn,
                    str(resolved_category_name),
                    normalized["type"],
                )
                if not cat_id:
                    resolved_category_name = None
            normalized["_resolved_category_name"] = resolved_category_name
        normalized_rows.append(normalized)

    if errors:
        print(
            "Fehler: Import abgebrochen. Pflichtfelder fehlen oder Werte sind ungültig:",
            file=sys.stderr,
        )
        for row_idx, fields in errors:
            fields_str = ", ".join(fields)
            print(f"  Zeile {row_idx}: {fields_str}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    try:
        for normalized in normalized_rows:
            row_type = normalized["type"]
            payment_date = normalized["payment_date"]
            invoice_date = normalized["invoice_date"]
            party = normalized["party"]
            category_name = normalized["_resolved_category_name"]
            amount = normalized["amount_eur"]
            account = normalized["account"]
            ledger_account = normalized["ledger_account"]
            foreign_amount = normalized["foreign_amount"]
            receipt_name = normalized["receipt_name"]
            notes = normalized["notes"]
            rc_type = normalized["rc_type"]
            private_paid = normalized["private_paid"]
            vat_input = normalized["vat_input"]
            vat_output = normalized["vat_output"]
            vat_rate = normalized["vat_rate"]
            vat_code = normalized["vat_code"]
            tax_free = normalized["tax_free"]

            if row_type == "expense":
                created = create_expense(
                    conn,
                    payment_date=str(payment_date) if payment_date is not None else None,
                    invoice_date=str(invoice_date) if invoice_date is not None else None,
                    vendor=str(party),
                    category_name=str(category_name) if category_name is not None else None,
                    amount_eur=float(amount),
                    account=str(account) if account is not None else None,
                    ledger_account_key=(
                        str(ledger_account) if ledger_account is not None else None
                    ),
                    ledger_accounts=ledger_accounts,
                    foreign_amount=str(foreign_amount) if foreign_amount is not None else None,
                    receipt_name=str(receipt_name) if receipt_name is not None else None,
                    notes=str(notes) if notes is not None else None,
                    rc_type=str(rc_type),
                    vat_input=vat_input,
                    vat_output=vat_output,
                    vat_rate=vat_rate,
                    vat_code=vat_code,
                    private_paid=bool(private_paid),
                    private_accounts=private_accounts,
                    audit_user=audit_user,
                    tax_mode=tax_mode,
                    on_duplicate=DuplicateAction.SKIP,
                    auto_commit=False,
                )
                if created is None:
                    duplicates += 1
                    continue
                inserted_expenses += 1
            else:
                created = create_income(
                    conn,
                    payment_date=str(payment_date) if payment_date is not None else None,
                    invoice_date=str(invoice_date) if invoice_date is not None else None,
                    source=str(party),
                    category_name=str(category_name) if category_name is not None else None,
                    amount_eur=float(amount),
                    ledger_account_key=(
                        str(ledger_account) if ledger_account is not None else None
                    ),
                    ledger_accounts=ledger_accounts,
                    foreign_amount=str(foreign_amount) if foreign_amount is not None else None,
                    receipt_name=str(receipt_name) if receipt_name is not None else None,
                    notes=str(notes) if notes is not None else None,
                    vat_output=vat_output,
                    vat_rate=vat_rate,
                    vat_code=vat_code,
                    tax_free=bool(tax_free),
                    audit_user=audit_user,
                    tax_mode=tax_mode,
                    on_duplicate=DuplicateAction.SKIP,
                    auto_commit=False,
                )
                if created is None:
                    duplicates += 1
                    continue
                inserted_income += 1
    except ValidationError as exc:
        conn.rollback()
        conn.close()
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        conn.rollback()
    else:
        conn.commit()
    conn.close()

    print("Import abgeschlossen")
    print(f"  Zeilen gesamt: {total}")
    print(f"  Ausgaben angelegt: {inserted_expenses}")
    print(f"  Einnahmen angelegt: {inserted_income}")
    print(f"  Duplikate übersprungen: {duplicates}")
    if args.dry_run:
        print("  Dry-Run: keine Änderungen gespeichert")
