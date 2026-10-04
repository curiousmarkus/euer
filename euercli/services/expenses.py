from __future__ import annotations

import sqlite3
import uuid

from ..db import log_audit, row_to_dict
from ..utils import compute_hash
from .categories import get_category_by_name, resolve_ledger_account
from .duplicates import DuplicateAction, find_exact_duplicate
from .entertainment import resolve_entertainment_fields
from .errors import RecordNotFoundError, ValidationError
from .eur import category_key_for_name, is_entertainment_category
from .models import Expense, LedgerAccount
from .private_classification import classify_expense_private_paid
from .utils import get_optional, hash_date, normalize_account_name, resolve_dates
from .validation import (
    DEFAULT_AMOUNT_THRESHOLD,
    check_fuzzy_duplicate,
    validate_amount_threshold,
    validate_date_plausibility,
    validate_vat_math,
)
from .vat import (
    EXPENSE_VAT_CODES,
    INPUT_INVOICE,
    RC_VAT_CODE_BY_TYPE,
    validate_vat_code,
    validate_vat_rate,
)

VALID_RC_TYPES = {"none", "eu", "third_country", "unclassified"}
CREATABLE_RC_TYPES = {"none", "eu", "third_country"}


def row_to_expense(row: sqlite3.Row) -> Expense:
    rc_type = get_optional(row, "rc_type")
    if rc_type is None:
        rc_jurisdiction = get_optional(row, "rc_jurisdiction")
        if rc_jurisdiction:
            rc_type = rc_jurisdiction
        elif bool(get_optional(row, "is_rc") or 0):
            rc_type = "unclassified"
        else:
            rc_type = "none"

    return Expense(
        id=row["id"],
        uuid=row["uuid"],
        payment_date=get_optional(row, "payment_date"),
        invoice_date=get_optional(row, "invoice_date"),
        vendor=row["vendor"],
        amount_eur=row["amount_eur"],
        category_id=get_optional(row, "category_id"),
        category_name=get_optional(row, "category_name"),
        category_eur_line=None,
        category_eur_key=get_optional(row, "category_eur_key"),
        account=get_optional(row, "account"),
        ledger_account=get_optional(row, "ledger_account"),
        receipt_name=get_optional(row, "receipt_name"),
        invoice_number=get_optional(row, "invoice_number"),
        foreign_amount=get_optional(row, "foreign_amount"),
        notes=get_optional(row, "notes"),
        rc_type=rc_type,
        vat_input=get_optional(row, "vat_input"),
        vat_output=get_optional(row, "vat_output"),
        vat_rate=get_optional(row, "vat_rate"),
        vat_code=get_optional(row, "vat_code"),
        entertainment_tip_eur=get_optional(row, "entertainment_tip_eur"),
        entertainment_vat_status=get_optional(row, "entertainment_vat_status"),
        is_private_paid=bool(get_optional(row, "is_private_paid") or 0),
        private_classification=get_optional(row, "private_classification") or "none",
        hash=get_optional(row, "hash"),
        deleted_at=get_optional(row, "deleted_at"),
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


def _resolve_expense_vat_classification(
    *,
    rc_type: str,
    vat_input: float | None,
    vat_rate: float | None,
    vat_code: str | None,
) -> tuple[float | None, str | None]:
    resolved_rate = validate_vat_rate(vat_rate)
    resolved_code = validate_vat_code(vat_code, EXPENSE_VAT_CODES)

    if rc_type in RC_VAT_CODE_BY_TYPE:
        expected_code = RC_VAT_CODE_BY_TYPE[rc_type]
        if resolved_code is not None and resolved_code != expected_code:
            raise ValidationError(
                "Steuerklasse passt nicht zum Reverse-Charge-Typ.",
                code="vat_code_rc_type_mismatch",
                details={"rc_type": rc_type, "vat_code": resolved_code},
            )
        if resolved_rate is not None and resolved_rate != 19.0:
            raise ValidationError(
                "Reverse-Charge wird im MVP nur mit 19 % unterstützt.",
                code="unsupported_vat_rate",
                details={"vat_rate": resolved_rate},
            )
        return 19.0, expected_code

    if resolved_code in RC_VAT_CODE_BY_TYPE.values():
        raise ValidationError(
            "Reverse-Charge-Steuerklassen erfordern --rc eu oder --rc third-country.",
            code="vat_code_requires_rc",
            details={"vat_code": resolved_code},
        )

    if resolved_code is None and (
        resolved_rate is not None or (vat_input is not None and vat_input > 0)
    ):
        resolved_code = INPUT_INVOICE

    return resolved_rate, resolved_code


def _resolve_expense_category(
    conn: sqlite3.Connection,
    *,
    category_name: str | None,
    ledger_account_key: str | None,
    ledger_accounts: list[LedgerAccount] | None,
) -> tuple[int | None, str | None, str | None, str | None]:
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
    resolved_category_key: str | None = None
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
        resolved_category_key = category.eur_key or category_key_for_name(
            category.name,
            "expense",
        )

    return category_id, resolved_category_name, resolved_ledger_account_key, resolved_category_key


def _validate_rc_type(value: str) -> None:
    if value not in VALID_RC_TYPES:
        raise ValidationError(
            "Ungültiger Reverse-Charge-Typ. Erlaubt sind: none, eu, third_country.",
            code="invalid_rc_type",
            details={"rc_type": value},
        )


def _resolve_create_rc_type(rc_type: str) -> str:
    _validate_rc_type(rc_type)
    if rc_type == "unclassified":
        raise ValidationError(
            "Reverse-Charge-Typ 'unclassified' ist nur für migrierte Altbuchungen zulässig.",
            code="unclassified_rc_type_not_allowed",
        )
    return rc_type


def _resolve_update_rc_type(
    *,
    current_rc_type: str,
    rc_type: str | None,
) -> str:
    if rc_type is None:
        _validate_rc_type(current_rc_type)
        return current_rc_type
    _validate_rc_type(rc_type)
    if rc_type == "unclassified":
        raise ValidationError(
            "Reverse-Charge-Typ 'unclassified' ist nur für migrierte Altbuchungen zulässig.",
            code="unclassified_rc_type_not_allowed",
        )
    return rc_type


def migrate_legacy_entertainment_statuses(
    conn: sqlite3.Connection,
    *,
    audit_user: str = "default",
) -> int:
    """Markiert alte Bewirtungen wiederholbar als prüfbedürftig und auditiert sie."""
    rows = conn.execute(
        """SELECT e.id, e.uuid, e.entertainment_tip_eur, e.entertainment_vat_status,
                  e.amount_eur, e.vat_input, e.category_id
           FROM expenses e
           JOIN categories c ON c.id = e.category_id
           WHERE c.eur_key = 'entertainment'
             AND e.entertainment_vat_status IS NULL
           ORDER BY e.id"""
    ).fetchall()
    for row in rows:
        old_data = {
            "amount_eur": row["amount_eur"],
            "vat_input": row["vat_input"],
            "entertainment_tip_eur": row["entertainment_tip_eur"],
            "entertainment_vat_status": row["entertainment_vat_status"],
            "category_id": row["category_id"],
        }
        conn.execute(
            "UPDATE expenses SET entertainment_vat_status = 'needs_review' WHERE id = ?",
            (row["id"],),
        )
        log_audit(
            conn,
            "expenses",
            row["id"],
            "MIGRATE",
            record_uuid=row["uuid"],
            old_data=old_data,
            new_data={**old_data, "entertainment_vat_status": "needs_review"},
            user=audit_user,
        )
    if rows:
        conn.commit()
    return len(rows)


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
    default_account: str | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    invoice_number: str | None = None,
    notes: str | None = None,
    rc_type: str = "none",
    vat: float | None = None,
    vat_input: float | None = None,
    vat_output: float | None = None,
    vat_rate: float | None = None,
    vat_code: str | None = None,
    entertainment_tip_eur: float | None = None,
    entertainment_vat_status: str | None = None,
    allow_historical_entertainment_vat: bool = False,
    private_paid: bool = False,
    private_accounts: list[str] | None = None,
    tax_mode: str = "small_business",
    audit_user: str = "default",
    skip_vat_auto: bool = False,
    on_duplicate: DuplicateAction = DuplicateAction.RAISE,
    force: bool = False,
    allow_duplicate: bool = False,
    amount_threshold: float = DEFAULT_AMOUNT_THRESHOLD,
    auto_commit: bool = True,
) -> Expense | None:
    resolved_payment_date, resolved_invoice_date = resolve_dates(
        payment_date=payment_date,
        invoice_date=invoice_date,
        legacy_date=date,
    )

    validate_date_plausibility(
        payment_date=resolved_payment_date,
        invoice_date=resolved_invoice_date,
    )
    validate_amount_threshold(
        amount_eur=amount_eur,
        threshold=amount_threshold,
        force=force,
    )

    (
        category_id,
        resolved_category_name,
        resolved_ledger_account_key,
        resolved_category_key,
    ) = _resolve_expense_category(
        conn,
        category_name=category_name,
        ledger_account_key=ledger_account_key,
        ledger_accounts=ledger_accounts,
    )
    resolved_rc_type = _resolve_create_rc_type(rc_type)

    resolved_vat_input, resolved_vat_output = _resolve_create_vat(
        tax_mode=tax_mode,
        is_rc=resolved_rc_type != "none",
        amount_eur=amount_eur,
        legacy_vat=vat,
        vat_input=vat_input,
        vat_output=vat_output,
        skip_vat_auto=skip_vat_auto,
    )
    resolved_vat_rate, resolved_vat_code = _resolve_expense_vat_classification(
        rc_type=resolved_rc_type,
        vat_input=resolved_vat_input,
        vat_rate=vat_rate,
        vat_code=vat_code,
    )

    resolved_entertainment_tip = None
    resolved_entertainment_vat_status = None
    if is_entertainment_category(resolved_category_key):
        if resolved_rc_type != "none":
            raise ValidationError(
                "Bewirtung mit Reverse Charge wird nicht unterstützt.",
                code="unsupported_entertainment_reverse_charge",
            )
        raw_vat_input = vat_input if vat_input is not None else vat
        resolved_vat_input, resolved_entertainment_tip, resolved_entertainment_vat_status = (
            resolve_entertainment_fields(
                amount_eur=amount_eur,
                vat_input=raw_vat_input if raw_vat_input is not None else resolved_vat_input,
                tip_eur=entertainment_tip_eur,
                vat_status=entertainment_vat_status,
                tax_mode=tax_mode,
                vat_was_provided=raw_vat_input is not None,
                allow_historical_vat=allow_historical_entertainment_vat,
            )
        )
        resolved_vat_rate = None
        resolved_vat_code = INPUT_INVOICE if (resolved_vat_input or 0) > 0 else None
    elif entertainment_tip_eur is not None or entertainment_vat_status is not None:
        raise ValidationError(
            "Trinkgeld und Vorsteuerstatus sind nur für Bewirtungsaufwendungen zulässig.",
            code="entertainment_fields_require_category",
        )
    else:
        if (
            vat_rate is not None
            and vat_rate in (7.0, 19.0)
            and (vat is not None or vat_input is not None)
            and resolved_rc_type == "none"
        ):
            raw_vat = vat if vat is not None else vat_input
            validate_vat_math(
                amount_eur=amount_eur,
                vat_rate=vat_rate,
                vat_amount=raw_vat,
            )

    invoice_number = invoice_number.strip() or None if invoice_number is not None else None
    tx_hash = compute_hash(
        hash_date(resolved_payment_date, resolved_invoice_date),
        vendor,
        amount_eur,
        receipt_name or "",
        invoice_number,
    )
    existing_id = find_exact_duplicate(
        conn,
        table_name="expenses",
        payment_date=resolved_payment_date,
        invoice_date=resolved_invoice_date,
        party=vendor,
        amount_eur=amount_eur,
        receipt_name=receipt_name,
        invoice_number=invoice_number,
    )
    if existing_id is not None:
        if on_duplicate == DuplicateAction.SKIP:
            return None
        raise ValidationError(
            f"Duplikat erkannt (ID {existing_id})",
            code="duplicate",
            details={"existing_id": existing_id},
        )

    if on_duplicate == DuplicateAction.SKIP:
        check_fuzzy_duplicate(
            conn,
            table_name="expenses",
            name=vendor,
            amount_eur=amount_eur,
            date_val=resolved_payment_date or resolved_invoice_date,
            invoice_number=invoice_number,
            invoice_date=resolved_invoice_date,
            receipt_name=receipt_name,
            invoice_only=True,
        )
    else:
        check_fuzzy_duplicate(
            conn,
            table_name="expenses",
            name=vendor,
            amount_eur=amount_eur,
            date_val=resolved_payment_date or resolved_invoice_date,
            invoice_number=invoice_number.strip() or None if invoice_number else None,
            invoice_date=resolved_invoice_date,
            receipt_name=receipt_name,
            allow_duplicate=allow_duplicate,
            force=force,
        )

    record_uuid = str(uuid.uuid4())
    resolved_account = normalize_account_name(account) or normalize_account_name(default_account)
    is_private_paid, private_classification = classify_expense_private_paid(
        account=resolved_account,
        category_name=resolved_category_name,
        private_accounts=private_accounts or [],
        manual_override=private_paid,
    )

    cursor = conn.execute(
        """INSERT INTO expenses
           (uuid, receipt_name, payment_date, invoice_date, invoice_number, vendor, category_id,
            amount_eur, account, ledger_account, foreign_amount, notes, rc_type,
            vat_input, vat_output, vat_rate, vat_code,
            entertainment_tip_eur, entertainment_vat_status,
            is_private_paid, private_classification, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_uuid,
            receipt_name,
            resolved_payment_date,
            resolved_invoice_date,
            invoice_number,
            vendor,
            category_id,
            amount_eur,
            resolved_account,
            resolved_ledger_account_key,
            foreign_amount,
            notes,
            resolved_rc_type,
            resolved_vat_input,
            resolved_vat_output,
            resolved_vat_rate,
            resolved_vat_code,
            resolved_entertainment_tip,
            resolved_entertainment_vat_status,
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
        "invoice_number": invoice_number,
        "vendor": vendor,
        "category_id": category_id,
        "amount_eur": amount_eur,
        "account": resolved_account,
        "ledger_account": resolved_ledger_account_key,
        "foreign_amount": foreign_amount,
        "notes": notes,
        "rc_type": resolved_rc_type,
        "vat_input": resolved_vat_input,
        "vat_output": resolved_vat_output,
        "vat_rate": resolved_vat_rate,
        "vat_code": resolved_vat_code,
        "entertainment_tip_eur": resolved_entertainment_tip,
        "entertainment_vat_status": resolved_entertainment_vat_status,
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
        category_eur_key=resolved_category_key,
        account=resolved_account,
        ledger_account=resolved_ledger_account_key,
        receipt_name=receipt_name,
        invoice_number=invoice_number,
        foreign_amount=foreign_amount,
        notes=notes,
        rc_type=resolved_rc_type,
        vat_input=resolved_vat_input,
        vat_output=resolved_vat_output,
        vat_rate=resolved_vat_rate,
        vat_code=resolved_vat_code,
        entertainment_tip_eur=resolved_entertainment_tip,
        entertainment_vat_status=resolved_entertainment_vat_status,
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
    account: str | None = None,
    include_deleted: bool = False,
    trash_only: bool = False,
) -> list[Expense]:
    query = """
        SELECT e.id, e.uuid, e.payment_date, e.invoice_date, e.vendor, e.category_id,
               c.name as category_name,
               c.eur_key as category_eur_key,
               e.amount_eur, e.account, e.ledger_account,
               e.receipt_name, e.invoice_number,
               e.foreign_amount, e.notes, e.rc_type, e.vat_input, e.vat_output,
               e.vat_rate, e.vat_code,
               e.entertainment_tip_eur, e.entertainment_vat_status,
               e.is_private_paid, e.private_classification, e.hash,
               e.deleted_at
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE 1=1
    """
    params: list[object] = []

    if trash_only:
        query += " AND e.deleted_at IS NOT NULL"
    elif not include_deleted:
        query += " AND e.deleted_at IS NULL"

    if year:
        query += " AND strftime('%Y', COALESCE(e.payment_date, e.invoice_date)) = ?"
        params.append(str(year))
    if month:
        query += " AND strftime('%m', COALESCE(e.payment_date, e.invoice_date)) = ?"
        params.append(f"{month:02d}")
    if category_name:
        query += " AND LOWER(c.name) = LOWER(?)"
        params.append(category_name)
    if account:
        query += " AND LOWER(e.account) = LOWER(?)"
        params.append(account.strip())

    query += " ORDER BY COALESCE(e.payment_date, e.invoice_date) DESC, e.id DESC"

    rows = conn.execute(query, params).fetchall()
    return [row_to_expense(row) for row in rows]


def get_expense_detail(
    conn: sqlite3.Connection,
    record_id: int,
    include_deleted: bool = False,
) -> Expense:
    query = """SELECT e.id, e.uuid, e.payment_date, e.invoice_date, e.vendor, e.category_id,
                  c.name as category_name,
                  c.eur_key as category_eur_key,
                  e.amount_eur, e.account, e.ledger_account,
                  e.receipt_name, e.invoice_number,
                  e.foreign_amount, e.notes, e.rc_type, e.vat_input, e.vat_output,
                  e.vat_rate, e.vat_code,
                  e.entertainment_tip_eur, e.entertainment_vat_status,
                  e.is_private_paid, e.private_classification, e.hash,
                  e.deleted_at
           FROM expenses e
           LEFT JOIN categories c ON e.category_id = c.id
           WHERE e.id = ?"""
    if not include_deleted:
        query += " AND e.deleted_at IS NULL"

    row = conn.execute(query, (record_id,)).fetchone()
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
    invoice_number: str | None = None,
    notes: str | None = None,
    vat: float | None = None,
    vat_rate: float | None = None,
    vat_code: str | None = None,
    entertainment_tip_eur: float | None = None,
    entertainment_vat_status: str | None = None,
    rc_type: str | None = None,
    private_paid: bool | None = None,
    private_accounts: list[str] | None = None,
    tax_mode: str,
    audit_user: str,
    force: bool = False,
    allow_duplicate: bool = False,
    amount_threshold: float = DEFAULT_AMOUNT_THRESHOLD,
    auto_commit: bool = True,
) -> Expense:
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (record_id,),
    ).fetchone()
    if not row or (row["deleted_at"] is not None):
        raise RecordNotFoundError(
            f"Ausgabe #{record_id} nicht gefunden.",
            code="expense_not_found",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)

    new_receipt = receipt_name if receipt_name is not None else row["receipt_name"]
    new_invoice_number = (
        invoice_number.strip() or None if invoice_number is not None else row["invoice_number"]
    )
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

    validate_date_plausibility(
        payment_date=new_payment_date,
        invoice_date=new_invoice_date,
    )
    if amount_eur is not None:
        validate_amount_threshold(
            amount_eur=amount_eur,
            threshold=amount_threshold,
            force=force,
        )

    new_vendor = vendor if vendor else row["vendor"]
    new_amount = amount_eur if amount_eur is not None else row["amount_eur"]
    new_account = normalize_account_name(account) if account is not None else row["account"]
    new_foreign = foreign_amount if foreign_amount is not None else row["foreign_amount"]
    new_notes = notes if notes is not None else row["notes"]

    new_vat_input = row["vat_input"]
    new_vat_output = row["vat_output"]
    new_vat_rate = get_optional(row, "vat_rate")
    new_vat_code = get_optional(row, "vat_code")

    current_category_key: str | None = None
    if row["category_id"]:
        current_category_row = conn.execute(
            "SELECT name, eur_key FROM categories WHERE id = ?",
            (row["category_id"],),
        ).fetchone()
        if current_category_row:
            current_category_key = current_category_row["eur_key"] or category_key_for_name(
                current_category_row["name"],
                "expense",
            )

    manual_vat = vat
    current_rc_type = get_optional(row, "rc_type") or "none"
    new_rc_type = _resolve_update_rc_type(
        current_rc_type=current_rc_type,
        rc_type=rc_type,
    )
    new_rc = new_rc_type != "none"

    recalc_tax = (
        (vat is not None)
        or (vat_rate is not None)
        or (vat_code is not None)
        or (rc_type is not None)
        or (amount_eur is not None and current_category_key != "entertainment")
    )

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
        new_vat_rate, new_vat_code = _resolve_expense_vat_classification(
            rc_type=new_rc_type,
            vat_input=new_vat_input,
            vat_rate=vat_rate,
            vat_code=vat_code,
        )

    existing_category_name: str | None = None
    existing_category_key: str | None = None
    if row["category_id"]:
        cat_row = conn.execute(
            "SELECT name, eur_key FROM categories WHERE id = ?",
            (row["category_id"],),
        ).fetchone()
        if cat_row:
            existing_category_name = cat_row["name"]
            existing_category_key = cat_row["eur_key"] or category_key_for_name(
                cat_row["name"],
                "expense",
            )

    resolved_category_name = existing_category_name
    resolved_category_key = existing_category_key
    resolved_ledger_account_key = get_optional(row, "ledger_account")
    if ledger_account_key is not None:
        (
            category_id,
            resolved_category_name,
            resolved_ledger_account_key,
            resolved_category_key,
        ) = _resolve_expense_category(
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
            resolved_category_key = category.eur_key or category_key_for_name(
                category.name,
                "expense",
            )

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

    is_entertainment = is_entertainment_category(resolved_category_key)
    new_entertainment_tip = (
        entertainment_tip_eur if entertainment_tip_eur is not None else row["entertainment_tip_eur"]
    )
    new_entertainment_status = (
        entertainment_vat_status
        if entertainment_vat_status is not None
        else row["entertainment_vat_status"]
    )
    if is_entertainment:
        if new_rc_type != "none":
            raise ValidationError(
                "Bewirtung mit Reverse Charge wird nicht unterstützt.",
                code="unsupported_entertainment_reverse_charge",
            )
        if existing_category_key != "entertainment" and entertainment_vat_status is None:
            # Beim erstmaligen Umklassifizieren keine historische Behandlung aus
            # dem aktuell eingestellten Steuermodus ableiten.
            new_entertainment_status = "needs_review"
        elif vat is not None and entertainment_vat_status is None:
            new_entertainment_status = None
        raw_vat_input = vat if vat is not None else new_vat_input
        new_vat_input, new_entertainment_tip, new_entertainment_status = (
            resolve_entertainment_fields(
                amount_eur=new_amount,
                vat_input=raw_vat_input,
                tip_eur=new_entertainment_tip,
                vat_status=new_entertainment_status,
                tax_mode=tax_mode,
                vat_was_provided=vat is not None,
                allow_historical_vat=(
                    existing_category_key == "entertainment"
                    and entertainment_vat_status is not None
                ),
            )
        )
        new_vat_rate = None
        new_vat_code = INPUT_INVOICE if (new_vat_input or 0) > 0 else None
    elif entertainment_tip_eur is not None or entertainment_vat_status is not None:
        raise ValidationError(
            "Trinkgeld und Vorsteuerstatus sind nur für Bewirtungsaufwendungen zulässig.",
            code="entertainment_fields_require_category",
        )
    else:
        new_entertainment_tip = None
        new_entertainment_status = None
        if (
            vat_rate is not None
            and vat_rate in (7.0, 19.0)
            and vat is not None
            and new_rc_type == "none"
        ):
            validate_vat_math(
                amount_eur=new_amount,
                vat_rate=vat_rate,
                vat_amount=vat,
            )

    if (
        vendor is not None
        or amount_eur is not None
        or payment_date is not None
        or invoice_date is not None
        or invoice_number is not None
    ):
        check_fuzzy_duplicate(
            conn,
            table_name="expenses",
            name=new_vendor,
            amount_eur=new_amount,
            date_val=new_payment_date or new_invoice_date,
            invoice_number=new_invoice_number,
            invoice_date=new_invoice_date,
            receipt_name=new_receipt,
            allow_duplicate=allow_duplicate,
            force=force,
            exclude_id=record_id,
        )

    new_hash = compute_hash(
        hash_date(new_payment_date, new_invoice_date),
        new_vendor,
        new_amount,
        new_receipt or "",
        new_invoice_number,
    )

    conn.execute(
        """UPDATE expenses SET
           receipt_name = ?, payment_date = ?, invoice_date = ?, invoice_number = ?, vendor = ?,
           category_id = ?, amount_eur = ?,
           account = ?, ledger_account = ?, foreign_amount = ?, notes = ?, rc_type = ?,
           vat_input = ?, vat_output = ?, vat_rate = ?, vat_code = ?,
           entertainment_tip_eur = ?, entertainment_vat_status = ?,
           is_private_paid = ?, private_classification = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_payment_date,
            new_invoice_date,
            new_invoice_number,
            new_vendor,
            category_id,
            new_amount,
            new_account,
            resolved_ledger_account_key,
            new_foreign,
            new_notes,
            new_rc_type,
            new_vat_input,
            new_vat_output,
            new_vat_rate,
            new_vat_code,
            new_entertainment_tip,
            new_entertainment_status,
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
        "invoice_number": new_invoice_number,
        "vendor": new_vendor,
        "category_id": category_id,
        "amount_eur": new_amount,
        "account": new_account,
        "ledger_account": resolved_ledger_account_key,
        "foreign_amount": new_foreign,
        "notes": new_notes,
        "rc_type": new_rc_type,
        "vat_input": new_vat_input,
        "vat_output": new_vat_output,
        "vat_rate": new_vat_rate,
        "vat_code": new_vat_code,
        "entertainment_tip_eur": new_entertainment_tip,
        "entertainment_vat_status": new_entertainment_status,
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
        category_eur_key=resolved_category_key,
        account=new_account,
        ledger_account=resolved_ledger_account_key,
        receipt_name=new_receipt,
        invoice_number=new_invoice_number,
        foreign_amount=new_foreign,
        notes=new_notes,
        rc_type=new_rc_type,
        vat_input=new_vat_input,
        vat_output=new_vat_output,
        vat_rate=new_vat_rate,
        vat_code=new_vat_code,
        entertainment_tip_eur=new_entertainment_tip,
        entertainment_vat_status=new_entertainment_status,
        is_private_paid=new_is_private_paid,
        private_classification=new_private_classification,
        hash=new_hash,
    )


