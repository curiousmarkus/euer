from __future__ import annotations

import sqlite3
import uuid

from ..db import log_audit, row_to_dict
from ..utils import compute_hash
from .categories import get_category_by_name, resolve_ledger_account
from .duplicates import DuplicateAction, find_exact_duplicate
from .errors import RecordNotFoundError, ValidationError
from .eur import category_key_for_name, is_small_business_subset
from .models import Income, LedgerAccount
from .utils import get_optional, hash_date, resolve_dates
from .validation import (
    DEFAULT_AMOUNT_THRESHOLD,
    check_fuzzy_duplicate,
    validate_amount_threshold,
    validate_date_plausibility,
    validate_vat_math,
)
from .vat import (
    INCOME_CODE_BY_RATE,
    INCOME_RATE_BY_CODE,
    INCOME_VAT_CODES,
    OUTPUT_TAX_FREE_NO_VORSTEUER,
    included_vat_from_gross,
    validate_vat_code,
    validate_vat_rate,
)


def _row_to_income(row: sqlite3.Row) -> Income:
    return Income(
        id=row["id"],
        uuid=row["uuid"],
        payment_date=get_optional(row, "payment_date"),
        invoice_date=get_optional(row, "invoice_date"),
        source=row["source"],
        amount_eur=row["amount_eur"],
        category_id=get_optional(row, "category_id"),
        category_name=get_optional(row, "category_name"),
        category_eur_line=None,
        category_eur_key=get_optional(row, "category_eur_key"),
        ledger_account=get_optional(row, "ledger_account"),
        receipt_name=get_optional(row, "receipt_name"),
        invoice_number=get_optional(row, "invoice_number"),
        foreign_amount=get_optional(row, "foreign_amount"),
        notes=get_optional(row, "notes"),
        vat_output=get_optional(row, "vat_output"),
        vat_rate=get_optional(row, "vat_rate"),
        vat_code=get_optional(row, "vat_code"),
        hash=get_optional(row, "hash"),
        deleted_at=get_optional(row, "deleted_at"),
    )


def _validate_tax_mode(tax_mode: str) -> None:
    if tax_mode not in {"small_business", "standard"}:
        raise ValidationError(
            f"Unbekannter Steuermodus: {tax_mode}",
            code="invalid_tax_mode",
            details={"tax_mode": tax_mode},
        )


def _resolve_income_vat_classification(
    *,
    amount_eur: float,
    tax_mode: str,
    legacy_vat: float | None,
    vat_output: float | None,
    vat_rate: float | None,
    vat_code: str | None,
    tax_free: bool,
    skip_vat_auto: bool,
) -> tuple[float | None, float | None, str | None]:
    _validate_tax_mode(tax_mode)

    manual_vat_output = vat_output if vat_output is not None else legacy_vat
    if tax_free and (vat_rate is not None or legacy_vat is not None):
        raise ValidationError(
            "--tax-free darf nicht mit --vat-rate oder --vat kombiniert werden.",
            code="tax_free_conflict",
        )
    if tax_free and vat_code not in {None, OUTPUT_TAX_FREE_NO_VORSTEUER}:
        raise ValidationError(
            "--tax-free widerspricht der angegebenen Steuerklasse.",
            code="tax_free_vat_code_conflict",
            details={"vat_code": vat_code},
        )
    if tax_free and manual_vat_output not in {None, 0, 0.0}:
        raise ValidationError(
            "Steuerfreie Einnahmen dürfen keine Umsatzsteuer enthalten.",
            code="tax_free_vat_output_conflict",
        )

    resolved_rate = validate_vat_rate(vat_rate)
    resolved_code = validate_vat_code(vat_code, INCOME_VAT_CODES)

    if tax_free:
        return 0.0, 0.0, OUTPUT_TAX_FREE_NO_VORSTEUER

    if resolved_code is not None:
        code_rate = INCOME_RATE_BY_CODE[resolved_code]
        if resolved_rate is not None and resolved_rate != code_rate:
            raise ValidationError(
                "Steuersatz passt nicht zur Steuerklasse.",
                code="vat_rate_code_mismatch",
                details={"vat_rate": resolved_rate, "vat_code": resolved_code},
            )
        resolved_rate = code_rate
    elif resolved_rate is not None:
        resolved_code = INCOME_CODE_BY_RATE[resolved_rate]
    elif tax_mode == "small_business":
        if manual_vat_output not in {None, 0, 0.0}:
            return None, float(manual_vat_output), None
        resolved_rate = 0.0
        resolved_code = OUTPUT_TAX_FREE_NO_VORSTEUER
    else:
        resolved_rate = 19.0
        resolved_code = INCOME_CODE_BY_RATE[resolved_rate]

    if resolved_code == OUTPUT_TAX_FREE_NO_VORSTEUER:
        if manual_vat_output not in {None, 0, 0.0}:
            raise ValidationError(
                "Steuerfreie Einnahmen dürfen keine Umsatzsteuer enthalten.",
                code="tax_free_vat_output_conflict",
            )
        return resolved_rate, 0.0, resolved_code

    if resolved_rate == 0.0:
        resolved_vat_output = float(manual_vat_output or 0.0)
    elif manual_vat_output is not None:
        resolved_vat_output = float(manual_vat_output)
    elif skip_vat_auto:
        resolved_vat_output = None
    else:
        resolved_vat_output = included_vat_from_gross(amount_eur, resolved_rate)

    return resolved_rate, resolved_vat_output, resolved_code


