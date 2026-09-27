"""CLI-Befehle für den Papierkorb (Spec 016 §1.2)."""

from __future__ import annotations

from pathlib import Path

from ..config import get_audit_user, load_config
from ..db import get_db_connection
from ..services.expenses import delete_expense, list_expenses
from ..services.income import delete_income, list_income
from ..services.private_transfers import delete_private_transfer, get_private_transfer_list


def cmd_trash_list(args) -> None:
    """Zeigt gelöschte Einträge im Papierkorb an."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    expenses = list_expenses(conn, trash_only=True)
    income = list_income(conn, trash_only=True)
    transfers = get_private_transfer_list(conn, trash_only=True)

    conn.close()

    total = len(expenses) + len(income) + len(transfers)
    if total == 0:
        print("Papierkorb ist leer.")
        return

    print(f"Papierkorb ({total} gelöschte Einträge)")
    print("=" * 65)

    if expenses:
        print(f"\nAusgaben ({len(expenses)}):")
        for e in expenses:
            del_time = e.deleted_at or "-"
            print(
                f"  #{e.id:<4} {e.date:<10} {e.vendor:<22} {e.amount_eur:>9.2f} EUR (gelöscht: {del_time})"
            )

    if income:
        print(f"\nEinnahmen ({len(income)}):")
        for i in income:
            del_time = i.deleted_at or "-"
            print(
                f"  #{i.id:<4} {i.date:<10} {i.source:<22} {i.amount_eur:>9.2f} EUR (gelöscht: {del_time})"
            )

    if transfers:
        print(f"\nPrivatvorgänge ({len(transfers)}):")
        for t in transfers:
            del_time = t.deleted_at or "-"
            typ = "Einlage" if t.type == "deposit" else "Entnahme"
            print(
                f"  #{t.id:<4} {t.date:<10} {typ:<8} {t.description:<14} {t.amount_eur:>9.2f} EUR (gelöscht: {del_time})"
            )

    print("\nHinweis: Wiederherstellen mit 'euer restore <ID> [--table ...]'")
    print("Hinweis: Endgültig leeren mit 'euer trash empty --force'")


def cmd_trash_empty(args) -> None:
    """Löscht alle Einträge im Papierkorb endgültig (Purge)."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)

    expenses = list_expenses(conn, trash_only=True)
    income = list_income(conn, trash_only=True)
    transfers = get_private_transfer_list(conn, trash_only=True)

    total = len(expenses) + len(income) + len(transfers)
    if total == 0:
        conn.close()
        print("Papierkorb ist bereits leer.")
        return

    force = getattr(args, "force", False)
    if not force:
        confirm = input(
            f"Möchten Sie alle {total} gelöschten Einträge endgültig entfernen? (j/N): "
        )
        if confirm.lower() != "j":
            conn.close()
            print("Abgebrochen.")
            return

    for e in expenses:
        if e.id is not None:
            delete_expense(
                conn, record_id=e.id, audit_user=audit_user, purge=True, auto_commit=False
            )
    for i in income:
        if i.id is not None:
            delete_income(
                conn, record_id=i.id, audit_user=audit_user, purge=True, auto_commit=False
            )
    for t in transfers:
        if t.id is not None:
            delete_private_transfer(
                conn, transfer_id=t.id, audit_user=audit_user, purge=True, auto_commit=False
            )

    conn.commit()
    conn.close()

    print(f"{total} Eintrag/Einträge endgültig aus dem Papierkorb gelöscht (gepurgt).")
