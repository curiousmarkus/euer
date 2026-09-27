# CLI-Referenz

Alle Core-Befehle der aktiven CLI. Globale Optionen stehen vor dem Befehl;
`--ignore-skill-version` darf auch am Ende stehen. Plugin-Befehle sind hier nicht enthalten.

## Globale Optionen

| Argument | Bedeutung |
|---|---|
| `--version` | Zeigt die installierte Version an |
| `--db` | Pfad zur Datenbank (Standard: ./euer.db oder Projekt-Config) |
| `--ignore-skill-version` | Umgeht die Skill-Versionssperre für diesen Aufruf |

### euer init

Initialisiert oder aktualisiert die Datenbank

**Syntax:** `euer init [-h] [--create] [--dry-run] [--json] [--save-db-path]`

**Voraussetzung:** Keine Datenbank für Diagnose/Einrichtung erforderlich; Skill-Bestätigung für `init` und interaktives `setup`. `setup --set skill.version` ist ungeblockt.
**Ausgabe:** Migrations- oder Preflight-Bericht; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--create` | Erlaubt die Neuanlage einer Datenbank an einem explizit angegebenen Pfad |
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

**Beispiel:** `euer setup --set skill.version "1.1.0"`

### euer import

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
                     [--receipt RECEIPT] [--notes NOTES] [--vat VAT]
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
                    --amount AMOUNT [--foreign FOREIGN] [--receipt RECEIPT]
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
| `--foreign` | Fremdwährungsbetrag |
| `--receipt` | Belegname |
| `--notes` | Bemerkung |
| `--vat` | Umsatzsteuer-Betrag (für Regelb.) |
| `--vat-rate` | USt-Satz für Ausgangsumsätze (0, 7, 19) |
| `--tax-free` | Steuerfreie Einnahme ohne Vorsteuerabzug (§19/steuerfrei) |
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
                       [--category CATEGORY] [--format {table,csv}] [--full]
                       [--trash]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern (default: aktuelles) |
| `--month` | Monat filtern (1-12) |
| `--category` | Kategorie filtern |
| `--format` | Positionsargument |
| `--full` | Tabellenansicht mit zusätzlichen Spalten (Konto, Beleg, Fremdwährung, Notiz) |
| `--trash` | Nur gelöschte Ausgaben anzeigen |

**Beispiel:** `euer list expenses --year 2026`

### euer list income

Einnahmen anzeigen

**Syntax:** `euer list income [-h] [--year YEAR] [--month MONTH] [--category CATEGORY]
                     [--format {table,csv}] [--full] [--trash]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern (default: aktuelles) |
| `--month` | Monat filtern (1-12) |
| `--category` | Kategorie filtern |
| `--format` | Positionsargument |
| `--full` | Tabellenansicht mit zusätzlicher Spalte (Notiz) |
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
| `--format` | Positionsargument |

**Beispiel:** `euer list private-deposits --help` zeigt Syntax und Optionen der aktiven Version.

### euer list private-withdrawals

Privatentnahmen anzeigen

