---
name: euer-buchhaltung
description: Verwaltet EÜR-Buchhaltung für deutsche Kleinunternehmer. Nutze es um Ausgaben und Einnahmen zu erfassen, Belege zu prüfen und Zusammenfassungen zu erstellen. Triggers "Ausgabe buchen", "Einnahme erfassen", "Buchhaltung", "EÜR", "Beleg prüfen", "Rechnung buchen"
---

# EÜR Buchhaltung

Dieses Skill ermöglicht die Verwaltung einer Einnahmenüberschussrechnung (EÜR) für deutsche Kleinunternehmer via CLI.

## Tool-Pfad

Das CLI befindet sich im Projektverzeichnis:

```bash
python3 euer.py <command>
```

## Verfügbare Commands

### Ausgaben

```bash
# Ausgabe hinzufügen
python3 euer.py add expense \
    --date YYYY-MM-DD \
    --vendor "Lieferant" \
    --category "Kategorie" \
    --amount -XX.XX  # Brutto-Betrag (negativ, was vom Konto abgeht) \
    [--account "Bankkonto"] \
    [--receipt "Belegname.pdf"] \
    [--foreign "Betrag Währung"] \
    [--notes "Bemerkung"] \
    [--vat 3.50]  # Manueller Steuerbetrag in EUR (nicht %) \
    [--rc]  # Reverse-Charge für ausländische Anbieter

# Ausgaben anzeigen
python3 euer.py list expenses [--year YYYY] [--month MM] [--category "..."]
# Zeigt RC-Flag, USt (Output) und VorSt (Input) an, falls vorhanden.

# Ausgabe aktualisieren
python3 euer.py update expense <ID> [--date ...] [--vendor ...] [--amount ...] [--rc] ...

# Ausgabe löschen
python3 euer.py delete expense <ID> [--force]
```

### Einnahmen

```bash
# Einnahme hinzufügen
python3 euer.py add income \
    --date YYYY-MM-DD \
    --source "Kunde/Quelle" \
    --category "Kategorie" \
    --amount XX.XX  # Brutto-Betrag (positiv, was auf dem Konto eingeht) \
    [--receipt "Belegname.pdf"] \
    [--foreign "Betrag Währung"] \
    [--notes "Bemerkung"] \
    [--vat 285.00]  # Ausgewiesener Umsatzsteuer-Betrag bei Regelbesteuerung (nicht %)

# Einnahmen anzeigen
python3 euer.py list income [--year YYYY] [--month MM]

# Einnahme aktualisieren
python3 euer.py update income <ID> [--date ...] [--source ...] [--amount ...] ...

# Einnahme löschen
python3 euer.py delete income <ID> [--force]
```

### Übersicht & Export

```bash
# Zusammenfassung (Kategorien + Gewinn/Verlust)
python3 euer.py summary [--year YYYY]

# Export als CSV oder XLSX
python3 euer.py export [--year YYYY] [--format csv|xlsx]

# Kategorien anzeigen
python3 euer.py list categories [--type expense|income]

# Audit-Log für Transaktion
python3 euer.py audit <ID> [--table expenses|income]
```

### Bulk-Import

```bash
# Import von CSV oder JSONL
python3 euer.py import --file import.csv --format csv
python3 euer.py import --file import.jsonl --format jsonl

# Unvollständige Einträge anzeigen
python3 euer.py incomplete list
python3 euer.py incomplete list --format csv
```

Hinweis:
- Unvollständige Import-Zeilen (fehlende Pflichtfelder) landen in `incomplete_entries`.
- Standard `add`-Einträge dürfen optionale Felder (z.B. Beleg/Notiz) fehlen und werden
  später per `update` ergänzt.

Workflow:
1. Importieren bzw. Eintrag erfassen, auch wenn Details fehlen.
2. `euer incomplete list` prüfen und offene Aufgaben festhalten (z.B. fehlende Rechnung).
3. Sobald die Info vorliegt, Einträge per `update` ergänzen oder mit vollständigen
   Daten erneut erfassen.
### Beleg-Verwaltung

```bash
# Konfiguration anzeigen
python3 euer.py config show

# Fehlende Belege prüfen
python3 euer.py receipt check [--year YYYY] [--type expense|income]

# Beleg öffnen
python3 euer.py receipt open <ID> [--table expenses|income]
```

## Wichtige Regeln

### Beträge

Der Betrag (`--amount`) entspricht immer dem tatsächlichen **Zahlfluss auf dem Bankkonto** (Brutto).

- **Ausgaben**: Immer NEGATIV (z.B. `--amount -119.00`).
    - Standard-Fall: Das ist der Brutto-Preis inkl. USt.
    - Reverse-Charge: Das ist der Netto-Preis (da keine USt überwiesen wurde).
- **Einnahmen**: Immer POSITIV (z.B. `--amount 119.00`).
    - Standard-Fall: Brutto-Rechnungsbetrag, den der Kunde überwiesen hat.

### Steuermodus (Config)

Das Verhalten hängt von der Konfiguration ab (`~/.config/euer/config.toml`):

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

### Kategorien

Nur diese Kategorien sind verfügbar:

**Ausgaben (expense):**
| Kategorie | EÜR-Zeile |
|-----------|-----------|
| Telekommunikation | 44 |
| Laufende EDV-Kosten | 51 |
| Arbeitsmittel | 52 |
| Werbekosten | 54 |
| Gezahlte USt | 58 |
| Übrige Betriebsausgaben | 60 |
| Bewirtungsaufwendungen | 63 |

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

### Belegnamen

Format: `YYYY-MM-DD_Anbieter.pdf` oder `YYYYMMDD_Anbieter.pdf`

Beispiele:
- `2026-01-15_Render.pdf`
- `20260115_OpenAI.pdf`

Belege werden in Jahres-Unterordnern erwartet:
```
<belege-pfad>/<Jahr>/<Belegname>
```

## Typische Workflows

### Monatliche Buchung

1. Prüfe bestehende Einträge: `python3 euer.py list expenses --year 2026 --month 1`
2. Buche neue Ausgaben mit `add expense`
3. Buche neue Einnahmen mit `add income`
4. Prüfe Belege: `python3 euer.py receipt check --year 2026`

### Jahresabschluss

1. Zusammenfassung anzeigen: `python3 euer.py summary --year 2026`
2. Export erstellen: `python3 euer.py export --year 2026 --format xlsx`
3. Beleg-Vollständigkeit prüfen: `python3 euer.py receipt check --year 2026`

### Korrektur

1. Eintrag finden: `python3 euer.py list expenses --year 2026`
2. Aktualisieren: `python3 euer.py update expense <ID> --amount -XX.XX`
3. Historie prüfen: `python3 euer.py audit <ID>`

## Beispiele

### SaaS-Ausgabe buchen (Render)

```bash
python3 euer.py add expense \
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
python3 euer.py add income \
    --date 2026-01-20 \
    --source "Kunde ABC GmbH" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" \
    --amount 2500.00 \
    --receipt "2026-01-20_Rechnung_001.pdf"
```

### Telefon-Rechnung buchen

```bash
python3 euer.py add expense \
    --date 2026-01-15 \
    --vendor "1und1" \
    --category "Telekommunikation" \
    --amount -39.99 \
    --account "Sparkasse Giro"
```
