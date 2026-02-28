from __future__ import annotations

import sqlite3

from .errors import ValidationError
from .models import Category, LedgerAccount


def _row_to_category(row: sqlite3.Row) -> Category:
    return Category(
        id=row["id"],
        uuid=row["uuid"],
        name=row["name"],
        eur_line=row["eur_line"],
        type=row["type"],
    )


def get_category_list(conn: sqlite3.Connection, cat_type: str | None = None) -> list[Category]:
    query = "SELECT id, uuid, name, eur_line, type FROM categories"
    params: list[object] = []
    if cat_type:
        query += " WHERE type = ?"
        params.append(cat_type)
    query += " ORDER BY type, eur_line, name"
    rows = conn.execute(query, params).fetchall()
    return [_row_to_category(row) for row in rows]


def get_category_by_name(
    conn: sqlite3.Connection,
    name: str,
    cat_type: str,
) -> Category | None:
    row = conn.execute(
        "SELECT id, uuid, name, eur_line, type FROM categories WHERE LOWER(name) = LOWER(?) AND type = ?",
        (name, cat_type),
    ).fetchone()
    if not row:
        return None
    return _row_to_category(row)


def get_ledger_accounts_for_category(
    category_name: str,
    ledger_accounts: list[LedgerAccount],
) -> list[LedgerAccount]:
    return [
        ledger_account
        for ledger_account in ledger_accounts
        if ledger_account.category.lower() == category_name.lower()
    ]


def resolve_ledger_account(
    conn: sqlite3.Connection,
    key: str,
    ledger_accounts: list[LedgerAccount],
    expected_type: str,
) -> LedgerAccount:
    for ledger_account in ledger_accounts:
        if ledger_account.key.lower() == key.lower():
            category = get_category_by_name(conn, ledger_account.category, expected_type)
            if category:
                return LedgerAccount(
                    key=ledger_account.key,
                    name=ledger_account.name,
                    category=category.name,
                    account_number=ledger_account.account_number,
                )

            category_row = conn.execute(
                "SELECT type FROM categories WHERE LOWER(name) = LOWER(?)",
                (ledger_account.category,),
            ).fetchone()
            if not category_row:
                raise ValidationError(
                    f"Kategorie '{ledger_account.category}' für Buchungskonto "
                    f"'{ledger_account.key}' nicht gefunden.",
                    code="category_not_found",
                    details={
                        "category": ledger_account.category,
                        "ledger_account": ledger_account.key,
                        "type": expected_type,
                    },
                )

            raise ValidationError(
                f"Buchungskonto '{ledger_account.key}' gehört nicht zu einer "
                f"{'Ausgabe' if expected_type == 'expense' else 'Einnahme'}.",
                code="ledger_account_type_mismatch",
                details={
                    "ledger_account": ledger_account.key,
                    "expected_type": expected_type,
                    "actual_type": category_row["type"],
                },
            )

    raise ValidationError(
        f"Buchungskonto '{key}' nicht gefunden.",
        code="ledger_account_not_found",
        details={"ledger_account": key, "expected_type": expected_type},
    )
