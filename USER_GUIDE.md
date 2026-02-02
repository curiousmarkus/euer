# Benutzerhandbuch

Dieses Dokument richtet sich an Nutzer:innen des CLI‑Tools. Es erklärt Installation,
Konfiguration und typische Workflows.

## Voraussetzungen

- Python 3.11+
- Git (für das Herunterladen des Projekts)
- Optional: `openpyxl` für XLSX‑Export

## Projekt herunterladen

**Erster Schritt:** Lade das Projekt herunter und erstelle den Entwicklungsordner:

```bash
# Falls das Projekt auf GitHub/GitLab liegt:
git clone https://github.com/curiousmarkus/euer.git
cd euer

# Falls du das Projekt als ZIP erhalten hast:
unzip euer.zip
cd euer

# Falls du bereits im Projekt-Ordner bist:
cd /pfad/zum/euer
```

Nach diesem Schritt hast du einen Ordner (z.B. `~/dev/euer` oder `/Users/name/euer`), 
der den Quellcode enthält. **Hier** führst du die Installation aus.

## Installation

**Wichtig:** Die Installation erfolgt **einmalig** im Entwicklungsordner und macht das `euer`-Kommando
**systemweit verfügbar**. Deine Buchhaltungsdaten (Datenbank, Belege) liegen dann in einem
**separaten Arbeitsordner** deiner Wahl.

### Empfohlene Installation

```bash
# Im Entwicklungsordner (einmalig)
cd /pfad/zum/euer-repo
python -m pip install -e .
```

Der `-e` Flag (editable mode) sorgt dafür, dass Code-Änderungen sofort wirksam werden.

**Alternative mit pipx** (isolierte Umgebung):

```bash
brew install pipx
pipx ensurepath
cd /pfad/zum/euer-repo
pipx install -e .
```

### Ohne Installation (direkter Aufruf)

```bash
# Im Entwicklungsordner
cd /pfad/zum/euer-repo
python -m euercli <command>
```

## Erste Schritte

### Nach der Installation

Wechsle in deinen **Buchhaltungs-Arbeitsordner** (nicht das Repo!), z.B.:

```bash
# Beispiel: Separater Ordner für Buchhaltungsdaten
mkdir -p ~/Documents/Buchhaltung_2026
cd ~/Documents/Buchhaltung_2026

# Datenbank anlegen (erstellt euer.db + exports/ hier)
euer init

# Beleg-/Export-Pfade und Steuermodus konfigurieren (empfohlen)
euer setup

# Konfiguration prüfen
euer config show

# Erste Buchung
euer add expense --date 2026-02-02 --vendor "Test" --category "Laufende EDV-Kosten" --amount -10.00
```

### Wo liegen meine Daten?

- **Datenbank:** `euer.db` im aktuellen Verzeichnis (wo du `euer init` ausgeführt hast)
- **Konfiguration:** `~/.config/euer/config.toml` (systemweit)
- **Belege:** Pfade in der Konfiguration festgelegt
- **Exports:** `exports/` im aktuellen Verzeichnis oder in der Config festgelegt

## Grundbegriffe

- **Ausgaben** haben immer **negative** Beträge (`--amount -10.00`).
- **Einnahmen** haben immer **positive** Beträge (`--amount 10.00`).
- **Kategorien** sind vorgegeben und müssen existieren: `euer list categories`.
- **Belege** können geprüft und geöffnet werden, wenn Pfade konfiguriert sind.
- **Datenbank**: Standard `euer.db` im **aktuellen Verzeichnis**; alternativ via `--db PFAD`.
- **Arbeitsverzeichnis**: Das Tool sucht nach `euer.db` dort, wo du es aufrufst. 
  Wechsle vor dem Arbeiten in deinen Buchhaltungsordner!

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

`euer setup` legt Pfade und den Audit‑User in `~/.config/euer/config.toml` an.
Belege werden in Jahres‑Unterordnern erwartet: `<base>/<Jahr>/<Belegname>`.

```toml
[receipts]
expenses = "/pfad/zu/ausgaben-belege"
income = "/pfad/zu/einnahmen-belege"

[exports]
directory = "/pfad/zu/exports"

[user]
name = "Dein Name"
```

### Prüfen & Öffnen

```bash
euer receipt check --year 2026
euer receipt check --type expense

euer receipt open 12
euer receipt open 5 --table income
```

## USt‑Modus (Config)

Hier legst du fest, **wie das Tool mit Umsatzsteuer (USt)** rechnet:
- **Kleinunternehmerregelung (§19 UStG)** oder
- **Regelbesteuerung**.

Der Modus wird in der Config gesetzt (Standard: `small_business`).

```toml
[tax]
mode = "small_business"  # oder "standard"
```

- **`small_business`** = Kleinunternehmerregelung (§19 UStG): keine Vorsteuer; Reverse‑Charge erzeugt USt‑Zahllast.
- **`standard`** = Regelbesteuerung: Vorsteuer wird erfasst; Reverse‑Charge bucht USt und VorSt gleichzeitig.

### Steuermodus setzen, einsehen, aendern

- **Setzen (interaktiv):** `euer setup` fragt nach `small_business|standard`.
- **Einsehen:** `euer config show` zeigt den aktuellen Wert unter `[tax]`.
- **Aendern:** `euer setup` erneut ausfuehren und den Modus neu waehlen.
- **Manuell:** `~/.config/euer/config.toml` bearbeiten und `mode` anpassen.

### Audit‑User

Der Audit‑User wird für Änderungen in der `audit_log`‑Tabelle gespeichert.

- **Setzen (interaktiv):** `euer setup` fragt nach dem Namen.
- **Einsehen:** `euer config show` zeigt den aktuellen Wert unter `[user]`.
- **Manuell:** `~/.config/euer/config.toml` bearbeiten und `name` anpassen.

```bash
# aktuelle Konfiguration inkl. Steuermodus anzeigen
euer config show

# Steuermodus neu setzen (interaktiv)
euer setup
```

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
