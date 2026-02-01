from pathlib import Path

from ..db import get_db_connection


def cmd_audit(args):
    """Zeigt Audit-Log für einen Datensatz."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    table = args.table

    rows = conn.execute(
        """SELECT timestamp, action, old_data, new_data, user
           FROM audit_log
           WHERE table_name = ? AND record_id = ?
           ORDER BY timestamp""",
        (table, args.id),
    ).fetchall()

    conn.close()

    if not rows:
        print(f"Keine Audit-Einträge für {table} #{args.id} gefunden.")
        return

    print(f"Audit-Log für {table} #{args.id}")
    print("=" * 60)
    print()

    for r in rows:
        print(f"{r['timestamp']}  {r['action']} by {r['user']}")
        if r["old_data"]:
            print(f"  <- {r['old_data']}")
        if r["new_data"]:
            print(f"  -> {r['new_data']}")
        print()
