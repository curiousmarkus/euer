"""Transaktionale Datenbank-Migrations-Engine (Spec 020)."""

import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Callable

from .schema import SCHEMA, SEED_CATEGORIES
from .services.eur import category_key_for_name


@dataclass
class MigrationImpact:
    affected_count: int = 0
    affected_ids: list[int] = field(default_factory=list)
    description: str = ""
    next_steps: list[str] = field(default_factory=list)


@dataclass
class Migration:
    id: str
    name: str
    preflight: Callable[[sqlite3.Connection], MigrationImpact]
    apply: Callable[[sqlite3.Connection], None]


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> dict[str, dict]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        result = {}
        for row in rows:
            name = row["name"] if hasattr(row, "keys") else row[1]
            data = (
                dict(row)
                if hasattr(row, "keys")
                else {
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "notnull": row[3],
                    "dflt_value": row[4],
                    "pk": row[5],
                }
            )
            result[name] = data
        return result
    except Exception:
        return {}


def _get_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


# --- Preflights & Applies für Kern-Migrationen ---


def _preflight_001(conn: sqlite3.Connection) -> MigrationImpact:
    return MigrationImpact(
        affected_count=0,
        description="Erstellt Basistabellen und seeder Kategorien",
    )


def _apply_001(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    for name, eur_line, cat_type in SEED_CATEGORIES:
        eur_key = category_key_for_name(name, cat_type)
        exists = conn.execute(
            "SELECT 1 FROM categories WHERE name = ? AND type = ?",
            (name, cat_type),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO categories (uuid, name, eur_line, eur_key, type) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), name, eur_line, eur_key, cat_type),
            )


def _preflight_002(conn: sqlite3.Connection) -> MigrationImpact:
    exp_cols = _get_table_columns(conn, "expenses")
    inc_cols = _get_table_columns(conn, "income")
    needed = (
        "date" in exp_cols
        or "invoice_date" not in exp_cols
        or exp_cols.get("payment_date", {}).get("notnull") == 1
        or "rc_type" not in exp_cols
        or "is_rc" in exp_cols
        or "date" in inc_cols
        or "invoice_date" not in inc_cols
    )
    return MigrationImpact(
        affected_count=1 if needed else 0,
        description="Stellt Ausgaben und Einnahmen auf Wertstellungs- und Rechnungsdatum sowie rc_type um",
    )


