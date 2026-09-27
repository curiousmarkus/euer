"""CLI-Befehl für euer restore (Spec 016 §1.2)."""

from __future__ import annotations

import sys
from pathlib import Path

from ..config import get_audit_user, load_config
from ..db import get_db_connection
from ..services.errors import RecordNotFoundError, ValidationError
from ..services.restore import restore_entry


def cmd_restore(args) -> None:
    """Stellt einen gelöschten Datensatz wieder her."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)

    table_name = getattr(args, "table", None)

    try:
        table, record_id = restore_entry(
            conn,
            record_id=args.id,
            table_name=table_name,
            audit_user=audit_user,
        )
    except (RecordNotFoundError, ValidationError) as exc:
        conn.close()
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)

    conn.close()
    label = (
        "Ausgabe" if table == "expenses" else ("Einnahme" if table == "income" else "Privatvorgang")
    )
    print(f"{label} #{record_id} wiederhergestellt.")
