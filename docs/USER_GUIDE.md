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

## KI-Agenten Konfiguration

Das CLI-Tool ist so konzipiert, dass KI-Agenten die Buchhaltung automatisieren können.
Im Ordner `docs/templates/` findest du Vorlagen für die Agent-Konfiguration.

### Verfügbare Templates

| Datei | Beschreibung |
|-------|--------------|
| `Agents.md` | Template für persönliche Buchhaltungsdaten (Pfade, Konten, Kategorien) |
| `accountant-agent.md` | Agent-Definition für KI-Buchhalter (Regeln, Workflows, Steuerlogik) |
| `onboarding-prompt.md` | Interview-Prompt zur Erstellung einer personalisierten `Agents.md` |

### Schnellstart für KI-Agenten

1. **Onboarding durchführen:**
   - Kopiere den Inhalt von `docs/templates/onboarding-prompt.md` in einen neuen LLM-Chat
   - Der Assistent führt ein Interview und erstellt deine persönliche `Agents.md`

2. **Agent konfigurieren:**
   - Speichere die generierte `Agents.md` in deinem Buchhaltungsordner
   - Füge die `accountant-agent.md` als Agent-Definition zu deinem Agent-Framework hinzu
   - kopiere den Skill in den korrekten Pfad, so dass dein Agent darauf Zugriff hat: `docs/skills/euer-buchhaltung/SKILL.md`
   - Starte deinen KI-Agenten im Buchhaltungsordner (so hat er Zugriff auf `Agents.md` als Kontext)

3. **CLI einrichten:**
   - Führe `euer setup` aus, um die gleichen Pfade auch im CLI zu konfigurieren
   - Alternativ non-interaktiv: `euer setup --set tax.mode "small_business"` usw.
   - Die Konfiguration wird unter macOS/Linux in `~/.config/euer/config.toml` gespeichert, unter Windows in `%APPDATA%\\euer\\config.toml`

### Empfohlene Tools für Agenten

- **PDF-Parsing:** `markitdown` – extrahiert Text aus PDFs (Kontoauszüge, Rechnungen)
  ```bash
  # Installation
  pip install markitdown
  
  # Nutzung
  markitdown "pfad/zur/rechnung.pdf"
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

# Oder non-interaktiv (z.B. aus Onboarding-Output)
euer setup --set tax.mode "small_business"
euer setup --set accounts.private "privat, Sparkasse Kreditkarte"

# Konfiguration prüfen
euer config show

# Erste Buchung
euer add expense --payment-date 2026-02-02 --vendor "Test" --category "Laufende EDV-Kosten" --amount -10.00
```

### Wo liegen meine Daten?

- **Datenbank:** `euer.db` im aktuellen Verzeichnis (wo du `euer init` ausgeführt hast)
- **Konfiguration:** `~/.config/euer/config.toml` (systemweit)
- **Belege:** Pfade in der Konfiguration festgelegt
- **Exports:** `exports/` im aktuellen Verzeichnis oder in der Config festgelegt

## Grundbegriffe

- **Ausgaben** haben immer **negative** Beträge (`--amount -10.00`).
- **Einnahmen** haben immer **positive** Beträge (`--amount 10.00`).
- **Privateinlagen/Privatentnahmen** (`add private-*`) verwenden immer **positive** Beträge; die Richtung ergibt sich aus dem Command.
- **Kategorien** sind vorgegeben und müssen existieren: `euer list categories`.
- **Datumsfelder**: `payment_date` (Wertstellung, EÜR-relevant) und `invoice_date` (Rechnungsdatum).
  Mindestens eines der beiden muss gesetzt sein.
- **Belege** können geprüft und geöffnet werden, wenn Pfade konfiguriert sind.
- **Datenbank**: Standard `euer.db` im **aktuellen Verzeichnis**; alternativ via `--db PFAD`.
- **Arbeitsverzeichnis**: Das Tool sucht nach `euer.db` dort, wo du es aufrufst. 
  Wechsle vor dem Arbeiten in deinen Buchhaltungsordner!

## Typische Befehle

### Ausgaben & Einnahmen erfassen

