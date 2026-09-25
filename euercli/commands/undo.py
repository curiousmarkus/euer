"""CLI-Befehl für euer undo (Spec 016 §1.3)."""

from __future__ import annotations

import sys
from pathlib import Path

from ..config import get_audit_user, load_config
from ..db import get_db_connection
from ..services.errors import RecordNotFoundError, ValidationError
from ..services.undo import (
    get_audit_entry_by_id,
    get_last_undoable_audit_entry,
    undo_mutation,
)


def cmd_undo(args) -> None:
    """Macht eine Mutation aus dem Audit-Log rückgängig."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)

    audit_id = getattr(args, "id", None)
    force = getattr(args, "force", False)

    if audit_id is not None:
        entry = get_audit_entry_by_id(conn, audit_id)
        if not entry:
            conn.close()
            print(f"Fehler: Audit-Log-Eintrag #{audit_id} nicht gefunden.", file=sys.stderr)
            sys.exit(1)
    else:
        entry = get_last_undoable_audit_entry(conn)
        if not entry:
            conn.close()
            print(
                "Fehler: Keine rückgängig zu machenden Aktionen im Audit-Log gefunden.",
                file=sys.stderr,
            )
            sys.exit(1)

    if not force:
        action = entry["action"]
        table = entry["table_name"]
        rec_id = entry["record_id"]
        print("Letzte Mutation rückgängig machen:")
        print(f"  Aktion:     {action}")
        print(f"  Tabelle:    {table}")
        print(f"  Datensatz:  #{rec_id}")
        confirm = input("\nMöchten Sie diese Änderung rückgängig machen? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    try:
        result = undo_mutation(
            conn,
            audit_id=entry["id"],
            audit_user=audit_user,
        )
    except (RecordNotFoundError, ValidationError) as exc:
        conn.close()
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)

    conn.close()
    print(f"Rückgängig gemacht: {result.summary}")
