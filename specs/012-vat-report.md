# Spec 012: `vat-report` – USt-Voranmeldungs-Report

## Status

Implementiert

## Ziel

`euer vat-report` soll einen **möglichst vollständigen, ELSTER-nahen
USt-Voranmeldungs-Report** für typische Solo-Selbständige, Freelancer,
Softwareentwickler und Berater erzeugen.

Der Report ist kein internes Steuer-Summary, sondern ein fachlicher
Arbeitsbericht für die manuelle Übertragung in ELSTER.

## Motivation

Die bestehende `summary`-Ausgabe ist für eine EÜR-Zusammenfassung geeignet,
aber nicht formularnah genug für die USt-Voranmeldung. Für eine professionelle
Nutzung braucht `euer` einen eigenen Report mit:

- klaren ELSTER-Kennzahlen
- periodengenauer Selektion
- Warnungen bei unvollständigen oder fachlich nicht zuordenbaren Buchungen
- strukturiertem Export für Weiterverarbeitung

## Produktentscheidung

Diese Spec optimiert **nicht** auf minimale Implementierungskosten.
Wenn für einen belastbaren UStVA-Report zusätzliche Datenfelder oder
fachliche Klassifikationen nötig sind, werden diese eingeführt.

## Fachliche Grundlagen

### Quellenbasis

Die Umsetzung orientiert sich an den jeweils aktuellen offiziellen
ELSTER-/BMF-Vorgaben für die Umsatzsteuer-Voranmeldung.

Für 2026 sind insbesondere relevant:

- BMF Vordruckmuster UStVA 2026, veröffentlicht am **29. Dezember 2025**
- ELSTER Hilfe „UStVA 2026“

Referenzen:

- https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Umsatzsteuer/2025-12-29-vordruckmuster-USt-voranmeldung-2026.html
- https://www.elster.de/eportal/helpGlobal?themaGlobal=help_ustva_2026

Die Kennzahlen in dieser Spec beziehen sich auf das Formularjahr 2026. Bei
späteren Formularjahren muss das Mapping bewusst geprüft und angepasst werden.

### Zielgruppe / Praxisfokus

Im Fokus stehen typische Fälle von:

- Softwareentwicklern
- Beratern
- Designern
- Agenturen
- vergleichbaren Freelancern

Das bedeutet:

- reguläre inländische Umsätze
- reguläre Eingangsrechnungen mit Vorsteuer
- Reverse Charge bei SaaS-, Cloud- und Dienstleistungsbezug
- Kleinunternehmer-Fälle nach § 19 UStG

Komplexe Sonderfälle außerhalb dieses Kernbereichs sind nachrangig.

## Geltungsbereich

Der Report soll folgende Bereiche abdecken:

- **Kleinunternehmer**
  - eigene Umsätze ohne Ausgangs-USt
  - RC-Umsätze mit Aufteilung EU / Drittland
- **Regelbesteuerung**
  - steuerpflichtige Umsätze mit 19 %
  - steuerpflichtige Umsätze mit 7 %
  - RC-Umsätze EU / Drittland
  - abziehbare Vorsteuer

Zusätzlich:

- Warnungen für fehlende oder unvollständige Daten
- Export als CSV und optional XLSX

Nicht-Ziel:

- keine elektronische ELSTER-Übermittlung
- keine steuerliche Beratung
- keine automatische Entscheidung, ob ein Vorgang steuerlich korrekt klassifiziert
  wurde

## Abhängigkeiten

- Spec 004: Steuerlogik (KU/Standard)
- Spec 011: RC-Jurisdiktion

Ohne Spec 011 kann die Aufteilung KZ 46/47 vs. KZ 84/85 nicht korrekt erfolgen.

Spec 011 muss vor dieser Spec implementiert sein.

## Zentrale Designentscheidungen

### D1: Eigenständiger Command

Neuer CLI-Befehl:

```bash
euer vat-report --year 2026
euer vat-report --year 2026 --quarter 1
euer vat-report --year 2026 --month 3
```

### D2: `--year` ist Pflicht

Regeln:

- `--year` ist immer erforderlich
- optional zusätzlich **genau eines** von:
  - `--quarter 1|2|3|4`
  - `--month 1..12`
- ohne `--quarter` und ohne `--month` wird ein Jahresbericht erzeugt

`--quarter` und `--month` sind gegenseitig exklusiv.

### D3: Periodenbasis ist `payment_date`

