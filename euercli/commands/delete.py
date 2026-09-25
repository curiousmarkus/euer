"""Löscht Transaktionen (Soft-Delete standardmäßig, Purge mit --purge)."""

from __future__ import annotations

import sys
from pathlib import Path

from ..config import get_audit_user, load_config
from ..db import get_db_connection
from ..services.errors import RecordNotFoundError
from ..services.expenses import delete_expense, get_expense_detail
from ..services.income import delete_income, get_income_detail
from ..services.private_transfers import (
    delete_private_transfer,
    get_private_transfer_by_id,
)


def cmd_delete_expense(args) -> None:
    """Löscht eine Ausgabe."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    purge = getattr(args, "purge", False)

    try:
        expense = get_expense_detail(conn, args.id, include_deleted=purge)
    except RecordNotFoundError:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        action_desc = "endgültig löschen (Purge)" if purge else "löschen (in Papierkorb)"
        print(f"Ausgabe #{args.id}:")
        print(f"  Wertstellung: {expense.payment_date or '-'}")
        print(f"  Rechnung:     {expense.invoice_date or '-'}")
        print(f"  Lieferant:    {expense.vendor}")
        print(f"  Kategorie:    {expense.category_name or '-'}")
        print(f"  Betrag:       {expense.amount_eur:.2f} EUR")

        confirm = input(f"\nWirklich {action_desc}? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    try:
        delete_expense(conn, record_id=args.id, audit_user=audit_user, purge=purge)
    except RecordNotFoundError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    if purge:
        print(f"Ausgabe #{args.id} endgültig gelöscht (gepurgt).")
    else:
        print(f"Ausgabe #{args.id} gelöscht (in den Papierkorb verschoben).")


def cmd_delete_income(args) -> None:
    """Löscht eine Einnahme."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    purge = getattr(args, "purge", False)

    try:
        income = get_income_detail(conn, args.id, include_deleted=purge)
    except RecordNotFoundError:
        print(f"Fehler: Einnahme #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        action_desc = "endgültig löschen (Purge)" if purge else "löschen (in Papierkorb)"
        print(f"Einnahme #{args.id}:")
        print(f"  Wertstellung: {income.payment_date or '-'}")
        print(f"  Rechnung:     {income.invoice_date or '-'}")
        print(f"  Quelle:       {income.source}")
        print(f"  Kategorie:    {income.category_name or '-'}")
        print(f"  Betrag:       {income.amount_eur:.2f} EUR")

        confirm = input(f"\nWirklich {action_desc}? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    try:
        delete_income(conn, record_id=args.id, audit_user=audit_user, purge=purge)
    except RecordNotFoundError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    if purge:
        print(f"Einnahme #{args.id} endgültig gelöscht (gepurgt).")
    else:
        print(f"Einnahme #{args.id} gelöscht (in den Papierkorb verschoben).")


def cmd_delete_private_transfer(args) -> None:
    """Löscht einen Privatvorgang."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    purge = getattr(args, "purge", False)

    try:
        transfer = get_private_transfer_by_id(conn, args.id, include_deleted=purge)
    except RecordNotFoundError:
        print(f"Fehler: Privatvorgang #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        typ = "Privateinlage" if transfer.type == "deposit" else "Privatentnahme"
        action_desc = "endgültig löschen (Purge)" if purge else "löschen (in Papierkorb)"
        print(f"{typ} #{args.id}:")
        print(f"  Datum:        {transfer.date}")
        print(f"  Beschreibung: {transfer.description}")
        print(f"  Betrag:       {transfer.amount_eur:.2f} EUR")

        confirm = input(f"\nWirklich {action_desc}? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    try:
        delete_private_transfer(conn, args.id, audit_user=audit_user, purge=purge)
    except RecordNotFoundError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    if purge:
        print(f"Privatvorgang #{args.id} endgültig gelöscht (gepurgt).")
    else:
        print(f"Privatvorgang #{args.id} gelöscht (in den Papierkorb verschoben).")
