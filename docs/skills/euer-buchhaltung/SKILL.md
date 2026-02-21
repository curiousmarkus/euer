---
name: euer-buchhaltung
description: Verwaltet EÜR-Buchhaltung für deutsche Kleinunternehmer. Nutze es um Ausgaben und Einnahmen zu erfassen, Belege zu prüfen und Zusammenfassungen zu erstellen. Triggers "Ausgabe buchen", "Einnahme erfassen", "Buchhaltung", "EÜR", "Beleg prüfen", "Rechnung buchen"
---

# EÜR Buchhaltung

Dieses Skill ermöglicht die Verwaltung einer Einnahmenüberschussrechnung (EÜR) für deutsche Kleinunternehmer via CLI.

## Tool-Pfad

Das CLI befindet sich im Projektverzeichnis:

```bash
euer <command>
```

Falls das CLI nicht installiert ist, geht auch:

```bash
python -m euercli <command>
```

### Datenbank & Config

- Standard‑DB: `euer.db` im Projekt (oder via `--db PFAD`).
- Config: `~/.config/euer/config.toml` (Beleg‑Pfade, Export‑Verzeichnis, Steuer‑Modus, private Konten).
- Direkter sqlite3‑Zugriff ist **verboten**, da sonst Inkonsistenzen auftreten können und das Audit-Log umgangen wird.
- Für fortgeschrittene Abfragen **nur** `euer query` verwenden (nur SELECT, keine Writes).

### SQL‑Abfragen (nur lesend)

Nutze `euer query` für komplexe Filter. Ausgabe ist CSV auf stdout.

```bash
# Ausgaben eines Lieferanten in einem Zeitraum
euer query "SELECT id, date, vendor, amount_eur FROM expenses WHERE vendor LIKE '%OpenAI%' AND date BETWEEN '2026-01-01' AND '2026-12-31' ORDER BY date DESC"

# Große Ausgaben (Betrag <= -500)
euer query "SELECT id, date, vendor, amount_eur FROM expenses WHERE amount_eur <= -500 ORDER BY amount_eur ASC"
```

## Verfügbare Commands

### Ausgaben

```bash
# Ausgabe hinzufügen
euer add expense \
    --date YYYY-MM-DD \
    --vendor "Lieferant" \
    --category "Kategorie" \
    --amount -XX.XX  # Brutto-Betrag (negativ, was vom Konto abgeht) \
    [--account "Bankkonto"] \
    [--receipt "Belegname.pdf"] \
    [--foreign "Betrag Währung"] \
    [--notes "Bemerkung"] \
    [--vat 3.50]  # Manueller Steuerbetrag in EUR (nicht %) \
    [--rc]  # Reverse-Charge für ausländische Anbieter \
    [--private-paid]  # Als privat bezahlt markieren (Sacheinlage)

# Ausgaben anzeigen
euer list expenses [--year YYYY] [--month MM] [--category "..."]
# Zeigt RC-Flag, USt (Output) und VorSt (Input) an, falls vorhanden.

# Ausgabe aktualisieren
euer update expense <ID> [--date ...] [--vendor ...] [--amount ...] [--rc] [--private-paid|--no-private-paid] ...

# Ausgabe löschen
euer delete expense <ID> [--force]
```

### Einnahmen

```bash
# Einnahme hinzufügen
euer add income \
    --date YYYY-MM-DD \
    --source "Kunde/Quelle" \
    --category "Kategorie" \
    --amount XX.XX  # Brutto-Betrag (positiv, was auf dem Konto eingeht) \
    [--receipt "Belegname.pdf"] \
    [--foreign "Betrag Währung"] \
    [--notes "Bemerkung"] \
    [--vat 285.00]  # Ausgewiesener Umsatzsteuer-Betrag bei Regelbesteuerung (nicht %)

# Einnahmen anzeigen
euer list income [--year YYYY] [--month MM]

# Einnahme aktualisieren
euer update income <ID> [--date ...] [--source ...] [--amount ...] ...

# Einnahme löschen
euer delete income <ID> [--force]
```

### Privatvorgänge