Für die Zuordnung in einen Voranmeldungszeitraum gilt ausschließlich:

- `payment_date`

Buchungen ohne `payment_date` werden:

- nicht in die Kennzahlen eingerechnet
- als Warnung ausgegeben

Das gilt für Ausgaben und Einnahmen gleichermaßen.

Begründung:

`euer` ist EÜR- und CLI-first. Die erste Version von `vat-report` folgt deshalb
einer zahlungsorientierten Periodik. Abweichende Besteuerungsarten oder
leistungszeitraumbezogene Speziallogik werden nicht stillschweigend simuliert.

### D4: ELSTER-nahe Darstellung

Der Terminal-Report soll Bemessungsgrundlagen und Steuerbeträge formularnah
ausgeben:

- Bemessungsgrundlagen in vollen Euro
- Steuerbeträge mit Cent-Betrag, soweit das Formular eine Steuer-Spalte vorsieht

Zusätzlich kann eine Diagnose-/Detailsektion centgenaue Ursprungswerte zeigen,
damit Rundungen nachvollziehbar bleiben.

### D5: Keine stillschweigende Falschsicherheit

Wenn eine Kennzahl im Formular grundsätzlich existiert, aber aus den Daten nicht
fachlich sicher ableitbar ist, darf der Report **nicht** einfach `0` ausgeben.

Stattdessen:

- Kennzahl als `nicht unterstützt` oder `unvollständig`
- plus Warnung

Nur fachlich sicher als leer/0 ableitbare Kennzahlen dürfen als `0` erscheinen.

### D6: Keine neue Parallelsteuerlogik im Command

Der Command ist ein View-Controller. Aggregation und Klassifikation gehören in
einen Service, z.B. `euercli/services/vat_report.py`.

Der Command darf:

- Argumente parsen
- Service-Fehler in deutsche CLI-Ausgaben übersetzen
- Terminal/CSV/XLSX rendern

Der Command darf nicht:

- direkt in `expenses` oder `income` schreiben
- steuerliche Klassifikation ad hoc aus SQL-Zeilen zusammenbauen
- Business-Regeln duplizieren, die bereits im Service liegen

## Erforderliche Datenmodell-Erweiterungen

Der heutige Datenbestand reicht für einen möglichst vollständigen UStVA-Report
nicht aus. Insbesondere fehlt eine explizite fachliche Umsatzsteuer-Klassifikation.

### A1: Neue Felder für steuerliche Klassifikation

Es werden neue Felder für `expenses` und `income` benötigt:

- `vat_rate REAL | NULL`
- `vat_code TEXT | NULL`

Ziel der Felder:

- Steuersatz explizit speichern (`19`, `7`, `0`; optional später weitere Werte)
- steuerliche Behandlung explizit speichern
- spätere Reports von der aktuellen Config entkoppeln

Neue Datenbanken sollen `vat_rate` per `CHECK` auf unterstützte Werte begrenzen:

```sql
CHECK(vat_rate IS NULL OR vat_rate IN (0, 7, 19))
```

Für bestehende Datenbanken reicht die Service-Layer-Validierung. `euer init`
ergänzt die Spalten, erzwingt aber keine vollständige Tabellenmigration.

### A2: Persistierte Steuerlogik statt bloßer Herleitung aus Config

Die für UStVA relevante steuerliche Einordnung muss an der Buchung hängen,
nicht nur implizit aus aktuellem Modus oder Kategorie abgeleitet werden.

Begründung:

- Historie bleibt stabil
- Reports bleiben auditierbar
- spätere Config-Änderungen verfälschen keine alten Voranmeldungen

### A3: Persistierte `vat_code`-Werte

Die erste Version unterstützt folgende persistierte Codes:

- `output_standard_19`
- `output_reduced_7`
- `output_zero_0`
- `output_tax_free_no_vorsteuer`
- `input_invoice`
- `reverse_charge_eu`
- `reverse_charge_third_country`

Zuordnung:

| Tabelle | Code | Bedeutung |
|---|---|---|
| `income` | `output_standard_19` | steuerpflichtiger Ausgangsumsatz 19 % |
| `income` | `output_reduced_7` | steuerpflichtiger Ausgangsumsatz 7 % |
| `income` | `output_zero_0` | steuerpflichtiger Ausgangsumsatz 0 % |
| `income` | `output_tax_free_no_vorsteuer` | steuerfreier Umsatz ohne Vorsteuerabzug, inkl. § 19 UStG |
| `expenses` | `input_invoice` | abziehbare Vorsteuer aus Rechnungen anderer Unternehmer |
| `expenses` | `reverse_charge_eu` | RC-Leistung EU nach Spec 011 |
| `expenses` | `reverse_charge_third_country` | RC-Leistung Drittland nach Spec 011 |

