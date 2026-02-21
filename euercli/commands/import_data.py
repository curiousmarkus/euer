import json
import sys
import uuid
from pathlib import Path

from ..config import get_audit_user, get_private_accounts, load_config
from ..db import get_category_id, get_db_connection, log_audit
from ..importers import get_tax_config, iter_import_rows, normalize_import_row
from ..services.private_classification import classify_expense_private_paid
from ..utils import compute_hash


def print_import_schema() -> None:
    """Gibt Schema, Beispiele und Alias-Keys für den Import aus."""
    print("Import-Schema (CSV/JSONL)")
    print()
    print("Pflichtfelder:")
    print("  - type: expense|income (oder aus Vorzeichen von amount_eur abgeleitet)")
    print("  - date: YYYY-MM-DD")
    print("  - party: Lieferant/Quelle")
    print("  - amount_eur: Betrag in EUR (Ausgaben negativ, Einnahmen positiv)")
    print()
    print("Optionale Felder:")
    print(
        "  category, account, foreign_amount, receipt_name, notes, rc, private_paid, "
        "vat_input, vat_output"
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
    print("  rc: rc, is_rc, RC")
    print("  private_paid: private_paid, Privat bezahlt")
    print("  vat_input: vat_input, Vorsteuer, USt-VA")
    print("  vat_output: vat_output, Umsatzsteuer")
    print("  notes: notes, Bemerkung, Notiz")
    print("  account: account, Konto")
    print("  foreign_amount: foreign_amount, foreign, Fremdwährung")
    print()
    print("Hinweis:")
    print("  - CSV-Exporte von 'euer export' können direkt re-importiert werden.")
    print("  - Kategorien mit '(NN)' werden automatisch bereinigt.")
    print("  - private_paid=true|1|yes|X markiert manuell als Sacheinlage.")
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
        if not normalized["date"]:
            missing_fields.append("date")
        if normalized["amount_eur"] is None:
            missing_fields.append("amount_eur")
        if not normalized["party"]:
            missing_fields.append("party")
        if missing_fields:
            errors.append((idx, missing_fields))
        else:
            if normalized["category"]:
                cat_id = get_category_id(
                    conn,
                    str(normalized["category"]),
                    normalized["type"],
                )
                if cat_id:
                    normalized["_category_id"] = cat_id
        normalized_rows.append(normalized)

    if errors:
        print("Fehler: Import abgebrochen. Pflichtfelder fehlen:", file=sys.stderr)
        for row_idx, fields in errors:
            fields_str = ", ".join(fields)
            print(f"  Zeile {row_idx}: {fields_str}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    for normalized in normalized_rows:
        row_type = normalized["type"]
        date = normalized["date"]
        party = normalized["party"]
        category_name = normalized["category"]
        amount = normalized["amount_eur"]
        account = normalized["account"]
        foreign_amount = normalized["foreign_amount"]
        receipt_name = normalized["receipt_name"]
        notes = normalized["notes"]
        rc = normalized["rc"]
        private_paid = normalized["private_paid"]
        vat_input = normalized["vat_input"]
        vat_output = normalized["vat_output"]

        cat_id = normalized.get("_category_id")

        if row_type == "expense":
            # Automatische VAT-Berechnung für RC, falls nicht im Import
            if rc and amount is not None:
                calc_vat = round(abs(amount) * 0.19, 2)
                if tax_mode == "small_business":
                    if vat_output is None:
                        vat_output = calc_vat
                    if vat_input is None:
                        vat_input = 0.0
                else:
                    # Standard: RC = Nullsumme
                    if vat_output is None:
                        vat_output = calc_vat
                    if vat_input is None:
                        vat_input = calc_vat
            else:
                # Normale Ausgabe: im Standard-Modus bleibt vat_input optional
                if tax_mode == "small_business":
                    if vat_input is None:
                        vat_input = 0.0
                    if vat_output is None:
                        vat_output = 0.0
                else:
                    if vat_output is None:
                        vat_output = 0.0

            tx_hash = compute_hash(
                str(date), str(party), float(amount), receipt_name or ""
            )
            is_private_paid, private_classification = classify_expense_private_paid(
                account=str(account) if account is not None else None,
                category_name=str(category_name) if category_name is not None else None,
                private_accounts=private_accounts,
                manual_override=bool(private_paid),
            )
            existing = conn.execute(
                "SELECT id FROM expenses WHERE hash = ?", (tx_hash,)
            ).fetchone()
            if existing:
                duplicates += 1
                continue

            inserted_expenses += 1
            if args.dry_run:
                continue

            record_uuid = str(uuid.uuid4())
            cursor = conn.execute(
                """INSERT INTO expenses 
                   (uuid, receipt_name, date, vendor, category_id, amount_eur, account,
                    foreign_amount, notes, is_rc, vat_input, vat_output,
                    is_private_paid, private_classification, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_uuid,
                    receipt_name,
                    str(date),
                    str(party),
                    cat_id,
                    amount,
                    account,
                    foreign_amount,
                    notes,
                    1 if rc else 0,
                    vat_input,
                    vat_output,
                    1 if is_private_paid else 0,
                    private_classification,
                    tx_hash,
                ),
            )
            record_id = cursor.lastrowid
            assert record_id is not None

            new_data = {
                "uuid": record_uuid,
                "receipt_name": receipt_name,
                "date": str(date),
                "vendor": str(party),
                "category_id": cat_id,
                "amount_eur": amount,
                "account": account,
                "foreign_amount": foreign_amount,
                "notes": notes,
                "is_rc": 1 if rc else 0,
                "vat_input": vat_input,
                "vat_output": vat_output,
                "is_private_paid": 1 if is_private_paid else 0,
                "private_classification": private_classification,
            }
            log_audit(
                conn,
                "expenses",
                record_id,
                "INSERT",
                record_uuid=record_uuid,
                new_data=new_data,
                user=audit_user,
            )
        else:
            if tax_mode == "small_business":
                if vat_output is None:
                    vat_output = 0.0

            tx_hash = compute_hash(
                str(date), str(party), float(amount), receipt_name or ""
            )
            existing = conn.execute(
                "SELECT id FROM income WHERE hash = ?", (tx_hash,)
            ).fetchone()
            if existing:
                duplicates += 1
                continue

            inserted_income += 1
            if args.dry_run:
                continue

            record_uuid = str(uuid.uuid4())
            cursor = conn.execute(
                """INSERT INTO income
                   (uuid, receipt_name, date, source, category_id, amount_eur,
                    foreign_amount, notes, vat_output, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_uuid,
                    receipt_name,
                    str(date),
                    str(party),
                    cat_id,
                    amount,
                    foreign_amount,
                    notes,
                    vat_output,
                    tx_hash,
                ),
            )
            record_id = cursor.lastrowid
            assert record_id is not None

            new_data = {
                "uuid": record_uuid,
                "receipt_name": receipt_name,
                "date": str(date),
                "source": str(party),
                "category_id": cat_id,
                "amount_eur": amount,
                "foreign_amount": foreign_amount,
                "notes": notes,
                "vat_output": vat_output,
            }
            log_audit(
                conn,
                "income",
                record_id,
                "INSERT",
                record_uuid=record_uuid,
                new_data=new_data,
                user=audit_user,
            )

    if not args.dry_run:
        conn.commit()
    conn.close()

    print("Import abgeschlossen")
    print(f"  Zeilen gesamt: {total}")
    print(f"  Ausgaben angelegt: {inserted_expenses}")
    print(f"  Einnahmen angelegt: {inserted_income}")
    print(f"  Duplikate übersprungen: {duplicates}")
    if args.dry_run:
        print("  Dry-Run: keine Änderungen gespeichert")
