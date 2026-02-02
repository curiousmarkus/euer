# Buchungs-Ledger (EÜR) - Spezifikation

## Status
**Implemented** (2026-01-31)

## Zusammenfassung

Ersetzt die Excel-basierte EÜR durch eine SQLite-Datenbank mit CLI-Interface.
Single-User, lokal, keine Netzwerk-Komponenten.

**Autor:** Markus Keller  
**Zielgruppe für dieses Dokument:** Coding Agent / LLM  
**Stand:** 2026-01-31

---

## Kontext

### Steuerlicher Hintergrund
- **Kleinunternehmer** (nicht umsatzsteuerpflichtig nach §19 UStG)
- **Reverse Charge (RC)** bei Ausgaben in Fremdwährung / von ausländischen Anbietern
- EÜR = Einnahmen-Überschuss-Rechnung (vereinfachte Buchführung)

### Bestehende Lösung (wird ersetzt)
- Excel-Datei: `~/Dropbox/Beispielunternehmen/2026 EÜR Beispielunternehmen.xlsx`
- Sheets: "Ausgaben", "Einnahmen", "Übersicht" (Pivot)
- Belege: `~/Dropbox/Beispielunternehmen/Ausgaben-Belege/`

### Kategorisierungs-Regeln
Dokumentiert in: `/path/to/EÜR Kategorisierung.md` (intern, nicht Teil des Repos)

---

## Anforderungen

### Funktional
1. **SQLite-Datenbank** mit sauberem, normalisierten Schema
2. **Python CLI** (`ledger.py`) für alle CRUD-Operationen
3. **Idempotenz**: Duplikat-Erkennung (gleiche Transaktion nicht doppelt einfügen)
4. **Audit-Trail**: Jede Änderung wird geloggt (wer, wann, was, vorher/nachher)
5. **Export**: CSV und XLSX für Steuerberater
6. **Migration**: Einmaliger Import der bestehenden Excel-Daten (2025 + 2026)

### Nicht-Funktional
- Kein Web-UI, kein Server
- Minimal Dependencies (nur openpyxl für Excel)
- Python Standard-Library für CLI (argparse), keine externen CLI-Frameworks
- Einfach und robust, kein Over-Engineering
- Single-File CLI wenn möglich (`ledger.py`), Migration als separates Script

---

## Projektstruktur

```
~/dev/ledger/
├── ledger.py              # Haupt-CLI (alle Commands)
├── migrate_excel.py       # Einmalige Migration
├── ledger.db              # SQLite-Datenbank (wird bei init erstellt)
├── requirements.txt       # openpyxl
├── spec.md                # Diese Datei
├── README.md              # Kurze Nutzungsdoku
└── exports/               # Ausgabeverzeichnis für CSV/XLSX (wird erstellt)
```

---

## Datenbank-Schema

### Tabelle: `categories`

EÜR-Kategorien normalisiert für konsistente Zuordnung.

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- z.B. "Telekommunikation"
    eur_line INTEGER,             -- EÜR-Zeile (44, 51, etc.), NULL wenn keine
    type TEXT NOT NULL CHECK(type IN ('expense', 'income'))
);

CREATE UNIQUE INDEX idx_categories_name_type ON categories(name, type);
```

**Seed-Daten** (bei `ledger init` einfügen):

| name | eur_line | type |
|------|----------|------|
| Telekommunikation | 44 | expense |
| Laufende EDV-Kosten | 51 | expense |
| Arbeitsmittel | 52 | expense |
| Werbekosten | 54 | expense |
| Gezahlte USt | 58 | expense |
| Übrige Betriebsausgaben | 60 | expense |
| Bewirtungsaufwendungen | 63 | expense |
| Sonstige betriebsfremde Einnahme | NULL | income |
| Umsatzsteuerpflichtige Betriebseinnahmen | 14 | income |

### Tabelle: `expenses`

```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_name TEXT,                    -- Belegname (nur Dateiname, kein Pfad)
    date DATE NOT NULL,                   -- Abbuchungsdatum (YYYY-MM-DD)
    vendor TEXT NOT NULL,                 -- Lieferant/Zweck
    category_id INTEGER NOT NULL REFERENCES categories(id),
    amount_eur DECIMAL(10,2) NOT NULL,    -- Betrag in EUR (negativ = Ausgabe)
    account TEXT,                         -- Konto (N26, Sparkasse Giro, etc.)
    foreign_amount TEXT,                  -- Fremdwährung, z.B. "26.60 USD"
    notes TEXT,                           -- Bemerkung
    vat_amount DECIMAL(10,2),             -- USt-VA Betrag bei Reverse Charge
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash TEXT UNIQUE NOT NULL             -- SHA256 für Duplikat-Erkennung
);