**Syntax:** `euer list private-withdrawals [-h] [--year YEAR] [--format {table,csv}]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern |
| `--format` | Positionsargument |

**Beispiel:** `euer list private-withdrawals --help` zeigt Syntax und Optionen der aktiven Version.

### euer list private-transfers

Privateinlagen und Privatentnahmen anzeigen

**Syntax:** `euer list private-transfers [-h] [--year YEAR] [--format {table,csv}]`

**Voraussetzung:** Passende Skill-Bestätigung und, außer bei Einrichtung/Diagnose, eine vorhandene Datenbank.
**Ausgabe:** Formatierte Tabelle oder CSV je nach Option; Fehler auf stderr.

| Argument | Bedeutung |
|---|---|
| `--year` | Jahr filtern |
| `--format` | Positionsargument |

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
                        [--receipt RECEIPT] [--notes NOTES] [--vat VAT]
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
                       [--amount AMOUNT] [--foreign FOREIGN]
                       [--receipt RECEIPT] [--notes NOTES] [--vat VAT]
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
| `--foreign` | Neuer Fremdwährungsbetrag |
| `--receipt` | Neuer Belegname |
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
| `--format` | Positionsargument |
| `--output` | Ausgabeverzeichnis (default: exports.directory aus Config oder /Users/markus/dev/euer-buchhaltung/euer/exports) |
| `--force` | Bestehende Exportdateien überschreiben |

**Beispiel:** `euer export --year 2026`

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
| `--output` | Ausgabeverzeichnis für csv/xlsx (default: exports.directory aus Config oder /Users/markus/dev/euer-buchhaltung/euer/exports) |

**Beispiel:** `euer vat-report --year 2026 --quarter 1`

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

**Syntax:** `euer receipt [-h] {check,open} ...`

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
| `--format` | Positionsargument |

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

## Bedienung, Beispiele und Fehlerfälle

Die folgenden bewährten Arbeitsabläufe und Beispiele stammen aus dem bisherigen
Benutzerhandbuch. Bei Syntaxfragen gilt die obige Befehlsübersicht der aktiven CLI.

## KI-Agenten Konfiguration

Das CLI-Tool ist so konzipiert, dass KI-Agenten die Buchhaltung automatisieren können.
Im Ordner `docs/templates/` findest du Vorlagen für die Agent-Konfiguration.

### Verfügbare Templates

| Datei | Beschreibung |
|-------|--------------|
| `accountant-role.md` | Optionale Startvorlage für spezialisierte Agenten; Grundregeln stehen im Skill |
| `Agents-Template.md` | Template für persönliche Buchhaltungsdaten (kann geführt mit dem Onboarding-Prompt erstellt werden) |
| `onboarding-prompt.md` | Interview-Prompt zur Erstellung einer personalisierten `AGENTS.md` |

### Schnellstart für KI-Agenten

1. **Agent konfigurieren:**
   - Kopiere den vollständigen Ordner `docs/skills/euer-buchhaltung/` einschließlich
     `references/` in den Skill-Pfad deiner KI-Anwendung.
   - Für einen allgemeinen Agenten genügt der Skill; übertrage `accountant-role.md`
     nur bei Bedarf in eine eigene Agenten-Konfiguration.
   - Starte den Agenten in deinem Buchhaltungsordner.

2. **Einrichtung beauftragen:**
   - Sage: „Richte meine Buchhaltung mit euer ein.“
   - Der Skill prüft den Bestand und lädt bei fehlender Einrichtung den
     [Onboarding-Leitfaden](onboarding.md).
   - Der Agent fragt nur fehlende Angaben ab und erstellt oder ergänzt das persönliche
     Mandanten-Dossier sowie die technische Konfiguration. Vorhandene Dateien bleiben erhalten.
   - Alternativ führt `docs/templates/onboarding-prompt.md` aus dem Repository durch ein
     Interview in einem separaten Chat; anschließend lokal speichern und einrichten.

3. **Einrichtung prüfen und starten:**
   - Der Agent prüft Datenbank, Config und Ablage, dann setzt er einen bereits
     erteilten Buchungsauftrag fort. Bei vollständiger Einrichtung entfällt das Interview.
   - Die Config liegt unter macOS/Linux in `~/.config/euer/config.toml`, unter Windows
     in `%APPDATA%\euer\config.toml` und gilt über Arbeitsordner hinweg.
   - Die Prüfung ist eine Agenten-Anweisung im Skill, kein neuer CLI-Befehl.

### Empfohlene Tools für Agenten

- **PDF-Parsing:** `markitdown` – extrahiert Text aus PDFs (Kontoauszüge, Rechnungen)
  - siehe: https://github.com/microsoft/markitdown

## Erste Schritte

### Nach der Installation

Wechsle in deinen **Buchhaltungs-Arbeitsordner**, z.B.:

```bash
# Beispiel: Separater Ordner für Buchhaltungsdaten
mkdir -p ~/Documents/Buchhaltung
cd ~/Documents/Buchhaltung

# Datenbank anlegen (erstellt euer.db, .euer/config.toml und exports/ hier)
euer init --create

# Beleg-/Export-Pfade und Steuermodus konfigurieren (empfohlen)
euer setup

# Konfiguration prüfen
euer config show