def _apply_002(conn: sqlite3.Connection) -> None:
    # Migration Wertstellungs- und Rechnungsdatum (Spec 006)
    expense_columns = _get_table_columns(conn, "expenses")
    income_columns = _get_table_columns(conn, "income")

    migrate_expenses = (
        "date" in expense_columns
        or "invoice_date" not in expense_columns
        or expense_columns.get("payment_date", {}).get("notnull") == 1
        or "rc_type" not in expense_columns
        or "is_rc" in expense_columns
        or "rc_jurisdiction" in expense_columns
    )
    migrate_income = (
        "date" in income_columns
        or "invoice_date" not in income_columns
        or income_columns.get("payment_date", {}).get("notnull") == 1
    )

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        if migrate_expenses:
            payment_expr = "payment_date" if "payment_date" in expense_columns else "date"
            invoice_expr = "invoice_date" if "invoice_date" in expense_columns else "NULL"
            is_private_paid_expr = (
                "is_private_paid" if "is_private_paid" in expense_columns else "0"
            )
            ledger_account_expr = (
                "ledger_account" if "ledger_account" in expense_columns else "NULL"
            )
            vat_rate_expr = "vat_rate" if "vat_rate" in expense_columns else "NULL"
            vat_code_expr = "vat_code" if "vat_code" in expense_columns else "NULL"
            if "rc_type" in expense_columns:
                rc_type_expr = "rc_type"
            elif "is_rc" in expense_columns:
                rc_jurisdiction_expr = (
                    "rc_jurisdiction" if "rc_jurisdiction" in expense_columns else "NULL"
                )
                rc_type_expr = (
                    "CASE "
                    "WHEN COALESCE(is_rc, 0) = 0 THEN 'none' "
                    f"WHEN {rc_jurisdiction_expr} IN ('eu', 'third_country') "
                    f"THEN {rc_jurisdiction_expr} "
                    "ELSE 'unclassified' END"
                )
            else:
                rc_type_expr = "'none'"
            private_classification_expr = (
                "private_classification"
                if "private_classification" in expense_columns
                else "'none'"
            )

            conn.execute("ALTER TABLE expenses RENAME TO expenses_old")
            conn.execute(
                """
                CREATE TABLE expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    receipt_name TEXT,
                    payment_date DATE,
                    invoice_date DATE,
                    vendor TEXT NOT NULL,
                    category_id INTEGER REFERENCES categories(id),
                    amount_eur REAL NOT NULL,
                    account TEXT,
                    ledger_account TEXT,
                    foreign_amount TEXT,
                    notes TEXT,
                    rc_type TEXT NOT NULL DEFAULT 'none'
                        CHECK(rc_type IN ('none', 'eu', 'third_country', 'unclassified')),
                    vat_input REAL,
                    vat_output REAL,
                    vat_rate REAL CHECK(vat_rate IS NULL OR vat_rate IN (0, 7, 19)),
                    vat_code TEXT CHECK(vat_code IS NULL OR vat_code IN (
                        'input_invoice',
                        'reverse_charge_eu',
                        'reverse_charge_third_country'
                    )),
                    is_private_paid INTEGER NOT NULL DEFAULT 0 CHECK(is_private_paid IN (0, 1)),
                    private_classification TEXT NOT NULL DEFAULT 'none'
                        CHECK(private_classification IN (
                            'none', 'account_rule', 'category_rule', 'manual'
                        )),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hash TEXT UNIQUE NOT NULL,
                    CHECK(invoice_date IS NOT NULL OR payment_date IS NOT NULL)
                )
                """
            )
            conn.execute(
                f"""
                INSERT INTO expenses (
                    id, uuid, receipt_name, payment_date, invoice_date, vendor, category_id,
                    amount_eur, account, ledger_account, foreign_amount, notes, rc_type,
                    vat_input, vat_output, vat_rate, vat_code,
                    is_private_paid, private_classification, created_at, hash
                )
                SELECT
                    id, uuid, receipt_name, {payment_expr}, {invoice_expr}, vendor, category_id,
                    amount_eur, account, {ledger_account_expr}, foreign_amount, notes,
                    {rc_type_expr}, vat_input, vat_output, {vat_rate_expr}, {vat_code_expr},
                    {is_private_paid_expr}, {private_classification_expr}, created_at, hash
                FROM expenses_old
                """
            )
            conn.execute("DROP TABLE expenses_old")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expenses_payment_date ON expenses(payment_date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_vendor ON expenses(vendor)")

        if migrate_income:
            payment_expr = "payment_date" if "payment_date" in income_columns else "date"
            invoice_expr = "invoice_date" if "invoice_date" in income_columns else "NULL"
            ledger_account_expr = "ledger_account" if "ledger_account" in income_columns else "NULL"
            vat_rate_expr = "vat_rate" if "vat_rate" in income_columns else "NULL"
            vat_code_expr = "vat_code" if "vat_code" in income_columns else "NULL"

            conn.execute("ALTER TABLE income RENAME TO income_old")
            conn.execute(
                """
                CREATE TABLE income (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    receipt_name TEXT,
                    payment_date DATE,
                    invoice_date DATE,
                    source TEXT NOT NULL,
                    category_id INTEGER REFERENCES categories(id),
                    amount_eur REAL NOT NULL,
                    ledger_account TEXT,
                    foreign_amount TEXT,
                    notes TEXT,
                    vat_output REAL,
                    vat_rate REAL CHECK(vat_rate IS NULL OR vat_rate IN (0, 7, 19)),
                    vat_code TEXT CHECK(vat_code IS NULL OR vat_code IN (
                        'output_standard_19',
                        'output_reduced_7',
                        'output_zero_0',
                        'output_tax_free_no_vorsteuer'
                    )),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hash TEXT UNIQUE NOT NULL,
                    CHECK(invoice_date IS NOT NULL OR payment_date IS NOT NULL)
                )
                """
            )
            conn.execute(
                f"""
                INSERT INTO income (
                    id, uuid, receipt_name, payment_date, invoice_date, source, category_id,
                    amount_eur, ledger_account, foreign_amount, notes,
                    vat_output, vat_rate, vat_code, created_at, hash
                )
                SELECT
                    id, uuid, receipt_name, {payment_expr}, {invoice_expr}, source, category_id,
                    amount_eur, {ledger_account_expr}, foreign_amount, notes,
                    vat_output, {vat_rate_expr}, {vat_code_expr}, created_at, hash
                FROM income_old
                """
            )
            conn.execute("DROP TABLE income_old")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_income_payment_date ON income(payment_date)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_income_category ON income(category_id)")
    finally:
        conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("DROP INDEX IF EXISTS idx_expenses_date")
    conn.execute("DROP INDEX IF EXISTS idx_income_date")


def _preflight_003(conn: sqlite3.Connection) -> MigrationImpact:
    cols = _get_table_columns(conn, "expenses")
    needed = "is_private_paid" not in cols or "private_classification" not in cols
    return MigrationImpact(
        affected_count=1 if needed else 0,
        description="Ergänzt Spalten für Privatauslagen (Spec 008)",
    )


def _apply_003(conn: sqlite3.Connection) -> None:
    cols = _get_table_columns(conn, "expenses")
    if "is_private_paid" not in cols:
        conn.execute(
            "ALTER TABLE expenses ADD COLUMN is_private_paid INTEGER NOT NULL DEFAULT 0 "
            "CHECK(is_private_paid IN (0, 1))"
        )
    if "private_classification" not in cols:
        conn.execute(
            "ALTER TABLE expenses ADD COLUMN private_classification TEXT NOT NULL DEFAULT 'none' "
            "CHECK(private_classification IN ('none', 'account_rule', 'category_rule', 'manual'))"
        )


def _preflight_004(conn: sqlite3.Connection) -> MigrationImpact:
    exp_cols = _get_table_columns(conn, "expenses")
    inc_cols = _get_table_columns(conn, "income")
    needed = "ledger_account" not in exp_cols or "ledger_account" not in inc_cols
    return MigrationImpact(
        affected_count=1 if needed else 0,
        description="Ergänzt Buchungskonten (Spec 010)",
    )


def _apply_004(conn: sqlite3.Connection) -> None:
    exp_cols = _get_table_columns(conn, "expenses")
    inc_cols = _get_table_columns(conn, "income")
    if "ledger_account" not in exp_cols:
        conn.execute("ALTER TABLE expenses ADD COLUMN ledger_account TEXT")
    if "ledger_account" not in inc_cols:
        conn.execute("ALTER TABLE income ADD COLUMN ledger_account TEXT")


def _preflight_005(conn: sqlite3.Connection) -> MigrationImpact:
    exp_cols = _get_table_columns(conn, "expenses")
    needed = "vat_rate" not in exp_cols or "vat_code" not in exp_cols
    return MigrationImpact(
        affected_count=1 if needed else 0,
        description="Ergänzt USt-Klassifikationsspalten (Spec 012)",
    )


def _apply_005(conn: sqlite3.Connection) -> None:
    exp_cols = _get_table_columns(conn, "expenses")
    inc_cols = _get_table_columns(conn, "income")
    if "vat_rate" not in exp_cols:
        conn.execute(
            "ALTER TABLE expenses ADD COLUMN vat_rate REAL "
            "CHECK(vat_rate IS NULL OR vat_rate IN (0, 7, 19))"
        )
    if "vat_code" not in exp_cols:
        conn.execute(
            "ALTER TABLE expenses ADD COLUMN vat_code TEXT "
            "CHECK(vat_code IS NULL OR vat_code IN ("
            "'input_invoice', 'reverse_charge_eu', 'reverse_charge_third_country'))"
        )
    if "vat_rate" not in inc_cols:
        conn.execute(
            "ALTER TABLE income ADD COLUMN vat_rate REAL "
            "CHECK(vat_rate IS NULL OR vat_rate IN (0, 7, 19))"
        )
    if "vat_code" not in inc_cols:
        conn.execute(
            "ALTER TABLE income ADD COLUMN vat_code TEXT "
            "CHECK(vat_code IS NULL OR vat_code IN ("
            "'output_standard_19', 'output_reduced_7', 'output_zero_0', "
            "'output_tax_free_no_vorsteuer'))"
        )


def _preflight_006(conn: sqlite3.Connection) -> MigrationImpact:
    # Prüft, wie viele Bewirtungsbuchungen auf 'needs_review' gesetzt werden (Spec 018 / 020)
    tables = _get_tables(conn)
    if "expenses" not in tables or "categories" not in tables:
        return MigrationImpact()
    cols = _get_table_columns(conn, "expenses")
    has_status_col = "entertainment_vat_status" in cols

    # Bewirtungskategorien finden
    cat_query = "SELECT id FROM categories WHERE name LIKE '%Bewirtung%'"
    cat_cols = _get_table_columns(conn, "categories")
    if "eur_key" in cat_cols:
        cat_query = (
            "SELECT id FROM categories WHERE eur_key = 'entertainment' OR name LIKE '%Bewirtung%'"
        )

    cat_rows = conn.execute(cat_query).fetchall()
    cat_ids = [r[0] for r in cat_rows]
    if not cat_ids:
        return MigrationImpact(description="Bewirtungsspalten ergänzen (Spec 018)")

    placeholders = ",".join("?" for _ in cat_ids)
    if has_status_col:
        query = (
            f"SELECT id FROM expenses WHERE category_id IN ({placeholders}) "
            f"AND entertainment_vat_status IS NULL ORDER BY id"
        )
    else:
        query = f"SELECT id FROM expenses WHERE category_id IN ({placeholders}) ORDER BY id"

    rows = conn.execute(query, cat_ids).fetchall()
    affected_ids = [r[0] for r in rows]

    next_steps = []
    if affected_ids:
        next_steps = [
            "Führe 'euer incomplete list' aus.",
            "Prüfe die Belege der betroffenen Buchungen auf ausgewiesene Vorsteuer.",
            "Pflege die Vorsteuer nach mit: euer update expense <ID> --vat <BETRAG>",
        ]

    return MigrationImpact(
        affected_count=len(affected_ids),
        affected_ids=affected_ids,
        description="Bewirtungsaufwendungen & Vorsteuerstatus ergänzen (Spec 018)",
        next_steps=next_steps,
    )


def _apply_006(conn: sqlite3.Connection) -> None:
    cols = _get_table_columns(conn, "expenses")
    if "entertainment_tip_eur" not in cols:
        conn.execute(
            "ALTER TABLE expenses ADD COLUMN entertainment_tip_eur REAL "
            "CHECK(entertainment_tip_eur IS NULL OR entertainment_tip_eur >= 0)"
        )
    if "entertainment_vat_status" not in cols:
        conn.execute(
            "ALTER TABLE expenses ADD COLUMN entertainment_vat_status TEXT "
            "CHECK(entertainment_vat_status IS NULL OR entertainment_vat_status IN "
            "('deductible', 'no_deduction', 'needs_review'))"
        )

    # Status auf needs_review setzen für bestehende Bewirtungen
    cat_cols = _get_table_columns(conn, "categories")
    cat_clause = (
        "eur_key = 'entertainment' OR name LIKE '%Bewirtung%'"
        if "eur_key" in cat_cols
        else "name LIKE '%Bewirtung%'"
    )
    conn.execute(
        f"""
        UPDATE expenses
        SET entertainment_vat_status = 'needs_review'
        WHERE category_id IN (
            SELECT id FROM categories WHERE {cat_clause}
        )
        AND entertainment_vat_status IS NULL
        """
    )


def _preflight_007(conn: sqlite3.Connection) -> MigrationImpact:
    cols = _get_table_columns(conn, "categories")
    needed = "eur_key" not in cols
    return MigrationImpact(
        affected_count=1 if needed else 0,
        description="Fachlicher EÜR-Schlüssel für Kategorien (Spec 018)",
    )


def _apply_007(conn: sqlite3.Connection) -> None:
    cols = _get_table_columns(conn, "categories")
    if "eur_key" not in cols:
        conn.execute("ALTER TABLE categories ADD COLUMN eur_key TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_eur_key "
        "ON categories(type, eur_key) WHERE eur_key IS NOT NULL"
    )

    # Fix Zeile 14 -> 15 für USt-pflichtige Betriebseinnahmen
    conn.execute(
        "UPDATE categories SET eur_line = 15 WHERE name = ? AND type = ? AND eur_line = 14",
        ("Umsatzsteuerpflichtige Betriebseinnahmen", "income"),
    )

    for name, eur_line, cat_type in SEED_CATEGORIES:
        eur_key = category_key_for_name(name, cat_type)
        exists = conn.execute(
            "SELECT 1 FROM categories WHERE name = ? AND type = ?",
            (name, cat_type),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO categories (uuid, name, eur_line, eur_key, type) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), name, eur_line, eur_key, cat_type),
            )
        if eur_key is not None:
            conn.execute(
                "UPDATE categories SET eur_key = ? WHERE name = ? AND type = ? "
                "AND (eur_key IS NULL OR eur_key = ?)",
                (eur_key, name, cat_type, eur_key),
            )


