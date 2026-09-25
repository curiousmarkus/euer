"""Wiederherstellungs-Service für Soft-Delete (Spec 016 §1.2)."""

from __future__ import annotations

import sqlite3

from ..constants import DEFAULT_USER
from .errors import RecordNotFoundError, ValidationError
from .expenses import restore_expense
from .income import restore_income
from .private_transfers import restore_private_transfer


def restore_entry(
    conn: sqlite3.Connection,
    record_id: int,
    table_name: str | None = None,
    *,
    audit_user: str = DEFAULT_USER,
    auto_commit: bool = True,
) -> tuple[str, int]:
    """Stellt einen gelöschten Datensatz wieder her.

    Returns:
        (resolved_table_name, record_id)
    """
    valid_tables = ("expenses", "income", "private_transfers")

    if table_name:
        table = table_name.lower().strip()
        if table in ("expense", "ausgabe", "ausgaben"):
            table = "expenses"
        elif table in ("income", "einnahme", "einnahmen"):
            table = "income"
        elif table in ("private_transfer", "private_transfers", "privat", "privatvorgang"):
            table = "private_transfers"

        if table not in valid_tables:
            raise ValidationError(
                f"Ungültige Tabelle '{table_name}'. Erlaubt: {', '.join(valid_tables)}",
                code="invalid_table",
            )
        resolved_table = table
    else:
        # Automatisch ermitteln
        deleted_matches: list[str] = []
        active_matches: list[str] = []

        for tbl in valid_tables:
            row = conn.execute(
                f"SELECT deleted_at FROM {tbl} WHERE id = ?",
                (record_id,),
            ).fetchone()
            if row:
                if row["deleted_at"] is not None:
                    deleted_matches.append(tbl)
                else:
                    active_matches.append(tbl)

        if len(deleted_matches) == 1:
            resolved_table = deleted_matches[0]
        elif len(deleted_matches) > 1:
            raise ValidationError(
                f"Mehrere gelöschte Einträge mit ID #{record_id} gefunden in: "
                f"{', '.join(deleted_matches)}. Bitte --table angeben.",
                code="ambiguous_restore_target",
                details={"matches": deleted_matches},
            )
        else:
            if active_matches:
                raise ValidationError(
                    f"Eintrag #{record_id} in '{active_matches[0]}' ist nicht gelöscht.",
                    code="record_not_deleted",
                    details={"table": active_matches[0], "id": record_id},
                )
            raise RecordNotFoundError(
                f"Kein gelöschter Eintrag mit ID #{record_id} gefunden.",
                code="record_not_found",
                details={"id": record_id},
            )

    if resolved_table == "expenses":
        restore_expense(conn, record_id=record_id, audit_user=audit_user, auto_commit=auto_commit)
    elif resolved_table == "income":
        restore_income(conn, record_id=record_id, audit_user=audit_user, auto_commit=auto_commit)
    elif resolved_table == "private_transfers":
        restore_private_transfer(
            conn, transfer_id=record_id, audit_user=audit_user, auto_commit=auto_commit
        )

    return resolved_table, record_id
