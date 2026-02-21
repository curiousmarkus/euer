from __future__ import annotations

import sqlite3


def get_optional(row: sqlite3.Row, key: str):
    return row[key] if key in row.keys() else None