```bash
# Privateinlage/Privatentnahme direkt buchen
euer add private-deposit --date YYYY-MM-DD --amount XX.XX --description "..."
euer add private-withdrawal --date YYYY-MM-DD --amount XX.XX --description "..."

# Optional mit Referenz auf Ausgabe (Ausgleich)
euer add private-withdrawal --date YYYY-MM-DD --amount XX.XX --description "..." --related-expense-id <EXPENSE_ID>

# Anzeigen
euer list private-transfers [--year YYYY]
euer list private-deposits [--year YYYY]
euer list private-withdrawals [--year YYYY]

# Ändern/Löschen
euer update private-transfer <ID> [--amount ...] [--description ...] [--related-expense-id <ID>|--clear-related-expense]
euer delete private-transfer <ID> [--force]
```

### Übersicht & Export

```bash
# Zusammenfassung (Kategorien + Gewinn/Verlust)
euer summary [--year YYYY]
euer summary [--year YYYY] [--include-private]

# Privat-Zusammenfassung (ELSTER Zeile 121/122)
euer private-summary --year YYYY

# Export als CSV oder XLSX
euer export [--year YYYY] [--format csv|xlsx]

# SQL-Query (nur SELECT, Ausgabe als CSV)
euer query "SELECT ... FROM ... WHERE ..."

# Kategorien anzeigen
euer list categories [--type expense|income]

# Audit-Log für Transaktion
euer audit <ID> [--table expenses|income|private_transfers]
```

### Bulk-Import

```bash
# Import von CSV oder JSONL
euer import --file import.csv --format csv
euer import --file import.jsonl --format jsonl
euer import --schema  # Schema + Beispiele

# Unvollständige Einträge anzeigen
euer incomplete list
euer incomplete list --format csv
```

Hinweis:
- Fehlende Pflichtfelder brechen den Import ab.
- Standard `add`-Einträge dürfen optionale Felder (z.B. Beleg/Notiz) fehlen und werden
  später per `update` ergänzt.

Workflow:
1. Importieren bzw. Eintrag erfassen, Pflichtfelder müssen vorhanden sein.
2. `euer incomplete list` prüfen und offene Aufgaben festhalten
   (fehlende `category`, `receipt`, `vat`, `account`).
3. Fehlende Felder per `euer update expense <ID>` /
   `euer update income <ID>` ergänzen.
Hinweis: Für die Kategorie **Gezahlte USt (57)** ist kein Beleg erforderlich.

Import-Schema (Kurzfassung):
- Pflichtfelder: `type`, `date`, `party`, `amount_eur`
- Optional: `category`, `account`, `foreign_amount`, `receipt_name`, `notes`, `rc`,
  `vat_input`, `vat_output`
- Fehlende Pflichtfelder führen zu einem Import-Abbruch.
- Alias-Keys (Auszug): `EUR`, `Belegname`, `Lieferant`, `Quelle`, `RC`,
  `Vorsteuer`, `Umsatzsteuer`
- Kategorien wie `Arbeitsmittel (51)` werden automatisch auf `Arbeitsmittel` bereinigt.
- Steuerfelder:
  - `small_business` + `rc=true`: `vat_output` wird automatisch aus `amount_eur * 0.19` berechnet,
    `vat_input` wird auf `0.0` gesetzt (Felder können weggelassen werden).
  - `standard`: `vat_input` wird **nicht** automatisch berechnet (außer bei RC). Ohne `vat_input`
    bleibt es `0.0`. `amount_eur` wird immer 1:1 gespeichert (keine Netto/Brutto‑Umrechnung).
- `private_transfers`/`Sacheinlagen` aus dem Export sind kein Standard-Bulk-Importformat.

### Beleg-Verwaltung

```bash
# Konfiguration anzeigen
euer config show

# Fehlende Belege prüfen
euer receipt check [--year YYYY] [--type expense|income]

# Beleg öffnen
euer receipt open <ID> [--table expenses|income]
```

## Wichtige Regeln

### Beträge

Der Betrag (`--amount`) entspricht immer dem tatsächlichen **Zahlfluss auf dem Bankkonto** (Brutto).

