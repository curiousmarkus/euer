import json
import sqlite3
from pathlib import Path
from typing import Optional

from .constants import DEFAULT_USER


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """Erstellt eine Datenbankverbindung mit Row-Factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def log_audit(
    conn: sqlite3.Connection,
    table_name: str,
    record_id: int,
    action: str,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
    user: str = DEFAULT_USER,
) -> None:
    """Schreibt einen Audit-Log-Eintrag."""
    conn.execute(
        """INSERT INTO audit_log (table_name, record_id, action, old_data, new_data, user)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            table_name,
            record_id,
            action,
            json.dumps(old_data, ensure_ascii=False) if old_data else None,
            json.dumps(new_data, ensure_ascii=False) if new_data else None,
            user,
        ),
    )


def get_category_id(
    conn: sqlite3.Connection, name: str, cat_type: str
) -> Optional[int]:
    """Sucht Kategorie-ID nach Name (case-insensitive)."""
    row = conn.execute(
        "SELECT id FROM categories WHERE LOWER(name) = LOWER(?) AND type = ?",
        (name, cat_type),
    ).fetchone()
    return row["id"] if row else None


def get_category_name_with_line(conn: sqlite3.Connection, category_id: int) -> str:
    """Gibt Kategorie-Name mit EÜR-Zeile zurück, z.B. 'Laufende EDV-Kosten (51)'."""
    row = conn.execute(
        "SELECT name, eur_line FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if not row:
        return "Unbekannt"
    if row["eur_line"]:
        return f"{row['name']} ({row['eur_line']})"
    return row["name"]


def row_to_dict(row: sqlite3.Row) -> dict:
    """Konvertiert sqlite3.Row zu dict."""
    return dict(row)