def delete_expense(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    audit_user: str,
    purge: bool = False,
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

    if not purge and row["deleted_at"] is not None:
        raise RecordNotFoundError(
            f"Ausgabe #{record_id} ist bereits gelöscht.",
            code="expense_already_deleted",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)
    record_uuid = row["uuid"]

    if purge:
        conn.execute("DELETE FROM expenses WHERE id = ?", (record_id,))
        log_audit(
            conn,
            "expenses",
            record_id,
            "DELETE",
            record_uuid=record_uuid,
            old_data=old_data,
            new_data={"purged": True},
            user=audit_user,
        )
    else:
        conn.execute(
            "UPDATE expenses SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (record_id,),
        )
        log_audit(
            conn,
            "expenses",
            record_id,
            "DELETE",
            record_uuid=record_uuid,
            old_data=old_data,
            new_data={"deleted_at": "CURRENT_TIMESTAMP"},
            user=audit_user,
        )

    if auto_commit:
        conn.commit()


def restore_expense(
    conn: sqlite3.Connection,
    *,
    record_id: int,
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
    if row["deleted_at"] is None:
        raise ValidationError(
            f"Ausgabe #{record_id} ist nicht gelöscht.",
            code="expense_not_deleted",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)
    record_uuid = row["uuid"]

    conn.execute(
        "UPDATE expenses SET deleted_at = NULL WHERE id = ?",
        (record_id,),
    )
    log_audit(
        conn,
        "expenses",
        record_id,
        "UPDATE",
        record_uuid=record_uuid,
        old_data=old_data,
        new_data={"deleted_at": None},
        user=audit_user,
    )

    if auto_commit:
        conn.commit()

    return get_expense_detail(conn, record_id)