# Erste Buchung
euer add expense --payment-date 2026-02-02 --vendor "Test" --category "Laufende EDV-Kosten" --amount -10.00
```

### Wo liegen meine Daten?

- **Datenbank:** Standard `euer.db` im aktuellen Projektordner; der tatsächliche
  Pfad steht in `.euer/config.toml`.
- **Allgemeine Konfiguration:** `~/.config/euer/config.toml` (nutzerweit)
- **Belege:** Pfade in der Konfiguration festgelegt
- **Exports:** `exports/` im aktuellen Verzeichnis oder als konkreter Pfad in der Config
  festgelegt. `exports.directory` unterstützt keinen `{year}`-Platzhalter.

## Grundbegriffe

- **Ausgaben** haben immer **negative** Beträge (`--amount -10.00`).
- **Einnahmen** haben immer **positive** Beträge (`--amount 10.00`).
- **Privateinlagen/Privatentnahmen** (`add private-*`) verwenden immer **positive** Beträge; die Richtung ergibt sich aus dem Command.
- **Kategorien** sind vorgegeben und müssen existieren: `euer list categories`.
- **Buchungskonten** (`--ledger-account`) sind optional und werden in der Config als
  `[[ledger_accounts]]` gepflegt. Sie setzen die Kategorie automatisch.
- **Datumsfelder**: `payment_date` (Wertstellung, EÜR-relevant) und `invoice_date` (Rechnungsdatum).
  Mindestens eines der beiden muss gesetzt sein.
- **Belege** können geprüft und geöffnet werden, wenn Pfade konfiguriert sind.
- **Datenbank**: Standard `euer.db` im **aktuellen Verzeichnis**; `.euer/config.toml`
  kann pro Projekt einen anderen Pfad speichern. `--db PFAD` gilt für einen Aufruf.
- **Arbeitsverzeichnis**: Das Tool liest dort die Projekt-Config und verwendet
  ohne gespeicherten Pfad `./euer.db`. Wechsle vor dem Arbeiten in deinen
  Buchhaltungsordner!

## Typische Befehle

### Ausgaben & Einnahmen erfassen

```bash
# Ausgabe
euer add expense --payment-date 2026-01-15 --invoice-date 2026-01-14 --vendor "1und1" \
    --category "Telekommunikation" --amount -39.99 --account "Sparkasse Giro"

# Ausgabe mit Kontenrahmen
euer add expense --payment-date 2026-01-15 --vendor "Hetzner" \
    --ledger-account hosting --amount -29.00 --account "g-n26"

# Einnahme
euer add income --payment-date 2026-01-20 --invoice-date 2026-01-18 --source "Kunde ABC" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" --amount 1500.00

# Einnahme bei Regelbesteuerung mit explizitem USt-Satz
euer add income --payment-date 2026-01-20 --source "Kunde ABC" \
    --category "Umsatzsteuerpflichtige Betriebseinnahmen" --amount 1190.00 --vat-rate 19

# Einnahme mit Kontenrahmen
euer add income --payment-date 2026-01-20 --source "Kunde ABC" \
    --ledger-account erloese-19 --amount 1500.00
```

### Anzeigen & Filtern

```bash
# Default: aktuelles Jahr
euer list expenses --year 2026
euer list expenses --year 2026 --month 1
euer list expenses --year 2026 --full
euer list income --year 2026
euer list income --year 2026 --full
euer list categories
euer list categories --year 2026
euer list ledger-accounts
euer list ledger-accounts --category "Laufende EDV-Kosten"
```

Hinweis: `list ... --format csv` gibt die Liste als CSV auf stdout aus (für Pipes/Redirects).
Hinweis: `euer list expenses --full` erweitert die Tabellenansicht um fachliche Details wie
`Konto`, `Beleg`, `Fremdw.` und `Notiz`.
Hinweis: `euer list income` zeigt in der Tabellenansicht die Spalte `USt` (vat_output) immer an.
Hinweis: RC-Ausgaben zeigen in der Spalte `RC` den Typ `eu` oder `third-country`.
Hinweis: `euer list income --full` ergänzt die Tabellenansicht um die Spalte `Notiz`.
Hinweis: `list expenses` und `list income` zeigen für das angezeigte Jahr eine
EÜR-Zeile nur dann an, wenn dafür eine geprüfte Formularzuordnung mitgeliefert
wird. Mit `euer list categories --year YYYY` lässt sich die Zuordnung für ein
konkretes Formularjahr anzeigen. Ohne Formularjahr erscheinen keine festen
ELSTER-Zeilennummern.

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

### Korrigieren, Löschen, Papierkorb & Undo

```bash
# Ausgabe korrigieren
euer update expense 42 --amount -25.00 --notes "Korrigiert"
euer update expense 42 --payment-date 2026-01-17
euer update expense 42 --invoice-date 2026-01-15
euer update expense 42 --ledger-account hosting
euer update expense 42 --private-paid
euer update expense 42 --no-private-paid
euer update expense 42 --rc eu
euer update expense 42 --rc third-country
euer update expense 42 --no-rc
euer update income 17 --vat-rate 7
euer update income 17 --tax-free

