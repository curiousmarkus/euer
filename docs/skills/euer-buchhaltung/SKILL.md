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
- Config: `~/.config/euer/config.toml` (Beleg‑Pfade, Export‑Verzeichnis, Steuer‑Modus, private Konten, optionaler Kontenrahmen via `[[ledger_accounts]]`).
- Non-interaktiv setzen: `euer setup --set <section.key> <value>` (z.B. `tax.mode`, `accounts.private`).
- Direkter sqlite3‑Zugriff ist **verboten**, da sonst Inkonsistenzen auftreten können und das Audit-Log umgangen wird.
- Für fortgeschrittene Abfragen **nur** `euer query` verwenden (nur SELECT, keine Writes).

### Config-Verwaltung

Alle Config-Werte lassen sich mit `euer setup` lesen und ändern:

```bash
# Aktuelle Config anzeigen
euer config show

# Einzelne Werte setzen
euer setup --set tax.mode "small_business"           # oder "standard"
euer setup --set receipts.expenses "/pfad/zu/belegen"
euer setup --set receipts.income "/pfad/zu/rechnungen"
euer setup --set exports.directory "/pfad/zu/exports"
euer setup --set user.name "Max"

# Private Konten (kommasepariert)
euer setup --set accounts.private "p-sparkasse-giro, p-sparkasse-kk"
```

**`accounts.private`** — Liste von Konto-Kennungen, die als privat gelten.
Wenn eine Ausgabe mit `--account <kennung>` gebucht wird und die Kennung in dieser Liste steht,
wird die Ausgabe automatisch als Sacheinlage (Privateinlage) klassifiziert.
Das Matching ist **case-insensitiv**. Nach Änderung der Liste: `euer reconcile private`
ausführen, um bestehende Buchungen gegen die neue Config abzugleichen.

**`[[ledger_accounts]]`** — optionaler Kontenrahmen für Buchungskonten.
Wenn vorhanden, kann der Agent statt `--category` auch `--ledger-account <key>`
verwenden. Die Kategorie wird dann automatisch aus der Config aufgelöst.

### SQL‑Abfragen (nur lesend)

Nutze `euer query` für komplexe Filter. Ausgabe ist CSV auf stdout.

```bash
# Ausgaben eines Lieferanten in einem Zeitraum
euer query "SELECT id, payment_date, invoice_date, vendor, amount_eur FROM expenses WHERE vendor LIKE '%OpenAI%' AND payment_date BETWEEN '2026-01-01' AND '2026-12-31' ORDER BY payment_date DESC"

# Große Ausgaben (Betrag <= -500)
euer query "SELECT id, payment_date, invoice_date, vendor, amount_eur FROM expenses WHERE amount_eur <= -500 ORDER BY amount_eur ASC"
```

## Verfügbare Commands

### Ausgaben

```bash
# Ausgabe hinzufügen
euer add expense \
    --payment-date YYYY-MM-DD \
    [--invoice-date YYYY-MM-DD] \
    --vendor "Lieferant" \
    [--category "Kategorie"] \
    [--ledger-account "hosting"] \
    --amount -XX.XX  # Brutto-Betrag (negativ, was vom Konto abgeht) \
    [--account "Bankkonto"] \
    [--receipt "Belegname.pdf"] \
    [--foreign "Betrag Währung"] \
    [--notes "Bemerkung"] \
    [--vat 3.50]  # Manueller Steuerbetrag in EUR (nicht %) \
    [--rc]  # Reverse-Charge für ausländische Anbieter \
    [--private-paid]  # Als privat bezahlt markieren (Sacheinlage)

# Ausgaben anzeigen
euer list expenses [--year YYYY] [--month MM] [--category "..."] [--full]
# Zeigt RC-Flag, USt (Output) und VorSt (Input) an, falls vorhanden.
# Mit --full zeigt die Tabelle zusätzlich Konto, Beleg, Fremdwährung und Notiz.
# Kategorieanzeige in Listen: `(<EÜR-Zeile>) <Name>` (z.B. `(51) Arbeitsmittel`).

# Ausgabe aktualisieren
euer update expense <ID> [--payment-date ...] [--invoice-date ...] [--vendor ...] [--amount ...] [--rc] [--private-paid|--no-private-paid] ...

# Ausgabe löschen
euer delete expense <ID> [--force]
```

### Einnahmen