Die CLI soll diese technischen Codes nicht als primäre Nutzerschnittstelle
erzwingen. Sie dürfen für Import/Export und Tests sichtbar sein, aber normale
Erfassung soll über verständliche Flags erfolgen.

### A4: Default-Steuersatz

Wenn bei `add income` im Modus `standard` kein expliziter Steuersatz angegeben
ist und keine steuerfreie Behandlung gesetzt wurde, gilt als Default:

- `19 %`

Diese Default-Regel gilt nur dort, wo der Vorgang fachlich bereits als
steuerpflichtiger Standardumsatz feststeht.

Sie darf **nicht** verwendet werden, um unklare Fälle blind zu raten.

### A5: Nutzerfreundliche CLI-Flags

Die CLI bleibt konsistent mit bestehenden Commands:

- `--vat` bleibt der manuelle Steuerbetrag in EUR.
- `--rc eu|third-country` aus Spec 011 bleibt die Nutzerschnittstelle für
  Reverse-Charge-Ausgaben.
- Neue interne Codes werden nicht als Pflichtwissen für Nutzer vorausgesetzt.

Für Einnahmen werden ergänzt:

```bash
euer add income ... --vat-rate 19
euer add income ... --vat-rate 7
euer add income ... --vat-rate 0
euer add income ... --tax-free
euer update income 42 --vat-rate 7
euer update income 42 --tax-free
```

Regeln:

- `--vat-rate` erlaubt `19`, `7`, `0`.
- `--tax-free` ist gegenseitig exklusiv mit `--vat-rate` und `--vat`.
- Im Modus `small_business` setzt der Service neue Einnahmen standardmäßig auf
  `output_tax_free_no_vorsteuer`; `--vat` ist dort wie bisher nicht sinnvoll.
- Im Modus `standard` setzt `--vat-rate 19` den Code `output_standard_19`.
- Im Modus `standard` setzt `--vat-rate 7` den Code `output_reduced_7`.
- Im Modus `standard` setzt `--vat-rate 0` den Code `output_zero_0`.
- `--tax-free` setzt `output_tax_free_no_vorsteuer`.

Für Ausgaben werden keine zusätzlichen Alltagsflags eingeführt:

- Normale Vorsteuer wird wie bisher über `--vat` erfasst und als
  `input_invoice` klassifiziert.
- RC wird über `--rc eu|third-country` erfasst und daraus als
  `reverse_charge_eu` oder `reverse_charge_third_country` klassifiziert.
- `--vat-rate` ist für Ausgaben im MVP nicht erforderlich.

## Kennzahlen-Mapping (MVP mit professionellem Scope)

Die erste Version des Reports soll für die Kernzielgruppe mindestens folgende
Kennzahlen belastbar liefern oder als unvollständig markieren.

### B1: Kleinunternehmer

Für Kleinunternehmer relevant:

- eigene Umsätze ohne Ausgangs-USt:
  - KZ 48 Bemessungsgrundlage, wenn eine UStVA-Ausgabe benötigt wird
  - zusätzlich als klar beschrifteter Kontextblock
- RC EU:
  - KZ 46 Bemessungsgrundlage
  - KZ 47 Steuer
- RC Drittland:
  - KZ 84 Bemessungsgrundlage
  - KZ 85 Steuer

Hinweis:

Kleinunternehmer führen für eigene Umsätze keine Ausgangs-USt ab und ziehen keine
Vorsteuer. RC-Steuerbeträge bleiben als Zahllast relevant; ein Vorsteuerabzug aus
RC (`KZ 67`) wird im Modus `small_business` nicht angesetzt.

### B2: Regelbesteuerung

Für Regelbesteuerte im Kernbereich:

- steuerpflichtige Umsätze 19 %:
  - KZ 81 Bemessungsgrundlage
  - Steuerbetrag daraus im Report berechnet bzw. mit `vat_output` abgeglichen
- steuerpflichtige Umsätze 7 %:
  - KZ 86 Bemessungsgrundlage
  - Steuerbetrag daraus im Report berechnet bzw. mit `vat_output` abgeglichen
