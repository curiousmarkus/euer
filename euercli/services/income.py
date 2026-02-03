from __future__ import annotations

import sqlite3
import uuid

from ..db import log_audit, row_to_dict
from ..utils import compute_hash
from .categories import get_category_by_name
from .errors import RecordNotFoundError, ValidationError
from .models import Income


def _get_optional(row: sqlite3.Row, key: str):
    return row[key] if key in row.keys() else None


def _row_to_income(row: sqlite3.Row) -> Income:
    return Income(
        id=row["id"],
        uuid=row["uuid"],
        date=row["date"],
        source=row["source"],
        amount_eur=row["amount_eur"],
        category_id=_get_optional(row, "category_id"),
        category_name=_get_optional(row, "category_name"),
        category_eur_line=_get_optional(row, "category_eur_line"),
        receipt_name=_get_optional(row, "receipt_name"),
        foreign_amount=_get_optional(row, "foreign_amount"),
        notes=_get_optional(row, "notes"),
        vat_output=_get_optional(row, "vat_output"),
        hash=_get_optional(row, "hash"),
    )


def create_income(
    conn: sqlite3.Connection,
    *,
    date: str,
    source: str,
    amount_eur: float,
    category_name: str | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    notes: str | None = None,
    vat: float | None = None,
    tax_mode: str,
    audit_user: str,
) -> Income:
    category_id: int | None = None
    if category_name:
        category = get_category_by_name(conn, category_name, "income")
        if not category:
            raise ValidationError(
                f"Kategorie '{category_name}' nicht gefunden.",
                code="category_not_found",
                details={"category": category_name, "type": "income"},
            )
        category_id = category.id

    vat_output: float | None = 0.0
    if tax_mode == "standard":
        if vat is not None:
            vat_output = vat
        else:
            vat_output = None
    elif tax_mode == "small_business":
        vat_output = 0.0
    else:
        raise ValidationError(
            f"Unbekannter Steuermodus: {tax_mode}",
            code="invalid_tax_mode",
            details={"tax_mode": tax_mode},
        )

    tx_hash = compute_hash(date, source, amount_eur, receipt_name or "")
    existing = conn.execute(
        "SELECT id FROM income WHERE hash = ?",
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
        """INSERT INTO income
           (uuid, receipt_name, date, source, category_id, amount_eur,
            foreign_amount, notes, vat_output, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_uuid,
            receipt_name,
            date,
            source,
            category_id,
            amount_eur,
            foreign_amount,
            notes,
            vat_output,
            tx_hash,
        ),
    )
    record_id = cursor.lastrowid
    assert record_id is not None

    new_data = {
        "uuid": record_uuid,
        "receipt_name": receipt_name,
        "date": date,
        "source": source,
        "category_id": category_id,
        "amount_eur": amount_eur,
        "foreign_amount": foreign_amount,
        "notes": notes,
        "vat_output": vat_output,
    }
    log_audit(
        conn,
        "income",
        record_id,
        "INSERT",
        record_uuid=record_uuid,
        new_data=new_data,
        user=audit_user,
    )

    conn.commit()

    return Income(
        id=record_id,
        uuid=record_uuid,
        date=date,
        source=source,
        amount_eur=amount_eur,
        category_id=category_id,
        receipt_name=receipt_name,
        foreign_amount=foreign_amount,
        notes=notes,
        vat_output=vat_output,
        hash=tx_hash,
    )


def list_income(
    conn: sqlite3.Connection,
    *,
    year: int | None = None,
    month: int | None = None,
    category_name: str | None = None,
) -> list[Income]:
    query = """
        SELECT i.id, i.uuid, i.date, i.source, i.category_id, c.name as category_name,
               c.eur_line as category_eur_line, i.amount_eur, i.receipt_name,
               i.foreign_amount, i.notes, i.vat_output, i.hash
        FROM income i
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE 1=1
    """
    params: list[object] = []

    if year:
        query += " AND strftime('%Y', i.date) = ?"
        params.append(str(year))
    if month:
        query += " AND strftime('%m', i.date) = ?"
        params.append(f"{month:02d}")
    if category_name:
        query += " AND LOWER(c.name) = LOWER(?)"
        params.append(category_name)

    query += " ORDER BY i.date DESC, i.id DESC"

    rows = conn.execute(query, params).fetchall()
    return [_row_to_income(row) for row in rows]


def get_income_detail(conn: sqlite3.Connection, record_id: int) -> Income:
    row = conn.execute(
        """SELECT i.id, i.uuid, i.date, i.source, i.category_id, c.name as category_name,
                  c.eur_line as category_eur_line, i.amount_eur, i.receipt_name,
                  i.foreign_amount, i.notes, i.vat_output, i.hash
           FROM income i
           LEFT JOIN categories c ON i.category_id = c.id
           WHERE i.id = ?""",
        (record_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Einnahme #{record_id} nicht gefunden.",
            code="income_not_found",
            details={"id": record_id},
        )
    return _row_to_income(row)


def update_income(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    date: str | None = None,
    source: str | None = None,
    category_name: str | None = None,
    amount_eur: float | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    notes: str | None = None,
    vat: float | None = None,
    tax_mode: str,
    audit_user: str,
) -> Income:
    row = conn.execute(
        "SELECT * FROM income WHERE id = ?",
        (record_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Einnahme #{record_id} nicht gefunden.",
            code="income_not_found",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)

    new_receipt = receipt_name if receipt_name is not None else row["receipt_name"]
    new_date = date if date else row["date"]
    new_source = source if source else row["source"]
    new_amount = amount_eur if amount_eur is not None else row["amount_eur"]
    new_foreign = foreign_amount if foreign_amount is not None else row["foreign_amount"]
    new_notes = notes if notes is not None else row["notes"]
    new_vat_output = row["vat_output"]
    if vat is not None:
        new_vat_output = vat
    elif tax_mode == "standard" and row["vat_output"] is None:
        new_vat_output = None

    if category_name:
        category = get_category_by_name(conn, category_name, "income")
        if not category:
            raise ValidationError(
                f"Kategorie '{category_name}' nicht gefunden.",
                code="category_not_found",
                details={"category": category_name, "type": "income"},
            )
        category_id = category.id
    else:
        category_id = row["category_id"]

    new_hash = compute_hash(new_date, new_source, new_amount, new_receipt or "")

    conn.execute(
        """UPDATE income SET
           receipt_name = ?, date = ?, source = ?, category_id = ?, amount_eur = ?,
           foreign_amount = ?, notes = ?, vat_output = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_date,
            new_source,
            category_id,
            new_amount,
            new_foreign,
            new_notes,
            new_vat_output,
            new_hash,
            record_id,
        ),
    )

    record_uuid = row["uuid"]

    new_data = {
        "uuid": record_uuid,
        "receipt_name": new_receipt,
        "date": new_date,
        "source": new_source,
        "category_id": category_id,
        "amount_eur": new_amount,
        "foreign_amount": new_foreign,
        "notes": new_notes,
        "vat_output": new_vat_output,
    }
    log_audit(
        conn,
        "income",
        record_id,
        "UPDATE",
        record_uuid=record_uuid,
        old_data=old_data,
        new_data=new_data,
        user=audit_user,
    )

    conn.commit()

    return Income(
        id=record_id,
        uuid=record_uuid,
        date=new_date,
        source=new_source,
        amount_eur=new_amount,
        category_id=category_id,
        receipt_name=new_receipt,
        foreign_amount=new_foreign,
        notes=new_notes,
        vat_output=new_vat_output,
        hash=new_hash,
    )


def delete_income(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    audit_user: str,
) -> None:
    row = conn.execute(
        "SELECT * FROM income WHERE id = ?",
        (record_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Einnahme #{record_id} nicht gefunden.",
            code="income_not_found",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)
    record_uuid = row["uuid"]

    conn.execute("DELETE FROM income WHERE id = ?", (record_id,))
    log_audit(
        conn,
        "income",
        record_id,
        "DELETE",
        record_uuid=record_uuid,
        old_data=old_data,
        user=audit_user,
    )

    conn.commit()
