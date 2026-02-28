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
from ..services.categories import get_category_list, get_ledger_accounts_for_category
from ..services.errors import ValidationError
from ..services.expenses import create_expense
from ..services.income import create_income
from ..services.private_transfers import create_private_transfer
from ..utils import format_amount
from .helpers import warn_unusual_date_order


def _print_category_error_with_ledger_hint(conn, booking_type: str, ledger_accounts) -> None:
    print("Fehler: Kategorie erforderlich.", file=sys.stderr)
    print("Verfügbare Kategorien:", file=sys.stderr)
    for category in get_category_list(conn, booking_type):
        accounts = get_ledger_accounts_for_category(category.name, ledger_accounts)
        if not accounts:
            continue
        account_keys = ", ".join(account.key for account in accounts)
        print(f"  - {category.name} (Konten: {account_keys})", file=sys.stderr)
    print(
        "Tipp: Verwende --ledger-account <Schlüssel>, um die Kategorie automatisch zu setzen.",
        file=sys.stderr,
    )


def cmd_add_expense(args):
    """Fügt eine Ausgabe hinzu."""
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

    if tax_mode == "small_business" and not args.rc and args.vat is not None:
        print(
            "Warnung: --vat wird im Kleinunternehmermodus bei normalen Ausgaben ignoriert.",
            file=sys.stderr,
        )

    if not args.category and not args.ledger_account and ledger_accounts:
        _print_category_error_with_ledger_hint(conn, "expense", ledger_accounts)
        conn.close()
        sys.exit(1)

    try:
        expense = create_expense(
            conn,
            payment_date=args.payment_date,
            invoice_date=args.invoice_date,
            vendor=args.vendor,
            amount_eur=args.amount,
            category_name=args.category,
            ledger_account_key=args.ledger_account,
            ledger_accounts=ledger_accounts,
            account=args.account,
            foreign_amount=args.foreign,
            receipt_name=args.receipt,
            notes=args.notes,
            is_rc=bool(args.rc),
            vat=args.vat,
            private_paid=bool(args.private_paid),
            private_accounts=private_accounts,
            tax_mode=tax_mode,
            audit_user=audit_user,
        )
    except ValidationError as exc:
        if exc.code == "category_not_found" and args.category:
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            print("Verfügbare Kategorien:", file=sys.stderr)
            for category in get_category_list(conn, "expense"):
                print(f"  - {category.name}", file=sys.stderr)
            conn.close()
            sys.exit(1)
        if exc.code == "duplicate":
            existing_id = exc.details.get("existing_id")
            print(
                f"Warnung: Duplikat erkannt (ID {existing_id}), überspringe.",
                file=sys.stderr,
            )
            conn.close()
            return
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    warn_unusual_date_order(expense.payment_date, expense.invoice_date)

    vat_info = ""
    vat_output_val = expense.vat_output or 0.0
    vat_input_val = expense.vat_input or 0.0
    if vat_output_val > 0 or vat_input_val > 0:
        if tax_mode == "small_business":
            vat_info = f" (USt-VA: {vat_output_val:.2f})"
        else:
            diff = vat_output_val - vat_input_val
            vat_info = (
                f" (Vorst: {vat_input_val:.2f}, USt: {vat_output_val:.2f}, Saldo: {diff:.2f})"
            )

    print(
        f"Ausgabe #{expense.id} hinzugefügt: {expense.vendor} {format_amount(expense.amount_eur)} EUR{vat_info}"
    )

    warn_missing_receipt(
        expense.receipt_name,
        expense.invoice_date or expense.payment_date,
        "expenses",
        config,
    )


def cmd_add_income(args):
    """Fügt eine Einnahme hinzu."""
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

    if not args.category and not args.ledger_account and ledger_accounts:
        _print_category_error_with_ledger_hint(conn, "income", ledger_accounts)
        conn.close()
        sys.exit(1)

    try:
        income = create_income(
            conn,
            payment_date=args.payment_date,
            invoice_date=args.invoice_date,
            source=args.source,
            amount_eur=args.amount,
            category_name=args.category,
            ledger_account_key=args.ledger_account,
            ledger_accounts=ledger_accounts,
            foreign_amount=args.foreign,
            receipt_name=args.receipt,
            notes=args.notes,
            vat=args.vat,
            tax_mode=tax_mode,
            audit_user=audit_user,
        )
    except ValidationError as exc:
        if exc.code == "category_not_found" and args.category:
            print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
            print("Verfügbare Kategorien:", file=sys.stderr)
            for category in get_category_list(conn, "income"):
                print(f"  - {category.name}", file=sys.stderr)
            conn.close()
            sys.exit(1)
        if exc.code == "duplicate":
            existing_id = exc.details.get("existing_id")
            print(
                f"Warnung: Duplikat erkannt (ID {existing_id}), überspringe.",
                file=sys.stderr,
            )
            conn.close()
            return
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    warn_unusual_date_order(income.payment_date, income.invoice_date)

    vat_info = f" (USt: {income.vat_output:.2f})" if income.vat_output else ""

    print(
        f"Einnahme #{income.id} hinzugefügt: {income.source} {format_amount(income.amount_eur)} EUR{vat_info}"
    )

    warn_missing_receipt(
        income.receipt_name,
        income.invoice_date or income.payment_date,
        "income",
        config,
    )


def _cmd_add_private_transfer(args, *, transfer_type: str) -> None:
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)

    try:
        transfer = create_private_transfer(
            conn,
            date=args.date,
            transfer_type=transfer_type,
            amount_eur=args.amount,
            description=args.description,
            notes=args.notes,
            related_expense_id=args.related_expense_id,
            audit_user=audit_user,
        )
    except ValidationError as exc:
        if exc.code == "duplicate":
            existing_id = exc.details.get("existing_id")
            print(
                f"Warnung: Duplikat erkannt (ID {existing_id}), überspringe.",
                file=sys.stderr,
            )
            conn.close()
            return
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    label = "Privateinlage" if transfer_type == "deposit" else "Privatentnahme"
    print(
        f"{label} #{transfer.id} hinzugefügt: {transfer.description} "
        f"{format_amount(transfer.amount_eur)} EUR"
    )


def cmd_add_private_deposit(args):
    """Fügt eine direkte Privateinlage hinzu."""
    _cmd_add_private_transfer(args, transfer_type="deposit")


def cmd_add_private_withdrawal(args):
    """Fügt eine direkte Privatentnahme hinzu."""
    _cmd_add_private_transfer(args, transfer_type="withdrawal")
