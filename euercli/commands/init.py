import uuid
from pathlib import Path

from ..config import get_export_dir, load_config
from ..constants import DEFAULT_EXPORT_DIR
from ..db import get_db_connection
from ..schema import SCHEMA, SEED_CATEGORIES


def _get_table_columns(conn, table_name: str) -> dict[str, dict]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"]: dict(row) for row in rows}


def _migrate_expenses_dates(conn) -> None:
    columns = _get_table_columns(conn, "expenses")
    payment_expr = "payment_date" if "payment_date" in columns else "date"
    invoice_expr = "invoice_date" if "invoice_date" in columns else "NULL"
    is_private_paid_expr = "is_private_paid" if "is_private_paid" in columns else "0"
    ledger_account_expr = "ledger_account" if "ledger_account" in columns else "NULL"
    private_classification_expr = (
        "private_classification" if "private_classification" in columns else "'none'"
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
            is_rc INTEGER NOT NULL DEFAULT 0,
            vat_input REAL,
            vat_output REAL,
            is_private_paid INTEGER NOT NULL DEFAULT 0 CHECK(is_private_paid IN (0, 1)),
            private_classification TEXT NOT NULL DEFAULT 'none'
                CHECK(private_classification IN ('none', 'account_rule', 'category_rule', 'manual')),
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
            amount_eur, account, ledger_account, foreign_amount, notes, is_rc, vat_input,
            vat_output,
            is_private_paid, private_classification, created_at, hash
        )
        SELECT
            id, uuid, receipt_name, {payment_expr}, {invoice_expr}, vendor, category_id,
            amount_eur, account, {ledger_account_expr}, foreign_amount, notes, is_rc,
            vat_input, vat_output,
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


def _migrate_income_dates(conn) -> None:
    columns = _get_table_columns(conn, "income")
    payment_expr = "payment_date" if "payment_date" in columns else "date"
    invoice_expr = "invoice_date" if "invoice_date" in columns else "NULL"
    ledger_account_expr = "ledger_account" if "ledger_account" in columns else "NULL"

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
            amount_eur, ledger_account, foreign_amount, notes, vat_output, created_at, hash
        )
        SELECT
            id, uuid, receipt_name, {payment_expr}, {invoice_expr}, source, category_id,
            amount_eur, {ledger_account_expr}, foreign_amount, notes, vat_output, created_at,
            hash
        FROM income_old
        """
    )
    conn.execute("DROP TABLE income_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_income_payment_date ON income(payment_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_income_category ON income(category_id)")


def ensure_payment_invoice_columns(conn) -> None:
    expense_columns = _get_table_columns(conn, "expenses")
    income_columns = _get_table_columns(conn, "income")

    # Migration ist nötig wenn:
    # - Altes Schema mit 'date'-Spalte statt 'payment_date' vorliegt
    # - 'invoice_date'-Spalte fehlt (Spec 006 noch nicht migriert)
    # - 'payment_date' als NOT NULL definiert ist (muss nullable sein,
    #   da Buchungen auch nur mit invoice_date erfasst werden können)
    migrate_expenses = (
        "date" in expense_columns
        or "invoice_date" not in expense_columns
        or expense_columns.get("payment_date", {}).get("notnull") == 1
    )
    migrate_income = (
        "date" in income_columns
        or "invoice_date" not in income_columns
        or income_columns.get("payment_date", {}).get("notnull") == 1
    )

    if not migrate_expenses and not migrate_income:
        conn.execute("DROP INDEX IF EXISTS idx_expenses_date")
        conn.execute("DROP INDEX IF EXISTS idx_income_date")
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        if migrate_expenses:
            _migrate_expenses_dates(conn)
        if migrate_income:
            _migrate_income_dates(conn)
    finally:
        conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("DROP INDEX IF EXISTS idx_expenses_date")
    conn.execute("DROP INDEX IF EXISTS idx_income_date")
    conn.commit()


def ensure_expenses_private_columns(conn) -> None:
    """Ergänzt fehlende private-Spalten in bestehenden Datenbanken."""
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
    }
    if "is_private_paid" not in columns:
        conn.execute(
            """ALTER TABLE expenses ADD COLUMN
               is_private_paid INTEGER NOT NULL DEFAULT 0 CHECK(is_private_paid IN (0, 1))"""
        )
    if "private_classification" not in columns:
        conn.execute(
            """ALTER TABLE expenses ADD COLUMN
               private_classification TEXT NOT NULL DEFAULT 'none'"""
        )


def ensure_ledger_account_columns(conn) -> None:
    """Ergänzt fehlende ledger_account-Spalten in bestehenden Datenbanken."""
    expense_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
    }
    income_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(income)").fetchall()
    }
    if "ledger_account" not in expense_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN ledger_account TEXT")
    if "ledger_account" not in income_columns:
        conn.execute("ALTER TABLE income ADD COLUMN ledger_account TEXT")


def ensure_seed_categories(conn) -> None:
    """Ergänzt fehlende Seed-Kategorien und korrigiert EÜR-Zeilen in bestehenden DBs."""
    # Fix: "Umsatzsteuerpflichtige Betriebseinnahmen" war fälschlich auf Zeile 14 (→ 15)
    conn.execute(
        "UPDATE categories SET eur_line = 15 WHERE name = ? AND type = ? AND eur_line = 14",
        ("Umsatzsteuerpflichtige Betriebseinnahmen", "income"),
    )

    added = 0
    for name, eur_line, cat_type in SEED_CATEGORIES:
        exists = conn.execute(
            "SELECT 1 FROM categories WHERE name = ? AND type = ?",
            (name, cat_type),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO categories (uuid, name, eur_line, type) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), name, eur_line, cat_type),
            )
            added += 1

    if added:
        conn.commit()
        print(f"  {added} neue Kategorie(n) ergänzt")


def cmd_init(args):
    """Initialisiert die Datenbank."""
    db_path = Path(args.db)

    print(f"Initialisiere Datenbank: {db_path}")

    conn = get_db_connection(db_path)
    conn.executescript(SCHEMA)
    ensure_payment_invoice_columns(conn)
    ensure_expenses_private_columns(conn)
    ensure_ledger_account_columns(conn)

    # Kategorien seeden (nur wenn leer) oder fehlende ergänzen
    existing = conn.execute("SELECT COUNT(*) as cnt FROM categories").fetchone()["cnt"]
    if existing == 0:
        print("Seede Kategorien...")
        for name, eur_line, cat_type in SEED_CATEGORIES:
            conn.execute(
                "INSERT INTO categories (uuid, name, eur_line, type) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), name, eur_line, cat_type),
            )
        conn.commit()
        print(f"  {len(SEED_CATEGORIES)} Kategorien angelegt")
    else:
        print(f"  Kategorien existieren bereits ({existing})")
        ensure_seed_categories(conn)

    conn.close()

    config = load_config()
    export_dir = get_export_dir(config)
    if export_dir:
        export_path = Path(export_dir)
        export_path.mkdir(exist_ok=True)
        print(f"Export-Verzeichnis: {export_path}")
    else:
        DEFAULT_EXPORT_DIR.mkdir(exist_ok=True)
        print(f"Export-Verzeichnis: {DEFAULT_EXPORT_DIR}")

    print("Fertig.")
