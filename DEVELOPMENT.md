# EÜR - Entwicklerdokumentation

## Übersicht

EÜR ist ein CLI-Tool zur Verwaltung der Einnahmenüberschussrechnung für Kleinunternehmer. Es ersetzt eine Excel-basierte Lösung durch eine SQLite-Datenbank mit vollständigem Audit-Trail.

**Zielgruppe:** Coding Agents / LLMs, die Buchungen per CLI verwalten.

---

## Architektur

### Dateien

```
euer/
├── euer.py           # Haupt-CLI (Single-File, ~1200 Zeilen)
├── euer.db           # SQLite-Datenbank (nach init)
├── exports/          # Export-Verzeichnis für CSV/XLSX
├── requirements.txt  # openpyxl (nur für XLSX-Export)
├── spec.md           # Ursprüngliche Spezifikation
├── README.md         # Schnellstart für Agents
└── DEVELOPMENT.md    # Diese Datei
```

### Design-Entscheidungen

| Entscheidung | Begründung |
|--------------|------------|
| Single-File CLI | Einfach zu verstehen und zu deployen |
| SQLite | Keine Installation, Datei = Backup, Standard-Library |
| Kein ORM | Direktes SQL ist transparenter für einfaches Schema |
| argparse | Standard-Library, keine externe Dependency |
| Hash-basierte Duplikate | Idempotente Imports, gleiche Transaktion nicht doppelt |
| Audit-Log in Python | Mehr Kontrolle als DB-Trigger, Quell-Kontext möglich |

---

## Datenbank-Schema

### Tabelle: `categories`

EÜR-Kategorien für konsistente Zuordnung.

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- z.B. "Telekommunikation"
    eur_line INTEGER,             -- EÜR-Formular-Zeile (44, 51, etc.)
    type TEXT NOT NULL            -- 'expense' oder 'income'
);
```

**Seed-Kategorien (bei init):**

| Name | EÜR-Zeile | Typ |
|------|-----------|-----|
| Telekommunikation | 44 | expense |
| Laufende EDV-Kosten | 51 | expense |
| Arbeitsmittel | 52 | expense |
| Werbekosten | 54 | expense |
| Gezahlte USt | 58 | expense |
| Übrige Betriebsausgaben | 60 | expense |
| Bewirtungsaufwendungen | 63 | expense |
| Sonstige betriebsfremde Einnahme | - | income |
| Umsatzsteuerpflichtige Betriebseinnahmen | 14 | income |

### Tabelle: `expenses`

```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_name TEXT,            -- Belegname (nur Dateiname)
    date DATE NOT NULL,           -- YYYY-MM-DD
    vendor TEXT NOT NULL,         -- Lieferant/Zweck
    category_id INTEGER NOT NULL, -- FK -> categories
    amount_eur REAL NOT NULL,     -- Betrag in EUR (negativ!)
    account TEXT,                 -- Bankkonto
    foreign_amount TEXT,          -- z.B. "26.60 USD"
    notes TEXT,                   -- Bemerkung
    vat_amount REAL,              -- Reverse-Charge USt (19%)
    created_at TIMESTAMP,
    hash TEXT UNIQUE NOT NULL     -- Duplikat-Erkennung
);
```

### Tabelle: `income`

```sql
CREATE TABLE income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_name TEXT,
    date DATE NOT NULL,
    source TEXT NOT NULL,         -- Quelle/Kunde
    category_id INTEGER NOT NULL,
    amount_eur REAL NOT NULL,     -- Betrag in EUR (positiv!)
    foreign_amount TEXT,
    notes TEXT,
    created_at TIMESTAMP,
    hash TEXT UNIQUE NOT NULL
);
```

### Tabelle: `audit_log`

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    table_name TEXT NOT NULL,     -- 'expenses' oder 'income'
    record_id INTEGER NOT NULL,
    action TEXT NOT NULL,         -- INSERT, UPDATE, DELETE, MIGRATE
    old_data TEXT,                -- JSON (NULL bei INSERT)
    new_data TEXT,                -- JSON (NULL bei DELETE)
    user TEXT DEFAULT 'markus'
);
```

