#!/usr/bin/env python3
"""
EÜR (Einnahmenüberschussrechnung) - Buchungs-Ledger CLI

SQLite-basierte Buchhaltung für Kleinunternehmer.
Ersetzt Excel-basierte EÜR durch saubere Datenbank mit Audit-Trail.
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Optional

# Optional: openpyxl für XLSX-Export
try:
    import openpyxl

    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# =============================================================================
# Konfiguration
# =============================================================================

DEFAULT_DB_PATH = Path(__file__).parent / "euer.db"
DEFAULT_EXPORT_DIR = Path(__file__).parent / "exports"
DEFAULT_USER = "markus"
CONFIG_PATH = Path.home() / ".config" / "euer" / "config.toml"

# Seed-Kategorien für init
SEED_CATEGORIES = [
    ("Telekommunikation", 44, "expense"),
    ("Laufende EDV-Kosten", 51, "expense"),
    ("Arbeitsmittel", 52, "expense"),
    ("Werbekosten", 54, "expense"),
    ("Gezahlte USt", 58, "expense"),
    ("Übrige Betriebsausgaben", 60, "expense"),
    ("Bewirtungsaufwendungen", 63, "expense"),
    ("Sonstige betriebsfremde Einnahme", None, "income"),
    ("Umsatzsteuerpflichtige Betriebseinnahmen", 14, "income"),
]

# =============================================================================
# Schema
# =============================================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    eur_line INTEGER,
    type TEXT NOT NULL CHECK(type IN ('expense', 'income'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_name_type ON categories(name, type);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_name TEXT,
    date DATE NOT NULL,
    vendor TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    amount_eur REAL NOT NULL,
    account TEXT,
    foreign_amount TEXT,
    notes TEXT,
    is_rc INTEGER NOT NULL DEFAULT 0,
    vat_amount REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash TEXT UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
CREATE INDEX IF NOT EXISTS idx_expenses_vendor ON expenses(vendor);

CREATE TABLE IF NOT EXISTS income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_name TEXT,
    date DATE NOT NULL,
    source TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    amount_eur REAL NOT NULL,
    foreign_amount TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash TEXT UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_income_date ON income(date);
CREATE INDEX IF NOT EXISTS idx_income_category ON income(category_id);

CREATE TABLE IF NOT EXISTS incomplete_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('expense', 'income', 'unknown')),
    date DATE,
    party TEXT,
    category_name TEXT,
    amount_eur REAL,
    account TEXT,
    foreign_amount TEXT,
    receipt_name TEXT,
    notes TEXT,
    is_rc INTEGER NOT NULL DEFAULT 0,
    vat_amount REAL,
    raw_data TEXT,
    missing_fields TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incomplete_type ON incomplete_entries(type);
CREATE INDEX IF NOT EXISTS idx_incomplete_date ON incomplete_entries(date);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('INSERT', 'UPDATE', 'DELETE', 'MIGRATE')),
    old_data TEXT,
    new_data TEXT,
    user TEXT NOT NULL DEFAULT 'markus'
);

CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
"""

# =============================================================================
# Hilfsfunktionen
# =============================================================================


def compute_hash(
    date: str, vendor_or_source: str, amount_eur: float, receipt_name: str = ""
) -> str:
    """Erzeugt einen eindeutigen Hash für eine Transaktion."""
    data = f"{date}|{vendor_or_source}|{amount_eur:.2f}|{receipt_name or ''}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """Erstellt eine Datenbankverbindung mit Row-Factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def format_amount(amount: float) -> str:
    """Formatiert einen Betrag mit deutschem Zahlenformat."""
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_bool(value: object) -> bool:
    """Parst verschiedene Wahrheitswerte."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "ja", "j"}


def parse_amount(value: object) -> float | None:
    """Parst Betrag (unterstützt deutsches und internationales Format)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None

    text = text.replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def get_row_value(row: dict, *keys: str) -> object | None:
    """Liest den ersten nicht-leeren Wert aus einem Dict."""
    for key in keys:
        if key in row:
            value = row[key]
        else:
            bom_key = f"\ufeff{key}"
            if bom_key not in row:
                continue
            value = row[bom_key]
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                continue
        return value
    return None


def parse_import_type(value: object) -> str | None:
    """Normalisiert Typ-Angaben auf 'expense' oder 'income'."""
    if value is None:
        return None
    text = str(value).strip().lower()
    mapping = {
        "expense": "expense",
        "expenses": "expense",
        "ausgabe": "expense",
        "ausgaben": "expense",
        "debit": "expense",
        "outflow": "expense",
        "outgoing": "expense",
        "income": "income",
        "einnahme": "income",
        "einnahmen": "income",
        "credit": "income",
        "inflow": "income",
        "incoming": "income",
    }
    return mapping.get(text)


def normalize_import_row(row: dict) -> dict:
    """Normalisiert Importzeile auf kanonische Keys."""
    raw_type = get_row_value(row, "type", "kind", "direction")
    amount_value = get_row_value(row, "amount_eur", "amount")
    amount = parse_amount(amount_value)

    row_type = parse_import_type(raw_type)
    if not row_type and amount is not None:
        if amount < 0:
            row_type = "expense"
        elif amount > 0:
            row_type = "income"

    return {
        "type": row_type,
        "date": get_row_value(row, "date"),
        "party": get_row_value(row, "party", "vendor", "source", "counterparty"),
        "category": get_row_value(row, "category", "category_name"),
        "amount_eur": amount,
        "account": get_row_value(row, "account"),
        "foreign_amount": get_row_value(row, "foreign_amount", "foreign"),
        "receipt_name": get_row_value(row, "receipt_name", "receipt"),
        "notes": get_row_value(row, "notes"),
        "rc": parse_bool(get_row_value(row, "rc")),
        "vat_amount": parse_amount(get_row_value(row, "vat_amount")),
        "raw_data": row,
    }


def format_missing_fields(value: str | None) -> str:
    """Formatiert fehlende Felder für die Anzeige."""
    if not value:
        return ""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, list):
        return ", ".join(str(item) for item in parsed)
    return str(parsed)


def log_audit(
    conn: sqlite3.Connection,
    table_name: str,
    record_id: int,
    action: str,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
    user: str = DEFAULT_USER,
):
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


def load_config() -> dict:
    """Lädt Config, gibt leeres Dict zurück wenn nicht vorhanden."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def toml_escape(value: str) -> str:
    """Escaped String für TOML."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def toml_format_value(value: object) -> str:
    """Formatiert einfache TOML-Werte."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value}"
    if isinstance(value, str):
        return f"\"{toml_escape(value)}\""
    if isinstance(value, list):
        inner = ", ".join(toml_format_value(v) for v in value)
        return f"[{inner}]"
    return f"\"{toml_escape(str(value))}\""


def dump_toml(config: dict) -> str:
    """Erzeugt TOML aus einer flachen Config-Struktur."""
    lines = []
    for section, value in config.items():
        if isinstance(value, dict):
            lines.append(f"[{section}]")
            for key, val in value.items():
                lines.append(f"{key} = {toml_format_value(val)}")
            lines.append("")
        else:
            lines.append(f"{section} = {toml_format_value(value)}")
    return "\n".join(lines).rstrip() + "\n"


def save_config(config: dict) -> None:
    """Schreibt Config nach ~/.config/euer/config.toml."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(dump_toml(config))


def prompt_path(label: str, default: str | None) -> str:
    """Fragt interaktiv einen Pfad ab."""
    prompt = f"{label}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    try:
        value = input(prompt).strip()
    except EOFError:
        print("\nAbgebrochen.", file=sys.stderr)
        sys.exit(1)
    if not value and default is not None:
        return default
    return value