- **Ausgaben**: Immer NEGATIV (z.B. `--amount -119.00`).
    - Standard-Fall: Das ist der Brutto-Preis inkl. USt.
    - Reverse-Charge: Das ist der Netto-Preis (da keine USt überwiesen wurde).
- **Einnahmen**: Immer POSITIV (z.B. `--amount 119.00`).
    - Standard-Fall: Brutto-Rechnungsbetrag, den der Kunde überwiesen hat.
- **Privateinlagen/Privatentnahmen**: Immer POSITIV (`add private-deposit`, `add private-withdrawal`), Richtung ergibt sich aus dem Typ.

### Steuermodus (Config)

Das Verhalten hängt von der Konfiguration ab (`~/.config/euer/config.toml`):

```toml
[tax]
mode = "small_business"  # oder "standard"
```

1.  **Kleinunternehmer (`mode = "small_business"`)**:
    *   Ausgaben werde brutto als Kosten erfasst.
    *   Einnahmen werden in der Regel netto (ohne USt) erfasst.
    *   Reverse-Charge: Erzeugt eine Umsatzsteuerschuld (`vat_output`), die nicht als Vorsteuer abgezogen werden kann.

2.  **Regelbesteuerung (`mode = "standard"`)**:
    *   Ausgaben: Vorsteuer (`vat_input`) wird erfasst (automatisch bei RC oder manuell via `--vat`).
    *   Einnahmen: Umsatzsteuer (`vat_output`) wird erfasst.
    *   Reverse-Charge: Nullsummenspiel (Umsatzsteuer = Vorsteuer).

### Reverse-Charge (--rc)

Verwende `--rc` bei ausländischen Anbietern ohne deutsche USt:
- OpenAI, Anthropic
- Render, Vercel, Netlify
- AWS, Google Cloud, Azure
- GitHub, Stripe

Berechnet automatisch 19% USt.
- **Kleinunternehmer**: Erhöht die Zahllast.
- **Regelbesteuerung**: Bucht USt und VorSt gleichzeitig (Zahllast-neutral).
Hinweis: Bei `small_business` setzt RC automatisch `vat_output`, `vat_input` bleibt `0.0`.

### Kategorien

Nur diese Kategorien sind verfügbar:

**Ausgaben (expense):**
| Kategorie | EÜR-Zeile |
|-----------|-----------|
| Waren, Rohstoffe und Hilfsstoffe | 27 |
| Bezogene Fremdleistungen | 29 |
| Aufwendungen für geringwertige Wirtschaftsgüter (GWG) | 36 |
| Telekommunikation | 43 |
| Übernachtungs- und Reisenebenkosten | 44 |
| Fortbildungskosten | 45 |
| Rechts- und Steuerberatung, Buchführung | 46 |
| Beiträge, Gebühren, Abgaben und Versicherungen | 49 |
| Laufende EDV-Kosten | 50 |
| Arbeitsmittel | 51 |
| Werbekosten | 54 |
| Gezahlte USt | 57 |
| Übrige Betriebsausgaben | 60 |
| Bewirtungsaufwendungen | 63 |
| Verpflegungsmehraufwendungen | 64 |
| Fahrtkosten (Nutzungseinlage) | 71 |

Hinweis: **Bewirtungsaufwendungen** werden in `euer summary` automatisch **70/30**
aufgeteilt. In `list expenses` und Exporten bleibt der volle Betrag (100%) erhalten;
der nicht abziehbare 30%-Anteil wird nur im Summary ausgewiesen.

**Einnahmen (income):**
| Kategorie | EÜR-Zeile |
|-----------|-----------|
| Sonstige betriebsfremde Einnahme | - |
| Umsatzsteuerpflichtige Betriebseinnahmen | 14 |

### Datenmodell (Interpretation der Spalten)