def _preflight_008(conn: sqlite3.Connection) -> MigrationImpact:
    tables = _get_tables(conn)
    exp_cols = _get_table_columns(conn, "expenses") if "expenses" in tables else {}
    inc_cols = _get_table_columns(conn, "income") if "income" in tables else {}
    priv_cols = _get_table_columns(conn, "private_transfers") if "private_transfers" in tables else {}
    needed = (
        ("expenses" in tables and "deleted_at" not in exp_cols)
        or ("income" in tables and "deleted_at" not in inc_cols)
        or ("private_transfers" in tables and "deleted_at" not in priv_cols)
    )
    return MigrationImpact(
        affected_count=1 if needed else 0,
        description="Fügt deleted_at Spalte zu expenses, income und private_transfers für Soft-Delete hinzu",
    )


def _apply_008(conn: sqlite3.Connection) -> None:
    tables = _get_tables(conn)
    if "expenses" in tables:
        exp_cols = _get_table_columns(conn, "expenses")
        if "deleted_at" not in exp_cols:
            conn.execute("ALTER TABLE expenses ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expenses_deleted_at ON expenses(deleted_at)"
            )

    if "income" in tables:
        inc_cols = _get_table_columns(conn, "income")
        if "deleted_at" not in inc_cols:
            conn.execute("ALTER TABLE income ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_income_deleted_at ON income(deleted_at)")

    if "private_transfers" in tables:
        priv_cols = _get_table_columns(conn, "private_transfers")
        if "deleted_at" not in priv_cols:
            conn.execute("ALTER TABLE private_transfers ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_private_transfers_deleted_at ON private_transfers(deleted_at)"
            )