def normalize_receipt_path(value: str) -> str:
    """Normalisiert Pfad-Eingaben."""
    if not value:
        return ""
    cleaned = value
    if (
        (cleaned.startswith('"') and cleaned.endswith('"'))
        or (cleaned.startswith("'") and cleaned.endswith("'"))
    ):
        cleaned = cleaned[1:-1]
    return str(Path(cleaned).expanduser())


def iter_import_rows(path: str, fmt: str) -> list[dict]:
    """Lädt Importdaten aus Datei oder stdin."""
    rows: list[dict] = []
    if path == "-":
        stream = sys.stdin
        if fmt == "csv":
            reader = csv.DictReader(stream)
            rows.extend(reader)
        else:
            for line in stream:
                if not line.strip():
                    continue
                rows.append(json.loads(line))
        return rows

    encoding = "utf-8-sig" if fmt == "csv" else "utf-8"
    with open(path, "r", encoding=encoding) as f:
        if fmt == "csv":
            reader = csv.DictReader(f)
            rows.extend(reader)
        else:
            for line in f:
                if not line.strip():
                    continue
                rows.append(json.loads(line))
    return rows


def resolve_receipt_path(
    receipt_name: str,
    date: str,  # YYYY-MM-DD
    receipt_type: str,  # 'expenses' oder 'income'
    config: dict,
) -> tuple[Path | None, list[Path]]:
    """
    Sucht Beleg-Datei.

    Returns:
        (found_path, checked_paths)
        found_path ist None wenn nicht gefunden
    """
    base = config.get("receipts", {}).get(receipt_type, "")
    if not base:
        return (None, [])

    base_path = Path(base)
    year = date[:4]  # "2026" aus "2026-01-15"

    # Reihenfolge: Erst Jahres-Ordner, dann Basis
    candidates = [
        base_path / year / receipt_name,
        base_path / receipt_name,
    ]

    for path in candidates:
        if path.exists():
            return (path, candidates)

    return (None, candidates)


def warn_missing_receipt(
    receipt_name: str | None,
    date: str,
    receipt_type: str,  # 'expenses' oder 'income'
    config: dict,
) -> None:
    """Gibt Warnung aus wenn Beleg nicht gefunden wird."""
    if not receipt_name:
        return

    found_path, checked_paths = resolve_receipt_path(
        receipt_name, date, receipt_type, config
    )

    if found_path is None and checked_paths:
        print(f"! Beleg '{receipt_name}' nicht gefunden:", file=sys.stderr)
        for p in checked_paths:
            print(f"  - {p}", file=sys.stderr)


# =============================================================================
# Commands
# =============================================================================


def cmd_init(args):
    """Initialisiert die Datenbank."""
    db_path = Path(args.db)

    print(f"Initialisiere Datenbank: {db_path}")

    conn = get_db_connection(db_path)
    conn.executescript(SCHEMA)

    # Kategorien seeden (nur wenn leer)
    existing = conn.execute("SELECT COUNT(*) as cnt FROM categories").fetchone()["cnt"]
    if existing == 0:
        print("Seede Kategorien...")
        for name, eur_line, cat_type in SEED_CATEGORIES:
            conn.execute(
                "INSERT INTO categories (name, eur_line, type) VALUES (?, ?, ?)",
                (name, eur_line, cat_type),
            )
        conn.commit()
        print(f"  {len(SEED_CATEGORIES)} Kategorien angelegt")
    else:
        print(f"  Kategorien existieren bereits ({existing})")

    # Export-Verzeichnis erstellen
    DEFAULT_EXPORT_DIR.mkdir(exist_ok=True)
    print(f"Export-Verzeichnis: {DEFAULT_EXPORT_DIR}")

    conn.close()
    print("Fertig.")


def cmd_setup(args):
    """Interaktive Ersteinrichtung."""
    print("Willkommen! Konfiguriere deine EÜR...")
    print()

    config = load_config()
    receipts_config = dict(config.get("receipts", {}))

    expenses_input = prompt_path(
        "Beleg-Pfad für Ausgaben", receipts_config.get("expenses")
    )
    income_input = prompt_path(
        "Beleg-Pfad für Einnahmen", receipts_config.get("income")
    )

    expenses_path = normalize_receipt_path(expenses_input)
    income_path = normalize_receipt_path(income_input)

    receipts_config["expenses"] = expenses_path
    receipts_config["income"] = income_path
    config["receipts"] = receipts_config

    ordered_config = {"receipts": receipts_config}
    for key, value in config.items():
        if key != "receipts":
            ordered_config[key] = value

    save_config(ordered_config)

    print()
    print(f"Konfiguration gespeichert: {CONFIG_PATH}")
    print()
    print("[receipts]")
    print(f"  expenses = {expenses_path or '(nicht gesetzt)'}")
    print(f"  income   = {income_path or '(nicht gesetzt)'}")

    for path in (expenses_path, income_path):
        if path and not Path(path).exists():
            print(f"! Hinweis: Pfad existiert nicht: {path}", file=sys.stderr)