- steuerpflichtige Umsätze 0 %:
  - KZ 87 Bemessungsgrundlage
- steuerfreie Umsätze ohne Vorsteuerabzug:
  - KZ 48 Bemessungsgrundlage
- RC EU:
  - KZ 46 Bemessungsgrundlage
  - KZ 47 Steuer
- RC Drittland:
  - KZ 84 Bemessungsgrundlage
  - KZ 85 Steuer
- abziehbare Vorsteuer aus Rechnungen:
  - KZ 66
- abziehbare Vorsteuer aus Reverse-Charge-Leistungen:
  - KZ 67
- verbleibende Umsatzsteuer-Vorauszahlung / Überschuss:
  - KZ 83 als berechneter Ergebniswert

### B3: Kennzahlen, die nur mit zusätzlicher Modellierung unterstützt werden

Wenn für eine Kennzahl zusätzliche Modellierung nötig ist, wird diese Modellierung
Teil dieser Spec und nicht auf unbestimmte Zeit verschoben.

Beispiele:

- 7 %-Umsätze erfordern expliziten `vat_rate`
- bestimmte Sonderfälle erfordern expliziten `vat_code`

### B4: Nicht unterstützte Kennzahlen im MVP

Folgende Kennzahlen werden in der ersten Version nicht berechnet und müssen im
Report als `nicht unterstützt` oder `nicht erfasst` erscheinen, wenn sie für den
Nutzer relevant sein könnten:

- innergemeinschaftliche Erwerbe, z.B. KZ 89/93/90
- Einfuhrumsatzsteuer, KZ 62
- Sondervorauszahlung / Dauerfristverlängerung, KZ 39
- Vorsteuerberichtigung, KZ 64
- andere Steuersätze, KZ 35/36
- Sonderfälle nach § 13b außerhalb EU/Drittland-Dienstleistungen für die
  Zielgruppe

Diese Liste ist nicht abschließend. Unbekannte oder nicht modellierte Fälle
dürfen nicht als `0` ausgegeben werden, wenn dadurch fachliche Vollständigkeit
vorgetäuscht würde.

## Report-Ausgabe

### C1: Terminal-Ausgabe

Beispielhafte Struktur:

```text
USt-Voranmeldung Q1/2026
==================================================

Zeitraum:
  2026-01-01 bis 2026-03-31

Steuermodus:
  standard

Ausgangsumsätze:
  KZ 81  Steuerpflichtige Umsätze 19%:         5.000 EUR
         Steuer:                              950,00 EUR
  KZ 86  Steuerpflichtige Umsätze 7%:              0 EUR
         Steuer:                                0,00 EUR
  KZ 87  Steuerpflichtige Umsätze 0%:              0 EUR
  KZ 48  Steuerfreie Umsätze ohne Vorsteuer:       0 EUR

Reverse Charge:
  KZ 46  EU-Bemessungsgrundlage:                  96 EUR
  KZ 47  EU-Steuer:                            18,24 EUR
  KZ 84  Drittland-Bemessungsgrundlage:          111 EUR
  KZ 85  Drittland-Steuer:                     21,09 EUR

Vorsteuer:
  KZ 66  Vorsteuer aus Rechnungen:            120,00 EUR
  KZ 67  Vorsteuer aus RC-Leistungen:          39,33 EUR

--------------------------------------------------
KZ 83  ZAHLLAST / ERSTATTUNG:                 811,76 EUR

Warnungen:
  - 2 RC-Buchungen ohne Jurisdiktion nicht eingerechnet: IDs 14, 27
  - 1 Einnahme ohne payment_date nicht eingerechnet: ID 31
```

Die Beschriftungen dürfen nutzerfreundlich sein, müssen aber eindeutig auf die
offiziellen Kennzahlen gemappt werden.

### C2: Warnsektion mit IDs

Der Report enthält eine Diagnose-/Warnsektion mit Buchungs-IDs.

Mindestens zu melden:

- RC-Buchungen ohne `rc_jurisdiction`
- Buchungen ohne `payment_date`
- Buchungen mit fehlender oder unklarer steuerlicher Klassifikation
- Buchungen, die wegen nicht unterstützter Fälle nicht eingerechnet wurden

### C3: `not supported` / `unvollständig`

Wenn für einen Formularbereich keine belastbare Ableitung möglich ist, zeigt der
Report dies explizit an.

Beispiel:

```text
KZ xx  Nicht unterstützt (fehlende steuerliche Klassifikation in 3 Buchungen)
```