```bash
# Ausgabe
euer add expense --payment-date 2026-01-15 --invoice-date 2026-01-14 --vendor "1und1" \
    --category "Telekommunikation" --amount -39.99 --account "Sparkasse Giro"

# Einnahme
euer add income --payment-date 2026-01-20 --invoice-date 2026-01-18 --source "Kunde ABC" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" --amount 1500.00
```

### Anzeigen & Filtern

```bash
# Default: aktuelles Jahr
euer list expenses --year 2026
euer list expenses --year 2026 --month 1
euer list income --year 2026
euer list categories
```

Hinweis: `list ... --format csv` gibt die Liste als CSV auf stdout aus (für Pipes/Redirects).

### Privatvorgänge

```bash
# Direkte Privatvorgänge
euer add private-deposit --date 2026-01-15 --amount 500 --description "Einlage"
euer add private-withdrawal --date 2026-01-20 --amount 200 --description "Entnahme"

# Als Liste (inkl. Sacheinlagen aus Ausgaben mit privater Zahlung)
euer list private-transfers --year 2026
euer list private-deposits --year 2026
euer list private-withdrawals --year 2026
```

Bei Ausgaben kannst du private Zahlung explizit markieren:

```bash
euer add expense --payment-date 2026-01-10 --vendor "Adobe" \
  --category "Laufende EDV-Kosten" --amount -22.99 --private-paid
```

### Korrigieren & Löschen

```bash
# Ausgabe korrigieren
euer update expense 42 --amount -25.00 --notes "Korrigiert"
euer update expense 42 --payment-date 2026-01-17
euer update expense 42 --invoice-date 2026-01-15
euer update expense 42 --private-paid
euer update expense 42 --no-private-paid

# Privatvorgang korrigieren
euer update private-transfer 7 --amount 600 --description "Korrektur"
euer update private-transfer 7 --clear-related-expense

# Löschen
euer delete expense 42
euer delete expense 42 --force
euer delete private-transfer 7 --force

# Änderungshistorie
euer audit 42 --table expenses
```

### Zusammenfassung & Export

```bash
euer summary --year 2026
euer summary --year 2026 --include-private
euer private-summary --year 2026
euer reconcile private --year 2026 --dry-run
euer reconcile private --year 2026

# Default: CSV, ohne --year = alle Jahre
euer export
euer export --year 2026
# XLSX benötigt openpyxl:
euer export --year 2026 --format xlsx
```

Hinweis: `export` schreibt Dateien ins Export-Verzeichnis:
- Ausgaben
- Einnahmen
- `PrivateTransfers` (direkte Privatvorgänge)
- `Sacheinlagen` (aus `expenses.is_private_paid` abgeleitet)

Hinweis: Für die Kategorie **Bewirtungsaufwendungen** rechnet `euer summary`
den Aufwand automatisch als **70% abziehbar / 30% nicht abziehbar**. In
`list expenses` und Exporten bleibt der Betrag **100%**.

### SQL‑Abfragen (nur lesend)

```bash
# Ausgabe als CSV auf stdout (nur SELECT)
euer query "SELECT id, payment_date, invoice_date, vendor, amount_eur FROM expenses WHERE vendor LIKE '%OpenAI%' ORDER BY payment_date DESC"
```

Hinweis: `query` ist **nur** für SELECT‑Abfragen. Keine Änderungen/Schreiboperationen.

### Bulk‑Import & Unvollständige Einträge

```bash
euer import --file import.csv --format csv
euer import --schema  # Schema + Beispiele

euer incomplete list
euer incomplete list --format csv
```

Hinweise zum Import:
- Pflichtfelder: `type`, `party`, `amount_eur` und mindestens eines aus `payment_date`/`invoice_date` (`date` ist Alias für `payment_date`)
- Optionale Felder: `category`, `account`, `foreign_amount`, `receipt_name`, `notes`, `rc`, `private_paid`, `vat_input`, `vat_output`
- Fehlende Pflichtfelder führen zu einem Import-Abbruch.
- `type` kann fehlen, wenn `amount_eur` ein Vorzeichen hat (negativ = Ausgabe, positiv = Einnahme).
- CSV‑Exports für **Ausgaben/Einnahmen** können direkt re‑importiert werden (Spaltennamen sind gemappt).
- Exporte `PrivateTransfers` und `Sacheinlagen` sind nicht als Standard-Importquelle vorgesehen.
- Kategorien mit `"(NN)"` werden beim Import automatisch bereinigt.
- Alias‑Keys werden akzeptiert (z.B. `EUR`, `Belegname`, `Lieferant`, `Quelle`, `RC`).
- `private_paid=true|1|yes|X` markiert eine importierte Ausgabe manuell als Sacheinlage.
- Steuerfelder:
  - `small_business` + `rc=true`: `vat_output` wird automatisch aus `amount_eur * 0.19` berechnet,
    `vat_input` wird auf `0.0` gesetzt (Felder können weggelassen werden).
  - `standard`: `vat_input` wird **nicht** automatisch berechnet (außer bei RC). Ohne `vat_input`
    bleibt es `0.0`. `amount_eur` wird immer 1:1 gespeichert (keine Netto/Brutto‑Umrechnung).

