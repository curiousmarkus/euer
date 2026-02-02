import sys
from pathlib import Path

from ..config import get_audit_user, load_config, warn_missing_receipt
from ..db import get_category_id, get_db_connection, log_audit, row_to_dict
from ..importers import get_tax_config
from ..utils import compute_hash


def cmd_update_expense(args):
    """Aktualisiert eine Ausgabe."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    tax_mode = get_tax_config(config)

    # Bestehenden Datensatz laden
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    old_data = row_to_dict(row)

    # Neue Werte bestimmen
    new_receipt = args.receipt if args.receipt is not None else row["receipt_name"]
    new_date = args.date if args.date else row["date"]
    new_vendor = args.vendor if args.vendor else row["vendor"]
    new_amount = args.amount if args.amount is not None else row["amount_eur"]
    new_account = args.account if args.account is not None else row["account"]
    new_foreign = args.foreign if args.foreign is not None else row["foreign_amount"]
    new_notes = args.notes if args.notes is not None else row["notes"]

    new_vat_input = row["vat_input"]
    new_vat_output = row["vat_output"]

    # Argumente: --vat und --rc
    # Hier wird es tricky, da --vat nun je nach Modus input oder output bedeuten kann.
    # Da update ein Patch ist, gehen wir wie bei add vor.

    manual_vat = args.vat

    current_rc = row["is_rc"] == 1
    new_rc = True if args.rc else current_rc

    # Wir machen es einfach: Wenn --vat oder --rc oder --amount,
    # berechnen wir die Steuerlogik neu basierend auf den neuen Werten.
    recalc_tax = (args.vat is not None) or args.rc or (args.amount is not None)

    if recalc_tax:
        # Basiswerte
        calc_amount = new_amount

        if tax_mode == "small_business":
            if new_rc:
                # RC = output tax
                if manual_vat is not None:
                    new_vat_output = manual_vat
                elif args.rc or (args.amount is not None):
                    # Recalc default if needed
                    # Only if we don't have a manual vat override from previous?
                    # "update" is tricky. Let's strictly follow arguments. If --vat provided, use it.
                    # If not, and --amount changed or --rc set, recalc 19%.
                    new_vat_output = round(abs(calc_amount) * 0.19, 2)
                else:
                    # Keep existing if sensible?
                    # If existing is 0 and amount changed, should we update? yes.
                    # Simplest: Recalc default if manual not provided.
                    new_vat_output = round(abs(calc_amount) * 0.19, 2)

                new_vat_input = 0.0
            else:
                new_vat_input = 0.0
                new_vat_output = 0.0

        elif tax_mode == "standard":
            if new_rc:
                if manual_vat is not None:
                    val = manual_vat
                else:
                    val = round(abs(calc_amount) * 0.19, 2)
                new_vat_input = val
                new_vat_output = val
            else:
                # Normal
                if manual_vat is not None:
                    new_vat_input = manual_vat
                else:
                    # Wenn amount geändert wurde, aber kein --vat, was tun?
                    # Wir lassen es beim alten (wenn es Sinn macht) oder 0?
                    # Wir lassen es beim alten, es sei denn es war vorher RC und jetzt nicht mehr (geht eh nicht ohne --no-rc)
                    # Da wir vorerst --no-rc nicht haben, bleibt es bei RC=False -> RC=False.
                    # Also nur amount update.
                    # Passt vat_input noch?
                    pass
                new_vat_output = 0.0

    # Kategorie
    if args.category:
        cat_id = get_category_id(conn, args.category, "expense")
        if not cat_id:
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            conn.close()
            sys.exit(1)
    else:
        cat_id = row["category_id"]

    # Neuen Hash berechnen
    new_hash = compute_hash(new_date, new_vendor, new_amount, new_receipt or "")

    # Update
    conn.execute(
        """UPDATE expenses SET
           receipt_name = ?, date = ?, vendor = ?, category_id = ?, amount_eur = ?,
           account = ?, foreign_amount = ?, notes = ?, is_rc = ?, vat_input = ?, vat_output = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_date,
            new_vendor,
            cat_id,
            new_amount,
            new_account,
            new_foreign,
            new_notes,
            1 if new_rc else 0,
            new_vat_input,
            new_vat_output,
            new_hash,
            args.id,
        ),
    )

    # Audit-Log
    new_data = {
        "receipt_name": new_receipt,
        "date": new_date,
        "vendor": new_vendor,
        "category_id": cat_id,
        "amount_eur": new_amount,
        "account": new_account,
        "foreign_amount": new_foreign,
        "notes": new_notes,
        "is_rc": 1 if new_rc else 0,
        "vat_input": new_vat_input,
        "vat_output": new_vat_output,
    }
    log_audit(
        conn,
        "expenses",
        args.id,
        "UPDATE",
        old_data=old_data,
        new_data=new_data,
        user=audit_user,
    )
    conn.commit()
    conn.close()

    print(f"Ausgabe #{args.id} aktualisiert.")

    # Beleg-Warnung (nach erfolgreicher Transaktion)
    warn_missing_receipt(new_receipt, new_date, "expenses", config)


def cmd_update_income(args):
    """Aktualisiert eine Einnahme."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    tax_mode = get_tax_config(config)

    row = conn.execute("SELECT * FROM income WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"Fehler: Einnahme #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    old_data = row_to_dict(row)

    new_receipt = args.receipt if args.receipt is not None else row["receipt_name"]
    new_date = args.date if args.date else row["date"]
    new_source = args.source if args.source else row["source"]
    new_amount = args.amount if args.amount is not None else row["amount_eur"]
    new_foreign = args.foreign if args.foreign is not None else row["foreign_amount"]
    new_notes = args.notes if args.notes is not None else row["notes"]
    new_vat_output = row["vat_output"]
    if args.vat is not None:
        new_vat_output = args.vat
    elif tax_mode == "standard" and row["vat_output"] is None:
        new_vat_output = None

    if args.category:
        cat_id = get_category_id(conn, args.category, "income")
        if not cat_id:
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            conn.close()
            sys.exit(1)
    else:
        cat_id = row["category_id"]

    new_hash = compute_hash(new_date, new_source, new_amount, new_receipt or "")

    conn.execute(
        """UPDATE income SET
           receipt_name = ?, date = ?, source = ?, category_id = ?, amount_eur = ?,
           foreign_amount = ?, notes = ?, vat_output = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_date,
            new_source,
            cat_id,
            new_amount,
            new_foreign,
            new_notes,
            new_vat_output,
            new_hash,
            args.id,
        ),
    )

    new_data = {
        "receipt_name": new_receipt,
        "date": new_date,
        "source": new_source,
        "category_id": cat_id,
        "amount_eur": new_amount,
        "foreign_amount": new_foreign,
        "notes": new_notes,
        "vat_output": new_vat_output,
    }
    log_audit(
        conn,
        "income",
        args.id,
        "UPDATE",
        old_data=old_data,
        new_data=new_data,
        user=audit_user,
    )
    conn.commit()
    conn.close()

    print(f"Einnahme #{args.id} aktualisiert.")

    # Beleg-Warnung (nach erfolgreicher Transaktion)
    warn_missing_receipt(new_receipt, new_date, "income", config)