# Privatvorgang korrigieren
euer update private-transfer 7 --amount 600 --description "Korrektur"
euer update private-transfer 7 --clear-related-expense

# Löschen (Standard: Soft-Delete in den Papierkorb)
euer delete expense 42
euer delete expense 42 --force

# Dauerhaftes physisches Löschen (ohne Papierkorb)
euer delete expense 42 --purge --force

# Papierkorb verwalten
euer trash list
euer trash empty
euer trash empty --force

# Wiederherstellung aus dem Papierkorb
euer restore 42
euer restore 42 --table expenses

# Letzte schreibende Aktion rückgängig machen (Undo)
euer undo
euer undo --force

# Änderungshistorie
euer audit 42 --table expenses
```

#### Papierkorb (Soft-Delete) & Wiederherstellung

Um versehentlichen Datenverlust durch Agenten oder Tippfehler zu verhindern, löscht
`euer delete` Einträge standardmäßig nicht physisch, sondern markiert sie mit einem
Zeitstempel (`deleted_at`).
- **Unsichtbar im Normalbetrieb:** Gelöschte Einträge erscheinen nicht in Listen,
  Berichten (`summary`, `vat-report`), EÜR-Ergebnissen oder Exporten.
- **Wiederherstellbar:** Mit `euer restore <ID>` wird die Buchung sofort wieder
  in den aktiven Bestand übernommen.
- **Papierkorb prüfen & leeren:** `euer trash list` zeigt alle gelöschten Datensätze;
  `euer trash empty` entfernt sie nach Bestätigung (oder mit `--force`) endgültig.
- **Physisches Löschen:** Nur mit dem Flag `--purge` wird ein Eintrag sofort
  dauerhaft gelöscht.

#### Undo-Mechanismus

Mit `euer undo` lässt sich die jeweils letzte schreibende Mutation (INSERT, UPDATE
oder DELETE) atomar zurückrollen:
- **INSERT rückgängig machen:** Der neu angelegte Datensatz wird soft-gelöscht.
- **UPDATE rückgängig machen:** Alle geänderten Spalten werden auf ihren vorherigen
  Zustand aus dem Audit-Log zurückgesetzt.
- **DELETE rückgängig machen:** Die gelöschte Zeile wird wiederhergestellt.
Ohne `--force` zeigt `euer undo` eine genaue Vorschau der rückgängig zu machenden
Änderung und fordert eine interaktive Bestätigung an.

### Zusammenfassung & Export

```bash
euer summary --year 2026
euer summary --year 2026 --include-private
euer private-summary --year 2026
euer reconcile private --year 2026 --dry-run
euer reconcile private --year 2026
euer vat-report --year 2026
euer vat-report --year 2026 --quarter 1
euer vat-report --year 2026 --month 3 --format csv --output exports/