# Registrierte Migrationen in sequentieller Reihenfolge
MIGRATIONS: list[Migration] = [
    Migration(
        "001_initial_schema", "Basis-Tabellen und Standardkategorien", _preflight_001, _apply_001
    ),
    Migration(
        "002_payment_invoice_dates",
        "Wertstellungs- und Rechnungsdatum trennen (Spec 006)",
        _preflight_002,
        _apply_002,
    ),
    Migration(
        "003_private_columns", "Spalten für Privatauslagen (Spec 008)", _preflight_003, _apply_003
    ),
    Migration(
        "004_ledger_accounts", "Buchungskonten je Kategorie (Spec 010)", _preflight_004, _apply_004
    ),
    Migration(
        "005_vat_classifications",
        "Umsatzsteuer-Klassifikation (Spec 012)",
        _preflight_005,
        _apply_005,
    ),
    Migration(
        "006_entertainment_fields",
        "Bewirtungsaufwendungen & Vorsteuerstatus (Spec 018)",
        _preflight_006,
        _apply_006,
    ),
    Migration(
        "007_category_eur_key",
        "Fachlicher EÜR-Schlüssel für Kategorien (Spec 018)",
        _preflight_007,
        _apply_007,
    ),
    Migration(
        "008_soft_delete",
        "Soft-Delete Unterstützung für Ausgaben, Einnahmen und Privatvorgänge (Spec 016)",
        _preflight_008,
        _apply_008,
    ),
]


