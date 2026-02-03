import sys
from pathlib import Path

from ..config import get_audit_user, load_config
from ..db import get_db_connection
from ..services.errors import RecordNotFoundError
from ..services.expenses import delete_expense, get_expense_detail
from ..services.income import delete_income, get_income_detail


def cmd_delete_expense(args):
    """Löscht eine Ausgabe."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)

    try:
        expense = get_expense_detail(conn, args.id)
    except RecordNotFoundError:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        print(f"Ausgabe #{args.id}:")
        print(f"  Datum:     {expense.date}")
        print(f"  Lieferant: {expense.vendor}")
        print(f"  Kategorie: {expense.category_name or '-'}")
        print(f"  Betrag:    {expense.amount_eur:.2f} EUR")

        confirm = input("\nWirklich löschen? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    try:
        delete_expense(conn, record_id=args.id, audit_user=audit_user)
    except RecordNotFoundError:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    print(f"Ausgabe #{args.id} gelöscht.")


def cmd_delete_income(args):
    """Löscht eine Einnahme."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)

    try:
        income = get_income_detail(conn, args.id)
    except RecordNotFoundError:
        print(f"Fehler: Einnahme #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        print(f"Einnahme #{args.id}:")
        print(f"  Datum:    {income.date}")
        print(f"  Quelle:   {income.source}")
        print(f"  Kategorie: {income.category_name or '-'}")
        print(f"  Betrag:   {income.amount_eur:.2f} EUR")

        confirm = input("\nWirklich löschen? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    try:
        delete_income(conn, record_id=args.id, audit_user=audit_user)
    except RecordNotFoundError:
        print(f"Fehler: Einnahme #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    print(f"Einnahme #{args.id} gelöscht.")
