# EÜR - Einnahmenüberschussrechnung

SQLite-basierte Buchhaltung für deutsche Kleinunternehmer (§19 UStG).

**AI-Agent-ready**: Dieses CLI-Tool ist so gestaltet, dass Coding Agents (OpenCode, Claude, Cursor, etc.) deine Buchhaltung selbstständig pflegen können.

## Warum dieses Tool?

- **Keine Excel-Sheets mehr** - Saubere SQLite-Datenbank mit Audit-Trail
- **Agent-freundlich** - Klare CLI-Struktur, die LLMs verstehen
- **Beleg-Validierung** - Automatische Prüfung ob Belege existieren
- **EÜR-konform** - Kategorien mit korrekten EÜR-Zeilennummern
- **Keine Dependencies** - Python 3.11+ Standard-Library (openpyxl optional für XLSX)

## Installation

```bash
git clone https://github.com/yourusername/euer.git
cd euer
python3 euer.py init
```

## Ersteinrichtung (Onboarding)

```bash
# Datenbank initialisieren (einmalig)
python3 euer.py init

# Interaktive Konfiguration der Beleg-Pfade
python3 euer.py setup

# Konfiguration prüfen
python3 euer.py config show
```

## AI-Agent Setup

Kopiere den Skill in dein Projekt oder global:

```bash
# Projekt-spezifisch
cp -r skills/euer-buchhaltung .opencode/skill/

# Oder global
cp -r skills/euer-buchhaltung ~/.config/opencode/skill/
```

Dann kann dein Agent Anweisungen wie diese verstehen:
- "Buche die Render-Rechnung vom Januar"
- "Zeig mir die Ausgaben für 2026"
- "Prüfe ob alle Belege vorhanden sind"

## Schnellstart

```bash
# Datenbank initialisieren (einmalig)
python3 euer.py init

# Beleg-Pfade konfigurieren (optional, aber empfohlen)
python3 euer.py setup

# Kategorien anzeigen
python3 euer.py list categories
```

## Ausgaben erfassen

```bash
# Standard-Ausgabe
python3 euer.py add expense \
    --date 2026-01-15 \
    --vendor "1und1" \
    --category "Telekommunikation" \
    --amount -39.99 \
    --account "Sparkasse Giro"

# Ausgabe mit Reverse-Charge (ausländischer Anbieter, berechnet 19% USt)
python3 euer.py add expense \
    --date 2026-01-04 \
    --vendor "RENDER.COM" \
    --category "Laufende EDV-Kosten" \
    --amount -22.71 \
    --foreign "26.60 USD" \
    --receipt "2026-01-04_Render.pdf" \
    --rc
```

**Wichtig:**
- `--amount` ist negativ für Ausgaben
- `--rc` bei ausländischen Anbietern (OpenAI, Render, Vercel, AWS, etc.)
- `--category` muss existieren (siehe `list categories`)

## Einnahmen erfassen

```bash
python3 euer.py add income \
    --date 2026-01-20 \
    --source "Kunde ABC" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" \
    --amount 1500.00 \
    --receipt "Rechnung_001.pdf"
```

## Daten anzeigen

```bash
# Ausgaben (mit Filter)
python3 euer.py list expenses --year 2026
python3 euer.py list expenses --year 2026 --month 1
python3 euer.py list expenses --category "Laufende EDV-Kosten"

# Einnahmen
python3 euer.py list income --year 2026

# Zusammenfassung (Kategorien + Gewinn/Verlust + USt-VA)
python3 euer.py summary --year 2026
```

## Korrigieren & Löschen

```bash
# Einzelne Felder aktualisieren
python3 euer.py update expense 42 --amount -25.00 --notes "Korrigiert"

# Löschen (mit Bestätigung)
python3 euer.py delete expense 42

# Löschen ohne Rückfrage
python3 euer.py delete expense 42 --force

# Änderungshistorie prüfen
python3 euer.py audit 42 --table expenses
```

## Export

```bash
# CSV (immer verfügbar)
python3 euer.py export --year 2026 --format csv

# XLSX (benötigt: pip install openpyxl)
python3 euer.py export --year 2026 --format xlsx
```

