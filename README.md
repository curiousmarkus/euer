# EÜR - Einnahmenüberschussrechnung

SQLite-basierte Buchhaltung für Kleinunternehmer (§19 UStG).

## Schnellstart

```bash
# Datenbank initialisieren (einmalig)
python euer.py init

# Kategorien anzeigen
python euer.py list categories
```

## Ausgaben erfassen

```bash
# Standard-Ausgabe
python euer.py add expense \
    --date 2026-01-15 \
    --vendor "1und1" \
    --category "Telekommunikation" \
    --amount -39.99 \
    --account "Sparkasse Giro"

# Ausgabe mit Reverse-Charge (ausländischer Anbieter, berechnet 19% USt)
python euer.py add expense \
    --date 2026-01-04 \
    --vendor "RENDER.COM" \
    --category "Laufende EDV-Kosten" \
    --amount -22.71 \
    --foreign "26.60 USD" \
    --receipt "statement-2026-01.pdf" \
    --rc
```

**Wichtig:**
- `--amount` ist negativ für Ausgaben
- `--rc` bei ausländischen Anbietern (OpenAI, Render, Vercel, AWS, etc.)
- `--category` muss existieren (siehe `list categories`)

## Einnahmen erfassen

```bash
python euer.py add income \
    --date 2026-01-20 \
    --source "Kunde ABC" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" \
    --amount 1500.00 \
    --receipt "Rechnung_001.pdf"
```

## Daten anzeigen

```bash
# Ausgaben (mit Filter)
python euer.py list expenses --year 2026
python euer.py list expenses --year 2026 --month 1
python euer.py list expenses --category "Laufende EDV-Kosten"

# Einnahmen
python euer.py list income --year 2026

# Zusammenfassung (Kategorien + Gewinn/Verlust + USt-VA)
python euer.py summary --year 2026
```

## Korrigieren & Löschen

```bash
# Einzelne Felder aktualisieren
python euer.py update expense 42 --amount -25.00 --notes "Korrigiert"

# Löschen (mit Bestätigung)
python euer.py delete expense 42

# Löschen ohne Rückfrage
python euer.py delete expense 42 --force

# Änderungshistorie prüfen
python euer.py audit 42 --table expenses
```

## Export

```bash
# CSV (immer verfügbar)
python euer.py export --year 2026 --format csv

# XLSX (benötigt: pip install openpyxl)
python euer.py export --year 2026 --format xlsx
```

Erzeugt: `exports/EÜR_2026_Ausgaben.csv` und `exports/EÜR_2026_Einnahmen.csv`

## Beleg-Verwaltung

Belege können mit Transaktionen verknüpft und validiert werden.

### Konfiguration

Erstelle `~/.config/euer/config.toml`:

```toml
[receipts]
expenses = "/pfad/zu/ausgaben-belege"
income = "/pfad/zu/einnahmen-belege"
```

Belege werden in Jahres-Unterordnern erwartet: `<base>/<Jahr>/<Belegname>`

```bash
# Konfiguration anzeigen
python euer.py config show
```

### Beleg-Prüfung

```bash
# Alle Transaktionen prüfen (aktuelles Jahr)
python euer.py receipt check

# Bestimmtes Jahr prüfen
python euer.py receipt check --year 2025

# Nur Ausgaben oder Einnahmen prüfen
python euer.py receipt check --type expense
python euer.py receipt check --type income
```

Bei `add` und `update` wird automatisch gewarnt, wenn ein angegebener Beleg nicht gefunden wird.

### Beleg öffnen

```bash
# Beleg einer Ausgabe öffnen
python euer.py receipt open 12

# Beleg einer Einnahme öffnen
python euer.py receipt open 5 --table income
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

## Dokumentation

- [DEVELOPMENT.md](DEVELOPMENT.md) - Entwicklerdokumentation, Schema, Erweiterung
- [specs/001-init.md](specs/001-init.md) - Ursprüngliche Spezifikation
- [specs/002-receipts.md](specs/002-receipts.md) - Beleg-Management Spezifikation
