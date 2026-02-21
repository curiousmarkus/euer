from __future__ import annotations

import sqlite3
import uuid

from ..db import log_audit, row_to_dict
from ..utils import compute_hash
from .expenses import row_to_expense
from .errors import RecordNotFoundError, ValidationError
from .models import Expense, PrivateTransfer
from .utils import get_optional

UNSET = object()


def _row_to_private_transfer(row: sqlite3.Row) -> PrivateTransfer:
    return PrivateTransfer(
        id=row["id"],
        uuid=row["uuid"],
        date=row["date"],
        type=row["type"],
        amount_eur=row["amount_eur"],
        description=row["description"],
        notes=get_optional(row, "notes"),
        related_expense_id=get_optional(row, "related_expense_id"),
        hash=get_optional(row, "hash"),
    )


def create_private_transfer(
    conn: sqlite3.Connection,
    *,
    date: str,
    transfer_type: str,
    amount_eur: float,
    description: str,
    notes: str | None = None,
    related_expense_id: int | None = None,
    audit_user: str,
) -> PrivateTransfer:
    if transfer_type not in {"deposit", "withdrawal"}:
        raise ValidationError(
            "Typ muss 'deposit' oder 'withdrawal' sein.",
            code="invalid_type",
            details={"type": transfer_type},
        )
    if amount_eur <= 0:
        raise ValidationError(
            "Betrag muss positiv sein.",
            code="invalid_amount",
            details={"amount_eur": amount_eur},
        )
    if not description.strip():
        raise ValidationError(
            "Beschreibung darf nicht leer sein.",
            code="invalid_description",
        )

    if related_expense_id is not None:
        expense = conn.execute(
            "SELECT id FROM expenses WHERE id = ?",
            (related_expense_id,),
        ).fetchone()
        if not expense:
            raise ValidationError(
                f"Ausgabe #{related_expense_id} nicht gefunden.",
                code="expense_not_found",
                details={"related_expense_id": related_expense_id},
            )

    tx_hash = compute_hash(date, description, amount_eur)
    existing = conn.execute(
        "SELECT id FROM private_transfers WHERE hash = ?",
        (tx_hash,),
    ).fetchone()
    if existing:
        raise ValidationError(
            f"Duplikat erkannt (ID {existing['id']})",
            code="duplicate",
            details={"existing_id": existing["id"]},
        )

    record_uuid = str(uuid.uuid4())
    cursor = conn.execute(
        """INSERT INTO private_transfers
           (uuid, date, type, amount_eur, description, notes, related_expense_id, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_uuid,
            date,
            transfer_type,
            amount_eur,
            description,
            notes,
            related_expense_id,
            tx_hash,
        ),
    )
    record_id = cursor.lastrowid
    assert record_id is not None

    new_data = {
        "uuid": record_uuid,
        "date": date,
        "type": transfer_type,
        "amount_eur": amount_eur,
        "description": description,
        "notes": notes,
        "related_expense_id": related_expense_id,
    }
    log_audit(
        conn,
        "private_transfers",
        record_id,
        "INSERT",
        record_uuid=record_uuid,
        new_data=new_data,
        user=audit_user,
    )

    conn.commit()

    return PrivateTransfer(
        id=record_id,
        uuid=record_uuid,
        date=date,
        type=transfer_type,
        amount_eur=amount_eur,
        description=description,
        notes=notes,
        related_expense_id=related_expense_id,
        hash=tx_hash,
    )


def get_private_transfer_list(
    conn: sqlite3.Connection,
    *,
    transfer_type: str | None = None,
    year: int | None = None,
) -> list[PrivateTransfer]:
    query = """
        SELECT id, uuid, date, type, amount_eur, description, notes, related_expense_id, hash
        FROM private_transfers
        WHERE 1=1
    """
    params: list[object] = []

    if transfer_type:
        query += " AND type = ?"
        params.append(transfer_type)
    if year:
        query += " AND strftime('%Y', date) = ?"
        params.append(str(year))

    query += " ORDER BY date DESC, id DESC"

    rows = conn.execute(query, params).fetchall()
    return [_row_to_private_transfer(row) for row in rows]


def get_private_transfer_by_id(
    conn: sqlite3.Connection,
    transfer_id: int,
) -> PrivateTransfer:
    row = conn.execute(
        """SELECT id, uuid, date, type, amount_eur, description, notes, related_expense_id, hash
           FROM private_transfers WHERE id = ?""",
        (transfer_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Privatvorgang #{transfer_id} nicht gefunden.",
            code="private_transfer_not_found",
            details={"id": transfer_id},
        )
    return _row_to_private_transfer(row)


def update_private_transfer(
    conn: sqlite3.Connection,
    transfer_id: int,
    *,
    date: str | None = None,
    amount_eur: float | None = None,
    description: str | None = None,
    notes: str | None = None,
    related_expense_id: int | None | object = UNSET,
    audit_user: str,
) -> PrivateTransfer:
    row = conn.execute(
        "SELECT * FROM private_transfers WHERE id = ?",
        (transfer_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Privatvorgang #{transfer_id} nicht gefunden.",
            code="private_transfer_not_found",
            details={"id": transfer_id},
        )

    old_data = row_to_dict(row)

    new_date = date if date else row["date"]
    new_amount = amount_eur if amount_eur is not None else row["amount_eur"]
    new_description = description if description is not None else row["description"]
    new_notes = notes if notes is not None else row["notes"]
    if related_expense_id is UNSET:
        new_related_expense_id = row["related_expense_id"]
    else:
        new_related_expense_id = related_expense_id

    if new_amount <= 0:
        raise ValidationError(
            "Betrag muss positiv sein.",
            code="invalid_amount",
            details={"amount_eur": new_amount},
        )
    if not str(new_description).strip():
        raise ValidationError(
            "Beschreibung darf nicht leer sein.",
            code="invalid_description",
        )

    if new_related_expense_id is not None:
        expense = conn.execute(
            "SELECT id FROM expenses WHERE id = ?",
            (new_related_expense_id,),
        ).fetchone()
        if not expense:
            raise ValidationError(
                f"Ausgabe #{new_related_expense_id} nicht gefunden.",
                code="expense_not_found",
                details={"related_expense_id": new_related_expense_id},
            )

    new_hash = compute_hash(new_date, str(new_description), float(new_amount))

    existing = conn.execute(
        "SELECT id FROM private_transfers WHERE hash = ? AND id != ?",
        (new_hash, transfer_id),
    ).fetchone()
    if existing:
        raise ValidationError(
            f"Duplikat erkannt (ID {existing['id']})",
            code="duplicate",
            details={"existing_id": existing["id"]},
        )

    conn.execute(
        """UPDATE private_transfers SET
           date = ?, amount_eur = ?, description = ?, notes = ?, related_expense_id = ?, hash = ?
           WHERE id = ?""",
        (
            new_date,
            new_amount,
            new_description,
            new_notes,
            new_related_expense_id,
            new_hash,
            transfer_id,
        ),
    )

    record_uuid = row["uuid"]
    new_data = {
        "uuid": record_uuid,
        "date": new_date,
        "type": row["type"],
        "amount_eur": new_amount,
        "description": new_description,
        "notes": new_notes,
        "related_expense_id": new_related_expense_id,
    }
    log_audit(
        conn,
        "private_transfers",
        transfer_id,
        "UPDATE",
        record_uuid=record_uuid,
        old_data=old_data,
        new_data=new_data,
        user=audit_user,
    )

    conn.commit()

    return PrivateTransfer(
        id=transfer_id,
        uuid=record_uuid,
        date=new_date,
        type=row["type"],
        amount_eur=new_amount,
        description=str(new_description),
        notes=new_notes,
        related_expense_id=new_related_expense_id,
        hash=new_hash,
    )


def delete_private_transfer(
    conn: sqlite3.Connection,
    transfer_id: int,
    *,
    audit_user: str,
) -> None:
    row = conn.execute(
        "SELECT * FROM private_transfers WHERE id = ?",
        (transfer_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Privatvorgang #{transfer_id} nicht gefunden.",
            code="private_transfer_not_found",
            details={"id": transfer_id},
        )

    old_data = row_to_dict(row)
    record_uuid = row["uuid"]

    conn.execute("DELETE FROM private_transfers WHERE id = ?", (transfer_id,))
    log_audit(
        conn,
        "private_transfers",
        transfer_id,
        "DELETE",
        record_uuid=record_uuid,
        old_data=old_data,
        user=audit_user,
    )

    conn.commit()


def get_sacheinlagen(
    conn: sqlite3.Connection,
    *,
    year: int | None = None,
) -> list[Expense]:
    query = """
        SELECT e.id, e.uuid, e.date, e.vendor, e.category_id, c.name as category_name,
               c.eur_line as category_eur_line, e.amount_eur, e.account, e.receipt_name,
               e.foreign_amount, e.notes, e.is_rc, e.vat_input, e.vat_output,
               e.is_private_paid, e.private_classification, e.hash
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.is_private_paid = 1
    """
    params: list[object] = []

    if year:
        query += " AND strftime('%Y', e.date) = ?"
        params.append(str(year))

    query += " ORDER BY e.date DESC, e.id DESC"

    rows = conn.execute(query, params).fetchall()
    return [row_to_expense(row) for row in rows]


def get_private_summary(
    conn: sqlite3.Connection,
    *,
    year: int,
) -> dict:
    direct = conn.execute(
        """SELECT
               SUM(CASE WHEN type = 'deposit' THEN amount_eur ELSE 0 END) AS deposits_direct,
               SUM(CASE WHEN type = 'withdrawal' THEN amount_eur ELSE 0 END) AS withdrawals_total
           FROM private_transfers
           WHERE strftime('%Y', date) = ?""",
        (str(year),),
    ).fetchone()

    sacheinlagen = conn.execute(
        """SELECT SUM(ABS(amount_eur)) AS deposits_sacheinlagen
           FROM expenses
           WHERE is_private_paid = 1 AND strftime('%Y', date) = ?""",
        (str(year),),
    ).fetchone()

    deposits_direct = (direct["deposits_direct"] if direct else 0.0) or 0.0
    withdrawals_total = (direct["withdrawals_total"] if direct else 0.0) or 0.0
    deposits_sacheinlagen = (
        (sacheinlagen["deposits_sacheinlagen"] if sacheinlagen else 0.0) or 0.0
    )

    return {
        "deposits_direct": deposits_direct,
        "deposits_sacheinlagen": deposits_sacheinlagen,
        "deposits_total": deposits_direct + deposits_sacheinlagen,
        "withdrawals_total": withdrawals_total,
        "balance": (deposits_direct + deposits_sacheinlagen) - withdrawals_total,
    }
