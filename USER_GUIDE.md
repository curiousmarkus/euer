# Benutzerhandbuch

Dieses Dokument richtet sich an Nutzer:innen des CLI‑Tools. Es erklärt Installation,
Konfiguration und typische Workflows.

## Voraussetzungen

- Python 3.11+
- Optional: `openpyxl` für XLSX‑Export

## Installation

### Empfehlung (pipx)

```bash
brew install pipx
pipx ensurepath
pipx install -e .
```

### Lokale Installation (im Repo)

```bash
git clone <repo-url>
cd euer
python -m pip install -e .
```

### Alternative: ohne Installation

```bash
python -m euercli <command>
```

## Erste Schritte

```bash
# Datenbank anlegen (erstellt euer.db + exports/)
euer init

# Beleg- und Export-Pfade konfigurieren (empfohlen)
euer setup

# Konfiguration prüfen
euer config show
```

## Grundbegriffe

- **Ausgaben** haben immer **negative** Beträge (`--amount -10.00`).
- **Einnahmen** haben immer **positive** Beträge (`--amount 10.00`).
- **Kategorien** sind vorgegeben und müssen existieren: `euer list categories`.
- **Belege** können geprüft und geöffnet werden, wenn Pfade konfiguriert sind.
- **Datenbank**: Standard `euer.db` im Projekt; alternativ via `--db PFAD`.

## Typische Befehle

### Ausgaben & Einnahmen erfassen

```bash
# Ausgabe
euer add expense --date 2026-01-15 --vendor "1und1" \
    --category "Telekommunikation" --amount -39.99 --account "Sparkasse Giro"

# Einnahme
euer add income --date 2026-01-20 --source "Kunde ABC" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" --amount 1500.00
```

### Anzeigen & Filtern

```bash
euer list expenses --year 2026
euer list expenses --year 2026 --month 1
euer list income --year 2026
euer list categories
```

### Korrigieren & Löschen

```bash
euer update expense 42 --amount -25.00 --notes "Korrigiert"
euer delete expense 42
euer delete expense 42 --force

# Änderungshistorie
euer audit 42 --table expenses
```

### Zusammenfassung & Export

```bash
euer summary --year 2026

euer export --year 2026 --format csv
# XLSX benötigt openpyxl:
euer export --year 2026 --format xlsx
```

### Bulk‑Import & Unvollständige Einträge

```bash
euer import --file import.csv --format csv

euer incomplete list
euer incomplete list --format csv
```

## Beleg‑Verwaltung

### Konfiguration

`euer setup` legt Pfade in `~/.config/euer/config.toml` an.
Belege werden in Jahres‑Unterordnern erwartet: `<base>/<Jahr>/<Belegname>`.

```toml
[receipts]
expenses = "/pfad/zu/ausgaben-belege"
income = "/pfad/zu/einnahmen-belege"

[exports]
directory = "/pfad/zu/exports"
```

### Prüfen & Öffnen

```bash
euer receipt check --year 2026
euer receipt check --type expense

euer receipt open 12
euer receipt open 5 --table income
```

## Steuer‑Modus (Config)

Der Steuer‑Modus wird in der Config gesetzt (Standard: `small_business`).

```toml
[tax]
mode = "small_business"  # oder "standard"
```

- **small_business**: Keine Vorsteuer, RC erzeugt Umsatzsteuer‑Zahllast.
- **standard**: Vorsteuer wird erfasst, RC bucht USt und VorSt gleichzeitig.

## Reverse‑Charge (RC)

Verwende `--rc` für ausländische Anbieter ohne deutsche USt:

```bash
euer add expense --date 2026-01-04 --vendor "RENDER.COM" \
    --category "Laufende EDV-Kosten" --amount -22.71 --rc
```

## Troubleshooting

- **Kategorie fehlt**: `euer list categories` prüfen.
- **Duplikat erkannt**: gleiche Transaktion wurde bereits importiert.
- **Beleg nicht gefunden**: Pfade in `config.toml` prüfen und Ordnerstruktur beachten.

## Hilfe

Für Details zu Parametern:

```bash
euer --help
euer add expense --help
euer receipt --help
```
