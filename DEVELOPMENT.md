# EÜR - Entwicklerdokumentation

## Übersicht

EÜR ist ein CLI-Tool zur Verwaltung der Einnahmenüberschussrechnung für Kleinunternehmer (§19 UStG). Es ersetzt eine Excel-basierte Lösung durch eine SQLite-Datenbank mit vollständigem Audit-Trail.

**Zielgruppe:** Coding Agents / LLMs, die Buchungen per CLI verwalten.

---

## Projektstruktur

```
euer/
├── euer.py              # Haupt-CLI (Single-File, ~1600 Zeilen)
├── euer.db              # SQLite-Datenbank (nach init)
├── exports/             # Export-Verzeichnis für CSV/XLSX
├── requirements.txt     # openpyxl (optional, für XLSX-Export)
├── skills/
│   └── euer-buchhaltung/
│       └── SKILL.md     # AI-Agent Anleitung
├── specs/
│   ├── 001-init.md      # Ursprüngliche Spezifikation
│   ├── 002-receipts.md  # Beleg-Management
│   └── 003-modularization.md  # Zukünftige Modularisierung
├── README.md            # Schnellstart & Open-Source-Info
└── DEVELOPMENT.md       # Diese Datei
```

---

## Design-Entscheidungen

| Entscheidung | Begründung |
|--------------|------------|
| Single-File CLI | Einfach zu verstehen, deployen, AI-Agent-freundlich |
| SQLite | Keine Installation, Datei = Backup, Standard-Library |
| Kein ORM | Direktes SQL ist transparenter für einfaches Schema |
| argparse | Standard-Library, keine externe Dependency |
| Hash-basierte Duplikate | Idempotente Imports, gleiche Transaktion nicht doppelt |
| Audit-Log in Python | Mehr Kontrolle als DB-Trigger, Quell-Kontext möglich |
| TOML-Config | Standard-Library ab Python 3.11 (`tomllib`) |

---

## Datenbank-Schema

### Tabelle: `categories`

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- z.B. "Telekommunikation"
    eur_line INTEGER,             -- EÜR-Formular-Zeile (44, 51, etc.)
    type TEXT NOT NULL            -- 'expense' oder 'income'
);
```

**Seed-Kategorien:**

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
    notes TEXT,
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

## Konfiguration

### Config-Datei

Pfad: `~/.config/euer/config.toml`

```toml
[receipts]
expenses = "/pfad/zu/ausgaben-belege"
income = "/pfad/zu/einnahmen-belege"
```

### Beleg-Struktur

Belege werden in Jahres-Unterordnern erwartet:

```
<base>/<Jahr>/<Belegname>
```

Beispiel: `/pfad/zu/ausgaben-belege/2026/2026-01-15_Render.pdf`

---

## Steuerliche Besonderheiten

### Kleinunternehmer (§19 UStG)

- Nicht umsatzsteuerpflichtig
- Keine USt auf Einnahmen
- Keine Vorsteuer-Abzug auf normale Ausgaben

### Reverse Charge (RC)

Bei Ausgaben an ausländische Anbieter ohne deutsche USt:

```bash
python3 euer.py add expense --date 2026-01-20 --vendor "OpenAI" \
    --category "Laufende EDV-Kosten" --amount -20.00 --rc
```

Berechnet automatisch 19% USt für die USt-Voranmeldung.

**Typische RC-Anbieter:** OpenAI, Anthropic, Render, Vercel, AWS, GitHub, Stripe

---

## CLI-Referenz

### Globale Optionen

```bash
python3 euer.py [--db PFAD] <command>
```

### Commands

| Command | Beschreibung |
|---------|--------------|
| `init` | Datenbank initialisieren |
| `add expense` | Ausgabe hinzufügen |
| `add income` | Einnahme hinzufügen |
| `list expenses` | Ausgaben anzeigen |
| `list income` | Einnahmen anzeigen |
| `list categories` | Kategorien anzeigen |
| `update expense <id>` | Ausgabe aktualisieren |
| `update income <id>` | Einnahme aktualisieren |
| `delete expense <id>` | Ausgabe löschen |
| `delete income <id>` | Einnahme löschen |
| `export` | CSV/XLSX-Export |
| `summary` | Jahres-Zusammenfassung |
| `audit <id>` | Änderungshistorie |
| `config show` | Konfiguration anzeigen |
| `receipt check` | Fehlende Belege prüfen |
| `receipt open <id>` | Beleg öffnen |

### Wichtige Argumente

#### `add expense`

| Argument | Required | Beschreibung |
|----------|----------|--------------|
| `--date` | Ja | YYYY-MM-DD |
| `--vendor` | Ja | Lieferant/Zweck |
| `--category` | Ja | Kategorie-Name |
| `--amount` | Ja | Betrag in EUR (**negativ!**) |
| `--account` | Nein | Bankkonto |
| `--foreign` | Nein | Fremdwährung (z.B. "15.00 USD") |
| `--receipt` | Nein | Belegname |
| `--notes` | Nein | Bemerkung |
| `--rc` | Nein | Reverse-Charge (19% USt) |
| `--vat` | Nein | USt-Betrag (manuell) |

#### `add income`

| Argument | Required | Beschreibung |
|----------|----------|--------------|
| `--date` | Ja | YYYY-MM-DD |
| `--source` | Ja | Kunde/Quelle |
| `--category` | Ja | Kategorie-Name |
| `--amount` | Ja | Betrag in EUR (**positiv!**) |
| `--receipt` | Nein | Belegname |

---

## Hash-Berechnung

```python
def compute_hash(date, vendor_or_source, amount_eur, receipt_name=""):
    data = f"{date}|{vendor_or_source}|{amount_eur:.2f}|{receipt_name or ''}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
```

Ermöglicht idempotente Imports - gleiche Transaktion wird als Duplikat erkannt.

---

## Erweiterung

### Neue Kategorie

```sql
INSERT INTO categories (name, eur_line, type) VALUES ('Neue Kategorie', 99, 'expense');
```

Oder in `SEED_CATEGORIES` ergänzen und DB neu initialisieren.

### Neuen Command

1. Funktion `cmd_<name>(args)` implementieren
2. Parser in `main()` hinzufügen
3. `set_defaults(func=cmd_<name>)`

### Modularisierung

Siehe `specs/003-modularization.md` für den Plan zur Aufteilung in Module (wenn >2500 Zeilen).

---

## Bekannte Einschränkungen

- **Single-User:** Keine Concurrent-Write-Unterstützung
- **Keine Undo-Funktion:** Nur über Audit-Log rekonstruierbar
- **Kategorien:** Müssen vorab existieren
- **XLSX-Export:** Benötigt `pip install openpyxl`

---

## Referenzen

- [README.md](README.md) - Schnellstart & Open-Source-Info
- [specs/001-init.md](specs/001-init.md) - Ursprüngliche Spezifikation
- [specs/002-receipts.md](specs/002-receipts.md) - Beleg-Management
- [specs/003-modularization.md](specs/003-modularization.md) - Modularisierungs-Plan
- [skills/euer-buchhaltung/SKILL.md](skills/euer-buchhaltung/SKILL.md) - AI-Agent Skill