Erzeugt: `exports/EÜR_2026_Ausgaben.csv` und `exports/EÜR_2026_Einnahmen.csv`

## Bulk-Import (Bankauszug / AI-Agent)

Der Import akzeptiert CSV oder JSONL. Unvollständige Zeilen werden automatisch
als "incomplete" gespeichert und können später korrigiert werden.
Fehlender `type` wird aus dem Vorzeichen von `amount_eur` abgeleitet.

```bash
python3 euer.py import --file import.csv --format csv
```

Beispiel CSV:

```csv
type,date,party,category,amount_eur,receipt_name,notes
expense,2026-01-10,Vendor A,Arbeitsmittel,-20.00,2026-01-10_VendorA.pdf,Monatsabo
income,2026-01-12,Client A,Umsatzsteuerpflichtige Betriebseinnahmen,200.00,Rechnung_001.pdf,
,2026-01-13,Vendor B,Arbeitsmittel,,missing.pdf,
```

### Unvollständige Einträge anzeigen

```bash
python3 euer.py incomplete list
python3 euer.py incomplete list --format csv
```

## Beleg-Verwaltung

Belege können mit Transaktionen verknüpft und validiert werden.

### Konfiguration

Empfohlen: `euer setup` (interaktiver Wizard).

```bash
python3 euer.py setup
```

Oder manuell: `~/.config/euer/config.toml`:

```toml
[receipts]
expenses = "/pfad/zu/ausgaben-belege"
income = "/pfad/zu/einnahmen-belege"
```

Belege werden in Jahres-Unterordnern erwartet: `<base>/<Jahr>/<Belegname>`

```bash
# Konfiguration anzeigen
python3 euer.py config show
```

### Beleg-Prüfung

```bash
# Alle Transaktionen prüfen (aktuelles Jahr)
python3 euer.py receipt check

# Bestimmtes Jahr prüfen
python3 euer.py receipt check --year 2025

# Nur Ausgaben oder Einnahmen prüfen
python3 euer.py receipt check --type expense
python3 euer.py receipt check --type income
```

Bei `add` und `update` wird automatisch gewarnt, wenn ein angegebener Beleg nicht gefunden wird.

### Beleg öffnen

```bash
# Beleg einer Ausgabe öffnen
python3 euer.py receipt open 12

# Beleg einer Einnahme öffnen
python3 euer.py receipt open 5 --table income
```

## Verfügbare Kategorien

| Typ | Kategorie | EÜR-Zeile |
|-----|-----------|-----------|
| expense | Telekommunikation | 44 |
| expense | Laufende EDV-Kosten | 51 |
| expense | Arbeitsmittel | 52 |
| expense | Werbekosten | 54 |
| expense | Gezahlte USt | 58 |
| expense | Übrige Betriebsausgaben | 60 |
| expense | Bewirtungsaufwendungen | 63 |
| income | Sonstige betriebsfremde Einnahme | - |
| income | Umsatzsteuerpflichtige Betriebseinnahmen | 14 |

## Projektstruktur

```
euer/
├── euer.py              # CLI-Tool
├── euer.db              # SQLite-Datenbank
├── exports/             # CSV/XLSX-Exporte
├── skills/
│   └── euer-buchhaltung/
│       └── SKILL.md     # AI-Agent Anleitung
├── specs/               # Feature-Spezifikationen
└── README.md
```

## Dokumentation

- [DEVELOPMENT.md](DEVELOPMENT.md) - Entwicklerdokumentation, Schema, Erweiterung
- [TESTING.md](TESTING.md) - Teststrategie & Ausführung
- [specs/001-init.md](specs/001-init.md) - Ursprüngliche Spezifikation
- [specs/002-receipts.md](specs/002-receipts.md) - Beleg-Management Spezifikation
- [skills/euer-buchhaltung/SKILL.md](skills/euer-buchhaltung/SKILL.md) - AI-Agent Skill

## Tests

```bash
python3 -m unittest discover -s tests
```

## Lizenz

MIT