## Export

### D1: CSV/XLSX als Kennzahlen-Export

`--format csv` und `--format xlsx` sollen **keine bloße Kopie der Terminalansicht**
sein, sondern einen strukturierten Kennzahlen-Export liefern.

CLI:

```bash
euer vat-report --year 2026 --format table
euer vat-report --year 2026 --quarter 1 --format csv --output exports/
euer vat-report --year 2026 --month 3 --format xlsx --output exports/
```

Regeln:

- `--format` erlaubt `table`, `csv`, `xlsx`; Default ist `table`.
- `table` schreibt auf stdout.
- `csv` und `xlsx` schreiben Dateien in `--output` oder das konfigurierte
  Export-Verzeichnis.
- Wenn `openpyxl` fehlt, schlägt `xlsx` mit einer klaren deutschen Fehlermeldung
  fehl.

Beispielhafte Spalten:

- `period_label`
- `period_start`
- `period_end`
- `tax_mode`
- `section`
- `line_label`
- `kennzahl`
- `description`
- `basis_eur_raw`
- `basis_eur_rounded`
- `tax_eur_raw`
- `tax_eur_rounded`
- `status`
- `notes`

### D2: Optionales Diagnosesheet / Diagnose-CSV

Zusätzlich soll ein Diagnose-Export möglich sein oder standardmäßig mit erzeugt
werden, z.B.:

- `status = included|warning|excluded|unsupported`
- `booking_type = expense|income`
- `booking_id`
- `reason`
- `reason_code`
- `amount_eur`
- `vat_input`
- `vat_output`
- `vat_rate`
- `vat_code`

Für `xlsx` soll ein zweites Sheet `Diagnose` erzeugt werden. Für `csv` soll
entweder eine zweite Datei mit Suffix `_diagnose.csv` entstehen oder der
Diagnoseexport über ein explizites Flag aktivierbar sein. Die konkrete Variante
muss in der Implementierung konsistent dokumentiert werden.

## Erforderliche Implementierungsänderungen außerhalb des Reports

Damit der Report fachlich funktioniert, müssen vorgelagerte Features erweitert
werden.

### E1: Add/Update/Import müssen neue Steuerfelder unterstützen

Betroffen:

- `add expense`
- `update expense`
- `add income`
- `update income`
- `import`

Diese Commands müssen die in A5 beschriebenen nutzerfreundlichen Flags
entgegennehmen, validieren und über den Service Layer persistieren.

Interne `vat_code`-Werte dürfen im normalen CLI nicht als Pflichtparameter
auftauchen. Für Import/Export sind sie erlaubt, damit Daten round-trip-fähig
bleiben.

### E2: Service Layer

Die Services für `expenses` und `income` müssen:

- neue Felder validieren
- sinnvolle Defaults setzen
- widersprüchliche Kombinationen ablehnen
- typisierte Rückgaben liefern
- `vat_code` aus den nutzerfreundlichen CLI-/Import-Werten ableiten
- RC-Codes konsistent aus `is_rc` und `rc_jurisdiction` aus Spec 011 ableiten
- alte Buchungen ohne `vat_code` lesbar lassen und im Report als
  `unvollständig` markieren, wenn keine sichere Ableitung möglich ist

### E3: Import-Normalisierung

Der Import braucht zusätzliche Felder/Aliase für:

- `vat_rate`
- `vat_code`
- `tax-free`
- `Steuersatz`
- `Steuerklasse`

sowie konsistente Normalisierung.

Akzeptierte nutzerfreundliche Importwerte:

- `vat_rate`: `19`, `7`, `0`, `19%`, `7%`, `0%`
- `vat_code`: persistierte interne Codes aus A3
- `tax-free`: boolescher Wert analog zu bestehenden Bool-Feldern

Wenn `vat_code` und nutzerfreundliche Felder gleichzeitig angegeben sind und
widersprechen, ist der Import fehlerhaft.

## Periodenlogik

### F1: Filterregeln

- `--year 2026` → ganzer Zeitraum 2026-01-01 bis 2026-12-31
- `--year 2026 --quarter 2` → 2026-04-01 bis 2026-06-30
- `--year 2026 --month 3` → 2026-03-01 bis 2026-03-31

### F2: Validierung

Ungültige Kombinationen führen zu einem Fehler:

- fehlendes `--year`
- `--quarter` und `--month` gemeinsam
- `quarter` außerhalb 1..4
- `month` außerhalb 1..12

