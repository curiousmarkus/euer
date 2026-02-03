from __future__ import annotations

import sqlite3

from .models import Category


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
