import sys
from pathlib import Path

from ..config import get_audit_user, load_config
from ..db import get_db_connection, log_audit, row_to_dict


def cmd_delete_expense(args):
    """Löscht eine Ausgabe."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)

    row = conn.execute(
        """SELECT e.*, c.name as category_name 
           FROM expenses e JOIN categories c ON e.category_id = c.id 
           WHERE e.id = ?""",
        (args.id,),
    ).fetchone()

    if not row:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        print(f"Ausgabe #{args.id}:")
        print(f"  Datum:     {row['date']}")
        print(f"  Lieferant: {row['vendor']}")
        print(f"  Kategorie: {row['category_name']}")
        print(f"  Betrag:    {row['amount_eur']:.2f} EUR")

        confirm = input("\nWirklich löschen? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    old_data = row_to_dict(row)

    conn.execute("DELETE FROM expenses WHERE id = ?", (args.id,))
    log_audit(
        conn,
        "expenses",
        args.id,
        "DELETE",
        old_data=old_data,
        user=audit_user,
    )

    conn.commit()
    conn.close()

    print(f"Ausgabe #{args.id} gelöscht.")


def cmd_delete_income(args):
    """Löscht eine Einnahme."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)

    row = conn.execute(
        """SELECT i.*, c.name as category_name 
           FROM income i JOIN categories c ON i.category_id = c.id 
           WHERE i.id = ?""",
        (args.id,),
    ).fetchone()

    if not row:
        print(f"Fehler: Einnahme #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        print(f"Einnahme #{args.id}:")
        print(f"  Datum:    {row['date']}")
        print(f"  Quelle:   {row['source']}")
        print(f"  Kategorie: {row['category_name']}")
        print(f"  Betrag:   {row['amount_eur']:.2f} EUR")

        confirm = input("\nWirklich löschen? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    old_data = row_to_dict(row)

    conn.execute("DELETE FROM income WHERE id = ?", (args.id,))
    log_audit(
        conn,
        "income",
        args.id,
        "DELETE",
        old_data=old_data,
        user=audit_user,
    )

    conn.commit()
    conn.close()

    print(f"Einnahme #{args.id} gelöscht.")
