import sys
from pathlib import Path

from ..config import get_audit_user, load_config, warn_missing_receipt
from ..db import get_db_connection
from ..importers import get_tax_config
from ..services.errors import RecordNotFoundError, ValidationError
from ..services.expenses import update_expense
from ..services.income import update_income


def cmd_update_expense(args):
    """Aktualisiert eine Ausgabe."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    tax_mode = get_tax_config(config)

    try:
        expense = update_expense(
            conn,
            record_id=args.id,
            date=args.date,
            vendor=args.vendor,
            category_name=args.category,
            amount_eur=args.amount,
            account=args.account,
            foreign_amount=args.foreign,
            receipt_name=args.receipt,
            notes=args.notes,
            vat=args.vat,
            is_rc=bool(args.rc),
            tax_mode=tax_mode,
            audit_user=audit_user,
        )
    except RecordNotFoundError:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)
    except ValidationError as exc:
        if exc.code == "category_not_found":
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            conn.close()
            sys.exit(1)
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    print(f"Ausgabe #{args.id} aktualisiert.")

    warn_missing_receipt(expense.receipt_name, expense.date, "expenses", config)


def cmd_update_income(args):
    """Aktualisiert eine Einnahme."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    tax_mode = get_tax_config(config)

    try:
        income = update_income(
            conn,
            record_id=args.id,
            date=args.date,
            source=args.source,
            category_name=args.category,
            amount_eur=args.amount,
            foreign_amount=args.foreign,
            receipt_name=args.receipt,
            notes=args.notes,
            vat=args.vat,
            tax_mode=tax_mode,
            audit_user=audit_user,
        )
    except RecordNotFoundError:
        print(f"Fehler: Einnahme #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)
    except ValidationError as exc:
        if exc.code == "category_not_found":
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            conn.close()
            sys.exit(1)
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    print(f"Einnahme #{args.id} aktualisiert.")

    warn_missing_receipt(income.receipt_name, income.date, "income", config)