def cmd_import(args):
    """Bulk-Import von Transaktionen."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    try:
        rows = iter_import_rows(args.file, args.format)
    except (OSError, json.JSONDecodeError) as exc:
        conn.close()
        print(f"Fehler: Importdatei konnte nicht gelesen werden: {exc}", file=sys.stderr)
        sys.exit(1)

    total = 0
    inserted_expenses = 0
    inserted_income = 0
    duplicates = 0
    incomplete = 0

    for row in rows:
        total += 1
        normalized = normalize_import_row(row)
        row_type = normalized["type"]
        date = normalized["date"]
        party = normalized["party"]
        category_name = normalized["category"]
        amount = normalized["amount_eur"]
        account = normalized["account"]
        foreign_amount = normalized["foreign_amount"]
        receipt_name = normalized["receipt_name"]
        notes = normalized["notes"]
        rc = normalized["rc"]
        vat_amount = normalized["vat_amount"]

        missing_fields = []

        if not row_type:
            missing_fields.append("type")
        if not date:
            missing_fields.append("date")
        if amount is None:
            missing_fields.append("amount_eur")
        if not party:
            missing_fields.append("party")
        if not category_name:
            missing_fields.append("category")

        cat_id = None
        if row_type in ("expense", "income") and category_name:
            cat_id = get_category_id(conn, str(category_name), row_type)
            if not cat_id:
                missing_fields.append("category")

        if missing_fields:
            incomplete += 1
            if not args.dry_run:
                cursor = conn.execute(
                    """INSERT INTO incomplete_entries
                       (type, date, party, category_name, amount_eur, account,
                        foreign_amount, receipt_name, notes, is_rc, vat_amount,
                        raw_data, missing_fields)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row_type or "unknown",
                        str(date) if date else None,
                        str(party) if party else None,
                        str(category_name) if category_name else None,
                        amount,
                        str(account) if account else None,
                        str(foreign_amount) if foreign_amount else None,
                        str(receipt_name) if receipt_name else None,
                        str(notes) if notes else None,
                        1 if rc else 0,
                        vat_amount,
                        json.dumps(normalized["raw_data"], ensure_ascii=False),
                        json.dumps(missing_fields, ensure_ascii=False),
                    ),
                )
                record_id = cursor.lastrowid
                assert record_id is not None
                log_audit(
                    conn,
                    "incomplete_entries",
                    record_id,
                    "INSERT",
                    new_data={
                        "type": row_type or "unknown",
                        "date": str(date) if date else None,
                        "party": str(party) if party else None,
                        "category_name": str(category_name) if category_name else None,
                        "amount_eur": amount,
                        "account": str(account) if account else None,
                        "foreign_amount": str(foreign_amount) if foreign_amount else None,
                        "receipt_name": str(receipt_name) if receipt_name else None,
                        "notes": str(notes) if notes else None,
                        "is_rc": 1 if rc else 0,
                        "vat_amount": vat_amount,
                        "missing_fields": missing_fields,
                    },
                )
            continue

        if row_type == "expense":
            if rc and vat_amount is None and amount is not None:
                vat_amount = round(abs(amount) * 0.19, 2)

            tx_hash = compute_hash(
                str(date), str(party), float(amount), receipt_name or ""
            )
            existing = conn.execute(
                "SELECT id FROM expenses WHERE hash = ?", (tx_hash,)
            ).fetchone()
            if existing:
                duplicates += 1
                continue

            inserted_expenses += 1
            if args.dry_run:
                continue

            cursor = conn.execute(
                """INSERT INTO expenses 
                   (receipt_name, date, vendor, category_id, amount_eur, account,
                    foreign_amount, notes, is_rc, vat_amount, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_name,
                    str(date),
                    str(party),
                    cat_id,
                    amount,
                    account,
                    foreign_amount,
                    notes,
                    1 if rc else 0,
                    vat_amount,
                    tx_hash,
                ),
            )
            record_id = cursor.lastrowid
            assert record_id is not None

            new_data = {
                "receipt_name": receipt_name,
                "date": str(date),
                "vendor": str(party),
                "category_id": cat_id,
                "amount_eur": amount,
                "account": account,
                "foreign_amount": foreign_amount,
                "notes": notes,
                "is_rc": 1 if rc else 0,
                "vat_amount": vat_amount,
            }
            log_audit(conn, "expenses", record_id, "INSERT", new_data=new_data)
        else:
            tx_hash = compute_hash(
                str(date), str(party), float(amount), receipt_name or ""
            )
            existing = conn.execute(
                "SELECT id FROM income WHERE hash = ?", (tx_hash,)
            ).fetchone()
            if existing:
                duplicates += 1
                continue

            inserted_income += 1
            if args.dry_run:
                continue

            cursor = conn.execute(
                """INSERT INTO income
                   (receipt_name, date, source, category_id, amount_eur,
                    foreign_amount, notes, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_name,
                    str(date),
                    str(party),
                    cat_id,
                    amount,
                    foreign_amount,
                    notes,
                    tx_hash,
                ),
            )
            record_id = cursor.lastrowid
            assert record_id is not None

            new_data = {
                "receipt_name": receipt_name,
                "date": str(date),
                "source": str(party),
                "category_id": cat_id,
                "amount_eur": amount,
                "foreign_amount": foreign_amount,
                "notes": notes,
            }
            log_audit(conn, "income", record_id, "INSERT", new_data=new_data)

    if not args.dry_run:
        conn.commit()
    conn.close()

    print("Import abgeschlossen")
    print(f"  Zeilen gesamt: {total}")
    print(f"  Ausgaben angelegt: {inserted_expenses}")
    print(f"  Einnahmen angelegt: {inserted_income}")
    print(f"  Duplikate übersprungen: {duplicates}")
    print(f"  Unvollständig: {incomplete}")
    if args.dry_run:
        print("  Dry-Run: keine Änderungen gespeichert")