def _resolve_income_category(
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
            "income",
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
        category = get_category_by_name(conn, resolved_category_name, "income")
        if not category:
            raise ValidationError(
                f"Kategorie '{resolved_category_name}' nicht gefunden.",
                code="category_not_found",
                details={"category": resolved_category_name, "type": "income"},
            )
        category_id = category.id
        resolved_category_name = category.name
        resolved_category_key = category.eur_key or category_key_for_name(
            category.name,
            "income",
        )

    return category_id, resolved_category_name, resolved_ledger_account_key, resolved_category_key


def create_income(
    conn: sqlite3.Connection,
    *,
    source: str,
    amount_eur: float,
    payment_date: str | None = None,
    invoice_date: str | None = None,
    date: str | None = None,
    category_name: str | None = None,
    ledger_account_key: str | None = None,
    ledger_accounts: list[LedgerAccount] | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    invoice_number: str | None = None,
    notes: str | None = None,
    vat: float | None = None,
    vat_output: float | None = None,
    vat_rate: float | None = None,
    vat_code: str | None = None,
    tax_free: bool = False,
    tax_mode: str = "small_business",
    audit_user: str = "default",
    skip_vat_auto: bool = False,
    on_duplicate: DuplicateAction = DuplicateAction.RAISE,
    force: bool = False,
    allow_duplicate: bool = False,
    amount_threshold: float = DEFAULT_AMOUNT_THRESHOLD,
    auto_commit: bool = True,
) -> Income | None:
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
    ) = _resolve_income_category(
        conn,
        category_name=category_name,
        ledger_account_key=ledger_account_key,
        ledger_accounts=ledger_accounts,
    )

    resolved_vat_rate, resolved_vat_output, resolved_vat_code = _resolve_income_vat_classification(
        amount_eur=amount_eur,
        tax_mode=tax_mode,
        legacy_vat=vat,
        vat_output=vat_output,
        vat_rate=vat_rate,
        vat_code=vat_code,
        tax_free=tax_free,
        skip_vat_auto=skip_vat_auto,
    )

    if (
        vat_rate is not None
        and vat_rate in (7.0, 19.0)
        and (vat is not None or vat_output is not None)
        and not tax_free
    ):
        raw_vat = vat if vat is not None else vat_output
        validate_vat_math(
            amount_eur=amount_eur,
            vat_rate=vat_rate,
            vat_amount=raw_vat,
        )

    if is_small_business_subset(resolved_category_key):
        if tax_mode != "small_business":
            raise ValidationError(
                "Zeile 13 ist ein Unterfeld für nicht steuerbare Kleinunternehmerumsätze.",
                code="small_business_subset_requires_small_business_mode",
            )
        if resolved_vat_output not in {None, 0, 0.0}:
            raise ValidationError(
                "Das Zeile-13-Unterfeld darf keine Umsatzsteuer enthalten.",
                code="small_business_subset_vat_conflict",
            )

    invoice_number = invoice_number.strip() or None if invoice_number is not None else None
    tx_hash = compute_hash(
        hash_date(resolved_payment_date, resolved_invoice_date),
        source,
        amount_eur,
        receipt_name or "",
        invoice_number,
    )
    existing_id = find_exact_duplicate(
        conn,
        table_name="income",
        payment_date=resolved_payment_date,
        invoice_date=resolved_invoice_date,
        party=source,
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
            table_name="income",
            name=source,
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
            table_name="income",
            name=source,
            amount_eur=amount_eur,
            date_val=resolved_payment_date or resolved_invoice_date,
            invoice_number=invoice_number.strip() or None if invoice_number else None,
            invoice_date=resolved_invoice_date,
            receipt_name=receipt_name,
            allow_duplicate=allow_duplicate,
            force=force,
        )

    record_uuid = str(uuid.uuid4())

    cursor = conn.execute(
        """INSERT INTO income
           (uuid, receipt_name, payment_date, invoice_date, invoice_number, source, category_id, amount_eur,
            ledger_account, foreign_amount, notes, vat_output, vat_rate, vat_code, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_uuid,
            receipt_name,
            resolved_payment_date,
            resolved_invoice_date,
            invoice_number,
            source,
            category_id,
            amount_eur,
            resolved_ledger_account_key,
            foreign_amount,
            notes,
            resolved_vat_output,
            resolved_vat_rate,
            resolved_vat_code,
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
        "source": source,
        "category_id": category_id,
        "amount_eur": amount_eur,
        "ledger_account": resolved_ledger_account_key,
        "foreign_amount": foreign_amount,
        "notes": notes,
        "vat_output": resolved_vat_output,
        "vat_rate": resolved_vat_rate,
        "vat_code": resolved_vat_code,
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

    if auto_commit:
        conn.commit()

    return Income(
        id=record_id,
        uuid=record_uuid,
        payment_date=resolved_payment_date,
        invoice_date=resolved_invoice_date,
        source=source,
        amount_eur=amount_eur,
        category_id=category_id,
        category_name=resolved_category_name,
        category_eur_key=resolved_category_key,
        ledger_account=resolved_ledger_account_key,
        receipt_name=receipt_name,
        invoice_number=invoice_number,
        foreign_amount=foreign_amount,
        notes=notes,
        vat_output=resolved_vat_output,
        vat_rate=resolved_vat_rate,
        vat_code=resolved_vat_code,
        hash=tx_hash,
    )


def list_income(
    conn: sqlite3.Connection,
    *,
    year: int | None = None,
    month: int | None = None,
    category_name: str | None = None,
    include_deleted: bool = False,
    trash_only: bool = False,
) -> list[Income]:
    query = """
        SELECT i.id, i.uuid, i.payment_date, i.invoice_date, i.source, i.category_id,
               c.name as category_name,
               c.eur_key as category_eur_key,
               i.amount_eur, i.ledger_account, i.receipt_name, i.invoice_number,
               i.foreign_amount, i.notes, i.vat_output, i.vat_rate, i.vat_code, i.hash,
               i.deleted_at
        FROM income i
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE 1=1
    """
    params: list[object] = []

    if trash_only:
        query += " AND i.deleted_at IS NOT NULL"
    elif not include_deleted:
        query += " AND i.deleted_at IS NULL"

    if year:
        query += " AND strftime('%Y', COALESCE(i.payment_date, i.invoice_date)) = ?"
        params.append(str(year))
    if month:
        query += " AND strftime('%m', COALESCE(i.payment_date, i.invoice_date)) = ?"
        params.append(f"{month:02d}")
    if category_name:
        query += " AND LOWER(c.name) = LOWER(?)"
        params.append(category_name)

    query += " ORDER BY COALESCE(i.payment_date, i.invoice_date) DESC, i.id DESC"

    rows = conn.execute(query, params).fetchall()
    return [_row_to_income(row) for row in rows]


def get_income_detail(
    conn: sqlite3.Connection,
    record_id: int,
    include_deleted: bool = False,
) -> Income:
    query = """SELECT i.id, i.uuid, i.payment_date, i.invoice_date, i.source, i.category_id,
                  c.name as category_name,
                  c.eur_key as category_eur_key,
                  i.amount_eur, i.ledger_account, i.receipt_name, i.invoice_number,
                  i.foreign_amount, i.notes, i.vat_output, i.vat_rate, i.vat_code, i.hash,
                  i.deleted_at
           FROM income i
           LEFT JOIN categories c ON i.category_id = c.id
           WHERE i.id = ?"""
    if not include_deleted:
        query += " AND i.deleted_at IS NULL"

    row = conn.execute(query, (record_id,)).fetchone()
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
    payment_date: str | None = None,
    invoice_date: str | None = None,
    date: str | None = None,
    source: str | None = None,
    category_name: str | None = None,
    ledger_account_key: str | None = None,
    ledger_accounts: list[LedgerAccount] | None = None,
    amount_eur: float | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    invoice_number: str | None = None,
    notes: str | None = None,
    vat: float | None = None,
    vat_rate: float | None = None,
    vat_code: str | None = None,
    tax_free: bool = False,
    tax_mode: str,
    audit_user: str,
    force: bool = False,
    allow_duplicate: bool = False,
    amount_threshold: float = DEFAULT_AMOUNT_THRESHOLD,
    auto_commit: bool = True,
) -> Income:
    row = conn.execute(
        "SELECT * FROM income WHERE id = ?",
        (record_id,),
    ).fetchone()
    if not row or (row["deleted_at"] is not None):
        raise RecordNotFoundError(
            f"Einnahme #{record_id} nicht gefunden.",
            code="income_not_found",
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

    new_source = source if source else row["source"]
    new_amount = amount_eur if amount_eur is not None else row["amount_eur"]
    new_foreign = foreign_amount if foreign_amount is not None else row["foreign_amount"]
    new_notes = notes if notes is not None else row["notes"]
    new_vat_output = row["vat_output"]
    new_vat_rate = get_optional(row, "vat_rate")
    new_vat_code = get_optional(row, "vat_code")

    explicit_tax_change = (
        vat is not None or vat_rate is not None or vat_code is not None or tax_free
    )
    recalc_existing_tax = (
        amount_eur is not None
        and not explicit_tax_change
        and new_vat_code in INCOME_RATE_BY_CODE
        and new_vat_code != OUTPUT_TAX_FREE_NO_VORSTEUER
    )
    if explicit_tax_change or recalc_existing_tax:
        if explicit_tax_change:
            base_vat_rate = vat_rate
            base_vat_code = vat_code
            if vat is not None and vat_rate is None and vat_code is None and not tax_free:
                base_vat_rate = new_vat_rate
                base_vat_code = new_vat_code
        else:
            base_vat_rate = new_vat_rate
            base_vat_code = new_vat_code

        new_vat_rate, new_vat_output, new_vat_code = _resolve_income_vat_classification(
            amount_eur=new_amount,
            tax_mode=tax_mode,
            legacy_vat=vat,
            vat_output=None,
            vat_rate=base_vat_rate,
            vat_code=base_vat_code,
            tax_free=tax_free,
            skip_vat_auto=False,
        )

        if vat_rate is not None and vat_rate in (7.0, 19.0) and vat is not None and not tax_free:
            validate_vat_math(
                amount_eur=new_amount,
                vat_rate=vat_rate,
                vat_amount=vat,
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
                "income",
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
        ) = _resolve_income_category(
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
                    "income",
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
            category = get_category_by_name(conn, category_name, "income")
            if not category:
                raise ValidationError(
                    f"Kategorie '{category_name}' nicht gefunden.",
                    code="category_not_found",
                    details={"category": category_name, "type": "income"},
                )
            category_id = category.id
            resolved_category_name = category.name
            resolved_category_key = category.eur_key or category_key_for_name(
                category.name,
                "income",
            )

    if is_small_business_subset(resolved_category_key):
        if tax_mode != "small_business" and (
            resolved_category_key != existing_category_key or explicit_tax_change
        ):
            raise ValidationError(
                "Zeile 13 ist ein Unterfeld für nicht steuerbare Kleinunternehmerumsätze.",
                code="small_business_subset_requires_small_business_mode",
            )
        if new_vat_output not in {None, 0, 0.0}:
            raise ValidationError(
                "Das Zeile-13-Unterfeld darf keine Umsatzsteuer enthalten.",
                code="small_business_subset_vat_conflict",
            )

    if (
        source is not None
        or amount_eur is not None
        or payment_date is not None
        or invoice_date is not None
        or invoice_number is not None
    ):
        check_fuzzy_duplicate(
            conn,
            table_name="income",
            name=new_source,
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
        new_source,
        new_amount,
        new_receipt or "",
        new_invoice_number,
    )

    conn.execute(
        """UPDATE income SET
           receipt_name = ?, payment_date = ?, invoice_date = ?, invoice_number = ?, source = ?,
           category_id = ?, amount_eur = ?,
           ledger_account = ?, foreign_amount = ?, notes = ?,
           vat_output = ?, vat_rate = ?, vat_code = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_payment_date,
            new_invoice_date,
            new_invoice_number,
            new_source,
            category_id,
            new_amount,
            resolved_ledger_account_key,
            new_foreign,
            new_notes,
            new_vat_output,
            new_vat_rate,
            new_vat_code,
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
        "source": new_source,
        "category_id": category_id,
        "amount_eur": new_amount,
        "ledger_account": resolved_ledger_account_key,
        "foreign_amount": new_foreign,
        "notes": new_notes,
        "vat_output": new_vat_output,
        "vat_rate": new_vat_rate,
        "vat_code": new_vat_code,
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

    if auto_commit:
        conn.commit()

    return Income(
        id=record_id,
        uuid=record_uuid,
        payment_date=new_payment_date,
        invoice_date=new_invoice_date,
        source=new_source,
        amount_eur=new_amount,
        category_id=category_id,
        category_name=resolved_category_name,
        category_eur_key=resolved_category_key,
        ledger_account=resolved_ledger_account_key,
        receipt_name=new_receipt,
        invoice_number=new_invoice_number,
        foreign_amount=new_foreign,
        notes=new_notes,
        vat_output=new_vat_output,
        vat_rate=new_vat_rate,
        vat_code=new_vat_code,
        hash=new_hash,
    )


def delete_income(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    audit_user: str,
    purge: bool = False,
    auto_commit: bool = True,
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

    if not purge and row["deleted_at"] is not None:
        raise RecordNotFoundError(
            f"Einnahme #{record_id} ist bereits gelöscht.",
            code="income_already_deleted",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)
    record_uuid = row["uuid"]

    if purge:
        conn.execute("DELETE FROM income WHERE id = ?", (record_id,))
        log_audit(
            conn,
            "income",
            record_id,
            "DELETE",
            record_uuid=record_uuid,
            old_data=old_data,
            new_data={"purged": True},
            user=audit_user,
        )
    else:
        conn.execute(
            "UPDATE income SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (record_id,),
        )
        log_audit(
            conn,
            "income",
            record_id,
            "DELETE",
            record_uuid=record_uuid,
            old_data=old_data,
            new_data={"deleted_at": "CURRENT_TIMESTAMP"},
            user=audit_user,
        )

    if auto_commit:
        conn.commit()


def restore_income(
    conn: sqlite3.Connection,
    *,
    record_id: int,
    audit_user: str,
    auto_commit: bool = True,
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
    if row["deleted_at"] is None:
        raise ValidationError(
            f"Einnahme #{record_id} ist nicht gelöscht.",
            code="income_not_deleted",
            details={"id": record_id},
        )

    old_data = row_to_dict(row)
    record_uuid = row["uuid"]

    conn.execute(
        "UPDATE income SET deleted_at = NULL WHERE id = ?",
        (record_id,),
    )
    log_audit(
        conn,
        "income",
        record_id,
        "UPDATE",
        record_uuid=record_uuid,
        old_data=old_data,
        new_data={"deleted_at": None},
        user=audit_user,
    )

    if auto_commit:
        conn.commit()

    return get_income_detail(conn, record_id)
