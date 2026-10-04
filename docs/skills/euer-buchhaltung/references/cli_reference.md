# CLI-Referenz

Alle Core-Befehle der aktiven CLI. Globale Optionen stehen vor dem Befehl;
`--ignore-skill-version` darf auch am Ende stehen. Plugin-Befehle sind hier nicht enthalten.
Für den Ablauf gilt [SKILL.md](../SKILL.md#arbeitsablauf), für die fachliche
Einordnung gelten die [Fachregeln](domain_rules.md). Diese Referenz beschreibt
die CLI-Syntax und Ausgabe, nicht die Buchungsentscheidung.

## Globale Optionen

| Argument | Bedeutung |
|---|---|
| `--version` | Zeigt die installierte Version an |
| `--db` | Pfad zur Datenbank (Standard: ./euer.db oder Projekt-Config) |
| `--config` | Alternative Config für `datev`-Befehle (auch vor `datev` möglich) |
| `--ignore-skill-version` | Umgeht die Skill-Versionssperre für diesen Aufruf |

### euer init

Initialisiert oder aktualisiert die Datenbank

**Syntax:** `euer init [-h] [--create] [--dry-run] [--json] [--save-db-path]`

**Voraussetzung:** Keine Datenbank für Diagnose/Einrichtung erforderlich; Skill-Bestätigung für `init` und interaktives `setup`. `setup --set skill.version` ist ungeblockt.
**Ausgabe:** Migrations- oder Preflight-Bericht; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--create` | Erlaubt die bestätigte Neuanlage einer Datenbank am gewählten Pfad |
| `--dry-run` | Führt Migrationen nur zur Probe aus und zeigt den Plan an, ohne Daten zu verändern |
| `--json` | Gibt den Migrationsbericht oder Dry-Run als JSON aus |
| `--save-db-path` | Speichert den mit --db gewählten Pfad dauerhaft in der Projekt-Config |

**Beispiel:** `euer init --create`

### euer setup

Ersteinrichtung (interaktiv oder --set KEY VALUE)

**Syntax:** `euer setup [-h] [--set KEY VALUE]`

**Voraussetzung:** Keine Datenbank für Diagnose/Einrichtung erforderlich; Skill-Bestätigung für `init` und interaktives `setup`. `setup --set skill.version` ist ungeblockt.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--set` | Setzt einen Config-Wert direkt (z.B. tax.mode small_business) |

**Beispiel:** `euer setup --set skill.version "1.2.0"`

### euer import

Optionale Rechnungsnummern können im CSV-/JSONL-Import als `invoice_number`
oder `Rechnungsnummer` übergeben werden.
Verdächtige Duplikate anhand der Rechnungsnummer brechen den gesamten Import
mit Zeilennummer ab und rollen bereits vorbereitete Buchungen zurück. Exakte
Duplikate werden wie bisher übersprungen.

Bulk-Import von Transaktionen

**Syntax:** `euer import [-h] [--file FILE] [--format {csv,jsonl}] [--dry-run]
                [--schema]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Zusammenfassung des Importlaufs (importiert, Duplikate, Fehler); Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--file` | Pfad zur Importdatei (csv|jsonl), '-' für stdin |
| `--format` | Importformat |
| `--dry-run` | Nur prüfen, nichts speichern |
| `--schema` | Zeigt Import-Schema, Beispiele und Alias-Keys |

**Beispiel:** `euer import --schema`

`euer import --schema` zeigt das aktuelle Importschema und die akzeptierten
Feldnamen. Für CSV/JSONL werden `party`, `amount_eur` und mindestens
`payment_date` oder `invoice_date` benötigt. Ohne `type` wird der Buchungstyp
aus dem Vorzeichen abgeleitet; `date` ist ein Alias für `payment_date`.
Exportierte Ausgaben und Einnahmen sind als Importquelle vorgesehen,
`PrivateTransfers` und `Sacheinlagen` nicht. Bankdateien vor dem Import auf
das Schema normalisieren und den Lauf zuerst mit `--dry-run` prüfen.

### euer add

Fügt Transaktion hinzu

**Syntax:** `euer add [-h] {expense,income,private-deposit,private-withdrawal} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer add --help` zeigt Syntax und Optionen der aktiven Version.

### euer add expense

Ausgabe hinzufügen

**Syntax:** `euer add expense [-h] [--payment-date PAYMENT_DATE]
                     [--invoice-date INVOICE_DATE] --vendor VENDOR
                     [--category CATEGORY] [--ledger-account LEDGER_ACCOUNT]
                     --amount AMOUNT [--account ACCOUNT] [--foreign FOREIGN]
                     [--receipt RECEIPT] [--invoice-number INVOICE_NUMBER]
                     [--notes NOTES] [--vat VAT]
                     [--vat-rate {0.0,7.0,19.0}] [--tip ENTERTAINMENT_TIP_EUR]
                     [--entertainment-vat-status {deductible,no_deduction,needs_review}]
                     [--private-paid] [--rc {eu,third-country}] [--force]
                     [--allow-duplicate]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--payment-date`, `--date` | Wertstellungsdatum (YYYY-MM-DD) |
| `--invoice-date` | Rechnungsdatum (YYYY-MM-DD) |
| `--vendor` | Lieferant/Zweck |
| `--category` | Kategorie |
| `--ledger-account` | Buchungskonto aus dem Kontenrahmen (setzt Kategorie automatisch) |
| `--amount` | Betrag in EUR |
| `--account` | Bankkonto |
| `--foreign` | Fremdwährungsbetrag |
| `--receipt` | Belegname |
| `--invoice-number` | Optionale Rechnungsnummer |
| `--notes` | Bemerkung |
| `--vat` | Belegter abziehbarer Vorsteuerbetrag in EUR (bei Bewirtung ausdrücklich geprüft) |
| `--vat-rate` | Vorsteuer-Steuersatz (0, 7, 19) |
| `--tip` | Im Zahlbetrag enthaltenes freiwilliges Trinkgeld (nur Bewirtung) |
| `--entertainment-vat-status` | Vorsteuerstatus bzw. Prüfbedarf der Bewirtung |
| `--private-paid` | Markiert Ausgabe als privat bezahlt (Sacheinlage) |
| `--rc` | Reverse-Charge mit Jurisdiktion: eu oder third-country |
| `--force` | Erzwingt Buchung trotz Schwellenwert-Überschreitung oder möglicher Duplikate |
| `--allow-duplicate` | Erlaubt mögliches Duplikat trotz Ähnlichkeit |

**Beispiel:** `euer add expense --date 2026-01-15 --vendor "Hosting" --category "Laufende EDV-Kosten" --amount -10.00`

### euer add income

Einnahme hinzufügen

**Syntax:** `euer add income [-h] [--payment-date PAYMENT_DATE]
                    [--invoice-date INVOICE_DATE] --source SOURCE
                    [--category CATEGORY] [--ledger-account LEDGER_ACCOUNT]
                    --amount AMOUNT [--account ACCOUNT] [--foreign FOREIGN]
                    [--receipt RECEIPT] [--invoice-number INVOICE_NUMBER]
                    [--notes NOTES] [--vat VAT] [--vat-rate {0.0,7.0,19.0}]
                    [--tax-free] [--force] [--allow-duplicate]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--payment-date`, `--date` | Wertstellungsdatum (YYYY-MM-DD) |
| `--invoice-date` | Rechnungsdatum (YYYY-MM-DD) |
| `--source` | Quelle/Zweck |
| `--category` | Kategorie |
| `--ledger-account` | Buchungskonto aus dem Kontenrahmen (setzt Kategorie automatisch) |
| `--amount` | Betrag in EUR |
| `--account` | Bankkonto/Zahlungskonto |
| `--foreign` | Fremdwährungsbetrag |
| `--receipt` | Belegname |
| `--invoice-number` | Optionale Rechnungsnummer |
| `--notes` | Bemerkung |
| `--vat` | Umsatzsteuer-Betrag (für Regelb.) |
| `--vat-rate` | USt-Satz für Ausgangsumsätze (0, 7, 19) |
| `--tax-free` | Steuerfreie oder nicht steuerbare Einnahme nach fachlicher Prüfung |
| `--force` | Erzwingt Buchung trotz Schwellenwert-Überschreitung oder möglicher Duplikate |
| `--allow-duplicate` | Erlaubt mögliches Duplikat trotz Ähnlichkeit |

**Beispiel:** `euer add income --date 2026-01-20 --source "Kunde" --amount 150.00`

### euer add private-deposit

Privateinlage hinzufügen

**Syntax:** `euer add private-deposit [-h] --date DATE --amount AMOUNT
                             --description DESCRIPTION [--notes NOTES]
                             [--related-expense-id RELATED_EXPENSE_ID]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--date` | Datum (YYYY-MM-DD) |
| `--amount` | Betrag in EUR (positiv) |
| `--description` | Beschreibung |
| `--notes` | Bemerkung |
| `--related-expense-id` | Optionale Referenz auf Ausgabe-ID |

**Beispiel:** `euer add private-deposit --help` zeigt Syntax und Optionen der aktiven Version.

### euer add private-withdrawal

Privatentnahme hinzufügen

**Syntax:** `euer add private-withdrawal [-h] --date DATE --amount AMOUNT
                                --description DESCRIPTION [--notes NOTES]
                                [--related-expense-id RELATED_EXPENSE_ID]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--date` | Datum (YYYY-MM-DD) |
| `--amount` | Betrag in EUR (positiv) |
| `--description` | Beschreibung |
| `--notes` | Bemerkung |
| `--related-expense-id` | Optionale Referenz auf Ausgabe-ID |

**Beispiel:** `euer add private-withdrawal --help` zeigt Syntax und Optionen der aktiven Version.

### euer list

Listet Daten

**Syntax:** `euer list [-h] [--trash]
              {expenses,income,categories,ledger-accounts,private-deposits,private-withdrawals,private-transfers} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--trash` | Gelöschte Einträge (Papierkorb) anzeigen |

**Beispiel:** `euer list --help` zeigt Syntax und Optionen der aktiven Version.

### euer list expenses

Ausgaben anzeigen

**Syntax:** `euer list expenses [-h] [--year YEAR] [--month MONTH]
                       [--category CATEGORY] [--account ACCOUNT]
                       [--format {table,csv}] [--full] [--trash]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern (default: aktuelles) |
| `--month` | Monat filtern (1-12) |
| `--category` | Kategorie filtern |
| `--account` | Konto filtern |
| `--format` | Ausgabeformat (`table` oder `csv`) |
| `--full` | Tabellenansicht mit zusätzlichen Spalten (Konto, Beleg, Fremdwährung, Notiz) |
| `--trash` | Nur gelöschte Ausgaben anzeigen |

**Beispiel:** `euer list expenses --year 2026`

### euer list income

Einnahmen anzeigen

**Syntax:** `euer list income [-h] [--year YEAR] [--month MONTH] [--category CATEGORY]
                     [--account ACCOUNT] [--format {table,csv}] [--full] [--trash]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern (default: aktuelles) |
| `--month` | Monat filtern (1-12) |
| `--category` | Kategorie filtern |
| `--account` | Konto filtern |
| `--format` | Ausgabeformat (`table` oder `csv`) |
| `--full` | Tabellenansicht mit zusätzlichen Spalten (Konto, Beleg, Fremdwährung, Notiz) |
| `--trash` | Nur gelöschte Einnahmen anzeigen |

**Beispiel:** `euer list income --year 2026`

### euer list categories

Kategorien anzeigen

**Syntax:** `euer list categories [-h] [--type {expense,income}] [--year YEAR]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--type` | Typ filtern |
| `--year` | Geprüftes Formularjahr anzeigen |

**Beispiel:** `euer list categories --year 2026`

### euer list ledger-accounts

Kontenrahmen anzeigen

**Syntax:** `euer list ledger-accounts [-h] [--category CATEGORY]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Textübersicht nach Kategorien; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--category` | Kategorie filtern |

**Beispiel:** `euer list ledger-accounts`

### euer list private-deposits

Privateinlagen anzeigen

**Syntax:** `euer list private-deposits [-h] [--year YEAR] [--format {table,csv}]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern |
| `--format` | Ausgabeformat (`table` oder `csv`) |

**Beispiel:** `euer list private-deposits --help` zeigt Syntax und Optionen der aktiven Version.

### euer list private-withdrawals

Privatentnahmen anzeigen

**Syntax:** `euer list private-withdrawals [-h] [--year YEAR] [--format {table,csv}]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern |
| `--format` | Ausgabeformat (`table` oder `csv`) |

**Beispiel:** `euer list private-withdrawals --help` zeigt Syntax und Optionen der aktiven Version.

### euer list private-transfers

Privateinlagen und Privatentnahmen anzeigen

**Syntax:** `euer list private-transfers [-h] [--year YEAR] [--format {table,csv}]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern |
| `--format` | Ausgabeformat (`table` oder `csv`) |

**Beispiel:** `euer list private-transfers --help` zeigt Syntax und Optionen der aktiven Version.

### euer update

Aktualisiert Transaktion

**Syntax:** `euer update [-h] {expense,income,private-transfer} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer update --help` zeigt Syntax und Optionen der aktiven Version.

### euer update expense

Ausgabe aktualisieren

**Syntax:** `euer update expense [-h] [--payment-date PAYMENT_DATE]
                        [--invoice-date INVOICE_DATE] [--vendor VENDOR]
                        [--category CATEGORY]
                        [--ledger-account LEDGER_ACCOUNT] [--amount AMOUNT]
                        [--account ACCOUNT] [--foreign FOREIGN]
                        [--receipt RECEIPT] [--invoice-number INVOICE_NUMBER]
                        [--notes NOTES] [--vat VAT]
                        [--vat-rate {0.0,7.0,19.0}]
                        [--tip ENTERTAINMENT_TIP_EUR]
                        [--entertainment-vat-status {deductible,no_deduction,needs_review}]
                        [--private-paid | --no-private-paid]
                        [--rc {eu,third-country} | --no-rc] [--force]
                        [--allow-duplicate]
                        id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | ID der Ausgabe |
| `--payment-date`, `--date` | Neues Wertstellungsdatum |
| `--invoice-date` | Neues Rechnungsdatum |
| `--vendor` | Neuer Lieferant |
| `--category` | Neue Kategorie |
| `--ledger-account` | Neues Buchungskonto aus dem Kontenrahmen |
| `--amount` | Neuer Betrag |
| `--account` | Neues Konto |
| `--foreign` | Neuer Fremdwährungsbetrag |
| `--receipt` | Neuer Belegname |
| `--invoice-number` | Neue Rechnungsnummer; leerer Wert entfernt sie |
| `--notes` | Neue Bemerkung |
| `--vat` | Belegter abziehbarer Vorsteuerbetrag in EUR |
| `--vat-rate` | Neuer Vorsteuer-Steuersatz (0, 7, 19) |
| `--tip` | Im Zahlbetrag enthaltenes Trinkgeld (nur Bewirtung) |
| `--entertainment-vat-status` | Vorsteuerstatus bzw. Prüfbedarf der Bewirtung nachpflegen |
| `--private-paid` | Markiert Ausgabe als privat bezahlt (Sacheinlage) |
| `--no-private-paid` | Entfernt Markierung als privat bezahlt |
| `--rc` | Setzt Reverse-Charge mit Jurisdiktion: eu oder third-country |
| `--no-rc` | Entfernt Reverse-Charge und Jurisdiktion |
| `--force` | Erzwingt Änderung trotz Schwellenwert-Überschreitung oder möglicher Duplikate |
| `--allow-duplicate` | Erlaubt mögliches Duplikat trotz Ähnlichkeit |

**Beispiel:** `euer update expense 1 --notes "Beleg geprüft"`

### euer update income

Einnahme aktualisieren

**Syntax:** `euer update income [-h] [--payment-date PAYMENT_DATE]
                       [--invoice-date INVOICE_DATE] [--source SOURCE]
                       [--category CATEGORY] [--ledger-account LEDGER_ACCOUNT]
                       [--amount AMOUNT] [--account ACCOUNT] [--foreign FOREIGN]
                       [--receipt RECEIPT] [--invoice-number INVOICE_NUMBER]
                       [--notes NOTES] [--vat VAT]
                       [--vat-rate {0.0,7.0,19.0}] [--tax-free] [--force]
                       [--allow-duplicate]
                       id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | ID der Einnahme |
| `--payment-date`, `--date` | Neues Wertstellungsdatum |
| `--invoice-date` | Neues Rechnungsdatum |
| `--source` | Neue Quelle |
| `--category` | Neue Kategorie |
| `--ledger-account` | Neues Buchungskonto aus dem Kontenrahmen |
| `--amount` | Neuer Betrag |
| `--account` | Neues Zahlungskonto (leer zum Entfernen) |
| `--foreign` | Neuer Fremdwährungsbetrag |
| `--receipt` | Neuer Belegname |
| `--invoice-number` | Neue Rechnungsnummer; leerer Wert entfernt sie |
| `--notes` | Neue Bemerkung |
| `--vat` | Neue Umsatzsteuer |
| `--vat-rate` | Neuer USt-Satz für Ausgangsumsätze (0, 7, 19) |
| `--tax-free` | Setzt die Einnahme auf steuerfrei ohne Vorsteuerabzug |
| `--force` | Erzwingt Änderung trotz Schwellenwert-Überschreitung oder möglicher Duplikate |
| `--allow-duplicate` | Erlaubt mögliches Duplikat trotz Ähnlichkeit |

**Beispiel:** `euer update income --help` zeigt Syntax und Optionen der aktiven Version.

### euer update private-transfer

Privatvorgang aktualisieren

**Syntax:** `euer update private-transfer [-h] [--date DATE] [--amount AMOUNT]
                                 [--description DESCRIPTION] [--notes NOTES]
                                 [--related-expense-id RELATED_EXPENSE_ID |
                                 --clear-related-expense]
                                 id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | ID des Privatvorgangs |
| `--date` | Neues Datum |
| `--amount` | Neuer Betrag |
| `--description` | Neue Beschreibung |
| `--notes` | Neue Bemerkung |
| `--related-expense-id` | Optionale Referenz auf Ausgabe-ID |
| `--clear-related-expense` | Entfernt die Referenz auf eine Ausgabe |

**Beispiel:** `euer update private-transfer --help` zeigt Syntax und Optionen der aktiven Version.

### euer delete

Löscht Transaktion

**Syntax:** `euer delete [-h] {expense,income,private-transfer} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer delete --help` zeigt Syntax und Optionen der aktiven Version.

### euer delete expense

Ausgabe löschen

**Syntax:** `euer delete expense [-h] [--force] [--purge] id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | ID der Ausgabe |
| `--force` | Keine Rückfrage |
| `--purge` | Endgültig löschen (Purge statt Papierkorb) |

**Beispiel:** `euer delete expense 1`

### euer delete income

Einnahme löschen

**Syntax:** `euer delete income [-h] [--force] [--purge] id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | ID der Einnahme |
| `--force` | Keine Rückfrage |
| `--purge` | Endgültig löschen (Purge statt Papierkorb) |

**Beispiel:** `euer delete income --help` zeigt Syntax und Optionen der aktiven Version.

### euer delete private-transfer

Privatvorgang löschen

**Syntax:** `euer delete private-transfer [-h] [--force] [--purge] id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | ID des Privatvorgangs |
| `--force` | Keine Rückfrage |
| `--purge` | Endgültig löschen (Purge statt Papierkorb) |

**Beispiel:** `euer delete private-transfer --help` zeigt Syntax und Optionen der aktiven Version.

### euer restore

Stellt gelöschten Datensatz wieder her

**Syntax:** `euer restore [-h] [--table {expenses,income,private_transfers}] id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | ID des wiederherzustellenden Eintrags |
| `--table` | Tabelle des Eintrags (optional, wird sonst automatisch ermittelt) |

**Beispiel:** `euer restore 1 --table expenses`

### euer undo

Macht eine Änderung rückgängig

**Syntax:** `euer undo [-h] [--id ID] [--force]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--id` | Spezifische Audit-Log-ID rückgängig machen |
| `--force` | Keine interaktive Bestätigung anfordern |

**Beispiel:** `euer undo`

### euer trash

Verwaltet den Papierkorb

**Syntax:** `euer trash [-h] {list,empty} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer trash --help` zeigt Syntax und Optionen der aktiven Version.

### euer trash list

Gelöschte Einträge anzeigen

**Syntax:** `euer trash list [-h]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle gelöschter Einträge; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer trash list`

### euer trash empty

Papierkorb endgültig leeren

**Syntax:** `euer trash empty [-h] [--force]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--force` | Keine Rückfrage |

**Beispiel:** `euer trash empty --help` zeigt Syntax und Optionen der aktiven Version.

### euer export

Exportiert Daten

**Syntax:** `euer export [-h] [--year YEAR] [--format {csv,xlsx}] [--output OUTPUT]
                [--force]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung und Exportdateien (CSV oder XLSX); Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern (ohne Angabe: alle Jahre exportieren) |
| `--format` | Exportformat (`csv` oder `xlsx`) |
| `--output` | Ausgabeverzeichnis (Config `exports.directory` oder `./exports`) |
| `--force` | Bestehende Exportdateien überschreiben |

**Beispiel:** `euer export --year 2026`

Ohne `--year` werden alle Jahre exportiert; Standardformat ist CSV, XLSX
benötigt `openpyxl`. Der Export schreibt Ausgaben, Einnahmen, direkte
Privatvorgänge und aus privat bezahlten Ausgaben abgeleitete Sacheinlagen.
Vorhandene Zieldateien blockieren den Export; `--force` überschreibt sie
erst nach Prüfung des Zielordners. Gelöschte Buchungen bleiben ausgeschlossen.
Der Dateisatz wird nicht als Ganzes atomar ersetzt. Ein Export ist weder
vollständiges SQLite-Backup noch rechtlich revisionssicheres Archiv.

### euer summary

Zeigt Zusammenfassung

**Syntax:** `euer summary [-h] [--year YEAR] [--include-private]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** EÜR-Jahreszusammenfassung als formatierter Text; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr (default: aktuelles) |
| `--include-private` | Zeigt zusätzlich Privateinlagen und Privatentnahmen |

**Beispiel:** `euer summary --year 2026`

### euer vat-report

Erzeugt einen ELSTER-nahen USt-Voranmeldungs-Report

**Syntax:** `euer vat-report [-h] --year YEAR [--quarter {1,2,3,4} |
                    --month {1,2,3,4,5,6,7,8,9,10,11,12}]
                    [--format {table,csv,xlsx}] [--output OUTPUT]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** UStVA-Bericht (Tabelle, CSV oder XLSX); Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr |
| `--quarter` | Quartal |
| `--month` | Monat |
| `--format` | Ausgabeformat |
| `--output` | Ausgabeverzeichnis für CSV/XLSX (Config `exports.directory` oder `./exports`) |

**Beispiel:** `euer vat-report --year 2026 --quarter 1`

Der Arbeitsbericht nutzt nur `payment_date`; Buchungen ohne Wertstellungsdatum
erscheinen in der Diagnose und werden nicht summiert. CSV erzeugt zusätzlich
eine Diagnose-Datei, XLSX ein Sheet `Diagnose`. Er übermittelt nichts an ELSTER.

### euer private-summary

Zeigt ELSTER-Summen für Privatvorgänge

**Syntax:** `euer private-summary [-h] --year YEAR`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Übersicht der Privatvorgänge; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr |

**Beispiel:** `euer private-summary --year 2026`

### euer reconcile

Abgleich/Fix für persistierte Daten

**Syntax:** `euer reconcile [-h] {private} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Deutschsprachige Bestätigung oder Bericht; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer reconcile --help` zeigt Syntax und Optionen der aktiven Version.

### euer reconcile private

Reklassifiziert Sacheinlagen anhand aktueller Config

**Syntax:** `euer reconcile private [-h] [--year YEAR] [--dry-run]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Zusammenfassung der reklassifizierten Sacheinlagen; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Optionales Jahr (ohne Angabe: alle Jahre) |
| `--dry-run` | Nur geplante Änderungen anzeigen |

**Beispiel:** `euer reconcile private --help` zeigt Syntax und Optionen der aktiven Version.

### euer query

Führt eine SQL-SELECT-Query aus (nur lesend)

**Syntax:** `euer query [-h] ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle der Abfrageergebnisse; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `sql` | SQL-Query (nur SELECT, bitte in Anführungszeichen) |

**Beispiel:** `euer query "SELECT id, vendor FROM expenses LIMIT 5"`

### euer audit

Zeigt Änderungshistorie

**Syntax:** `euer audit [-h] [--table {expenses,income,private_transfers}] id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle der Änderungshistorie; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | Datensatz-ID |
| `--table` | Tabelle (default: expenses) |

**Beispiel:** `euer audit 1 --table expenses`

### euer config

Konfiguration verwalten

**Syntax:** `euer config [-h] {show} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Konfigurationsausgabe; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer config --help` zeigt Syntax und Optionen der aktiven Version.

### euer config show

Zeigt aktuelle Konfiguration

**Syntax:** `euer config show [-h]`

**Voraussetzung:** Keine Datenbank für Diagnose/Einrichtung erforderlich; Skill-Bestätigung für `init` und interaktives `setup`. `setup --set skill.version` ist ungeblockt.
**Ausgabe:** Formatierte Konfigurationsübersicht; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer config show`

### euer receipt

Beleg-Verwaltung

**Syntax:** `euer receipt [-h] {check,unbooked,open} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Prüfbericht oder Bestätigung; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer receipt --help` zeigt Syntax und Optionen der aktiven Version.

### euer receipt check

Prüft Transaktionen auf fehlende Belege

**Syntax:** `euer receipt check [-h] [--year YEAR] [--type {expense,income}]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierter Prüfbericht; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr (default: aktuelles) |
| `--type` | Nur diesen Typ prüfen |

**Beispiel:** `euer receipt check --year 2026`

### euer receipt unbooked

Findet unterstützte Belegdateien im Zahlungsjahr ohne zugeordnete aktive Buchung.
Der Befehl scannt rekursiv die konfigurierten Ausgaben- und Einnahmenordner.
Ein Treffer kann bereits gebucht sein, wenn die Belegreferenz fehlt oder falsch ist.
Prüfe deshalb zuerst bestehende Buchungen und die Ablage im Zahlungsjahr; ordne
einen vorhandenen Vorgang per `update ... --receipt ...` zu. Buche nur einen
tatsächlich noch nicht erfassten Vorgang neu.

**Syntax:** `euer receipt unbooked [--year JAHR] [--type {expense,income}] [--format {table,csv,json}]`

`--year` wählt das Ablagejahr (Standard: aktuelles Kalenderjahr), `--type`
begrenzt den Scan auf einen Typordner. `--format` wählt Tabelle, CSV oder JSON;
JSON gibt Zähler, Treffer,
Warnungen, übersprungene Einträge und Fehler strukturiert aus. CSV enthält nur
Treffer; Diagnosen stehen auf stderr. Exit-Code 0 bedeutet vollständiger Scan
ohne Treffer, 1 vollständiger Scan mit Treffern und 2 fehlgeschlagene oder
unvollständige Prüfung. Warnungen, besonders `missing_payment_date`, auswerten.
Ein Scan ohne Treffer beweist weder Vollständigkeit noch fachliche Richtigkeit.

**Beispiel:** `euer receipt unbooked --year 2026 --format json`

### euer receipt open

Öffnet Beleg einer Transaktion

**Syntax:** `euer receipt open [-h] [--table {expenses,income}] id`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Öffnet die Datei im Standardbetrachter; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `id` | Transaktions-ID |
| `--table` | Tabelle (default: expenses) |

**Beispiel:** `euer receipt open 1`

### euer incomplete

Unvollständige Buchungen

**Syntax:** `euer incomplete [-h] {list} ...`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle unvollständiger Einträge; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|

**Beispiel:** `euer incomplete --help` zeigt Syntax und Optionen der aktiven Version.

### euer incomplete list

Listet unvollständige Einträge

**Syntax:** `euer incomplete list [-h] [--type {expense,income}] [--year YEAR]
                         [--format {table,csv}]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--type` | Typ filtern |
| `--year` | Jahr filtern |
| `--format` | Ausgabeformat (`table` oder `csv`) |

**Beispiel:** `euer incomplete list --year 2026`

### euer doctor

Umgebungs- und Pre-Flight-Diagnose

**Syntax:** `euer doctor [-h] [--json]`

**Voraussetzung:** Keine Datenbank für Diagnose/Einrichtung erforderlich; Skill-Bestätigung für `init` und interaktives `setup`. `setup --set skill.version` ist ungeblockt.
**Ausgabe:** Diagnosebericht; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--json` | Maschinenlesbare JSON-Ausgabe |

**Beispiel:** `euer doctor`