def cmd_incomplete_list(args):
    """Listet unvollständige Import-Einträge."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    query = """
        SELECT id, type, date, party, category_name, amount_eur,
               receipt_name, missing_fields, notes
        FROM incomplete_entries
        WHERE 1=1
    """
    params = []

    if args.type:
        query += " AND type = ?"
        params.append(args.type)
    if args.year:
        query += " AND date LIKE ?"
        params.append(f"{args.year}-%")

    query += " ORDER BY date DESC, id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Typ",
                "Datum",
                "Partei",
                "Kategorie",
                "EUR",
                "Beleg",
                "Fehlende Felder",
                "Notizen",
            ]
        )
        for r in rows:
            missing = format_missing_fields(r["missing_fields"])
            writer.writerow(
                [
                    r["id"],
                    r["type"],
                    r["date"] or "",
                    r["party"] or "",
                    r["category_name"] or "",
                    f"{r['amount_eur']:.2f}" if r["amount_eur"] is not None else "",
                    r["receipt_name"] or "",
                    missing,
                    r["notes"] or "",
                ]
            )
        return

    if not rows:
        print("Keine unvollständigen Einträge gefunden.")
        return

    print(
        f"{'ID':<5} {'Typ':<9} {'Datum':<12} {'Partei':<20} {'Kategorie':<25} {'EUR':>10} {'Fehlt':<20}"
    )
    print("-" * 105)
    for r in rows:
        missing = format_missing_fields(r["missing_fields"])
        amount_str = f"{r['amount_eur']:.2f}" if r["amount_eur"] is not None else ""
        print(
            f"{r['id']:<5} {r['type']:<9} {(r['date'] or ''):<12} {(r['party'] or '')[:20]:<20} {(r['category_name'] or '')[:25]:<25} {amount_str:>10} {missing[:20]:<20}"
        )


def cmd_add_expense(args):
    """Fügt eine Ausgabe hinzu."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    # Kategorie nachschlagen
    cat_id = get_category_id(conn, args.category, "expense")
    if not cat_id:
        print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
        print("Verfügbare Kategorien:", file=sys.stderr)
        for row in conn.execute("SELECT name FROM categories WHERE type = 'expense'"):
            print(f"  - {row['name']}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # Reverse-Charge: 19% USt automatisch berechnen
    vat_amount = args.vat
    if args.rc and not vat_amount:
        vat_amount = round(abs(args.amount) * 0.19, 2)

    # Hash berechnen
    tx_hash = compute_hash(args.date, args.vendor, args.amount, args.receipt or "")

    # Duplikat-Prüfung
    existing = conn.execute(
        "SELECT id FROM expenses WHERE hash = ?", (tx_hash,)
    ).fetchone()
    if existing:
        print(
            f"Warnung: Duplikat erkannt (ID {existing['id']}), überspringe.",
            file=sys.stderr,
        )
        conn.close()
        return

    # Insert
    cursor = conn.execute(
        """INSERT INTO expenses 
           (receipt_name, date, vendor, category_id, amount_eur, account, 
            foreign_amount, notes, is_rc, vat_amount, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            args.receipt,
            args.date,
            args.vendor,
            cat_id,
            args.amount,
            args.account,
            args.foreign,
            args.notes,
            1 if args.rc else 0,
            vat_amount,
            tx_hash,
        ),
    )
    record_id = cursor.lastrowid
    assert record_id is not None  # Always set after INSERT

    # Audit-Log
    new_data = {
        "receipt_name": args.receipt,
        "date": args.date,
        "vendor": args.vendor,
        "category_id": cat_id,
        "amount_eur": args.amount,
        "account": args.account,
        "foreign_amount": args.foreign,
        "notes": args.notes,
        "is_rc": 1 if args.rc else 0,
        "vat_amount": vat_amount,
    }
    log_audit(conn, "expenses", record_id, "INSERT", new_data=new_data)

    conn.commit()
    conn.close()

    vat_info = f" (USt-VA: {vat_amount:.2f})" if vat_amount else ""
    print(
        f"Ausgabe #{record_id} hinzugefügt: {args.vendor} {format_amount(args.amount)} EUR{vat_info}"
    )

    # Beleg-Warnung (nach erfolgreicher Transaktion)
    config = load_config()
    warn_missing_receipt(args.receipt, args.date, "expenses", config)


def cmd_add_income(args):
    """Fügt eine Einnahme hinzu."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    # Kategorie nachschlagen
    cat_id = get_category_id(conn, args.category, "income")
    if not cat_id:
        print(f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr)
        print("Verfügbare Kategorien:", file=sys.stderr)
        for row in conn.execute("SELECT name FROM categories WHERE type = 'income'"):
            print(f"  - {row['name']}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # Hash berechnen
    tx_hash = compute_hash(args.date, args.source, args.amount, args.receipt or "")

    # Duplikat-Prüfung
    existing = conn.execute(
        "SELECT id FROM income WHERE hash = ?", (tx_hash,)
    ).fetchone()
    if existing:
        print(
            f"Warnung: Duplikat erkannt (ID {existing['id']}), überspringe.",
            file=sys.stderr,
        )
        conn.close()
        return

    # Insert
    cursor = conn.execute(
        """INSERT INTO income 
           (receipt_name, date, source, category_id, amount_eur, foreign_amount, notes, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            args.receipt,
            args.date,
            args.source,
            cat_id,
            args.amount,
            args.foreign,
            args.notes,
            tx_hash,
        ),
    )
    record_id = cursor.lastrowid
    assert record_id is not None  # Always set after INSERT

    # Audit-Log
    new_data = {
        "receipt_name": args.receipt,
        "date": args.date,
        "source": args.source,
        "category_id": cat_id,
        "amount_eur": args.amount,
        "foreign_amount": args.foreign,
        "notes": args.notes,
    }
    log_audit(conn, "income", record_id, "INSERT", new_data=new_data)

    conn.commit()
    conn.close()

    print(
        f"Einnahme #{record_id} hinzugefügt: {args.source} {format_amount(args.amount)} EUR"
    )

    # Beleg-Warnung (nach erfolgreicher Transaktion)
    config = load_config()
    warn_missing_receipt(args.receipt, args.date, "income", config)


def cmd_list_expenses(args):
    """Listet Ausgaben."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    query = """
        SELECT e.id, e.date, e.vendor, c.name as category, c.eur_line,
               e.amount_eur, e.account, e.receipt_name, e.foreign_amount, 
               e.notes, e.is_rc, e.vat_amount
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE 1=1
    """
    params = []

    if args.year:
        query += " AND strftime('%Y', e.date) = ?"
        params.append(str(args.year))
    if args.month:
        query += " AND strftime('%m', e.date) = ?"
        params.append(f"{args.month:02d}")
    if args.category:
        query += " AND LOWER(c.name) = LOWER(?)"
        params.append(args.category)

    query += " ORDER BY e.date DESC, e.id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Datum",
                "Lieferant",
                "Kategorie",
                "EUR",
                "Konto",
                "Beleg",
                "Fremdwährung",
                "Bemerkung",
            ]
        )
        for r in rows:
            cat_str = (
                f"{r['category']} ({r['eur_line']})" if r["eur_line"] else r["category"]
            )
            writer.writerow(
                [
                    r["id"],
                    r["date"],
                    r["vendor"],
                    cat_str,
                    f"{r['amount_eur']:.2f}",
                    r["account"] or "",
                    r["receipt_name"] or "",
                    r["foreign_amount"] or "",
                    r["notes"] or "",
                ]
            )
    else:
        # Table format
        if not rows:
            print("Keine Ausgaben gefunden.")
            return

        # Check if any row has VAT or RC
        has_vat = any(r["vat_amount"] or r["is_rc"] for r in rows)

        if has_vat:
            print(
                f"{'ID':<5} {'Datum':<12} {'Lieferant':<20} {'Kategorie':<25} {'EUR':>10} {'RC':<3} {'USt-VA':>8} {'Konto':<10}"
            )
            print("-" * 100)
        else:
            print(
                f"{'ID':<5} {'Datum':<12} {'Lieferant':<20} {'Kategorie':<30} {'EUR':>10} {'Konto':<12}"
            )
            print("-" * 95)

        total = 0.0
        vat_total = 0.0
        for r in rows:
            cat_str = (
                f"{r['category']} ({r['eur_line']})" if r["eur_line"] else r["category"]
            )
            if has_vat:
                vat_str = f"{r['vat_amount']:.2f}" if r["vat_amount"] else ""
                rc_str = "X" if r["is_rc"] else ""
                print(
                    f"{r['id']:<5} {r['date']:<12} {r['vendor'][:20]:<20} {cat_str[:25]:<25} {r['amount_eur']:>10.2f} {rc_str:<3} {vat_str:>8} {(r['account'] or ''):<10}"
                )
                if r["vat_amount"]:
                    vat_total += r["vat_amount"]
            else:
                print(
                    f"{r['id']:<5} {r['date']:<12} {r['vendor'][:20]:<20} {cat_str[:30]:<30} {r['amount_eur']:>10.2f} {(r['account'] or ''):<12}"
                )
            total += r["amount_eur"]
        print("-" * (100 if has_vat else 95))
        if has_vat:
            print(f"{'GESAMT':<68} {total:>10.2f}     {vat_total:>8.2f}")
        else:
            print(f"{'GESAMT':<69} {total:>10.2f}")


def cmd_list_income(args):
    """Listet Einnahmen."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    query = """
        SELECT i.id, i.date, i.source, c.name as category, c.eur_line,
               i.amount_eur, i.receipt_name, i.foreign_amount, i.notes
        FROM income i
        JOIN categories c ON i.category_id = c.id
        WHERE 1=1
    """
    params = []

    if args.year:
        query += " AND strftime('%Y', i.date) = ?"
        params.append(str(args.year))
    if args.month:
        query += " AND strftime('%m', i.date) = ?"
        params.append(f"{args.month:02d}")
    if args.category:
        query += " AND LOWER(c.name) = LOWER(?)"
        params.append(args.category)

    query += " ORDER BY i.date DESC, i.id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Datum",
                "Quelle",
                "Kategorie",
                "EUR",
                "Beleg",
                "Fremdwährung",
                "Bemerkung",
            ]
        )
        for r in rows:
            cat_str = (
                f"{r['category']} ({r['eur_line']})" if r["eur_line"] else r["category"]
            )
            writer.writerow(
                [
                    r["id"],
                    r["date"],
                    r["source"],
                    cat_str,
                    f"{r['amount_eur']:.2f}",
                    r["receipt_name"] or "",
                    r["foreign_amount"] or "",
                    r["notes"] or "",
                ]
            )
    else:
        if not rows:
            print("Keine Einnahmen gefunden.")
            return

        print(f"{'ID':<5} {'Datum':<12} {'Quelle':<25} {'Kategorie':<35} {'EUR':>12}")
        print("-" * 95)
        total = 0.0
        for r in rows:
            cat_str = (
                f"{r['category']} ({r['eur_line']})" if r["eur_line"] else r["category"]
            )
            print(
                f"{r['id']:<5} {r['date']:<12} {r['source'][:25]:<25} {cat_str[:35]:<35} {r['amount_eur']:>12.2f}"
            )
            total += r["amount_eur"]
        print("-" * 95)
        print(f"{'GESAMT':<79} {total:>12.2f}")


def cmd_list_categories(args):
    """Listet alle Kategorien."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    query = "SELECT id, name, eur_line, type FROM categories"
    params = []

    if args.type:
        query += " WHERE type = ?"
        params.append(args.type)

    query += " ORDER BY type, eur_line, name"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    print(f"{'ID':<4} {'Typ':<8} {'EÜR':<5} {'Name':<40}")
    print("-" * 60)
    for r in rows:
        eur = str(r["eur_line"]) if r["eur_line"] else "-"
        print(f"{r['id']:<4} {r['type']:<8} {eur:<5} {r['name']:<40}")


def cmd_update_expense(args):
    """Aktualisiert eine Ausgabe."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    # Bestehenden Datensatz laden
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    old_data = row_to_dict(row)

    # Neue Werte bestimmen
    new_receipt = args.receipt if args.receipt is not None else row["receipt_name"]
    new_date = args.date if args.date else row["date"]
    new_vendor = args.vendor if args.vendor else row["vendor"]
    new_amount = args.amount if args.amount is not None else row["amount_eur"]
    new_account = args.account if args.account is not None else row["account"]
    new_foreign = args.foreign if args.foreign is not None else row["foreign_amount"]
    new_notes = args.notes if args.notes is not None else row["notes"]
    new_vat = args.vat if args.vat is not None else row["vat_amount"]
    new_rc = (1 if args.rc else 0) if args.rc else row["is_rc"]

    # Automatisches vat_amount bei RC Update wenn bisher 0/None
    if new_rc and not new_vat:
        new_vat = round(abs(new_amount) * 0.19, 2)

    # Kategorie
    if args.category:
        cat_id = get_category_id(conn, args.category, "expense")
        if not cat_id:
            print(
                f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr
            )
            conn.close()
            sys.exit(1)
    else:
        cat_id = row["category_id"]

    # Neuen Hash berechnen
    new_hash = compute_hash(new_date, new_vendor, new_amount, new_receipt or "")

    # Update
    conn.execute(
        """UPDATE expenses SET
           receipt_name = ?, date = ?, vendor = ?, category_id = ?, amount_eur = ?,
           account = ?, foreign_amount = ?, notes = ?, is_rc = ?, vat_amount = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_date,
            new_vendor,
            cat_id,
            new_amount,
            new_account,
            new_foreign,
            new_notes,
            new_rc,
            new_vat,
            new_hash,
            args.id,
        ),
    )

    # Audit-Log
    new_data = {
        "receipt_name": new_receipt,
        "date": new_date,
        "vendor": new_vendor,
        "category_id": cat_id,
        "amount_eur": new_amount,
        "account": new_account,
        "foreign_amount": new_foreign,
        "notes": new_notes,
        "is_rc": new_rc,
        "vat_amount": new_vat,
    }
    log_audit(conn, "expenses", args.id, "UPDATE", old_data=old_data, new_data=new_data)

    conn.commit()
    conn.close()

    print(f"Ausgabe #{args.id} aktualisiert.")

    # Beleg-Warnung (nach erfolgreicher Transaktion)
    config = load_config()
    warn_missing_receipt(new_receipt, new_date, "expenses", config)


def cmd_update_income(args):
    """Aktualisiert eine Einnahme."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    row = conn.execute("SELECT * FROM income WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"Fehler: Einnahme #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    old_data = row_to_dict(row)

    new_receipt = args.receipt if args.receipt is not None else row["receipt_name"]
    new_date = args.date if args.date else row["date"]
    new_source = args.source if args.source else row["source"]
    new_amount = args.amount if args.amount is not None else row["amount_eur"]
    new_foreign = args.foreign if args.foreign is not None else row["foreign_amount"]
    new_notes = args.notes if args.notes is not None else row["notes"]

    if args.category:
        cat_id = get_category_id(conn, args.category, "income")
        if not cat_id:
            print(
                f"Fehler: Kategorie '{args.category}' nicht gefunden.", file=sys.stderr
            )
            conn.close()
            sys.exit(1)
    else:
        cat_id = row["category_id"]

    new_hash = compute_hash(new_date, new_source, new_amount, new_receipt or "")

    conn.execute(
        """UPDATE income SET
           receipt_name = ?, date = ?, source = ?, category_id = ?, amount_eur = ?,
           foreign_amount = ?, notes = ?, hash = ?
           WHERE id = ?""",
        (
            new_receipt,
            new_date,
            new_source,
            cat_id,
            new_amount,
            new_foreign,
            new_notes,
            new_hash,
            args.id,
        ),
    )

    new_data = {
        "receipt_name": new_receipt,
        "date": new_date,
        "source": new_source,
        "category_id": cat_id,
        "amount_eur": new_amount,
        "foreign_amount": new_foreign,
        "notes": new_notes,
    }
    log_audit(conn, "income", args.id, "UPDATE", old_data=old_data, new_data=new_data)

    conn.commit()
    conn.close()

    print(f"Einnahme #{args.id} aktualisiert.")

    # Beleg-Warnung (nach erfolgreicher Transaktion)
    config = load_config()
    warn_missing_receipt(new_receipt, new_date, "income", config)


def cmd_delete_expense(args):
    """Löscht eine Ausgabe."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    row = conn.execute(
        """SELECT e.*, c.name as category_name 
           FROM expenses e JOIN categories c ON e.category_id = c.id 
           WHERE e.id = ?""",
        (args.id,),
    ).fetchone()

    if not row:
        print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        print(f"Ausgabe #{args.id}:")
        print(f"  Datum:     {row['date']}")
        print(f"  Lieferant: {row['vendor']}")
        print(f"  Kategorie: {row['category_name']}")
        print(f"  Betrag:    {row['amount_eur']:.2f} EUR")

        confirm = input("\nWirklich löschen? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    old_data = row_to_dict(row)

    conn.execute("DELETE FROM expenses WHERE id = ?", (args.id,))
    log_audit(conn, "expenses", args.id, "DELETE", old_data=old_data)

    conn.commit()
    conn.close()

    print(f"Ausgabe #{args.id} gelöscht.")


def cmd_delete_income(args):
    """Löscht eine Einnahme."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    row = conn.execute(
        """SELECT i.*, c.name as category_name 
           FROM income i JOIN categories c ON i.category_id = c.id 
           WHERE i.id = ?""",
        (args.id,),
    ).fetchone()

    if not row:
        print(f"Fehler: Einnahme #{args.id} nicht gefunden.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not args.force:
        print(f"Einnahme #{args.id}:")
        print(f"  Datum:    {row['date']}")
        print(f"  Quelle:   {row['source']}")
        print(f"  Kategorie: {row['category_name']}")
        print(f"  Betrag:   {row['amount_eur']:.2f} EUR")

        confirm = input("\nWirklich löschen? (j/N): ")
        if confirm.lower() != "j":
            print("Abgebrochen.")
            conn.close()
            return

    old_data = row_to_dict(row)

    conn.execute("DELETE FROM income WHERE id = ?", (args.id,))
    log_audit(conn, "income", args.id, "DELETE", old_data=old_data)

    conn.commit()
    conn.close()

    print(f"Einnahme #{args.id} gelöscht.")


def cmd_export(args):
    """Exportiert Daten als CSV oder XLSX."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    year = args.year or datetime.now().year

    # Ausgaben laden
    expenses = conn.execute(
        """SELECT e.receipt_name, e.date, e.vendor, c.name as category, c.eur_line,
                  e.amount_eur, e.account, e.foreign_amount, e.notes, e.is_rc, e.vat_amount
           FROM expenses e
           JOIN categories c ON e.category_id = c.id
           WHERE strftime('%Y', e.date) = ?
           ORDER BY e.date, e.id""",
        (str(year),),
    ).fetchall()

    # Einnahmen laden
    income = conn.execute(
        """SELECT i.receipt_name, i.date, i.source, c.name as category, c.eur_line,
                  i.amount_eur, i.foreign_amount, i.notes
           FROM income i
           JOIN categories c ON i.category_id = c.id
           WHERE strftime('%Y', i.date) = ?
           ORDER BY i.date, i.id""",
        (str(year),),
    ).fetchall()

    conn.close()

    if args.format == "csv":
        # CSV Export
        exp_path = output_dir / f"EÜR_{year}_Ausgaben.csv"
        with open(exp_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Belegname",
                    "Datum",
                    "Lieferant",
                    "Kategorie",
                    "EUR",
                    "Konto",
                    "Fremdwährung",
                    "Bemerkung",
                    "RC",
                    "USt-VA",
                ]
            )
            for r in expenses:
                cat = (
                    f"{r['category']} ({r['eur_line']})"
                    if r["eur_line"]
                    else r["category"]
                )
                writer.writerow(
                    [
                        r["receipt_name"] or "",
                        r["date"],
                        r["vendor"],
                        cat,
                        f"{r['amount_eur']:.2f}",
                        r["account"] or "",
                        r["foreign_amount"] or "",
                        r["notes"] or "",
                        "X" if r["is_rc"] else "",
                        f"{r['vat_amount']:.2f}" if r["vat_amount"] else "",
                    ]
                )
        print(f"Exportiert: {exp_path}")

        inc_path = output_dir / f"EÜR_{year}_Einnahmen.csv"
        with open(inc_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Belegname",
                    "Datum",
                    "Quelle",
                    "Kategorie",
                    "EUR",
                    "Fremdwährung",
                    "Bemerkung",
                ]
            )
            for r in income:
                cat = (
                    f"{r['category']} ({r['eur_line']})"
                    if r["eur_line"]
                    else r["category"]
                )
                writer.writerow(
                    [
                        r["receipt_name"] or "",
                        r["date"],
                        r["source"],
                        cat,
                        f"{r['amount_eur']:.2f}",
                        r["foreign_amount"] or "",
                        r["notes"] or "",
                    ]
                )
        print(f"Exportiert: {inc_path}")

    else:
        # XLSX Export
        if not HAS_OPENPYXL:
            print(
                "Fehler: openpyxl nicht installiert. Bitte 'pip install openpyxl'.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Ausgaben
        exp_path = output_dir / f"EÜR_{year}_Ausgaben.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ausgaben"
        ws.append(
            [
                "Belegname",
                "Datum",
                "Lieferant",
                "Kategorie",
                "EUR",
                "Konto",
                "Fremdwährung",
                "Bemerkung",
                "RC",
                "USt-VA",
            ]
        )
        for r in expenses:
            cat = (
                f"{r['category']} ({r['eur_line']})" if r["eur_line"] else r["category"]
            )
            ws.append(
                [
                    r["receipt_name"] or "",
                    r["date"],
                    r["vendor"],
                    cat,
                    r["amount_eur"],
                    r["account"] or "",
                    r["foreign_amount"] or "",
                    r["notes"] or "",
                    "X" if r["is_rc"] else "",
                    r["vat_amount"] if r["vat_amount"] else None,
                ]
            )
        wb.save(exp_path)
        print(f"Exportiert: {exp_path}")

        # Einnahmen
        inc_path = output_dir / f"EÜR_{year}_Einnahmen.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Einnahmen"
        ws.append(
            [
                "Belegname",
                "Datum",
                "Quelle",
                "Kategorie",
                "EUR",
                "Fremdwährung",
                "Bemerkung",
            ]
        )
        for r in income:
            cat = (
                f"{r['category']} ({r['eur_line']})" if r["eur_line"] else r["category"]
            )
            ws.append(
                [
                    r["receipt_name"] or "",
                    r["date"],
                    r["source"],
                    cat,
                    r["amount_eur"],
                    r["foreign_amount"] or "",
                    r["notes"] or "",
                ]
            )
        wb.save(inc_path)
        print(f"Exportiert: {inc_path}")


def cmd_summary(args):
    """Zeigt Kategorie-Zusammenfassung."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    year = args.year or datetime.now().year

    print(f"EÜR-Zusammenfassung {year}")
    print("=" * 50)
    print()

    # Ausgaben nach Kategorie
    expenses = conn.execute(
        """SELECT c.name, c.eur_line, SUM(e.amount_eur) as total
           FROM expenses e
           JOIN categories c ON e.category_id = c.id
           WHERE strftime('%Y', e.date) = ?
           GROUP BY c.id
           ORDER BY c.eur_line, c.name""",
        (str(year),),
    ).fetchall()

    print("Ausgaben nach Kategorie:")
    expense_total = 0.0
    for r in expenses:
        cat = f"{r['name']} ({r['eur_line']})" if r["eur_line"] else r["name"]
        print(f"  {cat:<40} {r['total']:>12.2f} EUR")
        expense_total += r["total"]
    print("  " + "-" * 54)
    print(f"  {'GESAMT Ausgaben':<40} {expense_total:>12.2f} EUR")
    print()

    # Reverse-Charge USt (für USt-Voranmeldung)
    rc_vat = conn.execute(
        """SELECT SUM(vat_amount) as total
           FROM expenses
           WHERE strftime('%Y', date) = ? AND is_rc = 1""",
        (str(year),),
    ).fetchone()
    rc_vat_total = rc_vat["total"] if rc_vat["total"] else 0.0

    if rc_vat_total != 0:
        print("Reverse-Charge USt (für USt-VA):")
        print(f"  {'Summe USt-VA (19% auf RC-Ausgaben)':<40} {rc_vat_total:>12.2f} EUR")
        print()

    # Einnahmen nach Kategorie
    income = conn.execute(
        """SELECT c.name, c.eur_line, SUM(i.amount_eur) as total
           FROM income i
           JOIN categories c ON i.category_id = c.id
           WHERE strftime('%Y', i.date) = ?
           GROUP BY c.id
           ORDER BY c.eur_line, c.name""",
        (str(year),),
    ).fetchall()

    print("Einnahmen nach Kategorie:")
    income_total = 0.0
    for r in income:
        cat = f"{r['name']} ({r['eur_line']})" if r["eur_line"] else r["name"]
        print(f"  {cat:<40} {r['total']:>12.2f} EUR")
        income_total += r["total"]
    print("  " + "-" * 54)
    print(f"  {'GESAMT Einnahmen':<40} {income_total:>12.2f} EUR")
    print()

    print("  " + "=" * 54)
    result = income_total + expense_total  # expense_total ist negativ
    label = "GEWINN" if result >= 0 else "VERLUST"
    print(f"  {label:<40} {result:>12.2f} EUR")

    conn.close()


def cmd_audit(args):
    """Zeigt Audit-Log für einen Datensatz."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    table = args.table

    rows = conn.execute(
        """SELECT timestamp, action, old_data, new_data, user
           FROM audit_log
           WHERE table_name = ? AND record_id = ?
           ORDER BY timestamp""",
        (table, args.id),
    ).fetchall()

    conn.close()

    if not rows:
        print(f"Keine Audit-Einträge für {table} #{args.id} gefunden.")
        return

    print(f"Audit-Log für {table} #{args.id}")
    print("=" * 60)
    print()

    for r in rows:
        print(f"{r['timestamp']}  {r['action']} by {r['user']}")
        if r["old_data"]:
            print(f"  <- {r['old_data']}")
        if r["new_data"]:
            print(f"  -> {r['new_data']}")
        print()


def cmd_config_show(args):
    """Zeigt aktuelle Konfiguration."""
    print("EÜR Konfiguration")
    print("=================")
    print()
    print(f"Config-Datei: {CONFIG_PATH}", end="")

    if not CONFIG_PATH.exists():
        print(" (nicht vorhanden)")
        print()
        print("Erstelle Config mit:")
        print()
        print("  euer setup")
        print()
        print("Oder manuell:")
        print()
        print("  mkdir -p ~/.config/euer")
        print("  cat > ~/.config/euer/config.toml << 'EOF'")
        print("  [receipts]")
        print('  expenses = "/pfad/zu/ausgaben-belege"')
        print('  income = "/pfad/zu/einnahmen-belege"')
        print("  EOF")
        return

    print()
    print()

    config = load_config()
    receipts = config.get("receipts", {})

    print("[receipts]")
    expenses_path = receipts.get("expenses", "")
    income_path = receipts.get("income", "")
    print(f"  expenses = {expenses_path or '(nicht gesetzt)'}")
    print(f"  income   = {income_path or '(nicht gesetzt)'}")


def cmd_receipt_check(args):
    """Prüft alle Transaktionen auf fehlende Belege."""
    config = load_config()
    receipts_config = config.get("receipts", {})

    if not receipts_config.get("expenses") and not receipts_config.get("income"):
        print("Fehler: Keine Beleg-Pfade konfiguriert.", file=sys.stderr)
        print("Siehe: euer config show", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    year = args.year or datetime.now().year
    print(f"Beleg-Prüfung {year}")
    print("=" * 50)
    print()

    missing_count = {"expenses": 0, "income": 0}
    total_count = {"expenses": 0, "income": 0}

    # Ausgaben prüfen
    if args.type in (None, "expense") and receipts_config.get("expenses"):
        expenses = conn.execute(
            """SELECT e.id, e.date, e.vendor, e.receipt_name
               FROM expenses e
               WHERE strftime('%Y', e.date) = ?
               ORDER BY e.date, e.id""",
            (str(year),),
        ).fetchall()

        missing_expenses = []
        for r in expenses:
            total_count["expenses"] += 1
            if not r["receipt_name"]:
                missing_expenses.append(
                    (r["id"], r["date"], r["vendor"], "(kein Beleg)")
                )
                missing_count["expenses"] += 1
            else:
                found_path, _ = resolve_receipt_path(
                    r["receipt_name"], r["date"], "expenses", config
                )
                if found_path is None:
                    missing_expenses.append(
                        (r["id"], r["date"], r["vendor"], r["receipt_name"])
                    )
                    missing_count["expenses"] += 1

        print("Fehlende Belege (Ausgaben):")
        if missing_expenses:
            for eid, date, vendor, receipt in missing_expenses:
                print(f"  #{eid:<4} {date}  {vendor[:20]:<20}  {receipt}")
        else:
            print("  (keine)")
        print()

    # Einnahmen prüfen
    if args.type in (None, "income") and receipts_config.get("income"):
        income_rows = conn.execute(
            """SELECT i.id, i.date, i.source, i.receipt_name
               FROM income i
               WHERE strftime('%Y', i.date) = ?
               ORDER BY i.date, i.id""",
            (str(year),),
        ).fetchall()

        missing_income = []
        for r in income_rows:
            total_count["income"] += 1
            if not r["receipt_name"]:
                missing_income.append((r["id"], r["date"], r["source"], "(kein Beleg)"))
                missing_count["income"] += 1
            else:
                found_path, _ = resolve_receipt_path(
                    r["receipt_name"], r["date"], "income", config
                )
                if found_path is None:
                    missing_income.append(
                        (r["id"], r["date"], r["source"], r["receipt_name"])
                    )
                    missing_count["income"] += 1

        print("Fehlende Belege (Einnahmen):")
        if missing_income:
            for iid, date, source, receipt in missing_income:
                print(f"  #{iid:<4} {date}  {source[:20]:<20}  {receipt}")
        else:
            print("  (keine)")
        print()

    conn.close()

    # Zusammenfassung
    print("Zusammenfassung:")
    if args.type in (None, "expense") and receipts_config.get("expenses"):
        print(
            f"  Ausgaben: {missing_count['expenses']} von {total_count['expenses']} ohne gültigen Beleg"
        )
    if args.type in (None, "income") and receipts_config.get("income"):
        print(
            f"  Einnahmen: {missing_count['income']} von {total_count['income']} ohne gültigen Beleg"
        )

    # Exit-Code 1 wenn Belege fehlen
    if missing_count["expenses"] > 0 or missing_count["income"] > 0:
        sys.exit(1)


def cmd_receipt_open(args):
    """Öffnet den Beleg einer Transaktion."""
    config = load_config()
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    table = args.table
    if table == "expenses":
        row = conn.execute(
            "SELECT date, receipt_name FROM expenses WHERE id = ?", (args.id,)
        ).fetchone()
        entity_name = "Ausgabe"
    else:
        row = conn.execute(
            "SELECT date, receipt_name FROM income WHERE id = ?", (args.id,)
        ).fetchone()
        entity_name = "Einnahme"

    conn.close()

    if not row:
        print(f"Fehler: {entity_name} #{args.id} nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    if not row["receipt_name"]:
        print(f"Fehler: {entity_name} #{args.id} hat keinen Beleg.", file=sys.stderr)
        sys.exit(1)

    found_path, checked_paths = resolve_receipt_path(
        row["receipt_name"], row["date"], table, config
    )

    if found_path is None:
        print(f"Fehler: Beleg '{row['receipt_name']}' nicht gefunden:", file=sys.stderr)
        for p in checked_paths:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    print(f"Öffne: {found_path}")

    # Plattform-spezifisch öffnen
    if platform.system() == "Darwin":
        subprocess.run(["open", str(found_path)])
    elif platform.system() == "Linux":
        subprocess.run(["xdg-open", str(found_path)])
    else:
        # Windows
        os.startfile(str(found_path))  # type: ignore


# =============================================================================
# Hauptprogramm
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="EÜR - Einnahmenüberschussrechnung CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"Pfad zur Datenbank (default: {DEFAULT_DB_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- init ---
    init_parser = subparsers.add_parser("init", help="Initialisiert die Datenbank")
    init_parser.set_defaults(func=cmd_init)

    # --- setup ---
    setup_parser = subparsers.add_parser(
        "setup", help="Interaktive Ersteinrichtung"
    )
    setup_parser.set_defaults(func=cmd_setup)

    # --- import ---
    import_parser = subparsers.add_parser(
        "import", help="Bulk-Import von Transaktionen"
    )
    import_parser.add_argument(
        "--file",
        required=True,
        help="Pfad zur Importdatei (csv|jsonl), '-' für stdin",
    )
    import_parser.add_argument(
        "--format", choices=["csv", "jsonl"], required=True, help="Importformat"
    )
    import_parser.add_argument(
        "--dry-run", action="store_true", help="Nur prüfen, nichts speichern"
    )
    import_parser.set_defaults(func=cmd_import)

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Fügt Transaktion hinzu")
    add_subparsers = add_parser.add_subparsers(dest="type", required=True)

    # add expense
    add_expense_parser = add_subparsers.add_parser("expense", help="Ausgabe hinzufügen")
    add_expense_parser.add_argument("--date", required=True, help="Datum (YYYY-MM-DD)")
    add_expense_parser.add_argument("--vendor", required=True, help="Lieferant/Zweck")
    add_expense_parser.add_argument("--category", required=True, help="Kategorie")
    add_expense_parser.add_argument(
        "--amount", required=True, type=float, help="Betrag in EUR"
    )
    add_expense_parser.add_argument("--account", help="Bankkonto")
    add_expense_parser.add_argument("--foreign", help="Fremdwährungsbetrag")
    add_expense_parser.add_argument("--receipt", help="Belegname")
    add_expense_parser.add_argument("--notes", help="Bemerkung")
    add_expense_parser.add_argument("--vat", type=float, help="USt-VA Betrag (manuell)")
    add_expense_parser.add_argument(
        "--rc",
        action="store_true",
        help="Reverse-Charge: berechnet 19%% USt automatisch",
    )
    add_expense_parser.set_defaults(func=cmd_add_expense)

    # add income
    add_income_parser = add_subparsers.add_parser("income", help="Einnahme hinzufügen")
    add_income_parser.add_argument("--date", required=True, help="Datum (YYYY-MM-DD)")
    add_income_parser.add_argument("--source", required=True, help="Quelle/Zweck")
    add_income_parser.add_argument("--category", required=True, help="Kategorie")
    add_income_parser.add_argument(
        "--amount", required=True, type=float, help="Betrag in EUR"
    )
    add_income_parser.add_argument("--foreign", help="Fremdwährungsbetrag")
    add_income_parser.add_argument("--receipt", help="Belegname")
    add_income_parser.add_argument("--notes", help="Bemerkung")
    add_income_parser.set_defaults(func=cmd_add_income)

    # --- list ---
    list_parser = subparsers.add_parser("list", help="Listet Daten")
    list_subparsers = list_parser.add_subparsers(dest="type", required=True)

    # list expenses
    list_exp_parser = list_subparsers.add_parser("expenses", help="Ausgaben anzeigen")
    list_exp_parser.add_argument("--year", type=int, help="Jahr filtern")
    list_exp_parser.add_argument("--month", type=int, help="Monat filtern (1-12)")
    list_exp_parser.add_argument("--category", help="Kategorie filtern")
    list_exp_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_exp_parser.set_defaults(func=cmd_list_expenses)

    # list income
    list_inc_parser = list_subparsers.add_parser("income", help="Einnahmen anzeigen")
    list_inc_parser.add_argument("--year", type=int, help="Jahr filtern")
    list_inc_parser.add_argument("--month", type=int, help="Monat filtern (1-12)")
    list_inc_parser.add_argument("--category", help="Kategorie filtern")
    list_inc_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_inc_parser.set_defaults(func=cmd_list_income)

    # list categories
    list_cat_parser = list_subparsers.add_parser(
        "categories", help="Kategorien anzeigen"
    )
    list_cat_parser.add_argument(
        "--type", choices=["expense", "income"], help="Typ filtern"
    )
    list_cat_parser.set_defaults(func=cmd_list_categories)

    # --- update ---
    update_parser = subparsers.add_parser("update", help="Aktualisiert Transaktion")
    update_subparsers = update_parser.add_subparsers(dest="type", required=True)

    # update expense
    upd_exp_parser = update_subparsers.add_parser(
        "expense", help="Ausgabe aktualisieren"
    )
    upd_exp_parser.add_argument("id", type=int, help="ID der Ausgabe")
    upd_exp_parser.add_argument("--date", help="Neues Datum")
    upd_exp_parser.add_argument("--vendor", help="Neuer Lieferant")
    upd_exp_parser.add_argument("--category", help="Neue Kategorie")
    upd_exp_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_exp_parser.add_argument("--account", help="Neues Konto")
    upd_exp_parser.add_argument("--foreign", help="Neuer Fremdwährungsbetrag")
    upd_exp_parser.add_argument("--receipt", help="Neuer Belegname")
    upd_exp_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_exp_parser.add_argument("--vat", type=float, help="Neuer USt-VA Betrag")
    upd_exp_parser.add_argument(
        "--rc",
        action="store_true",
        help="Reverse-Charge: setzt Flag und berechnet ggf. 19%% USt",
    )
    upd_exp_parser.set_defaults(func=cmd_update_expense)

    # update income
    upd_inc_parser = update_subparsers.add_parser(
        "income", help="Einnahme aktualisieren"
    )
    upd_inc_parser.add_argument("id", type=int, help="ID der Einnahme")
    upd_inc_parser.add_argument("--date", help="Neues Datum")
    upd_inc_parser.add_argument("--source", help="Neue Quelle")
    upd_inc_parser.add_argument("--category", help="Neue Kategorie")
    upd_inc_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_inc_parser.add_argument("--foreign", help="Neuer Fremdwährungsbetrag")
    upd_inc_parser.add_argument("--receipt", help="Neuer Belegname")
    upd_inc_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_inc_parser.set_defaults(func=cmd_update_income)

    # --- delete ---
    delete_parser = subparsers.add_parser("delete", help="Löscht Transaktion")
    delete_subparsers = delete_parser.add_subparsers(dest="type", required=True)

    # delete expense
    del_exp_parser = delete_subparsers.add_parser("expense", help="Ausgabe löschen")
    del_exp_parser.add_argument("id", type=int, help="ID der Ausgabe")
    del_exp_parser.add_argument("--force", action="store_true", help="Keine Rückfrage")
    del_exp_parser.set_defaults(func=cmd_delete_expense)

    # delete income
    del_inc_parser = delete_subparsers.add_parser("income", help="Einnahme löschen")
    del_inc_parser.add_argument("id", type=int, help="ID der Einnahme")
    del_inc_parser.add_argument("--force", action="store_true", help="Keine Rückfrage")
    del_inc_parser.set_defaults(func=cmd_delete_income)

    # --- export ---
    export_parser = subparsers.add_parser("export", help="Exportiert Daten")
    export_parser.add_argument("--year", type=int, help="Jahr (default: aktuelles)")
    export_parser.add_argument("--format", choices=["csv", "xlsx"], default="xlsx")
    export_parser.add_argument(
        "--output", default=str(DEFAULT_EXPORT_DIR), help="Ausgabeverzeichnis"
    )
    export_parser.set_defaults(func=cmd_export)

    # --- summary ---
    summary_parser = subparsers.add_parser("summary", help="Zeigt Zusammenfassung")
    summary_parser.add_argument("--year", type=int, help="Jahr (default: aktuelles)")
    summary_parser.set_defaults(func=cmd_summary)

    # --- audit ---
    audit_parser = subparsers.add_parser("audit", help="Zeigt Änderungshistorie")
    audit_parser.add_argument("id", type=int, help="Datensatz-ID")
    audit_parser.add_argument(
        "--table",
        choices=["expenses", "income"],
        default="expenses",
        help="Tabelle (default: expenses)",
    )
    audit_parser.set_defaults(func=cmd_audit)

    # --- config ---
    config_parser = subparsers.add_parser("config", help="Konfiguration verwalten")
    config_subparsers = config_parser.add_subparsers(dest="action", required=True)

    # config show
    config_show_parser = config_subparsers.add_parser(
        "show", help="Zeigt aktuelle Konfiguration"
    )
    config_show_parser.set_defaults(func=cmd_config_show)

    # --- receipt ---
    receipt_parser = subparsers.add_parser("receipt", help="Beleg-Verwaltung")
    receipt_subparsers = receipt_parser.add_subparsers(dest="action", required=True)

    # receipt check
    receipt_check_parser = receipt_subparsers.add_parser(
        "check", help="Prüft Transaktionen auf fehlende Belege"
    )
    receipt_check_parser.add_argument(
        "--year", type=int, help="Jahr (default: aktuelles)"
    )
    receipt_check_parser.add_argument(
        "--type", choices=["expense", "income"], help="Nur diesen Typ prüfen"
    )
    receipt_check_parser.set_defaults(func=cmd_receipt_check)

    # receipt open
    receipt_open_parser = receipt_subparsers.add_parser(
        "open", help="Öffnet Beleg einer Transaktion"
    )
    receipt_open_parser.add_argument("id", type=int, help="Transaktions-ID")
    receipt_open_parser.add_argument(
        "--table",
        choices=["expenses", "income"],
        default="expenses",
        help="Tabelle (default: expenses)",
    )
    receipt_open_parser.set_defaults(func=cmd_receipt_open)

    # --- incomplete ---
    incomplete_parser = subparsers.add_parser(
        "incomplete", help="Unvollständige Import-Einträge"
    )
    incomplete_subparsers = incomplete_parser.add_subparsers(
        dest="action", required=True
    )
    incomplete_list_parser = incomplete_subparsers.add_parser(
        "list", help="Listet unvollständige Einträge"
    )
    incomplete_list_parser.add_argument(
        "--type", choices=["expense", "income", "unknown"], help="Typ filtern"
    )
    incomplete_list_parser.add_argument("--year", type=int, help="Jahr filtern")
    incomplete_list_parser.add_argument(
        "--format", choices=["table", "csv"], default="table"
    )
    incomplete_list_parser.set_defaults(func=cmd_incomplete_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
