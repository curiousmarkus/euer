import json
import sys
from pathlib import Path

from ..config import get_audit_user, load_config
from ..db import get_category_id, get_db_connection, log_audit
from ..importers import get_tax_config, iter_import_rows, normalize_import_row
from ..utils import compute_hash


def cmd_import(args):
    """Bulk-Import von Transaktionen."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
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
    incomplete = 0

    for row in rows:
        total += 1
        normalized = normalize_import_row(row)
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
        vat_input = normalized["vat_input"]
        vat_output = normalized["vat_output"]

        missing_fields = []

        if not row_type:
            missing_fields.append("type")
        if not date:
            missing_fields.append("date")
        if amount is None:
            missing_fields.append("amount_eur")
        if not party:
            missing_fields.append("party")
        if not category_name:
            missing_fields.append("category")

        cat_id = None
        if row_type in ("expense", "income") and category_name:
            cat_id = get_category_id(conn, str(category_name), row_type)
            if not cat_id:
                missing_fields.append("category")

        if missing_fields:
            incomplete += 1
            if not args.dry_run:
                cursor = conn.execute(
                    """INSERT INTO incomplete_entries
                       (type, date, party, category_name, amount_eur, account,
                        foreign_amount, receipt_name, notes, is_rc, vat_input, vat_output,
                        raw_data, missing_fields)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row_type or "unknown",
                        str(date) if date else None,
                        str(party) if party else None,
                        str(category_name) if category_name else None,
                        amount,
                        str(account) if account else None,
                        str(foreign_amount) if foreign_amount else None,
                        str(receipt_name) if receipt_name else None,
                        str(notes) if notes else None,
                        1 if rc else 0,
                        vat_input,
                        vat_output,
                        json.dumps(normalized["raw_data"], ensure_ascii=False),
                        json.dumps(missing_fields, ensure_ascii=False),
                    ),
                )
                record_id = cursor.lastrowid
                assert record_id is not None
                log_audit(
                    conn,
                    "incomplete_entries",
                    record_id,
                    "INSERT",
                    new_data={
                        "type": row_type or "unknown",
                        "date": str(date) if date else None,
                        "party": str(party) if party else None,
                        "category_name": str(category_name) if category_name else None,
                        "amount_eur": amount,
                        "account": str(account) if account else None,
                        "foreign_amount": str(foreign_amount) if foreign_amount else None,
                        "receipt_name": str(receipt_name) if receipt_name else None,
                        "notes": str(notes) if notes else None,
                        "is_rc": 1 if rc else 0,
                        "vat_input": vat_input,
                        "vat_output": vat_output,
                        "missing_fields": missing_fields,
                    },
                    user=audit_user,
                )
            continue

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
                # Normale Ausgabe: Defaults auf 0 wenn nicht vorhanden
                if vat_input is None:
                    vat_input = 0.0
                if vat_output is None:
                    vat_output = 0.0

            tx_hash = compute_hash(
                str(date), str(party), float(amount), receipt_name or ""
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

            cursor = conn.execute(
                """INSERT INTO expenses 
                   (receipt_name, date, vendor, category_id, amount_eur, account,
                    foreign_amount, notes, is_rc, vat_input, vat_output, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
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
                    tx_hash,
                ),
            )
            record_id = cursor.lastrowid
            assert record_id is not None

            new_data = {
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
            }
            log_audit(
                conn,
                "expenses",
                record_id,
                "INSERT",
                new_data=new_data,
                user=audit_user,
            )
        else:
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

            cursor = conn.execute(
                """INSERT INTO income
                   (receipt_name, date, source, category_id, amount_eur,
                    foreign_amount, notes, vat_output, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
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
    print(f"  Unvollständig: {incomplete}")
    if args.dry_run:
        print("  Dry-Run: keine Änderungen gespeichert")