---

## Hash-Berechnung (Duplikat-Erkennung)

```python
def compute_hash(date: str, vendor_or_source: str, amount_eur: float, receipt_name: str = "") -> str:
    data = f"{date}|{vendor_or_source}|{amount_eur:.2f}|{receipt_name or ''}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
```

**Wichtig:** Der Hash wird aus Datum + Vendor/Source + Betrag + Belegname berechnet. Bei erneutem Import der gleichen Transaktion wird diese als Duplikat erkannt und übersprungen.

---

## Steuerliche Besonderheiten

### Kleinunternehmer (§19 UStG)

- Nicht umsatzsteuerpflichtig
- Keine USt auf Einnahmen
- Keine Vorsteuer-Abzug auf normale Ausgaben

### Reverse Charge (RC)

Bei Ausgaben an ausländische Anbieter (z.B. US-SaaS) gilt Reverse Charge:
- Der Empfänger muss die USt selbst abführen
- 19% des Netto-Betrags als USt-VA (Umsatzsteuer-Voranmeldung)

**CLI-Nutzung:**
```bash
# Automatisch 19% berechnen
python euer.py add expense --date 2026-01-20 --vendor "OpenAI" \
    --category "Laufende EDV-Kosten" --amount -20.00 --foreign "20.00 USD" --rc

# Manuell angeben
python euer.py add expense ... --vat 3.80
```

**Wann --rc verwenden:**
- Rechnung ohne deutsche USt
- Anbieter im EU-Ausland oder Drittland
- Beispiele: OpenAI, Render, Vercel, AWS, GitHub, etc.

---

## CLI-Referenz

### Globale Optionen

```bash
python euer.py [--db PFAD] <command>
```

| Option | Default | Beschreibung |
|--------|---------|--------------|
| `--db` | `./euer.db` | Pfad zur Datenbank |

### Commands

#### `init`

```bash
python euer.py init
```

- Erstellt Datenbank und Schema (IF NOT EXISTS)
- Seeded Kategorien (nur wenn leer)
- Erstellt `exports/` Verzeichnis
- **Idempotent** - kann mehrfach aufgerufen werden

#### `add expense`

```bash
python euer.py add expense \
    --date 2026-01-15 \
    --vendor "Render" \
    --category "Laufende EDV-Kosten" \
    --amount -15.50 \
    [--account "N26"] \
    [--foreign "15.00 USD"] \
    [--receipt "statement-2026-01.pdf"] \
    [--notes "Hosting Jan 2026"] \
    [--vat 2.95] \
    [--rc]
```

| Argument | Required | Beschreibung |
|----------|----------|--------------|
| `--date` | Ja | YYYY-MM-DD |
| `--vendor` | Ja | Lieferant/Zweck |
| `--category` | Ja | Kategorie-Name (case-insensitive) |
| `--amount` | Ja | Betrag in EUR (**negativ für Ausgaben!**) |
| `--account` | Nein | Bankkonto (N26, Sparkasse, etc.) |
| `--foreign` | Nein | Fremdwährungsbetrag (z.B. "15.00 USD") |
| `--receipt` | Nein | Belegname (nur Dateiname) |
| `--notes` | Nein | Bemerkung |
| `--vat` | Nein | USt-VA Betrag (manuell) |
| `--rc` | Nein | Reverse-Charge: berechnet 19% USt automatisch |

#### `add income`

```bash
python euer.py add income \
    --date 2026-01-20 \
    --source "Kunde ABC" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" \
    --amount 1500.00 \
    [--foreign "1600.00 USD"] \
    [--receipt "Rechnung_001.pdf"] \
    [--notes "Projekt XYZ"]
```

#### `list expenses`

