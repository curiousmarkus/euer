from __future__ import annotations

import sqlite3
import uuid

from ..db import log_audit, row_to_dict
from ..utils import compute_hash
from .categories import get_category_by_name, resolve_ledger_account
from .duplicates import DuplicateAction
from .errors import RecordNotFoundError, ValidationError
from .models import Expense, LedgerAccount
from .private_classification import classify_expense_private_paid
from .utils import get_optional, hash_date, resolve_dates


def row_to_expense(row: sqlite3.Row) -> Expense:
    return Expense(
        id=row["id"],
        uuid=row["uuid"],
        payment_date=get_optional(row, "payment_date"),
        invoice_date=get_optional(row, "invoice_date"),
        vendor=row["vendor"],
        amount_eur=row["amount_eur"],
        category_id=get_optional(row, "category_id"),
        category_name=get_optional(row, "category_name"),
        category_eur_line=get_optional(row, "category_eur_line"),
        account=get_optional(row, "account"),
        ledger_account=get_optional(row, "ledger_account"),
        receipt_name=get_optional(row, "receipt_name"),
        foreign_amount=get_optional(row, "foreign_amount"),
        notes=get_optional(row, "notes"),
        is_rc=bool(get_optional(row, "is_rc") or 0),
        vat_input=get_optional(row, "vat_input"),
        vat_output=get_optional(row, "vat_output"),
        is_private_paid=bool(get_optional(row, "is_private_paid") or 0),
        private_classification=get_optional(row, "private_classification") or "none",
        hash=get_optional(row, "hash"),
    )


def _resolve_create_vat(
    *,
    tax_mode: str,
    is_rc: bool,
    amount_eur: float,
    legacy_vat: float | None,
    vat_input: float | None,
    vat_output: float | None,
    skip_vat_auto: bool,
) -> tuple[float | None, float | None]:
    if tax_mode not in {"small_business", "standard"}:
        raise ValidationError(
            f"Unbekannter Steuermodus: {tax_mode}",
            code="invalid_tax_mode",
            details={"tax_mode": tax_mode},
        )

    resolved_vat_input = vat_input
    resolved_vat_output = vat_output
    calc_vat = round(abs(amount_eur) * 0.19, 2)

    if legacy_vat is not None:
        if is_rc:
            if resolved_vat_output is None:
                resolved_vat_output = legacy_vat
            if tax_mode == "standard":
                if resolved_vat_input is None:
                    resolved_vat_input = legacy_vat
            else:
                if resolved_vat_input is None:
                    resolved_vat_input = 0.0
        elif tax_mode == "standard":
            if resolved_vat_input is None:
                resolved_vat_input = legacy_vat

    if skip_vat_auto:
        return resolved_vat_input, resolved_vat_output

    if tax_mode == "small_business":
        if is_rc:
            if resolved_vat_output is None:
                resolved_vat_output = calc_vat
            if resolved_vat_input is None:
                resolved_vat_input = 0.0
        else:
            if resolved_vat_input is None:
                resolved_vat_input = 0.0
            if resolved_vat_output is None:
                resolved_vat_output = 0.0
    else:
        if is_rc:
            if resolved_vat_output is None:
                resolved_vat_output = calc_vat
            if resolved_vat_input is None:
                resolved_vat_input = calc_vat
        elif resolved_vat_output is None:
            resolved_vat_output = 0.0

    return resolved_vat_input, resolved_vat_output


