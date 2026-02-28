import sys
from pathlib import Path

from ..config import (
    get_audit_user,
    get_ledger_accounts,
    get_private_accounts,
    load_config,
    warn_missing_receipt,
)
from ..db import get_db_connection
from ..importers import get_tax_config
from ..services.errors import RecordNotFoundError, ValidationError
from ..services.expenses import update_expense
from ..services.income import update_income
from ..services.private_transfers import UNSET, update_private_transfer
from .helpers import warn_unusual_date_order


def cmd_update_expense(args):
    """Aktualisiert eine Ausgabe."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    private_accounts = get_private_accounts(config)
    tax_mode = get_tax_config(config)
    try:
        ledger_accounts = get_ledger_accounts(config)
    except ValidationError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    try:
        expense = update_expense(
            conn,
            record_id=args.id,
            payment_date=args.payment_date,
            invoice_date=args.invoice_date,
            vendor=args.vendor,
            category_name=args.category,
            ledger_account_key=args.ledger_account,
            ledger_accounts=ledger_accounts,
            amount_eur=args.amount,
            account=args.account,
            foreign_amount=args.foreign,
            receipt_name=args.receipt,
            notes=args.notes,
            vat=args.vat,
            is_rc=bool(args.rc),
            private_paid=args.private_paid,
            private_accounts=private_accounts,
            tax_mode=tax_mode,
            audit_user=audit_user,
        )
    except RecordNotFoundError:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)
    except ValidationError as exc:
        if exc.code == "category_not_found" and args.category:
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            conn.close()
            sys.exit(1)
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    warn_unusual_date_order(expense.payment_date, expense.invoice_date)

    print(f"Ausgabe #{args.id} aktualisiert.")

    warn_missing_receipt(
        expense.receipt_name,
        expense.invoice_date or expense.payment_date,
        "expenses",
        config,
    )


def cmd_update_income(args):
    """Aktualisiert eine Einnahme."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    tax_mode = get_tax_config(config)
    try:
        ledger_accounts = get_ledger_accounts(config)
    except ValidationError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    try:
        income = update_income(
            conn,
            record_id=args.id,
            payment_date=args.payment_date,
            invoice_date=args.invoice_date,
            source=args.source,
            category_name=args.category,
            ledger_account_key=args.ledger_account,
            ledger_accounts=ledger_accounts,
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
        if exc.code == "category_not_found" and args.category:
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            conn.close()
            sys.exit(1)
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    warn_unusual_date_order(income.payment_date, income.invoice_date)

    print(f"Einnahme #{args.id} aktualisiert.")

    warn_missing_receipt(
        income.receipt_name,
        income.invoice_date or income.payment_date,
        "income",
        config,
    )


def cmd_update_private_transfer(args):
    """Aktualisiert einen Privatvorgang."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    related_expense_id: int | None | object = UNSET
    if args.clear_related_expense:
        related_expense_id = None
    elif args.related_expense_id is not None:
        related_expense_id = args.related_expense_id

    try:
        transfer = update_private_transfer(
            conn,
            args.id,
            date=args.date,
            amount_eur=args.amount,
            description=args.description,
            notes=args.notes,
            related_expense_id=related_expense_id,
            audit_user=audit_user,
        )
    except RecordNotFoundError:
        print(f"Fehler: Privatvorgang #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)
    except ValidationError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    print(f"Privatvorgang #{transfer.id} aktualisiert.")