CREATE INDEX idx_expenses_date ON expenses(date);
CREATE INDEX idx_expenses_category ON expenses(category_id);
CREATE INDEX idx_expenses_vendor ON expenses(vendor);
```

### Tabelle: `income`

```sql
CREATE TABLE income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_name TEXT,
    date DATE NOT NULL,                   -- Datum Geldeingang
    source TEXT NOT NULL,                 -- Quelle/Zweck
    category_id INTEGER NOT NULL REFERENCES categories(id),
    amount_eur DECIMAL(10,2) NOT NULL,    -- Betrag in EUR (positiv)
    foreign_amount TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash TEXT UNIQUE NOT NULL
);

CREATE INDEX idx_income_date ON income(date);
CREATE INDEX idx_income_category ON income(category_id);
```

### Tabelle: `audit_log`

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    table_name TEXT NOT NULL,             -- 'expenses' oder 'income'
    record_id INTEGER NOT NULL,           -- ID des betroffenen Datensatzes
    action TEXT NOT NULL CHECK(action IN ('INSERT', 'UPDATE', 'DELETE', 'MIGRATE')),
    old_data TEXT,                        -- JSON des vorherigen Zustands (NULL bei INSERT)
    new_data TEXT,                        -- JSON des neuen Zustands (NULL bei DELETE)
    user TEXT NOT NULL DEFAULT 'default'   -- Hardcoded für jetzt
);

CREATE INDEX idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
```

### Hash-Berechnung (Duplikat-Erkennung)

```python
import hashlib

def compute_hash(date: str, vendor_or_source: str, amount_eur: float, receipt_name: str = "") -> str:
    """
    Erzeugt einen eindeutigen Hash für eine Transaktion.
    
    Verwendet: Datum + Vendor/Source + Betrag + Belegname
    So werden identische Transaktionen (z.B. bei erneutem Import) erkannt.
    """
    data = f"{date}|{vendor_or_source}|{amount_eur:.2f}|{receipt_name or ''}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
```

**Hinweis:** Der Hash muss VOR dem Insert berechnet und geprüft werden. Bei Duplikat → Skip (kein Fehler, nur Warnung).

---

## CLI-Interface

### Grundstruktur

```bash
ledger <command> [subcommand] [options]
```

### Commands im Detail

#### `ledger init`

Erstellt die Datenbank und das Schema. Idempotent (kann mehrfach aufgerufen werden).

```bash
ledger init [--db PATH]
```

- Standard-Pfad: `./ledger.db`
- Erstellt alle Tabellen (IF NOT EXISTS)
- Seeded Kategorien (nur wenn leer)
- Erstellt `exports/` Verzeichnis

---

#### `ledger add expense`

Fügt eine Ausgabe hinzu.

```bash
ledger add expense \
    --date 2026-01-15 \
    --vendor "Render" \
    --category "Laufende EDV-Kosten" \
    --amount -15.50 \
    --account "N26" \
    [--foreign "15.00 USD"] \
    [--receipt "20260115_Render.pdf"] \
    [--notes "Hosting Jan 2026"] \
    [--vat 2.95]
```

| Argument | Required | Beschreibung |
|----------|----------|--------------|
| `--date` | Ja | YYYY-MM-DD |
| `--vendor` | Ja | Lieferant/Zweck |
| `--category` | Ja | Kategorie-Name (muss existieren) |
| `--amount` | Ja | Betrag in EUR (Konvention: negativ für Ausgaben) |
| `--account` | Nein | Bankkonto |
| `--foreign` | Nein | Fremdwährungsbetrag (z.B. "15.00 USD") |
| `--receipt` | Nein | Belegname (nur Dateiname) |
| `--notes` | Nein | Bemerkung |
| `--vat` | Nein | USt-VA Betrag (bei Reverse Charge) |

**Verhalten:**
1. Kategorie nachschlagen → Fehler wenn nicht gefunden
2. Hash berechnen
3. Prüfen ob Hash existiert → Warnung + Skip wenn ja
4. INSERT in expenses
5. Audit-Log: INSERT

---

#### `ledger add income`

Fügt eine Einnahme hinzu.

```bash
ledger add income \
    --date 2026-01-20 \
    --source "Kunde XYZ" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" \
    --amount 1500.00 \
    [--foreign "1600.00 USD"] \
    [--receipt "20260120_KundeXYZ.pdf"] \
    [--notes "Projekt ABC"]
```

---

#### `ledger list expenses`

Listet Ausgaben mit optionalen Filtern.

```bash
ledger list expenses \
    [--year 2026] \
    [--month 01] \
    [--category "Laufende EDV-Kosten"] \
    [--format table|csv]  # Default: table
```