## Rundung

### G1: Interne Berechnung

Intern wird centgenau gerechnet.

### G2: Formularnahe Ausgabe

Für die ELSTER-nahe Ausgabe werden Beträge nach den gültigen UStVA-Regeln
ausgegeben:

- Bemessungsgrundlagen in vollen Euro
- Steuerbeträge mit Cent-Betrag, wenn die Kennzahl eine Steuer-Spalte hat
- Ergebnis/Zahllast mit Cent-Betrag

Die Rundungslogik muss zentral implementiert und testbar sein.

Die genaue Rundungsregel wird in einem zentralen Helper abgebildet und in Tests
gegen typische positive und negative Beträge abgesichert.

## Beziehung zu `summary`

`summary` bleibt eine EÜR-/Steuerübersicht und wird **nicht** zum UVA-Report
ausgebaut.

`vat-report` ist ein separater Command mit eigener fachlicher Darstellung.

## Nicht im Scope

Nicht prioritär für die erste Umsetzung sind Sonderfälle außerhalb der
Kernzielgruppe, insbesondere:

- Sondervorauszahlung
- Einfuhrumsatzsteuer
- OSS / IOSS
- atypische Spezialfälle außerhalb typischer Freelancer-/Berater-Workflows

Diese Fälle dürfen im Code nicht stillschweigend falsch behandelt werden.
Wenn sie erkannt werden, soll der Report warnen oder als nicht unterstützt
kennzeichnen.

## Betroffene Dateien

Mindestens zu erwarten:

| Datei | Änderung |
|---|---|
| `euercli/cli.py` | Neuer Parser `vat-report` |
| `euercli/commands/vat_report.py` | Neue Report-Ausgabe |
| `euercli/services/vat_report.py` | Aggregation, Kennzahlen-Mapping, Warnungen |
| `euercli/schema.py` | Neue Steuerfelder |
| `euercli/commands/init.py` | Migration |
| `euercli/services/models.py` | Neue Modellfelder |
| `euercli/services/expenses.py` | Persistenz/Validierung |
| `euercli/services/income.py` | Persistenz/Validierung |
| `euercli/importers.py` | Neue Importfelder |
| `euercli/commands/import_data.py` | Import-Weitergabe |
| `euercli/commands/add.py` | Neue Eingabefelder |
| `euercli/commands/update.py` | Neue Eingabefelder |
| `euercli/commands/export.py` | optional Wiederverwendung von Export-Helfern |
| `tests/test_cli.py` | CLI-Integrationstests |
| `tests/test_services_expenses.py` | Service-Tests |
| `tests/test_services_income.py` | Service-Tests |
| `TESTING.md` | Abdeckung ergänzen |

## Testanforderungen

Mindestens abzudecken:

1. `vat-report` verlangt `--year`
2. `--quarter` und `--month` sind exklusiv
3. Jahres-, Quartals- und Monatsfilter liefern korrekte Zeiträume
4. Buchungen ohne `payment_date` werden nicht eingerechnet, aber gewarnt
5. RC-EU landet in KZ 46/47
6. RC-Drittland landet in KZ 84/85
7. RC ohne Jurisdiktion wird gewarnt und nicht eingerechnet
8. Standardumsätze 19 % werden korrekt aggregiert
9. 7 %-Umsätze werden korrekt aggregiert
10. 0 %-Umsätze und steuerfreie Umsätze werden getrennt gemappt
11. Normale Vorsteuer landet in KZ 66
12. RC-Vorsteuer bei Regelbesteuerung landet in KZ 67
13. Kleinunternehmer-RC erzeugt keine KZ 67
14. CSV-Export enthält strukturierte Kennzahlenzeilen
15. XLSX-Export schlägt sauber fehl, wenn `openpyxl` fehlt
16. Nicht unterstützte Fälle werden als Warnung/Status ausgewiesen
17. `add income --vat-rate 7` persistiert `vat_rate` und `vat_code`
18. `add income --tax-free` ist exklusiv zu `--vat-rate` und `--vat`
19. `euer init` ergänzt `vat_rate` und `vat_code` bei bestehenden Datenbanken
20. Rundung von Bemessungsgrundlagen und Cent-Ausgabe von Steuerbeträgen ist
    reproduzierbar und getestet

## Verwandte Specs

- Spec 004: Steuerlogik (KU/Standard)
- Spec 011: Reverse-Charge-Jurisdiktion
