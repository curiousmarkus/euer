import sys
from pathlib import Path

from ..config import get_audit_user, load_config, warn_missing_receipt
from ..db import get_category_id, get_db_connection, log_audit
from ..importers import get_tax_config
from ..utils import compute_hash, format_amount


def cmd_add_expense(args):
    """Fügt eine Ausgabe hinzu."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    tax_mode = get_tax_config(config)

    cat_id = None
    if args.category:
        cat_id = get_category_id(conn, args.category, "expense")
        if not cat_id:
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            print("Verfügbare Kategorien:", file=sys.stderr)
            for row in conn.execute("SELECT name FROM categories WHERE type = 'expense'"):
                print(f"  - {row['name']}", file=sys.stderr)
            conn.close()
            sys.exit(1)

    vat_input: float | None = None
    vat_output: float | None = None
    manual_vat = args.vat

    if tax_mode == "small_business":
        # Kleinunternehmer
        if args.rc:
            # RC: 19% Schulden (vat_output), keine Vorsteuer
            if manual_vat is not None:
                vat_output = manual_vat
            else:
                vat_output = round(abs(args.amount) * 0.19, 2)
            vat_input = 0.0
        else:
            # Normal: Brutto = Kosten. Keine USt.
            vat_input = 0.0
            vat_output = 0.0
            if manual_vat is not None:
                print(
                    "Warnung: --vat wird im Kleinunternehmermodus bei normalen Ausgaben ignoriert.",
                    file=sys.stderr,
                )

    elif tax_mode == "standard":
        # Regelbesteuerung
        if args.rc:
            # RC: Nullsummenspiel. vat_input = vat_output (19% oder manuell)
            if manual_vat is not None:
                vat_val = manual_vat
            else:
                vat_val = round(abs(args.amount) * 0.19, 2)
            vat_input = vat_val
            vat_output = vat_val
        else:
            # Normal: Vorsteuer (vat_input) ziehen. vat_output = 0.
            if manual_vat is not None:
                vat_input = manual_vat
            else:
                # Ohne explizite VAT-Angabe und ohne RC gehen wir hier von 0 oder Brutto aus?
                # Spec sagt: "interpretieren EUR Beträge als Input".
                # Ohne --vat Argument können wir keine Steuer raten (7 vs 19).
                # Also bleibt vat_input 0, wenn nicht angegeben?
                # Oder default 19% aus Brutto rausrechnen?
                # "vorerst gehen wir davon aus, dass die EUR Beträge als Input geliefert werden"
                # -> Ich nehme an, ohne --vat ist es 0 (oder User muss --vat angeben).
                vat_input = None
            vat_output = 0.0

    # Hash für Duplikaterkennung
    tx_hash = compute_hash(args.date, args.vendor, args.amount, args.receipt or "")

    # Duplikat-Prüfung
    existing = conn.execute(
        "SELECT id FROM expenses WHERE hash = ?", (tx_hash,)
    ).fetchone()
    if existing:
        print(
            f"Warnung: Duplikat erkannt (ID {existing['id']}), überspringe.",
            file=sys.stderr,
        )
        conn.close()
        return

    cursor = conn.execute(
        """INSERT INTO expenses
           (receipt_name, date, vendor, category_id, amount_eur, account,
            foreign_amount, notes, is_rc, vat_input, vat_output, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            args.receipt,
            args.date,
            args.vendor,
            cat_id,
            args.amount,
            args.account,
            args.foreign,
            args.notes,
            1 if args.rc else 0,
            vat_input,
            vat_output,
            tx_hash,
        ),
    )
    record_id = cursor.lastrowid
    assert record_id is not None

    new_data = {
        "receipt_name": args.receipt,
        "date": args.date,
        "vendor": args.vendor,
        "category_id": cat_id,
        "amount_eur": args.amount,
        "account": args.account,
        "foreign_amount": args.foreign,
        "notes": args.notes,
        "is_rc": 1 if args.rc else 0,
        "vat_input": vat_input,
        "vat_output": vat_output,
    }
    log_audit(conn, "expenses", record_id, "INSERT", new_data=new_data, user=audit_user)

    conn.commit()
    conn.close()

    vat_info = ""
    vat_output_val = vat_output or 0.0
    vat_input_val = vat_input or 0.0
    if vat_output_val > 0 or vat_input_val > 0:
        if tax_mode == "small_business":
            vat_info = f" (USt-VA: {vat_output_val:.2f})"
        else:
            # RB: Saldo anzeigen? oder beide?
            diff = vat_output_val - vat_input_val
            vat_info = (
                f" (Vorst: {vat_input_val:.2f}, USt: {vat_output_val:.2f}, Saldo: {diff:.2f})"
            )

    print(
        f"Ausgabe #{record_id} hinzugefügt: {args.vendor} {format_amount(args.amount)} EUR{vat_info}"
    )

    # Beleg-Warnung (nach erfolgreicher Transaktion)
    warn_missing_receipt(args.receipt, args.date, "expenses", config)


def cmd_add_income(args):
    """Fügt eine Einnahme hinzu."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    tax_mode = get_tax_config(config)

    cat_id = None
    if args.category:
        cat_id = get_category_id(conn, args.category, "income")
        if not cat_id:
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            print("Verfügbare Kategorien:", file=sys.stderr)
            for row in conn.execute("SELECT name FROM categories WHERE type = 'income'"):
                print(f"  - {row['name']}", file=sys.stderr)
            conn.close()
            sys.exit(1)

    vat_output: float | None = 0.0
    if tax_mode == "standard":
        # Regelbesteuerung: USt angeben oder berechnen?
        # args.vat war bisher nicht verfügbar für income, muss im ArgumentParser ergänzt werden?
        # Ich habe args.vat noch nicht zu add_income hinzugefügt im Parser. Das muss ich noch tun.
        # Annahme: Wenn args.vat existiert, nutzen wir es.
        if hasattr(args, "vat") and args.vat is not None:
            vat_output = args.vat
        else:
            vat_output = None

    tx_hash = compute_hash(args.date, args.source, args.amount, args.receipt or "")

    existing = conn.execute(
        "SELECT id FROM income WHERE hash = ?", (tx_hash,)
    ).fetchone()
    if existing:
        print(
            f"Warnung: Duplikat erkannt (ID {existing['id']}), überspringe.",
            file=sys.stderr,
        )
        conn.close()
        return

    cursor = conn.execute(
        """INSERT INTO income
           (receipt_name, date, source, category_id, amount_eur,
            foreign_amount, notes, vat_output, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            args.receipt,
            args.date,
            args.source,
            cat_id,
            args.amount,
            args.foreign,
            args.notes,
            vat_output,
            tx_hash,
        ),
    )
    record_id = cursor.lastrowid
    assert record_id is not None

    new_data = {
        "receipt_name": args.receipt,
        "date": args.date,
        "source": args.source,
        "category_id": cat_id,
        "amount_eur": args.amount,
        "foreign_amount": args.foreign,
        "notes": args.notes,
        "vat_output": vat_output,
    }
    log_audit(conn, "income", record_id, "INSERT", new_data=new_data, user=audit_user)

    conn.commit()
    conn.close()

    vat_info = f" (USt: {vat_output:.2f})" if vat_output else ""

    print(
        f"Einnahme #{record_id} hinzugefügt: {args.source} {format_amount(args.amount)} EUR{vat_info}"
    )

    # Beleg-Warnung (nach erfolgreicher Transaktion)
    warn_missing_receipt(args.receipt, args.date, "income", config)