**Output (table):**
```
ID   Date        Vendor          Category                   EUR      Account
---  ----------  --------------  -------------------------  -------  --------
1    2026-01-15  Render          Laufende EDV-Kosten (51)   -15.50   N26
2    2026-01-16  1und1           Telekommunikation (44)     -39.99   N26
...
```

---

#### `ledger list income`

Analog zu expenses.

---

#### `ledger list categories`

Zeigt alle verfügbaren Kategorien.

```bash
ledger list categories [--type expense|income]
```

---

#### `ledger update expense <id>`

Aktualisiert eine bestehende Ausgabe.

```bash
ledger update expense 42 --amount -20.00 --notes "Korrigierter Betrag"
```

- Nur die angegebenen Felder werden aktualisiert
- Hash wird NEU berechnet (wichtig!)
- Audit-Log: UPDATE mit old_data + new_data

---

#### `ledger delete expense <id>`

Löscht eine Ausgabe.

```bash
ledger delete expense 42 [--force]
```

- Ohne `--force`: Zeigt Transaktion und fragt nach Bestätigung
- Mit `--force`: Keine Rückfrage
- Audit-Log: DELETE mit old_data

---

#### `ledger export`

Exportiert Daten für den Steuerberater.

```bash
ledger export \
    [--year 2025] \
    [--format csv|xlsx]  # Default: xlsx
    [--output ./exports/]
```

**Erzeugt:**
- `EÜR_2025_Ausgaben.xlsx` (oder .csv)
- `EÜR_2025_Einnahmen.xlsx` (oder .csv)

**XLSX-Format:** Spalten wie im Original-Excel:
- Ausgaben: Belegname, Datum, Lieferant, Kategorie (mit EÜR-Zeile), Betrag EUR, Konto, Fremdwährung, Bemerkung, USt-VA
- Einnahmen: Belegname, Datum, Quelle, Kategorie, Betrag EUR, Fremdwährung, Bemerkung

---

#### `ledger summary`

Zeigt Kategorie-Summen (wie Excel "Übersicht").

```bash
ledger summary [--year 2025]
```

**Output:**
```
EÜR-Zusammenfassung 2025
========================

Ausgaben nach Kategorie:
  Laufende EDV-Kosten (51):      -1,234.56 EUR
  Telekommunikation (44):          -479.88 EUR
  Arbeitsmittel (52):              -156.00 EUR
  ...
  ─────────────────────────────────────────────
  GESAMT Ausgaben:               -1,870.44 EUR

Einnahmen nach Kategorie:
  Umsatzsteuerpfl. Betriebseinnahmen (14):  4,500.00 EUR
  ...
  ─────────────────────────────────────────────
  GESAMT Einnahmen:               4,500.00 EUR

  ═════════════════════════════════════════════
  GEWINN/VERLUST:                 2,629.56 EUR
```

---

#### `ledger audit <id>`

Zeigt Änderungshistorie für einen Datensatz.

```bash
ledger audit 42 [--table expenses|income]  # Default: expenses
```

**Output:**
```
Audit-Log für expenses #42
==========================

2026-01-15 10:30:00  INSERT by default
  → {"date": "2026-01-15", "vendor": "Render", "amount_eur": -15.50, ...}

2026-01-16 14:22:00  UPDATE by default
  ← {"amount_eur": -15.50}
  → {"amount_eur": -20.00}
```

---

## Migration Script (`migrate_excel.py`)

### Verwendung

```bash
python migrate_excel.py "~/Dropbox/Beispielunternehmen/2025 EÜR Beispielunternehmen.xlsx"
python migrate_excel.py "~/Dropbox/Beispielunternehmen/2026 EÜR Beispielunternehmen.xlsx"
```

### Ablauf

1. **Excel öffnen** mit openpyxl
2. **Sheet "Ausgaben" lesen**:
   - Zeile 1 = Header (überspringen)
   - Ab Zeile 2: Daten
   - Spalten-Mapping:
     - A: receipt_name (Belegname)
     - B: date (Datum Abbuchung) → Format: YYYY-MM-DD
     - C: vendor (Lieferant/Zweck)
     - D: category (Kategorie) → Kategorie-Lookup (ohne "(Zeile XX)")
     - E: amount_eur (Betrag in EUR lt. Bank)
     - F: account (Konto)
     - G: foreign_amount (Betrag Fremdwährung)
     - H: notes (Bemerkung)
     - I: vat_amount (Betrag USt-VA)
3. **Sheet "Einnahmen" lesen** (analog)
4. **Für jede Zeile:**
   - Hash berechnen
   - Prüfen ob existiert → Skip wenn ja
   - INSERT
   - Audit-Log: MIGRATE mit Quell-Datei in notes
5. **Summary ausgeben:**
   - X Ausgaben importiert, Y übersprungen (Duplikate)
   - X Einnahmen importiert, Y übersprungen

### Kategorie-Matching