# Default: CSV, ohne --year = alle Jahre
euer export
euer export --year 2026
# XLSX benötigt openpyxl:
euer export --year 2026 --format xlsx
# Überschreiben vorhandener Exportdateien erzwingen:
euer export --year 2026 --force
```

Hinweis: `export` schreibt Dateien ins Export-Verzeichnis:
- Ausgaben
- Einnahmen
- `PrivateTransfers` (direkte Privatvorgänge)
- `Sacheinlagen` (aus `expenses.is_private_paid` abgeleitet)

#### Export-Schutz vor Überschreiben

- **Kollisionsprüfung:** Wenn im Zielordner bereits Exportdateien existieren, bricht
  `euer export` mit einem Fehler ab und nennt die betroffenen Dateipfade. Um bestehende
  Exporte bewusst zu überschreiben, muss `--force` übergeben werden.
- **Staging und Rückabwicklung:** Jede Exportdatei wird zunächst als temporäre Datei
  im Zielverzeichnis geschrieben. Wenn beim anschließenden Austausch einer Datei ein
  Fehler auftritt, werden bereits ersetzte Dateien nach Möglichkeit zurückgesetzt.
  Ein Dateisatz lässt sich auf Dateisystemebene nicht als Ganzes atomar austauschen.
- Gelöschte Buchungen (`deleted_at`) werden vom Export vollständig ausgeschlossen.

Auch ein Export schützt nur lokale Dateistände: `euer` beansprucht keine
GoBD-Konformität und bietet damit keine rechtlich revisionssichere Archivierung.
Ein versionierter Exportmodus mit Manifest ist als separates Feature geplant.

`exports.directory` ist ein konkreter Ordner und unterstützt keinen
`{year}`-Platzhalter. Für jahresweise Ablage nutze entweder `--output` mit einem
konkreten Jahresordner oder setze die Config entsprechend um:

```bash
euer export --year 2026 --output "/pfad/zu/Buchhaltung/2026/Exporte"
```

### Plausibilitätsprüfungen & Validierungs-Guardrails

Um Fehleingaben und Missverständnisse durch automatisierte Agenten zu verhindern,
verfügt `euer` über integrierte Plausibilitätsprüfungen:

1. **Umsatzsteuer-Konsistenz (Gross-VAT):**
   Wird bei einer Ausgabe oder Einnahme sowohl ein Steuersatz (`--vat-rate 19` oder `7`)
   als auch ein absoluter Steuerbetrag (`--vat`) übergeben, prüft `euer`, ob der
   Steuerbetrag rechnerisch zum Bruttobetrag passt:
   $$\text{USt} = \text{Brutto} - \frac{\text{Brutto}}{1 + \text{Satz}}$$
   Weicht der angegebene Betrag um mehr als 0,02 € (Rundungstoleranz) ab, wird die
   Buchung mit einem Fehler abgelehnt.
2. **Datumsplausibilität:**
   - **Keine Zukunftszahlungen:** Ein Wertstellungs-/Zahlungsdatum (`--payment-date`)
     in der Zukunft wird abgelehnt, da in der EÜR das Zufluss-/Abflussprinzip gilt
     (Geld kann erst nach tatsächlichem Fluss gebucht werden).
   - **Zukunftsrechnungen:** Ein Rechnungsdatum (`--invoice-date`) in der Zukunft ist
     nur zulässig, wenn die Rechnung noch unbezahlt ist (kein `payment_date`).
   - **Historien-Warnung:** Liegt ein Datum mehr als 2 Jahre in der Vergangenheit,
     weist `euer` mit einer Warnung darauf hin.
3. **Betragsschwelle (Großbeträge > 5.000 €):**
   Buchungen mit einem Betrag von über 5.000,00 € (absolut) werden abgewiesen,
   um Tippfehler (z. B. versehentlich weggelassenes Komma `500000`) zu verhindern.
   Soll die Buchung tatsächlich getätigt werden, muss `--force` angegeben werden.
   Der Schwellenwert kann in der Config unter `[safety].amount_threshold` angepasst werden.
   Der Wert muss endlich und größer als null sein. Bei einem ungültigen Wert bricht
   die Buchung mit einem Config-Fehler ab; `euer` verwendet dann keinen stillen Ersatzwert.
4. **Unscharfe Duplikaterkennung (Fuzzy Match):**
   Wird eine Ausgabe oder Einnahme erfasst, für die bereits eine Buchung mit exakt
   demselben Betrag im Zeitfenster von $\pm 2$ Tagen und ähnlichem Namen (Empfänger/Kunde)
   existiert, wird die Buchung als verdächtiges Duplikat abgelehnt.
   - Handelt es sich um eine berechtigte Mehrfachbuchung (z. B. zwei gleich hohe
     Lizenzgebühren), kann die Buchung mit `--allow-duplicate` (oder `--force`)
     erzwungen werden.

Hinweis: Jahres-Exporte für Ausgaben und Einnahmen enthalten zusätzlich die
Spalten `Buchungskonto`, `Kontonummer`, `Steuersatz` und `Steuerklasse`.
Ausgabenexporte ergänzen bei Bewirtung Vorsteuerstatus, Trinkgeld, Kostenbasis
und die berechnete Aufteilung. Ohne `--year` werden keine ELSTER-Zeilen behauptet.

### Bewirtungsaufwendungen buchen

Eine geschäftliche Bewirtung wird als ein Zahlungsvorgang mit dem vollständigen,
negativen Zahlbetrag erfasst. `--vat` ist die am Beleg ausgewiesene und tatsächlich
abziehbare Vorsteuer; `--tip` erfasst freiwilliges Trinkgeld, das bereits im
Zahlbetrag enthalten ist. Das folgende Beispiel gilt für die Regelbesteuerung
und einen Beleg, der 19,00 € abziehbare Vorsteuer ausweist.

```bash
euer add expense --payment-date 2026-03-19 --vendor "Restaurant Beispiel" \
    --category "Bewirtungsaufwendungen" --amount -129.00 --vat 19.00 --tip 10.00 \
    --account "Geschäftskonto" --receipt "rechnung.pdf"