def _resolve_expense_category(
    conn: sqlite3.Connection,
    *,
    category_name: str | None,
    ledger_account_key: str | None,
    ledger_accounts: list[LedgerAccount] | None,
) -> tuple[int | None, str | None, str | None]:
    resolved_category_name = category_name
    resolved_ledger_account_key: str | None = None

    if ledger_account_key is not None:
        resolved_ledger_account = resolve_ledger_account(
            conn,
            ledger_account_key,
            ledger_accounts or [],
            "expense",
        )
        if category_name and category_name.lower() != resolved_ledger_account.category.lower():
            raise ValidationError(
                f"Buchungskonto '{resolved_ledger_account.key}' gehört zur Kategorie "
                f"'{resolved_ledger_account.category}', nicht zu '{category_name}'.",
                code="ledger_account_category_mismatch",
                details={
                    "ledger_account": resolved_ledger_account.key,
                    "ledger_category": resolved_ledger_account.category,
                    "category": category_name,
                },
            )
        resolved_category_name = resolved_ledger_account.category
        resolved_ledger_account_key = resolved_ledger_account.key

    category_id: int | None = None
    if resolved_category_name:
        category = get_category_by_name(conn, resolved_category_name, "expense")
        if not category:
            raise ValidationError(
                f"Kategorie '{resolved_category_name}' nicht gefunden.",
                code="category_not_found",
                details={"category": resolved_category_name, "type": "expense"},
            )
        category_id = category.id
        resolved_category_name = category.name

    return category_id, resolved_category_name, resolved_ledger_account_key


