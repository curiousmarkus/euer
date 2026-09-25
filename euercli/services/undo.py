"""Undo-Service basierend auf audit_log (Spec 016 §1.3)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from ..constants import DEFAULT_USER
from ..db import log_audit, row_to_dict
from .errors import RecordNotFoundError, ValidationError


@dataclass
class UndoResult:
    audit_id: int
    table_name: str
    record_id: int
    action_undone: str
    summary: str


def get_last_undoable_audit_entry(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT * FROM audit_log
           WHERE action IN ('INSERT', 'UPDATE', 'DELETE')
             AND table_name IN ('expenses', 'income', 'private_transfers')
           ORDER BY id DESC LIMIT 1"""
    ).fetchone()


def get_audit_entry_by_id(conn: sqlite3.Connection, audit_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM audit_log WHERE id = ?",
        (audit_id,),
    ).fetchone()


def undo_mutation(
    conn: sqlite3.Connection,
    *,
    audit_id: int | None = None,
    audit_user: str = DEFAULT_USER,
    auto_commit: bool = True,
) -> UndoResult:
    """Macht eine Mutation anhand des Audit-Logs rückgängig."""
    if audit_id is not None:
        row = get_audit_entry_by_id(conn, audit_id)
        if not row:
            raise RecordNotFoundError(
                f"Audit-Log-Eintrag #{audit_id} nicht gefunden.",
                code="audit_entry_not_found",
                details={"audit_id": audit_id},
            )
    else:
        row = get_last_undoable_audit_entry(conn)
        if not row:
            raise ValidationError(
                "Keine rückgängig zu machenden Aktionen im Audit-Log gefunden.",
                code="no_undoable_mutations",
            )

    audit_entry_id = int(row["id"])
    table_name = str(row["table_name"])
    record_id = int(row["record_id"])
    record_uuid = row["record_uuid"]
    action = str(row["action"])
    old_data = json.loads(row["old_data"]) if row["old_data"] else None

    if table_name not in ("expenses", "income", "private_transfers"):
        raise ValidationError(
            f"Tabelle '{table_name}' unterstützt kein Undo.",
            code="table_not_undoable",
            details={"table_name": table_name},
        )

    # An older audit entry must not overwrite changes made to the same record later.
    later_entry = conn.execute(
        """SELECT id FROM audit_log
           WHERE id > ? AND table_name = ? AND record_id = ?
             AND action IN ('INSERT', 'UPDATE', 'DELETE', 'MIGRATE')
           ORDER BY id LIMIT 1""",
        (audit_entry_id, table_name, record_id),
    ).fetchone()
    if later_entry:
        raise ValidationError(
            f"Audit-Eintrag #{audit_entry_id} ist nicht mehr der letzte Stand von "
            f"{table_name} #{record_id} (späterer Eintrag #{later_entry['id']}).",
            code="stale_undo",
            details={"audit_id": audit_entry_id, "later_audit_id": later_entry["id"]},
        )

    current_row = conn.execute(
        f"SELECT * FROM {table_name} WHERE id = ?",
        (record_id,),
    ).fetchone()
    if current_row and record_uuid and current_row["uuid"] != record_uuid:
        raise ValidationError(
            f"Datensatz #{record_id} in {table_name} hat eine andere UUID als der Audit-Eintrag.",
            code="stale_undo",
            details={"audit_id": audit_entry_id, "record_id": record_id},
        )

    summary = ""

    if action == "INSERT":
        # INSERT rückgängig machen -> Soft-Delete
        if not current_row:
            raise RecordNotFoundError(
                f"Datensatz #{record_id} in {table_name} existiert nicht mehr.",
                code="record_not_found",
                details={"table": table_name, "id": record_id},
            )
        if current_row["deleted_at"] is not None:
            raise ValidationError(
                f"Datensatz #{record_id} in {table_name} ist bereits im Papierkorb.",
                code="already_deleted",
                details={"table": table_name, "id": record_id},
            )

        current_data = row_to_dict(current_row)
        conn.execute(
            f"UPDATE {table_name} SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (record_id,),
        )
        log_audit(
            conn,
            table_name,
            record_id,
            "DELETE",
            record_uuid=record_uuid,
            old_data=current_data,
            new_data={"undo_of_audit_id": audit_entry_id, "deleted_at": "CURRENT_TIMESTAMP"},
            user=audit_user,
        )
        summary = f"{table_name} #{record_id} (erstellt bei #{audit_entry_id}) in den Papierkorb verschoben."

    elif action == "DELETE":
        # DELETE rückgängig machen -> Soft-Delete aufheben oder Datensatz re-inserten
        if current_row:
            if current_row["deleted_at"] is None:
                raise ValidationError(
                    f"Datensatz #{record_id} in {table_name} ist nicht gelöscht.",
                    code="record_not_deleted",
                    details={"table": table_name, "id": record_id},
                )
            current_data = row_to_dict(current_row)
            conn.execute(
                f"UPDATE {table_name} SET deleted_at = NULL WHERE id = ?",
                (record_id,),
            )
            log_audit(
                conn,
                table_name,
                record_id,
                "UPDATE",
                record_uuid=record_uuid,
                old_data=current_data,
                new_data={"undo_of_audit_id": audit_entry_id, "deleted_at": None},
                user=audit_user,
            )
            summary = f"{table_name} #{record_id} aus dem Papierkorb wiederhergestellt."
        else:
            # Datensatz war physisch gelöscht (Purge / Altbestand): aus old_data wiederherstellen
            if not old_data:
                raise ValidationError(
                    f"Audit-Eintrag #{audit_entry_id} enthält keine Daten zur Wiederherstellung (old_data fehlt).",
                    code="missing_old_data",
                )
            cols_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            valid_cols = {r["name"] for r in cols_info}
            insert_keys = [k for k in old_data.keys() if k in valid_cols and k != "deleted_at"]
            insert_keys.append("deleted_at")
            insert_vals = [old_data[k] for k in insert_keys if k != "deleted_at"]
            insert_vals.append(None)

            placeholders = ", ".join(["?"] * len(insert_keys))
            col_names = ", ".join(insert_keys)
            conn.execute(
                f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                insert_vals,
            )
            log_audit(
                conn,
                table_name,
                record_id,
                "INSERT",
                record_uuid=record_uuid,
                new_data={"undo_of_audit_id": audit_entry_id, **old_data},
                user=audit_user,
            )
            summary = (
                f"{table_name} #{record_id} aus Audit-Historie neu angelegt (wiederhergestellt)."
            )

    elif action == "UPDATE":
        # UPDATE rückgängig machen -> old_data wieder einspielen
        if not current_row:
            raise RecordNotFoundError(
                f"Datensatz #{record_id} in {table_name} existiert nicht mehr.",
                code="record_not_found",
                details={"table": table_name, "id": record_id},
            )
        if not old_data:
            raise ValidationError(
                f"Audit-Eintrag #{audit_entry_id} enthält keine Vorher-Daten (old_data fehlt).",
                code="missing_old_data",
            )
        current_data = row_to_dict(current_row)
        cols_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        valid_cols = {r["name"] for r in cols_info} - {"id", "created_at"}

        update_keys = [k for k in old_data.keys() if k in valid_cols]
        update_vals = [old_data[k] for k in update_keys]
        update_vals.append(record_id)

        set_clause = ", ".join([f"{k} = ?" for k in update_keys])
        conn.execute(
            f"UPDATE {table_name} SET {set_clause} WHERE id = ?",
            update_vals,
        )
        log_audit(
            conn,
            table_name,
            record_id,
            "UPDATE",
            record_uuid=record_uuid,
            old_data=current_data,
            new_data={"undo_of_audit_id": audit_entry_id, **old_data},
            user=audit_user,
        )
        summary = (
            f"{table_name} #{record_id} auf den Stand vor Audit #{audit_entry_id} zurückgesetzt."
        )

    else:
        raise ValidationError(
            f"Aktion '{action}' kann nicht rückgängig gemacht werden.",
            code="action_not_undoable",
        )

    if auto_commit:
        conn.commit()

    return UndoResult(
        audit_id=audit_entry_id,
        table_name=table_name,
        record_id=record_id,
        action_undone=action,
        summary=summary,
    )