```bash
# Einnahme hinzufügen
euer add income \
    --payment-date YYYY-MM-DD \
    [--invoice-date YYYY-MM-DD] \
    --source "Kunde/Quelle" \
    [--category "Kategorie"] \
    [--ledger-account "erloese-19"] \
    --amount XX.XX  # Brutto-Betrag (positiv, was auf dem Konto eingeht) \
    [--receipt "Belegname.pdf"] \
    [--foreign "Betrag Währung"] \
    [--notes "Bemerkung"] \
    [--vat 285.00]  # Ausgewiesener Umsatzsteuer-Betrag bei Regelbesteuerung (nicht %)

# Einnahmen anzeigen
euer list income [--year YYYY] [--month MM] [--full]
# Tabellenansicht zeigt immer die Spalte USt (vat_output).
# Mit --full kommt zusätzlich die Spalte Notiz hinzu.

# Einnahme aktualisieren
euer update income <ID> [--payment-date ...] [--invoice-date ...] [--source ...] [--amount ...] ...

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

# Persistierte private Klassifikation nachziehen (z.B. nach Setup-Änderung)
euer reconcile private [--year YYYY] [--dry-run]

# Export als CSV oder XLSX
euer export [--year YYYY] [--format csv|xlsx]

# SQL-Query (nur SELECT, Ausgabe als CSV)
euer query "SELECT ... FROM ... WHERE ..."

# Kategorien anzeigen
euer list categories [--type expense|income]

# Kontenrahmen anzeigen
euer list ledger-accounts [--category "..."]

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
   (fehlende `payment_date`, `invoice_date`, `category`, `receipt`, `vat`, `account`).
3. Fehlende Felder per `euer update expense <ID>` /
   `euer update income <ID>` ergänzen.
Hinweis: Für die Kategorie **Gezahlte USt (57)** ist kein Beleg erforderlich.

Import-Schema (Kurzfassung):
- Pflichtfelder: `type`, `party`, `amount_eur` und mindestens eines aus `payment_date`/`invoice_date` (`date` gilt als Alias für `payment_date`)
- Optional: `category`, `account`, `ledger_account`, `foreign_amount`, `receipt_name`, `notes`, `rc`,
  `private_paid`, `vat_input`, `vat_output`
- Fehlende Pflichtfelder führen zu einem Import-Abbruch.
- Alias-Keys (Auszug): `EUR`, `Belegname`, `Lieferant`, `Quelle`, `RC`,
  `Vorsteuer`, `Umsatzsteuer`, `Privat bezahlt`
- `private_paid=true|1|yes|X` markiert die Ausgabe manuell als Sacheinlage.
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
| Betriebseinnahmen als Kleinunternehmer | 12 |
| Nicht steuerbare Umsätze | 13 |
| Umsatzsteuerpflichtige Betriebseinnahmen | 15 |
| Umsatzsteuerfreie, nicht umsatzsteuerbare Betriebseinnahmen | 16 |
| Vereinnahmte Umsatzsteuer | 17 |
| Vom Finanzamt erstattete Umsatzsteuer | 18 |
| Veräußerung oder Entnahme von Anlagevermögen | 19 |
| Private Kfz-Nutzung | 20 |
| Sonstige Sach-, Nutzungs- und Leistungsentnahmen | 21 |

### Datenmodell (Interpretation der Spalten)

#### Ausgaben (expenses)
| Spalte | Bedeutung | Format / Hinweis |
|--------|-----------|------------------|
| `id` | Eindeutige ID | Automatisch vergeben |
| `payment_date` | Wertstellungsdatum (EÜR) | `YYYY-MM-DD`, kann leer sein |
| `invoice_date` | Rechnungsdatum | `YYYY-MM-DD`, kann leer sein |
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
| `payment_date` | Wertstellungsdatum (EÜR) | `YYYY-MM-DD`, kann leer sein |
| `invoice_date` | Rechnungsdatum | `YYYY-MM-DD`, kann leer sein |
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

### Privat bezahlte Rechnung buchen (Sacheinlage)

```bash
euer add expense \
    --date 2026-01-15 \
    --vendor "Amazon" \
    --category "Arbeitsmittel" \
    --amount -19.99 \
    --account "p-sparkasse-giro" \
    --receipt "2026-01-15_Amazon.pdf"
```

Hinweis: Wenn `account` einen in `config.toml [accounts].private` konfigurierten Wert hat
(z.B. `p-sparkasse-giro`), wird die Ausgabe automatisch als Sacheinlage (Privateinlage) erfasst.
Alternativ kann `--private-paid` explizit gesetzt werden.

### Anteilig absetzbare Ausgabe buchen (gemischte Nutzung)

Bei Ausgaben mit sowohl privater als auch geschäftlicher Nutzung wird **nur der geschäftliche Anteil** gebucht.
Der volle Rechnungsbetrag wird in `--notes` dokumentiert.

**Beispiel: Internet-Anschluss, 50% geschäftlich, privat bezahlt:**

```bash
euer add expense \
    --date 2026-01-20 \
    --vendor "Vodafone" \
    --category "Telekommunikation" \
    --amount -24.95 \
    --account "p-sparkasse-giro" \
    --receipt "2026-01-20_Vodafone.pdf" \
    --notes "Internet 49,90 EUR, 50% geschäftlich"
```
