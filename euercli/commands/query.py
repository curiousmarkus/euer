import csv
import re
import sqlite3
import sys
from pathlib import Path


FORBIDDEN_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "vacuum",
    "pragma",
    "attach",
    "detach",
    "reindex",
    "begin",
    "commit",
    "rollback",
}


def _normalize_sql(raw_sql: str) -> str:
    sql = raw_sql.strip()
    if not sql:
        raise ValueError("Keine SQL-Query angegeben.")

    if sql.endswith(";"):
        sql = sql[:-1].strip()

    if ";" in sql:
        raise ValueError("Nur eine einzelne SELECT-Query erlaubt.")

    lowered = sql.lstrip().lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Nur SELECT-Queries sind erlaubt.")

    if lowered.startswith("with") and "select" not in lowered:
        raise ValueError("CTE muss eine SELECT-Query enthalten.")

    scan_sql = re.sub(r"'(?:''|[^'])*'", "''", lowered)
    scan_sql = re.sub(r'"(?:\"\"|[^"])*"', '""', scan_sql)
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\\b{keyword}\\b", scan_sql):
            raise ValueError("Nur SELECT-Queries sind erlaubt.")

    return sql


def _get_readonly_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_query(args):
    """Führt eine SQL-SELECT-Query aus (nur lesend)."""
    raw_sql = " ".join(args.sql).strip()
    try:
        sql = _normalize_sql(raw_sql)
    except ValueError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db)
    try:
        conn = _get_readonly_connection(db_path)
    except sqlite3.Error as exc:
        print(f"Fehler: Datenbank konnte nicht geöffnet werden: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        cursor = conn.execute(sql)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        writer = csv.writer(sys.stdout)
        if columns:
            writer.writerow(columns)
        for row in cursor.fetchall():
            writer.writerow([row[col] for col in columns])
    except sqlite3.Error as exc:
        print(f"Fehler: SQL-Query fehlgeschlagen: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()