```

Beispielausgabe:

```text
Ausgabe #1 hinzugefügt: Restaurant Beispiel -129,00 EUR (Vorst: 19.00, USt: 0.00, Saldo: -19.00)
  Bewirtung: Zahlbetrag 129.00 EUR, Vorsteuer 19.00 EUR, Kostenbasis 110.00 EUR, abziehbar 77.00 EUR, nicht abziehbar 33.00 EUR
```

Der Service berechnet `Kostenbasis = Zahlbetrag − Vorsteuer`, danach 70 %
abziehbar und 30 % nicht abziehbar. Die belegte Vorsteuer bleibt vollständig
separat erfasst; sie wird nicht aus einem Steuersatz geschätzt. Für eine geprüfte
Null-Vorsteuer im Standardmodus `--vat 0` angeben. Ohne `--vat` bleibt die
Behandlung `needs_review`, bis der Beleg geprüft und per `update expense` ergänzt
wurde. Im Kleinunternehmermodus wird `no_deduction` gespeichert; positive
Vorsteuerangaben werden bei neuen Buchungen abgewiesen. Importzeilen mit einem
expliziten Bewirtungsstatus erhalten den gespeicherten historischen Status auch
bei geändertem Steuermodus.

`summary` zeigt abziehbaren Bewirtungsaufwand und Vorsteuer getrennt. Bei
ungeprüften Altbuchungen zeigt es IDs und bekannte vorläufige Teilbeträge; die
70/30-Aufteilung, der Gewinn und die EÜR-Werte werden als unvollständig markiert.
Der nicht abziehbare Anteil wird nicht automatisch als Privatentnahme gebucht.
Bewirtung ausschließlich eigener Arbeitnehmer gehört nicht in diese Kategorie.

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
- Optionale Felder: `category`, `account`, `ledger_account`, `foreign_amount`, `receipt_name`, `notes`, `rc`, `private_paid`, `vat_input`, `vat_output`, `vat_rate`, `vat_code`, `tax_free`, `entertainment_tip_eur`, `entertainment_vat_status`
- Fehlende Pflichtfelder führen zu einem Import-Abbruch.
- `type` kann fehlen, wenn `amount_eur` ein Vorzeichen hat (negativ = Ausgabe, positiv = Einnahme).
- CSV‑Exports für **Ausgaben/Einnahmen** können direkt re‑importiert werden (Spaltennamen sind gemappt).
- Historische Kategorienlabels mit einer Endung wie `(63)` oder `(Zeile 64)` werden anhand des Kategorienamens aufgelöst.
- Exporte `PrivateTransfers` und `Sacheinlagen` sind nicht als Standard-Importquelle vorgesehen.
- Kategorien mit `"(NN)"` werden beim Import automatisch bereinigt.
- Alias‑Keys werden akzeptiert (z.B. `EUR`, `Belegname`, `Lieferant`, `Quelle`, `RC`).
- `private_paid=true|1|yes|X` markiert eine importierte Ausgabe manuell als Sacheinlage.
- `rc` akzeptiert `eu` oder `third-country`; Legacy-Werte `rc=true|X` brauchen zusätzlich eine Jurisdiktionsspalte.
- `vat_rate` akzeptiert `19`, `7`, `0` sowie Werte mit `%`.
- `vat_code` akzeptiert persistierte Steuerklassen wie `output_standard_19`,
  `output_reduced_7`, `output_zero_0`, `output_tax_free_no_vorsteuer`,
  `input_invoice`, `reverse_charge_eu`, `reverse_charge_third_country`.
- Bewirtungsimporte können `entertainment_tip_eur`/`tip`/`Trinkgeld` und
  `entertainment_vat_status`/`Bewirtung Vorsteuerstatus` enthalten. Vorsteuer ist
  ein belegter Betrag, kein aus dem Zahlbetrag geschätzter Steuersatz. Ein
  expliziter Status erhält bei einem Round-Trip die Behandlung der Einzelbuchung,
  auch wenn sich der globale Steuermodus geändert hat.
- `Nicht steuerbare Umsätze` ist fachlich das Unterfeld „Davon nicht steuerbare
  Kleinunternehmerumsätze (§ 19 Abs. 2 UStG)“. Es wird nur einmal als Einnahme
  gezählt; `summary` zeigt Zeile 13 zusätzlich als „davon“-Betrag innerhalb der
  Kleinunternehmer-Einnahmen.

## Kontenrahmen

Der optionale Kontenrahmen lebt in `~/.config/euer/config.toml` und ordnet
frei benannte Buchungskonten einer bestehenden EÜR-Kategorie zu:

```toml
[[ledger_accounts]]
key = "hosting"
name = "Hosting & Cloud-Dienste"
category = "Laufende EDV-Kosten"
account_number = "4940"

