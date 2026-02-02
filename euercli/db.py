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


def resolve_incomplete_entries(
    conn: sqlite3.Connection,
    row_type: str,
    date: str,
    party: str,
    amount_eur: float,
    receipt_name: str | None,
    user: str = DEFAULT_USER,
) -> int:
    """Entfernt passende unvollständige Einträge und schreibt Audit-Logs."""
    rows = conn.execute(
        """SELECT *
           FROM incomplete_entries
           WHERE type = ?
             AND date = ?
             AND amount_eur = ?
             AND LOWER(party) = LOWER(?)""",
        (row_type, date, amount_eur, party),
    ).fetchall()

    resolved = 0
    for row in rows:
        if row["receipt_name"] and receipt_name:
            if row["receipt_name"] != receipt_name:
                continue
        old_data = row_to_dict(row)
        conn.execute("DELETE FROM incomplete_entries WHERE id = ?", (row["id"],))
        log_audit(
            conn,
            "incomplete_entries",
            row["id"],
            "DELETE",
            old_data=old_data,
            user=user,
        )
        resolved += 1

    return resolved


def has_matching_transaction(
    conn: sqlite3.Connection,
    row_type: str,
    date: str,
    party: str,
    amount_eur: float,
    receipt_name: str | None,
) -> bool:
    """Prüft ob eine passende Buchung existiert (für Auto-Resolve)."""
    if row_type == "expense":
        if receipt_name:
            row = conn.execute(
                """SELECT id FROM expenses
                   WHERE date = ?
                     AND amount_eur = ?
                     AND LOWER(vendor) = LOWER(?)
                     AND receipt_name = ?""",
                (date, amount_eur, party, receipt_name),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT id FROM expenses
                   WHERE date = ?
                     AND amount_eur = ?
                     AND LOWER(vendor) = LOWER(?)""",
                (date, amount_eur, party),
            ).fetchone()
    else:
        if receipt_name:
            row = conn.execute(
                """SELECT id FROM income
                   WHERE date = ?
                     AND amount_eur = ?
                     AND LOWER(source) = LOWER(?)
                     AND receipt_name = ?""",
                (date, amount_eur, party, receipt_name),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT id FROM income
                   WHERE date = ?
                     AND amount_eur = ?
                     AND LOWER(source) = LOWER(?)""",
                (date, amount_eur, party),
            ).fetchone()
    return row is not None


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