#### Ausgaben (expenses)
| Spalte | Bedeutung | Format / Hinweis |
|--------|-----------|------------------|
| `id` | Eindeutige ID | Automatisch vergeben |
| `date` | Buchungsdatum | `YYYY-MM-DD` |
| `vendor` | Lieferant | Name des Anbieters |
| `category` | Kategorie | Name der Ausgabenkategorie |
| `amount_eur`| Bruttobetrag | **Immer negativ** (z.B. -10.00) |
| `rc` | Reverse-Charge | `X` markiert Steuerpflicht aus dem Ausland |
| `vat_input` | Vorsteuer | Forderung an FA (positiv), nur bei Regelbest. |
| `vat_output`| RC Umsatzsteuer | Schuld an FA (positiv), bei RC |
| `account` | Konto | Verwendetes Bankkonto/Zahlart |
| `receipt_name`| Belegdatei | Name der PDF/JPG Datei |
| `notes` | Notizen | Optionale Bemerkungen |

#### Einnahmen (income)
| Spalte | Bedeutung | Format / Hinweis |
|--------|-----------|------------------|
| `id` | Eindeutige ID | Automatisch vergeben |
| `date` | Buchungsdatum | `YYYY-MM-DD` |
| `source` | Kunde/Quelle | Wer hat gezahlt? |
| `category` | Kategorie | Name der Einnahmenkategorie |
| `amount_eur`| Bruttobetrag | **Immer positiv** (z.B. 1500.00) |
| `vat_output`| Umsatzsteuer | Schuld an FA (positiv), nur bei Regelbest. |
| `receipt_name`| Belegdatei | Name der Rechnungsdatei |
| `notes` | Notizen | Optionale Bemerkungen |

#### Privatvorgänge (private_transfers)
| Spalte | Bedeutung | Format / Hinweis |
|--------|-----------|------------------|
| `id` | Eindeutige ID | Automatisch vergeben |
| `date` | Buchungsdatum | `YYYY-MM-DD` |
| `type` | Richtung | `deposit` oder `withdrawal` |
| `amount_eur` | Betrag | **Immer positiv** |
| `description` | Beschreibung | Pflichtfeld |
| `related_expense_id` | Referenz | Optional, z.B. Ausgleich |

### Belegnamen

Format: `YYYY-MM-DD_Anbieter.pdf` oder `YYYYMMDD_Anbieter.pdf`

Beispiele:
- `2026-01-15_Render.pdf`
- `20260115_OpenAI.pdf`

Belege werden in Jahres-Unterordnern erwartet:
```
<belege-pfad>/<Jahr>/<Belegname>
```

Hinweis: Fehlt die Dateiendung, prüft `euer receipt check` automatisch
`.pdf`, `.jpg`, `.jpeg` und `.png`.

## Typische Workflows

### Monatliche Buchung

1. Prüfe bestehende Einträge: `euer list expenses --year 2026 --month 1`
2. Buche neue Ausgaben mit `add expense`
3. Buche neue Einnahmen mit `add income`
4. Prüfe Belege: `euer receipt check --year 2026`

### Jahresabschluss

1. Zusammenfassung anzeigen: `euer summary --year 2026`
2. Export erstellen: `euer export --year 2026 --format xlsx`
3. Beleg-Vollständigkeit prüfen: `euer receipt check --year 2026`

### Korrektur

1. Eintrag finden: `euer list expenses --year 2026`
2. Aktualisieren: `euer update expense <ID> --amount -XX.XX`
3. Historie prüfen: `euer audit <ID>`

## Beispiele

### SaaS-Ausgabe buchen (Render)

```bash
euer add expense \
    --date 2026-01-04 \
    --vendor "RENDER.COM" \
    --category "Laufende EDV-Kosten" \
    --amount -22.71 \
    --foreign "26.60 USD" \
    --receipt "2026-01-04_Render.pdf" \
    --rc
```

### Kundenrechnung buchen

```bash
euer add income \
    --date 2026-01-20 \
    --source "Kunde ABC GmbH" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" \
    --amount 2500.00 \
    --receipt "2026-01-20_Rechnung_001.pdf"
```

### Telefon-Rechnung buchen

```bash
euer add expense \
    --date 2026-01-15 \
    --vendor "1und1" \
    --category "Telekommunikation" \
    --amount -39.99 \
    --account "Sparkasse Giro"
```