[[ledger_accounts]]
key = "erloese-19"
name = "Erlöse 19% USt"
category = "Umsatzsteuerpflichtige Betriebseinnahmen"
account_number = "8400"
```

Wichtig:
- `--account` bleibt das Zahlungskonto (Bank-/Kreditkartenkonto).
- `--ledger-account` ist das Buchungskonto aus dem Kontenrahmen.
- `euer setup` kann Buchungskonten interaktiv anlegen.
- `euer list ledger-accounts` zeigt den aktuell konfigurierten Kontenrahmen.
- Steuerfelder:
  - `small_business` + `rc=eu|third-country`: `vat_output` wird automatisch aus `amount_eur * 0.19` berechnet,
    `vat_input` wird auf `0.0` gesetzt (Felder können weggelassen werden).
  - `small_business` + Einnahmen: neue Einnahmen werden als
    `output_tax_free_no_vorsteuer` klassifiziert.
  - `standard` + Ausgaben: `--vat` bzw. `vat_input` ist der belegte Vorsteuerbetrag;
    RC bucht `vat_input` und `vat_output` automatisch.
  - `standard` + Einnahmen: ohne explizite Angabe gilt `vat_rate=19`. Nutze
    `--vat-rate 7`, `--vat-rate 0` oder `--tax-free` für abweichende Fälle.
    `amount_eur` wird immer 1:1 als Brutto-Zahlfluss gespeichert.

Workflow für unvollständige Einträge:
1. Import/Add ausführen → Buchungen werden angelegt (Pflichtfelder müssen vorhanden sein).
2. `euer incomplete list` zeigt fehlende **Qualitätsfelder**:
   `payment_date`, `invoice_date`, `category`, `receipt`, `vat`,
   `entertainment_vat_status`, `account` (abhängig von Typ/Steuermodus).
3. Fehlende Infos per `euer update expense|income <ID>` nachpflegen.
Hinweis: Für die Kategorie **Gezahlte USt** ist kein Beleg erforderlich. Ihre
Formularzeile hängt vom Berichtsjahr ab und ist keine Vorsteuerzeile.

## Beleg‑Verwaltung

### Konfiguration

`euer setup` legt Pfade und den Audit‑User in `~/.config/euer/config.toml` an.
Belege werden unter einem gemeinsamen Root jahrzentriert erwartet:
`<root>/<Jahr>/<Typ>/<Belegname>`.
Mit `euer setup --set section.key value` kannst du einzelne Werte ohne Prompt setzen.

```toml
[receipts]
root = "/pfad/zu/Buchhaltung"
year_dir = "{year}"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"