```bash
python euer.py list expenses \
    [--year 2026] \
    [--month 1] \
    [--category "Laufende EDV-Kosten"] \
    [--format table|csv]
```

#### `list income`

```bash
python euer.py list income [--year] [--month] [--category] [--format]
```

#### `list categories`

```bash
python euer.py list categories [--type expense|income]
```

#### `update expense <id>`

```bash
python euer.py update expense 42 \
    [--date ...] [--vendor ...] [--category ...] [--amount ...] \
    [--account ...] [--foreign ...] [--receipt ...] [--notes ...] [--vat ...]
```

- Nur angegebene Felder werden aktualisiert
- Hash wird neu berechnet
- Audit-Log: UPDATE mit old_data + new_data

#### `update income <id>`

```bash
python euer.py update income 42 [--date ...] [--source ...] ...
```

#### `delete expense <id>`

```bash
python euer.py delete expense 42 [--force]
```

- Ohne `--force`: Zeigt Transaktion und fragt nach Bestätigung
- Audit-Log: DELETE mit old_data

#### `delete income <id>`

```bash
python euer.py delete income 42 [--force]
```

#### `export`

```bash
python euer.py export \
    [--year 2026] \
    [--format csv|xlsx] \
    [--output ./exports/]
```

- CSV: UTF-8 mit BOM (Excel-kompatibel)
- XLSX: benötigt openpyxl

**Output:**
- `EÜR_2026_Ausgaben.csv/xlsx`
- `EÜR_2026_Einnahmen.csv/xlsx`

#### `summary`

```bash
python euer.py summary [--year 2026]
```

Zeigt:
- Ausgaben nach Kategorie (mit EÜR-Zeile)
- Reverse-Charge USt-Summe (für USt-VA)
- Einnahmen nach Kategorie
- Gewinn/Verlust

#### `audit <id>`

```bash
python euer.py audit 42 [--table expenses|income]
```

Zeigt Änderungshistorie für einen Datensatz.

---

## Erweiterung

### Neue Kategorie hinzufügen

```sql
INSERT INTO categories (name, eur_line, type) VALUES ('Neue Kategorie', 99, 'expense');
```

Oder in `SEED_CATEGORIES` in `euer.py` ergänzen und DB neu initialisieren.

### Schema-Änderungen

1. Backup erstellen: `cp euer.db euer.db.backup`
2. `ALTER TABLE` für einfache Änderungen
3. Für komplexe Migrationen: Neues Script schreiben

### Neuen Command hinzufügen

1. Funktion `cmd_<name>(args)` implementieren
2. Parser in `main()` hinzufügen
3. `set_defaults(func=cmd_<name>)`

---

## Bekannte Einschränkungen

- **Single-User:** Keine Concurrent-Write-Unterstützung
- **Keine Undo-Funktion:** Nur über Audit-Log rekonstruierbar
- **Kategorien:** Müssen vorab existieren (kein Auto-Create)
- **XLSX-Export:** Benötigt openpyxl (`pip install openpyxl`)

---

## Typische Workflows

### Monatliche Buchung (Agent)

1. Kontoauszug/Belege lesen
2. Pro Transaktion: `add expense` oder `add income`
3. Bei RC-Ausgaben: `--rc` Flag verwenden
4. Prüfung: `list expenses --year --month`

### Quartalsabschluss

1. `summary --year` für Übersicht
2. `export --format csv` für Steuerberater
3. USt-VA aus Summary für Finanzamt

### Korrektur

1. `list expenses` um ID zu finden
2. `update expense <id> --amount -25.00`
3. `audit <id>` zur Verifizierung

---

## Referenzen

- [spec.md](spec.md) - Ursprüngliche Spezifikation
- [README.md](README.md) - Schnellstart
- Kategorisierungs-Regeln: `/Users/markus/dev/ItsMe/Mein Gewerbe/Organisatorisches/EÜR Kategorisierung.md`
