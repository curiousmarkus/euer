# Spec 012: `vat-report` – USt-Voranmeldungs-Report

## Status

Offen

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

## Abhängigkeiten

- Spec 004: Steuerlogik (KU/Standard)
- Spec 011: RC-Jurisdiktion

Ohne Spec 011 kann die Aufteilung KZ 46/47 vs. KZ 84/85 nicht korrekt erfolgen.

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

### D4: ELSTER-nahe Darstellung in vollen Euro

Der Terminal-Report soll Bemessungsgrundlagen und Kennzahlen **in vollen Euro**
ausgeben, analog zur UStVA-Logik.

Zusätzlich kann eine Diagnose-/Detailsektion centgenaue Ursprungswerte zeigen,
damit Rundungen nachvollziehbar bleiben.

### D5: Keine stillschweigende Falschsicherheit

Wenn eine Kennzahl im Formular grundsätzlich existiert, aber aus den Daten nicht
fachlich sicher ableitbar ist, darf der Report **nicht** einfach `0` ausgeben.

Stattdessen:

- Kennzahl als `nicht unterstützt` oder `unvollständig`
- plus Warnung

Nur fachlich sicher als leer/0 ableitbare Kennzahlen dürfen als `0` erscheinen.

## Erforderliche Datenmodell-Erweiterungen

Der heutige Datenbestand reicht für einen möglichst vollständigen UStVA-Report
nicht aus. Insbesondere fehlt eine explizite fachliche Umsatzsteuer-Klassifikation.

### A1: Neue Felder für steuerliche Klassifikation

Es werden neue Felder für `expenses` und `income` benötigt.

Mindestens erforderlich:

- `vat_rate REAL | NULL`
- `vat_code TEXT | NULL`

Ziel der Felder:

- Steuersatz explizit speichern (`19`, `7`, optional weitere Werte)
- steuerliche Behandlung explizit speichern

### A2: Persistierte Steuerlogik statt bloßer Herleitung aus Config

Die für UStVA relevante steuerliche Einordnung muss an der Buchung hängen,
nicht nur implizit aus aktuellem Modus oder Kategorie abgeleitet werden.

Begründung:

- Historie bleibt stabil
- Reports bleiben auditierbar
- spätere Config-Änderungen verfälschen keine alten Voranmeldungen

### A3: Empfohlene `vat_code`-Werte

Mindestens für die Zielgruppe sinnvoll:

- `output_standard_19`
- `output_reduced_7`
- `output_tax_free`
- `output_small_business`
- `input_standard`
- `reverse_charge_eu`
- `reverse_charge_third_country`

Die finale technische Benennung kann leicht abweichen, aber es braucht
fachlich äquivalente Codes.

### A4: Default-Steuersatz

Wenn für steuerpflichtige Standardumsätze kein expliziter Steuersatz angegeben
ist, gilt als Default:

- `19 %`

Diese Default-Regel gilt nur dort, wo der Vorgang fachlich bereits als
steuerpflichtiger Standardumsatz feststeht.

Sie darf **nicht** verwendet werden, um unklare Fälle blind zu raten.

## Kennzahlen-Mapping (MVP mit professionellem Scope)

Die erste Version des Reports soll für die Kernzielgruppe mindestens folgende
Kennzahlen belastbar liefern oder als unvollständig markieren.

### B1: Kleinunternehmer

Für Kleinunternehmer relevant:

- eigene Umsätze als Hinweis-/Kontextblock
- RC EU:
  - KZ 46 Bemessungsgrundlage
  - KZ 47 Steuer
- RC Drittland:
  - KZ 84 Bemessungsgrundlage
  - KZ 85 Steuer

Hinweis:

Eigene Umsätze von Kleinunternehmern sind keine normale Ausgangs-USt-Position,
können aber im Report als Kontextblock angezeigt werden.

### B2: Regelbesteuerung

Für Regelbesteuerte im Kernbereich:

- steuerpflichtige Umsätze 19 %
- steuerpflichtige Umsätze 7 %
- RC EU:
  - KZ 46
  - KZ 47
- RC Drittland:
  - KZ 84
  - KZ 85
- abziehbare Vorsteuer

### B3: Kennzahlen, die nur mit zusätzlicher Modellierung unterstützt werden

Wenn für eine Kennzahl zusätzliche Modellierung nötig ist, wird diese Modellierung
Teil dieser Spec und nicht auf unbestimmte Zeit verschoben.

Beispiele:

- 7 %-Umsätze erfordern expliziten `vat_rate`
- bestimmte Sonderfälle erfordern expliziten `vat_code`

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
  KZ xx  Steuerpflichtige Umsätze 19%:         5.000 EUR
         Steuer:                                 950 EUR
  KZ yy  Steuerpflichtige Umsätze 7%:              0 EUR
         Steuer:                                   0 EUR

Reverse Charge:
  KZ 46  EU-Bemessungsgrundlage:                  96 EUR
  KZ 47  EU-Steuer:                               18 EUR
  KZ 84  Drittland-Bemessungsgrundlage:          111 EUR
  KZ 85  Drittland-Steuer:                        21 EUR

Vorsteuer:
  KZ zz  Abziehbare Vorsteuer:                   120 EUR

--------------------------------------------------
ZAHLLAST / ERSTATTUNG:                           851 EUR

Warnungen:
  - 2 RC-Buchungen ohne Jurisdiktion nicht eingerechnet: IDs 14, 27
  - 1 Einnahme ohne payment_date nicht eingerechnet: ID 31
```

Die konkreten Kennzahlenamen werden aus den jeweils aktuellen offiziellen
Vorgaben abgeleitet.

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

Diese Commands müssen `vat_rate` / `vat_code` oder äquivalente fachliche Daten
entgegennehmen, validieren und über den Service Layer persistieren.

### E2: Service Layer

Die Services für `expenses` und `income` müssen:

- neue Felder validieren
- sinnvolle Defaults setzen
- widersprüchliche Kombinationen ablehnen
- typisierte Rückgaben liefern

### E3: Import-Normalisierung

Der Import braucht zusätzliche Felder/Aliase für:

- `vat_rate`
- `vat_code`

sowie konsistente Normalisierung.

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

Für die ELSTER-nahe Ausgabe werden Bemessungsgrundlagen und Steuerbeträge nach
den gültigen UStVA-Regeln in volle Euro ausgegeben.

Die Rundungslogik muss zentral implementiert und testbar sein.

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
10. Vorsteuer wird korrekt aggregiert
11. CSV-Export enthält strukturierte Kennzahlenzeilen
12. XLSX-Export schlägt sauber fehl, wenn `openpyxl` fehlt
13. Nicht unterstützte Fälle werden als Warnung/Status ausgewiesen
14. Rundung auf volle Euro ist reproduzierbar und getestet

## Verwandte Specs

- Spec 004: Steuerlogik (KU/Standard)
- Spec 011: Reverse-Charge-Jurisdiktion