[exports]
directory = "/pfad/zu/exports"

[user]
name = "Dein Name"

[accounts]
private = ["privat", "private Kreditkarte"]
```

Beispiele:

```text
/pfad/zu/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.pdf
/pfad/zu/Buchhaltung/2026/Einnahmen/2026-01-20_Rechnung_001.pdf
```

`year_dir` muss `{year}` enthalten. Damit sind auch Ordner wie
`Buchhaltung 2026` möglich:

```bash
euer setup --set receipts.root "/pfad/zu/Buchhaltung"
euer setup --set receipts.year_dir "Buchhaltung {year}"
euer setup --set receipts.expenses_dir "Ausgaben"
euer setup --set receipts.income_dir "Einnahmen"
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

### Einnahmen klassifizieren

Für den UStVA-Report speichert `euer` an Einnahmen `vat_rate` und `vat_code`.

```bash
euer add income ... --vat-rate 19
euer add income ... --vat-rate 7
euer add income ... --vat-rate 0
euer add income ... --tax-free
```

`--tax-free` ist exklusiv zu `--vat-rate` und `--vat`. Im Modus `standard`
setzt `euer` ohne Angabe automatisch `19 %`. Der Betrag bleibt der tatsächliche
Zahlfluss; `vat_output` wird aus dem Bruttobetrag herausgerechnet, sofern kein
manueller Steuerbetrag per `--vat` gesetzt ist.

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

Verwende `--rc eu` oder `--rc third-country` für ausländische Anbieter ohne deutsche USt.
Der RC-Typ ist Pflicht, damit spätere UStVA-Auswertungen EU-Leistungen und
Drittland-Leistungen trennen können:

```bash
euer add expense --date 2026-01-04 --vendor "RENDER.COM" \
    --category "Laufende EDV-Kosten" --amount -22.71 --rc third-country
```

Hinweis: Bei `small_business` setzt RC automatisch `vat_output`, `vat_input` bleibt `0.0`.
Bestehende RC-Buchungen ohne EU-/Drittland-Typ können nachgepflegt werden:

```bash
euer update expense 42 --rc eu
euer update expense 42 --rc third-country
```

## USt-Voranmeldung (`vat-report`)

`vat-report` ist ein separater, formularnaher Arbeitsbericht für die manuelle
Übertragung in ELSTER. Er nutzt ausschließlich `payment_date`; Buchungen ohne
Wertstellungsdatum werden nicht eingerechnet und erscheinen als Warnung.

```bash
euer vat-report --year 2026
euer vat-report --year 2026 --quarter 1
euer vat-report --year 2026 --month 3
euer vat-report --year 2026 --quarter 1 --format csv --output exports/
euer vat-report --year 2026 --month 3 --format xlsx --output exports/
```

Der Report enthält u.a. KZ 81/86/87/48 für Ausgangsumsätze, KZ 46/47 und
84/85 für Reverse Charge, KZ 66/67 für Vorsteuer sowie KZ 83 als Zahllast oder
Erstattung. CSV erzeugt zusätzlich eine Diagnose-Datei mit ausgeschlossenen und
gewarnten Buchungen; XLSX enthält ein zweites Sheet `Diagnose`.

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

## Hilfe & FAQ

- ❓ **[Häufig gestellte Fragen (FAQ)](domain_rules.md)** – Sonderfälle wie Prepaid-Guthaben (Google AI Studio, OpenAI), Nullbetragsrechnungen und Jahreswechsel.
- Parameter-Hilfe im Terminal:

```bash
euer --help
euer add expense --help
euer receipt --help
```

### Grenzen bei Bewirtungs-Sonderfällen

Bewirtungen mit Reverse Charge sowie positive Erstattungsbuchungen werden aktuell
nicht neu unterstützt. Vorhandene Sonderfälle erhalten keine automatische
70/30-Aufteilung; die EÜR bleibt als unvollständig gekennzeichnet. Diese Belege
separat prüfen und keine negativen Ausgaben erfinden, um eine Erstattung zu buchen.
Nach einem Upgrade betroffene Berichte und XLSX-Exporte erneut erzeugen.
