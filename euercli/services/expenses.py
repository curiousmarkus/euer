from __future__ import annotations

import sqlite3
import uuid

from ..db import log_audit, row_to_dict
from ..utils import compute_hash
from .categories import get_category_by_name
from .errors import RecordNotFoundError, ValidationError
from .models import Expense


def _get_optional(row: sqlite3.Row, key: str):
    return row[key] if key in row.keys() else None


def _row_to_expense(row: sqlite3.Row) -> Expense:
    return Expense(
        id=row["id"],
        uuid=row["uuid"],
        date=row["date"],
        vendor=row["vendor"],
        amount_eur=row["amount_eur"],
        category_id=_get_optional(row, "category_id"),
        category_name=_get_optional(row, "category_name"),
        category_eur_line=_get_optional(row, "category_eur_line"),
        account=_get_optional(row, "account"),
        receipt_name=_get_optional(row, "receipt_name"),
        foreign_amount=_get_optional(row, "foreign_amount"),
        notes=_get_optional(row, "notes"),
        is_rc=bool(_get_optional(row, "is_rc") or 0),
        vat_input=_get_optional(row, "vat_input"),
        vat_output=_get_optional(row, "vat_output"),
        hash=_get_optional(row, "hash"),
    )


def create_expense(
    conn: sqlite3.Connection,
    *,
    date: str,
    vendor: str,
    amount_eur: float,
    category_name: str | None = None,
    account: str | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    notes: str | None = None,
    is_rc: bool = False,
    vat: float | None = None,
    tax_mode: str,
    audit_user: str,
) -> Expense:
    category_id: int | None = None
    if category_name:
        category = get_category_by_name(conn, category_name, "expense")
        if not category:
            raise ValidationError(
                f"Kategorie '{category_name}' nicht gefunden.",
                code="category_not_found",
                details={"category": category_name, "type": "expense"},
            )
        category_id = category.id

    vat_input: float | None = None
    vat_output: float | None = None
    manual_vat = vat

    if tax_mode == "small_business":
        if is_rc:
            if manual_vat is not None:
                vat_output = manual_vat
            else:
                vat_output = round(abs(amount_eur) * 0.19, 2)
            vat_input = 0.0
        else:
            vat_input = 0.0
            vat_output = 0.0
    elif tax_mode == "standard":
        if is_rc:
            vat_val = manual_vat if manual_vat is not None else round(abs(amount_eur) * 0.19, 2)
            vat_input = vat_val
            vat_output = vat_val
        else:
            vat_input = manual_vat if manual_vat is not None else None
            vat_output = 0.0
    else:
        raise ValidationError(
            f"Unbekannter Steuermodus: {tax_mode}",
            code="invalid_tax_mode",
            details={"tax_mode": tax_mode},
        )

    tx_hash = compute_hash(date, vendor, amount_eur, receipt_name or "")
    existing = conn.execute(
        "SELECT id FROM expenses WHERE hash = ?",
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
        """INSERT INTO expenses
           (uuid, receipt_name, date, vendor, category_id, amount_eur, account,
            foreign_amount, notes, is_rc, vat_input, vat_output, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_uuid,
            receipt_name,
            date,
            vendor,
            category_id,
            amount_eur,
            account,
            foreign_amount,
            notes,
            1 if is_rc else 0,
            vat_input,
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
        "vendor": vendor,
        "category_id": category_id,
        "amount_eur": amount_eur,
        "account": account,
        "foreign_amount": foreign_amount,
        "notes": notes,
        "is_rc": 1 if is_rc else 0,
        "vat_input": vat_input,
        "vat_output": vat_output,
    }
    log_audit(
        conn,
        "expenses",
        record_id,
        "INSERT",
        record_uuid=record_uuid,
        new_data=new_data,
        user=audit_user,
    )

    conn.commit()

    return Expense(
        id=record_id,
        uuid=record_uuid,
        date=date,
        vendor=vendor,
        amount_eur=amount_eur,
        category_id=category_id,
        account=account,
        receipt_name=receipt_name,
        foreign_amount=foreign_amount,
        notes=notes,
        is_rc=is_rc,
        vat_input=vat_input,
        vat_output=vat_output,
        hash=tx_hash,
    )


def list_expenses(
    conn: sqlite3.Connection,
    *,
    year: int | None = None,
    month: int | None = None,
    category_name: str | None = None,
) -> list[Expense]:
    query = """
        SELECT e.id, e.uuid, e.date, e.vendor, e.category_id, c.name as category_name,
               c.eur_line as category_eur_line, e.amount_eur, e.account, e.receipt_name,
               e.foreign_amount, e.notes, e.is_rc, e.vat_input, e.vat_output, e.hash
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE 1=1
    """
    params: list[object] = []

    if year:
        query += " AND strftime('%Y', e.date) = ?"
        params.append(str(year))
    if month:
        query += " AND strftime('%m', e.date) = ?"
        params.append(f"{month:02d}")
    if category_name:
        query += " AND LOWER(c.name) = LOWER(?)"
        params.append(category_name)

    query += " ORDER BY e.date DESC, e.id DESC"

    rows = conn.execute(query, params).fetchall()
    return [_row_to_expense(row) for row in rows]


def get_expense_detail(conn: sqlite3.Connection, record_id: int) -> Expense:
    row = conn.execute(
        """SELECT e.id, e.uuid, e.date, e.vendor, e.category_id, c.name as category_name,
                  c.eur_line as category_eur_line, e.amount_eur, e.account, e.receipt_name,
                  e.foreign_amount, e.notes, e.is_rc, e.vat_input, e.vat_output, e.hash
           FROM expenses e
           LEFT JOIN categories c ON e.category_id = c.id
           WHERE e.id = ?""",
        (record_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Ausgabe #{record_id} nicht gefunden.",
            code="expense_not_found",
            details={"id": record_id},
        )
    return _row_to_expense(row)


def update_expense(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    date: str | None = None,
    vendor: str | None = None,
    category_name: str | None = None,
    amount_eur: float | None = None,
    account: str | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    notes: str | None = None,
    vat: float | None = None,
    is_rc: bool = False,
    tax_mode: str,
    audit_user: str,
) -> Expense:
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (record_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Ausgabe #{record_id} nicht gefunden.",
            code="expense_not_found",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)

    new_receipt = receipt_name if receipt_name is not None else row["receipt_name"]
    new_date = date if date else row["date"]
    new_vendor = vendor if vendor else row["vendor"]
    new_amount = amount_eur if amount_eur is not None else row["amount_eur"]
    new_account = account if account is not None else row["account"]
    new_foreign = foreign_amount if foreign_amount is not None else row["foreign_amount"]
    new_notes = notes if notes is not None else row["notes"]

    new_vat_input = row["vat_input"]
    new_vat_output = row["vat_output"]

    manual_vat = vat
    current_rc = row["is_rc"] == 1
    new_rc = True if is_rc else current_rc

    recalc_tax = (vat is not None) or is_rc or (amount_eur is not None)

    if recalc_tax:
        calc_amount = new_amount

        if tax_mode == "small_business":
            if new_rc:
                if manual_vat is not None:
                    new_vat_output = manual_vat
                else:
                    new_vat_output = round(abs(calc_amount) * 0.19, 2)
                new_vat_input = 0.0
            else:
                new_vat_input = 0.0
                new_vat_output = 0.0

        elif tax_mode == "standard":
            if new_rc:
                val = manual_vat if manual_vat is not None else round(abs(calc_amount) * 0.19, 2)
                new_vat_input = val
                new_vat_output = val
            else:
                if manual_vat is not None:
                    new_vat_input = manual_vat
                new_vat_output = 0.0
        else:
            raise ValidationError(
                f"Unbekannter Steuermodus: {tax_mode}",
                code="invalid_tax_mode",
                details={"tax_mode": tax_mode},
            )

    if category_name:
        category = get_category_by_name(conn, category_name, "expense")
        if not category:
            raise ValidationError(
                f"Kategorie '{category_name}' nicht gefunden.",
                code="category_not_found",
                details={"category": category_name, "type": "expense"},
            )
        category_id = category.id
    else:
        category_id = row["category_id"]

    new_hash = compute_hash(new_date, new_vendor, new_amount, new_receipt or "")

    conn.execute(
        """UPDATE expenses SET
           receipt_name = ?, date = ?, vendor = ?, category_id = ?, amount_eur = ?,
           account = ?, foreign_amount = ?, notes = ?, is_rc = ?, vat_input = ?, vat_output = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_date,
            new_vendor,
            category_id,
            new_amount,
            new_account,
            new_foreign,
            new_notes,
            1 if new_rc else 0,
            new_vat_input,
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
        "vendor": new_vendor,
        "category_id": category_id,
        "amount_eur": new_amount,
        "account": new_account,
        "foreign_amount": new_foreign,
        "notes": new_notes,
        "is_rc": 1 if new_rc else 0,
        "vat_input": new_vat_input,
        "vat_output": new_vat_output,
    }
    log_audit(
        conn,
        "expenses",
        record_id,
        "UPDATE",
        record_uuid=record_uuid,
        old_data=old_data,
        new_data=new_data,
        user=audit_user,
    )

    conn.commit()

    return Expense(
        id=record_id,
        uuid=record_uuid,
        date=new_date,
        vendor=new_vendor,
        amount_eur=new_amount,
        category_id=category_id,
        account=new_account,
        receipt_name=new_receipt,
        foreign_amount=new_foreign,
        notes=new_notes,
        is_rc=new_rc,
        vat_input=new_vat_input,
        vat_output=new_vat_output,
        hash=new_hash,
    )


def delete_expense(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    audit_user: str,
) -> None:
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (record_id,),
    ).fetchone()
    if not row:
        raise RecordNotFoundError(
            f"Ausgabe #{record_id} nicht gefunden.",
            code="expense_not_found",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)
    record_uuid = row["uuid"]

    conn.execute("DELETE FROM expenses WHERE id = ?", (record_id,))
    log_audit(
        conn,
        "expenses",
        record_id,
        "DELETE",
        record_uuid=record_uuid,
        old_data=old_data,
        user=audit_user,
    )

    conn.commit()