def init_migration_table(conn: sqlite3.Connection) -> None:
    """Stellt sicher, dass die Migrationstabelle existiert."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def get_applied_migrations(conn: sqlite3.Connection) -> set[str]:
    """Liefert die Menge aller bereits erfassten Migrations-IDs."""
    tables = _get_tables(conn)
    if "_schema_migrations" not in tables:
        return set()
    rows = conn.execute("SELECT version FROM _schema_migrations").fetchall()
    return {row["version"] for row in rows}


def detect_legacy_schema_state(conn: sqlite3.Connection) -> tuple[str, list[str]]:
    """Ermittelt für Legacy-DBs ohne _schema_migrations den abgeleiteten Stand.

    Returns:
        (status_text, list_of_satisfied_migration_ids)
    """
    tables = _get_tables(conn)
    if not tables or "categories" not in tables or "expenses" not in tables:
        return ("uninitialisiert", [])

    exp_cols = _get_table_columns(conn, "expenses")
    inc_cols = _get_table_columns(conn, "income")
    cat_cols = _get_table_columns(conn, "categories")

    satisfied: list[str] = ["001_initial_schema"]

    exp_002 = (
        "payment_date" in exp_cols
        and "date" not in exp_cols
        and "rc_type" in exp_cols
        and "is_rc" not in exp_cols
        and exp_cols.get("payment_date", {}).get("notnull") != 1
    )
    inc_002 = (
        "payment_date" in inc_cols
        and "date" not in inc_cols
        and "invoice_date" in inc_cols
        and inc_cols.get("payment_date", {}).get("notnull") != 1
    )
    if exp_002 and inc_002:
        satisfied.append("002_payment_invoice_dates")
    if "is_private_paid" in exp_cols:
        satisfied.append("003_private_columns")
    if "ledger_account" in exp_cols:
        satisfied.append("004_ledger_accounts")
    if "vat_rate" in exp_cols and "vat_code" in exp_cols:
        satisfied.append("005_vat_classifications")
    if "entertainment_vat_status" in exp_cols:
        satisfied.append("006_entertainment_fields")
    if "eur_key" in cat_cols:
        satisfied.append("007_category_eur_key")
    if "deleted_at" in exp_cols and "deleted_at" in inc_cols:
        satisfied.append("008_soft_delete")

    current_version = satisfied[-1] if satisfied else "unbekannt"
    return (f"{current_version} (abgeleitet)", satisfied)


def get_migration_plan(
    conn: sqlite3.Connection,
) -> tuple[str, str, list[tuple[Migration, MigrationImpact]], list[str]]:
    """Erstellt den Migrationsplan für die übergebene DB.

    Returns:
        (current_schema, target_schema, pending_migrations_with_impact, legacy_stamps)
    """
    init_migration_table(conn)
    applied = get_applied_migrations(conn)

    legacy_stamps: list[str] = []
    if not applied:
        state_desc, legacy_stamps = detect_legacy_schema_state(conn)
        applied = set(legacy_stamps)
        current_schema = state_desc
    else:
        # Finde höchste angewendete Version
        known_applied = [m.id for m in MIGRATIONS if m.id in applied]
        current_schema = known_applied[-1] if known_applied else "000_empty"

    pending: list[tuple[Migration, MigrationImpact]] = []
    for migration in MIGRATIONS:
        if migration.id not in applied:
            impact = migration.preflight(conn)
            pending.append((migration, impact))

    target_schema = MIGRATIONS[-1].id if MIGRATIONS else current_schema
    if not pending:
        target_schema = current_schema

    return (current_schema, target_schema, pending, legacy_stamps)
