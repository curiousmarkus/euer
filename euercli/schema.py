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
    vat_input REAL,
    vat_output REAL,
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
    vat_output REAL,
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
    vat_input REAL,
    vat_output REAL,
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