Workflow für unvollständige Einträge:
1. Import/Add ausführen → Buchungen werden angelegt (Pflichtfelder müssen vorhanden sein).
2. `euer incomplete list` zeigt fehlende **Qualitätsfelder**:
   `payment_date`, `invoice_date`, `category`, `receipt`, `vat`, `account` (abhängig von Typ/Steuermodus).
3. Fehlende Infos per `euer update expense|income <ID>` nachpflegen.
Hinweis: Für die Kategorie **Gezahlte USt (58)** ist kein Beleg erforderlich.

## Beleg‑Verwaltung

### Konfiguration

`euer setup` legt Pfade und den Audit‑User in `~/.config/euer/config.toml` an.
Belege werden in Jahres‑Unterordnern erwartet: `<base>/<Jahr>/<Belegname>`.
Mit `euer setup --set section.key value` kannst du einzelne Werte ohne Prompt setzen.

```toml
[receipts]
expenses = "/pfad/zu/ausgaben-belege"
income = "/pfad/zu/einnahmen-belege"

[exports]
directory = "/pfad/zu/exports"

[user]
name = "Dein Name"

[accounts]
private = ["privat", "private Kreditkarte"]
```

### Prüfen & Öffnen

```bash
euer receipt check --year 2026
euer receipt check --type expense

euer receipt open 12
euer receipt open 5 --table income
```

Tipp: Wenn der gespeicherte Belegname **keine Dateiendung** hat, versucht der Check automatisch
`.pdf`, `.jpg`, `.jpeg` und `.png`.

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

Hinweis: Bei `small_business` setzt RC automatisch `vat_output`, `vat_input` bleibt `0.0`.

## Backfill / Reklassifikation für bestehende DB

Empfohlen ist zuerst der CLI-Abgleich:

```bash
euer reconcile private --year 2026 --dry-run
euer reconcile private --year 2026
```

Das Kommando reklassifiziert persistierte `expenses.is_private_paid`-Werte auf Basis der
aktuellen Config (`[accounts].private`) und lässt manuelle Markierungen unverändert.

### Alternativ: Einmaliger Backfill direkt in SQLite

Wenn du alte Ausgaben nachträglich als private Sacheinlagen markieren willst:

1. Backup erstellen:

```bash
cp euer.db euer.backup.db
```

2. Sicherstellen, dass neue Spalten existieren:

```bash
euer init
```

3. Einmaliger Backfill (Beispiel-Regeln):

```bash
sqlite3 euer.db <<'SQL'
BEGIN;

-- Regel 1: private Konten
UPDATE expenses
SET is_private_paid = 1,
    private_classification = 'account_rule'
WHERE LOWER(COALESCE(account, '')) IN ('privat', 'private kreditkarte', 'barauslagen')
  AND is_private_paid = 0;

-- Regel 2: Nutzungseinlage-Kategorie
UPDATE expenses
SET is_private_paid = 1,
    private_classification = 'category_rule'
WHERE category_id IN (
  SELECT id FROM categories
  WHERE type = 'expense' AND name = 'Fahrtkosten (Nutzungseinlage)'
);

COMMIT;
SQL
```

4. Ergebnis prüfen:

```bash
euer private-summary --year 2026
euer list private-deposits --year 2026
```

Hinweis: Direkte Privatentnahmen/Privateinlagen aus früheren Jahren können nicht zuverlässig aus `expenses`/`income` rekonstruiert werden und sollten bei Bedarf manuell über `add private-deposit`/`add private-withdrawal` nachgetragen werden.


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