def create_expense(
    conn: sqlite3.Connection,
    *,
    vendor: str,
    amount_eur: float,
    payment_date: str | None = None,
    invoice_date: str | None = None,
    date: str | None = None,
    category_name: str | None = None,
    ledger_account_key: str | None = None,
    ledger_accounts: list[LedgerAccount] | None = None,
    account: str | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    notes: str | None = None,
    is_rc: bool = False,
    vat: float | None = None,
    vat_input: float | None = None,
    vat_output: float | None = None,
    private_paid: bool = False,
    private_accounts: list[str] | None = None,
    tax_mode: str = "small_business",
    audit_user: str = "default",
    skip_vat_auto: bool = False,
    on_duplicate: DuplicateAction = DuplicateAction.RAISE,
    auto_commit: bool = True,
) -> Expense | None:
    resolved_payment_date, resolved_invoice_date = resolve_dates(
        payment_date=payment_date,
        invoice_date=invoice_date,
        legacy_date=date,
    )

    category_id, resolved_category_name, resolved_ledger_account_key = _resolve_expense_category(
        conn,
        category_name=category_name,
        ledger_account_key=ledger_account_key,
        ledger_accounts=ledger_accounts,
    )

    resolved_vat_input, resolved_vat_output = _resolve_create_vat(
        tax_mode=tax_mode,
        is_rc=is_rc,
        amount_eur=amount_eur,
        legacy_vat=vat,
        vat_input=vat_input,
        vat_output=vat_output,
        skip_vat_auto=skip_vat_auto,
    )

    tx_hash = compute_hash(
        hash_date(resolved_payment_date, resolved_invoice_date),
        vendor,
        amount_eur,
        receipt_name or "",
    )
    existing = conn.execute(
        "SELECT id FROM expenses WHERE hash = ?",
        (tx_hash,),
    ).fetchone()
    if existing:
        if on_duplicate == DuplicateAction.SKIP:
            return None
        raise ValidationError(
            f"Duplikat erkannt (ID {existing['id']})",
            code="duplicate",
            details={"existing_id": existing["id"]},
        )

    record_uuid = str(uuid.uuid4())
    is_private_paid, private_classification = classify_expense_private_paid(
        account=account,
        category_name=resolved_category_name,
        private_accounts=private_accounts or [],
        manual_override=private_paid,
    )

    cursor = conn.execute(
        """INSERT INTO expenses
           (uuid, receipt_name, payment_date, invoice_date, vendor, category_id, amount_eur, account,
            ledger_account, foreign_amount, notes, is_rc, vat_input, vat_output,
            is_private_paid, private_classification, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_uuid,
            receipt_name,
            resolved_payment_date,
            resolved_invoice_date,
            vendor,
            category_id,
            amount_eur,
            account,
            resolved_ledger_account_key,
            foreign_amount,
            notes,
            1 if is_rc else 0,
            resolved_vat_input,
            resolved_vat_output,
            1 if is_private_paid else 0,
            private_classification,
            tx_hash,
        ),
    )
    record_id = cursor.lastrowid
    assert record_id is not None

    new_data = {
        "uuid": record_uuid,
        "receipt_name": receipt_name,
        "payment_date": resolved_payment_date,
        "invoice_date": resolved_invoice_date,
        "vendor": vendor,
        "category_id": category_id,
        "amount_eur": amount_eur,
        "account": account,
        "ledger_account": resolved_ledger_account_key,
        "foreign_amount": foreign_amount,
        "notes": notes,
        "is_rc": 1 if is_rc else 0,
        "vat_input": resolved_vat_input,
        "vat_output": resolved_vat_output,
        "is_private_paid": 1 if is_private_paid else 0,
        "private_classification": private_classification,
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

    if auto_commit:
        conn.commit()

    return Expense(
        id=record_id,
        uuid=record_uuid,
        payment_date=resolved_payment_date,
        invoice_date=resolved_invoice_date,
        vendor=vendor,
        amount_eur=amount_eur,
        category_id=category_id,
        category_name=resolved_category_name,
        account=account,
        ledger_account=resolved_ledger_account_key,
        receipt_name=receipt_name,
        foreign_amount=foreign_amount,
        notes=notes,
        is_rc=is_rc,
        vat_input=resolved_vat_input,
        vat_output=resolved_vat_output,
        is_private_paid=is_private_paid,
        private_classification=private_classification,
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
        SELECT e.id, e.uuid, e.payment_date, e.invoice_date, e.vendor, e.category_id,
               c.name as category_name,
               c.eur_line as category_eur_line, e.amount_eur, e.account, e.ledger_account,
               e.receipt_name,
               e.foreign_amount, e.notes, e.is_rc, e.vat_input, e.vat_output,
               e.is_private_paid, e.private_classification, e.hash
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE 1=1
    """
    params: list[object] = []

    if year:
        query += " AND strftime('%Y', COALESCE(e.payment_date, e.invoice_date)) = ?"
        params.append(str(year))
    if month:
        query += " AND strftime('%m', COALESCE(e.payment_date, e.invoice_date)) = ?"
        params.append(f"{month:02d}")
    if category_name:
        query += " AND LOWER(c.name) = LOWER(?)"
        params.append(category_name)

    query += " ORDER BY COALESCE(e.payment_date, e.invoice_date) DESC, e.id DESC"

    rows = conn.execute(query, params).fetchall()
    return [row_to_expense(row) for row in rows]


def get_expense_detail(conn: sqlite3.Connection, record_id: int) -> Expense:
    row = conn.execute(
        """SELECT e.id, e.uuid, e.payment_date, e.invoice_date, e.vendor, e.category_id,
                  c.name as category_name,
                  c.eur_line as category_eur_line, e.amount_eur, e.account, e.ledger_account,
                  e.receipt_name,
                  e.foreign_amount, e.notes, e.is_rc, e.vat_input, e.vat_output,
                  e.is_private_paid, e.private_classification, e.hash
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
    return row_to_expense(row)


def update_expense(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    payment_date: str | None = None,
    invoice_date: str | None = None,
    date: str | None = None,
    vendor: str | None = None,
    category_name: str | None = None,
    ledger_account_key: str | None = None,
    ledger_accounts: list[LedgerAccount] | None = None,
    amount_eur: float | None = None,
    account: str | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    notes: str | None = None,
    vat: float | None = None,
    is_rc: bool = False,
    private_paid: bool | None = None,
    private_accounts: list[str] | None = None,
    tax_mode: str,
    audit_user: str,
    auto_commit: bool = True,
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
    new_payment_date = (
        payment_date
        if payment_date is not None
        else (date if date is not None else row["payment_date"])
    )
    new_invoice_date = invoice_date if invoice_date is not None else row["invoice_date"]
    new_payment_date, new_invoice_date = resolve_dates(
        payment_date=new_payment_date,
        invoice_date=new_invoice_date,
    )
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

    existing_category_name: str | None = None
    if row["category_id"]:
        cat_row = conn.execute(
            "SELECT name FROM categories WHERE id = ?",
            (row["category_id"],),
        ).fetchone()
        if cat_row:
            existing_category_name = cat_row["name"]

    resolved_category_name = existing_category_name
    resolved_ledger_account_key = get_optional(row, "ledger_account")
    if ledger_account_key is not None:
        category_id, resolved_category_name, resolved_ledger_account_key = _resolve_expense_category(
            conn,
            category_name=category_name,
            ledger_account_key=ledger_account_key,
            ledger_accounts=ledger_accounts,
        )
    else:
        category_id = row["category_id"]
        if category_name:
            if resolved_ledger_account_key and ledger_accounts:
                resolved_ledger_account = resolve_ledger_account(
                    conn,
                    resolved_ledger_account_key,
                    ledger_accounts,
                    "expense",
                )
                if category_name.lower() != resolved_ledger_account.category.lower():
                    raise ValidationError(
                        f"Buchungskonto '{resolved_ledger_account.key}' gehört zur Kategorie "
                        f"'{resolved_ledger_account.category}', nicht zu '{category_name}'.",
                        code="ledger_account_category_mismatch",
                        details={
                            "ledger_account": resolved_ledger_account.key,
                            "ledger_category": resolved_ledger_account.category,
                            "category": category_name,
                        },
                    )
            category = get_category_by_name(conn, category_name, "expense")
            if not category:
                raise ValidationError(
                    f"Kategorie '{category_name}' nicht gefunden.",
                    code="category_not_found",
                    details={"category": category_name, "type": "expense"},
                )
            category_id = category.id
            resolved_category_name = category.name

    if private_paid is True:
        new_is_private_paid, new_private_classification = classify_expense_private_paid(
            account=new_account,
            category_name=resolved_category_name,
            private_accounts=private_accounts or [],
            manual_override=True,
        )
    elif private_paid is False:
        new_is_private_paid = False
        new_private_classification = "none"
    elif account is not None or category_name is not None:
        new_is_private_paid, new_private_classification = classify_expense_private_paid(
            account=new_account,
            category_name=resolved_category_name,
            private_accounts=private_accounts or [],
        )
    else:
        new_is_private_paid = bool(row["is_private_paid"])
        new_private_classification = row["private_classification"]

    new_hash = compute_hash(
        hash_date(new_payment_date, new_invoice_date),
        new_vendor,
        new_amount,
        new_receipt or "",
    )

    conn.execute(
        """UPDATE expenses SET
           receipt_name = ?, payment_date = ?, invoice_date = ?, vendor = ?, category_id = ?, amount_eur = ?,
           account = ?, ledger_account = ?, foreign_amount = ?, notes = ?, is_rc = ?, vat_input = ?, vat_output = ?,
           is_private_paid = ?, private_classification = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_payment_date,
            new_invoice_date,
            new_vendor,
            category_id,
            new_amount,
            new_account,
            resolved_ledger_account_key,
            new_foreign,
            new_notes,
            1 if new_rc else 0,
            new_vat_input,
            new_vat_output,
            1 if new_is_private_paid else 0,
            new_private_classification,
            new_hash,
            record_id,
        ),
    )

    record_uuid = row["uuid"]

    new_data = {
        "uuid": record_uuid,
        "receipt_name": new_receipt,
        "payment_date": new_payment_date,
        "invoice_date": new_invoice_date,
        "vendor": new_vendor,
        "category_id": category_id,
        "amount_eur": new_amount,
        "account": new_account,
        "ledger_account": resolved_ledger_account_key,
        "foreign_amount": new_foreign,
        "notes": new_notes,
        "is_rc": 1 if new_rc else 0,
        "vat_input": new_vat_input,
        "vat_output": new_vat_output,
        "is_private_paid": 1 if new_is_private_paid else 0,
        "private_classification": new_private_classification,
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

    if auto_commit:
        conn.commit()

    return Expense(
        id=record_id,
        uuid=record_uuid,
        payment_date=new_payment_date,
        invoice_date=new_invoice_date,
        vendor=new_vendor,
        amount_eur=new_amount,
        category_id=category_id,
        category_name=resolved_category_name,
        account=new_account,
        ledger_account=resolved_ledger_account_key,
        receipt_name=new_receipt,
        foreign_amount=new_foreign,
        notes=new_notes,
        is_rc=new_rc,
        vat_input=new_vat_input,
        vat_output=new_vat_output,
        is_private_paid=new_is_private_paid,
        private_classification=new_private_classification,
        hash=new_hash,
    )


def delete_expense(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    audit_user: str,
    auto_commit: bool = True,
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

    if auto_commit:
        conn.commit()
