SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    eur_line INTEGER,
    type TEXT NOT NULL CHECK(type IN ('expense', 'income'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_name_type ON categories(name, type);

CREATE TABLE IF NOT EXISTS expenses (
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
);

CREATE INDEX IF NOT EXISTS idx_expenses_payment_date ON expenses(payment_date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
CREATE INDEX IF NOT EXISTS idx_expenses_vendor ON expenses(vendor);

CREATE TABLE IF NOT EXISTS income (
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
);

CREATE INDEX IF NOT EXISTS idx_income_payment_date ON income(payment_date);
CREATE INDEX IF NOT EXISTS idx_income_category ON income(category_id);

CREATE TABLE IF NOT EXISTS private_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    date DATE NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('deposit', 'withdrawal')),
    amount_eur REAL NOT NULL CHECK(amount_eur > 0),
    description TEXT NOT NULL,
    notes TEXT,
    related_expense_id INTEGER REFERENCES expenses(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash TEXT UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_private_transfers_date ON private_transfers(date);
CREATE INDEX IF NOT EXISTS idx_private_transfers_type ON private_transfers(type);
CREATE INDEX IF NOT EXISTS idx_private_transfers_related_expense ON private_transfers(related_expense_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    record_uuid TEXT,
    action TEXT NOT NULL CHECK(action IN ('INSERT', 'UPDATE', 'DELETE', 'MIGRATE')),
    old_data TEXT,
    new_data TEXT,
    user TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
"""

SEED_CATEGORIES = [
    # EÜR-Zeilen folgen den ELSTER-Positionen; diese Liste ist die maßgebliche Quelle.
    ("Waren, Rohstoffe und Hilfsstoffe", 27, "expense"),
    ("Bezogene Fremdleistungen", 29, "expense"),
    ("Aufwendungen für geringwertige Wirtschaftsgüter (GWG)", 36, "expense"),
    ("Telekommunikation", 43, "expense"),
    ("Übernachtungs- und Reisenebenkosten", 44, "expense"),
    ("Fortbildungskosten", 45, "expense"),
    ("Rechts- und Steuerberatung, Buchführung", 46, "expense"),
    ("Beiträge, Gebühren, Abgaben und Versicherungen", 49, "expense"),
    ("Laufende EDV-Kosten", 50, "expense"),
    ("Arbeitsmittel", 51, "expense"),
    ("Werbekosten", 54, "expense"),
    ("Gezahlte USt", 57, "expense"),
    ("Übrige Betriebsausgaben", 60, "expense"),
    ("Bewirtungsaufwendungen", 63, "expense"),
    ("Verpflegungsmehraufwendungen", 64, "expense"),
    ("Fahrtkosten (Nutzungseinlage)", 71, "expense"),
    ("Betriebseinnahmen als Kleinunternehmer", 12, "income"),
    ("Nicht steuerbare Umsätze", 13, "income"),
    ("Umsatzsteuerpflichtige Betriebseinnahmen", 15, "income"),
    ("Umsatzsteuerfreie, nicht umsatzsteuerbare Betriebseinnahmen", 16, "income"),
    ("Vereinnahmte Umsatzsteuer", 17, "income"),
    ("Vom Finanzamt erstattete Umsatzsteuer", 18, "income"),
    ("Veräußerung oder Entnahme von Anlagevermögen", 19, "income"),
    ("Private Kfz-Nutzung", 20, "income"),
    ("Sonstige Sach-, Nutzungs- und Leistungsentnahmen", 21, "income"),
]