Excel enthält Kategorien wie `Laufende EDV-Kosten (51)`.

**Strategie:**
1. Regex: `(.+?)\s*\((\d+)\)$` → Extrahiere Name und EÜR-Zeile
2. Suche in categories-Tabelle nach Name (case-insensitive)
3. Wenn nicht gefunden: Warnung ausgeben, aber trotzdem importieren (ggf. neue Kategorie anlegen oder Fallback)

---

## Wichtige Hinweise für die Implementierung

### 1. Transaktionen verwenden

```python
with sqlite3.connect(db_path) as conn:
    conn.execute("BEGIN")
    try:
        # ... Operationen ...
        conn.commit()
    except:
        conn.rollback()
        raise
```

### 2. DECIMAL-Handling in SQLite

SQLite hat keinen echten DECIMAL-Typ. Optionen:
- **Empfohlen:** Als REAL speichern, bei Ausgabe auf 2 Dezimalstellen runden
- Alternativ: Als INTEGER (Cents) speichern

### 3. Datumsformat

- Intern: ISO 8601 (`YYYY-MM-DD`)
- Excel kann verschiedene Formate haben → `openpyxl` gibt datetime-Objekte zurück

### 4. Encoding

- SQLite: UTF-8 (Standard)
- CLI-Output: UTF-8
- Excel-Export: UTF-8 mit BOM für CSV (Excel-Kompatibilität)

### 5. Fehlerbehandlung

- Klare, hilfreiche Fehlermeldungen
- Exit-Codes: 0 = OK, 1 = Fehler
- Bei Duplikaten: Warnung (stderr), aber Exit-Code 0

### 6. CLI-Struktur

Empfohlen: argparse mit Subparsers für saubere Command-Struktur.

```python
parser = argparse.ArgumentParser(description="Buchungs-Ledger CLI")
subparsers = parser.add_subparsers(dest="command", required=True)

# init
init_parser = subparsers.add_parser("init", help="Initialize database")

# add
add_parser = subparsers.add_parser("add", help="Add transaction")
add_subparsers = add_parser.add_subparsers(dest="type", required=True)
add_expense_parser = add_subparsers.add_parser("expense")
add_expense_parser.add_argument("--date", required=True)
# ... etc
```

---

## FAQ

### Warum SQLite statt PostgreSQL/MySQL?

- Keine Installation nötig
- Eine Datei = einfaches Backup (Dropbox-Sync)
- Für Single-User mit <10.000 Transaktionen mehr als ausreichend
- Standard-Library-Support in Python

### Warum kein ORM (SQLAlchemy)?

- Overkill für einfaches Schema
- Direktes SQL ist transparenter
- Weniger Dependencies

### Warum separate audit_log statt Trigger?

- Mehr Kontrolle über das Format
- Einfacher zu debuggen
- Python-Side-Logging erlaubt mehr Kontext (z.B. Quell-Script bei Migration)

### Was passiert bei Schema-Änderungen?

- Für einfache Änderungen: `ALTER TABLE` manuell
- Für komplexe Migrationen: Eigenes Script
- Backup VOR Schema-Änderungen!

### Wie werden Backups gemacht?

- SQLite-DB ist eine Datei → einfach kopieren
- Empfehlung: Nach jedem Monat `cp ledger.db ledger_backup_2026-01.db`
- Oder: Symlink in Dropbox-Ordner für automatisches Cloud-Backup

### Kann das später ein Web-UI bekommen?

Ja, das Schema ist dafür ausgelegt:
- RESTful API über Flask/FastAPI wäre einfach
- Audit-Log funktioniert genauso
- Single-Writer-Konzept bleibt (SQLite WAL-Mode für concurrent reads)

---

## Nächste Schritte (Implementierungsreihenfolge)

1. [ ] `requirements.txt` erstellen (`openpyxl`)
2. [ ] `ledger.py` Grundgerüst mit argparse
3. [ ] `ledger init` - Schema + Seed
4. [ ] `ledger add expense/income` - Mit Hash + Audit
5. [ ] `ledger list expenses/income/categories`
6. [ ] `ledger update expense/income <id>`
7. [ ] `ledger delete expense/income <id>`
8. [ ] `ledger export` - CSV + XLSX
9. [ ] `ledger summary`
10. [ ] `ledger audit <id>`
11. [ ] `migrate_excel.py`
12. [ ] Migration durchführen (2025 + 2026)
13. [ ] `README.md` schreiben
14. [ ] Testen mit echten Daten

---

## Referenzen

- Excel-Dateien: `~/Dropbox/Beispielunternehmen/`
- Kategorisierungs-Regeln: `/path/to/EÜR Kategorisierung.md` (intern)
- Accounting SOP: `/path/to/sop-accounting-process/SKILL.md` (intern)
