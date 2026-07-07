# Spec 014: HTML-Pruefbericht fuer Buchungen

## Status

Offen

## Ziel

`euer` soll einen lokalen, statischen HTML-Pruefbericht erzeugen, mit dem
Nutzer:innen die durch CLI oder Agenten erfassten Buchungen vor Export,
Steuererklaerung oder USt-Voranmeldung komfortabel kontrollieren koennen.

Der Bericht ist eine **read-only Pruefansicht**. Er dient nicht der Erfassung,
Korrektur oder Freigabe von Buchungen.

## Motivation

Aktuell koennen Nutzer:innen die Arbeit eines Buchungsagenten vor allem ueber
Terminal-Listen, Summary-Ausgaben und Excel-/CSV-Exporte kontrollieren. Das ist
funktional, aber fuer eine menschliche Endpruefung nicht ideal:

- Excel erfordert manuelles Oeffnen, Formatieren und Filtern.
- Terminal-Ausgaben sind gut fuer Agenten und schnelle Checks, aber weniger gut
  fuer visuelle Durchsicht laengerer Buchungslisten.
- Nutzer:innen wollen vor einer Einreichung beim Finanzamt nachvollziehen
  koennen, ob Datum, Betrag, Kategorie, Steuerbehandlung, Beleg und Notizen
  plausibel sind.
- Eine chronologische Ansicht macht Cashflow, Runrate und Geschaeftsentwicklung
  intuitiver sichtbar als getrennte Listen fuer Einnahmen, Ausgaben und
  Privatvorgaenge.

Der HTML-Pruefbericht schliesst diese Luecke, ohne die CLI-first-Architektur in
eine Web-App umzubauen.

## Produktentscheidung

Die erste Version ist eine **Pruefuebersicht mit Detailnachweis**, aber keine
vollstaendige Web-App.

Der erste sichtbare Bereich soll die fuer die Einreichung relevanten
Kernaussagen zeigen:

- EÜR-/Summary-Kopfzahlen
- UStVA-Arbeitsbericht bzw. UStVA-Kennzahlen fuer den gewaehlten Zeitraum
- Warnungen und offene Pruefpunkte mit Buchungs-IDs
- danach die chronologische Detailansicht der Buchungen

Primaeres Produktziel:

- zuerst die Einreichungs- und Pruefsummen sichtbar machen
- alle relevanten Datensaetze chronologisch sichtbar machen
- Pruefauffaelligkeiten hervorheben
- schnelle Navigation, Filterung und Sortierung erlauben
- Belege aus der Ansicht heraus auffindbar machen
- Korrekturen bewusst auf CLI-Commands verweisen

Nicht-Ziel:

- keine Bearbeitung im Browser
- keine Schreiboperationen aus HTML oder JavaScript
- keine lokale Serverpflicht
- keine ELSTER-Uebermittlung
- keine steuerliche Freigabe oder fachliche Richtigkeitsgarantie
- keine Live-Verbindung zur Datenbank aus dem Browser

## Geltungsbereich

Der Bericht umfasst lesend:

- Ausgaben (`expenses`)
- Einnahmen (`income`)
- Privateinlagen und Privatentnahmen (`private_transfers`)
- privat bezahlte betriebliche Ausgaben, soweit sie in bestehenden Services
  bereits als Privateinlage ausgewertet werden
- Buchungsstatus gemaess Rechnungsdatum, Wertstellungsdatum und Beleg
- Kategorie, EÜR-Zeile und optionales Buchungskonto (`ledger_account`)
- Umsatzsteuer-/Vorsteuerwerte und Reverse-Charge-Typ
- Warnungen aus vorhandenen Pruefmechanismen, insbesondere fehlende Pflichtdaten,
  fehlende Belege, unklassifizierte RC-Buchungen und Buchungen ohne
  Wertstellungsdatum

Nicht im Scope:

- Schreibzugriffe auf `expenses`, `income` oder `private_transfers`
- Korrekturformulare
- Inline-Kommentare oder Review-Status in der Datenbank
- neue fachliche Steuerlogik
- neues Datenbankschema

## Zentrale Designentscheidungen

### D1: Statischer HTML-Export

Der Bericht wird als Datei erzeugt, z.B.:

```bash
euer report --year 2026 --format html
euer report --year 2026 --output exports/
```

Die Ausgabe ist eine einzelne HTML-Datei mit eingebettetem CSS und, falls
noetig, kleinem eingebettetem JavaScript fuer Filter und Sortierung.

Regeln:

- keine externen CDN-Abhaengigkeiten
- keine Netzwerkzugriffe
- keine Tracking- oder Cloud-Funktionen
- lokal per Browser oeffenbar
- druck- und PDF-freundlich

### D2: Aufbau: Summary zuerst, Details danach

Die Seite beginnt mit einer kompakten Pruefuebersicht, weil der Bericht vor
allem der Kontrolle vor Einreichung beim Finanzamt dient.

Reihenfolge:

1. Berichtskopf mit Zeitraum, Steuermodus, Erzeugungszeitpunkt und Datenbankpfad
2. Summary-/EÜR-Kopfzahlen
3. UStVA-Arbeitsbericht fuer denselben Zeitraum, soweit aus Spec 012 ableitbar
4. zentrale Warnungen und offene Pruefpunkte
5. chronologische Detailansicht aller relevanten Buchungen

Die Detailansicht bleibt der Nachweis fuer die Kopfzahlen. Jede aggregierte
Zahl muss entweder auf bestehende Services zurueckgehen oder aus dem
Report-Modell nachvollziehbar sein.

### D3: Chronologische Detailansicht

Die zentrale Detailansicht ist eine gemeinsame Chronologie aller relevanten
Buchungsereignisse. Sie steht unterhalb der Summary- und UStVA-Bereiche.

Sortierbasis:

1. `payment_date`, falls vorhanden
2. sonst `invoice_date`
3. sonst Datum des Privattransfers
4. Buchungs-ID als stabile Zweitsortierung

Eintraege ohne Wertstellungsdatum muessen sichtbar bleiben und duerfen nicht
stillschweigend aus der Pruefansicht verschwinden.

### D4: Read-only und CLI-Korrekturpfad

Korrekturen erfolgen ausschliesslich ueber bestehende oder neue CLI-Commands.

Begruendung:

- CLI-Kommandos laufen durch Service-Layer-Validierung.
- Mutationen erzeugen Audit-Log-Eintraege.
- Agenten-Workflows bleiben textbasiert und reproduzierbar.
- Der HTML-Bericht bleibt ein pruefbares Artefakt, kein zweiter Schreib-Client.

Der Bericht darf bei auffaelligen Buchungen konkrete CLI-Hinweise anzeigen,
z.B.:

```text
Korrektur per CLI:
euer update expense 42 --category "Laufende EDV-Kosten"
```

Diese Hinweise sind rein informativ und duerfen keine Aktion im Browser
ausloesen.

### D5: Filter und Sortierung bleiben lesend

Filter und Sortierung sind fachlich sinnvoll, weil sie bei der Pruefung schnell
gefragt sein werden.

Erlaubte erste Filter:

- Jahr
- Monat
- Typ: Einnahme, Ausgabe, Privateinlage, Privatentnahme
- Status: vollstaendig, unvollstaendig, Beleg fehlt, Wertstellung fehlt
- Kategorie
- Buchungskonto
- Zahlungs-/Bankkonto
- Reverse Charge
- private Klassifikation

Sortierung:

- Datum
- Betrag
- Gegenpartei
- Kategorie
- Status

Filter und Sortierung duerfen ausschliesslich clientseitig auf bereits im HTML
enthaltenen Daten arbeiten.

### D6: Beleglinks als Komfortfunktion

Wenn Belegpfade aus der Config ableitbar sind, soll der Bericht Belegnamen als
lokale Links darstellen.

Regeln:

- nur vorhandene Belege verlinken
- fehlende Belege sichtbar markieren
- Pfade muessen HTML-escaped werden
- keine automatische Dateiindexierung ueber die konfigurierten Belegordner
  hinaus
- wenn Browser-Sicherheitsregeln `file://`-Links blockieren, bleibt der
  Belegpfad zumindest sichtbar/kopierbar

### D7: Refresh durch erneuten CLI-Export

Der HTML-Bericht ist ein statisches Artefakt. Ein Browser-Refresh darf keine
Datenbank neu lesen und keine verdeckte Aktualisierung ausloesen.

Nach Korrekturen per CLI wird der Bericht erneut erzeugt:

```bash
euer report --year 2026 --output exports/
```

Regeln:

- der Command darf die bestehende HTML-Datei fuer denselben Zeitraum
  ueberschreiben
- der Bericht zeigt einen Erzeugungszeitpunkt, damit Nutzer:innen erkennen, ob
  sie eine alte Datei betrachten
- optional darf im HTML ein sichtbarer Hinweis stehen:
  `Nach CLI-Korrekturen Bericht erneut mit euer report erzeugen.`
- ein Button in der HTML-Seite darf hoechstens den Browser-Reload ausloesen,
  aber nicht suggerieren, dass dadurch neue Daten aus SQLite geladen werden

Begruendung:

- keine Serverpflicht
- keine zweite Datenzugriffsschicht im Browser
- reproduzierbares Pruefarbeitsprodukt
- konsistent mit CLI-first und Audit-Log

### D8: Keine duplizierte Business-Logik im Renderer

Der HTML-Renderer darf keine fachliche Buchhaltungs- oder Steuerlogik neu
implementieren.

Stattdessen:

- Aggregation und Pruefstatus in `euercli/services/`
- HTML-Erzeugung als View-Schicht in `euercli/commands/` oder einem kleinen
  Renderer-Modul ohne DB-Schreibzugriff
- bestehende Services fuer Listen, Privatvorgaenge und UStVA wiederverwenden
- bestehende Summary-Logik vor Nutzung im HTML-Bericht in einen Service
  auslagern, damit CLI und HTML dieselben Zahlen verwenden

## Anforderungen

### A1: Neuer Command `report`

Neuer CLI-Befehl:

```bash
euer report --year 2026
euer report --year 2026 --format html
euer report --year 2026 --output exports/
```

Regeln:

- Default-Format: `html`
- `--year` ist fuer die erste Version Pflicht
- `--output` ist ein Verzeichnis; Default ist `exports.directory` aus Config
  oder `exports/`
- Dateiname z.B. `Pruefbericht_2026.html`
- eine bestehende Datei fuer denselben Zeitraum wird ueberschrieben
- Ausgabe meldet den erzeugten Pfad

### A2: Gemeinsames Report-Modell im Service Layer

Neue Service-Funktionen, z.B. in `euercli/services/report.py`:

```python
def build_review_report(conn: sqlite3.Connection, *, year: int) -> ReviewReport:
    """Erzeugt ein read-only Datenmodell fuer den HTML-Pruefbericht."""
```

Das Datenmodell soll typisierte Dataclasses verwenden, z.B.:

- `ReviewReport`
- `ReviewEntry`
- `ReviewWarning`
- `ReviewTotals`

Der Service fuehrt nur lesende SQL-Abfragen aus.

### A3: Chronologische Eintraege

Jeder Eintrag enthaelt mindestens:

| Feld | Beschreibung |
|------|--------------|
| `entry_type` | `expense`, `income`, `private_deposit`, `private_withdrawal` |
| `id` | lokale numerische ID |
| `date` | Sortier-/Anzeigedatum |
| `payment_date` | Wertstellungsdatum, falls vorhanden |
| `invoice_date` | Rechnungsdatum, falls vorhanden |
| `party` | Lieferant, Kunde oder Beschreibung |
| `amount_eur` | Betrag in EUR |
| `category` | Kategorie mit EÜR-Zeile, falls vorhanden |
| `ledger_account` | Buchungskonto, falls vorhanden |
| `account` | Zahlungs-/Bankkonto, falls vorhanden |
| `receipt_name` | Belegname, falls vorhanden |
| `receipt_link` | lokaler Beleglink, falls aufloesbar |
| `vat_input` | Vorsteuer |
| `vat_output` | Umsatzsteuer |
| `vat_rate` | Steuersatz |
| `vat_code` | persistierte USt-Klassifikation |
| `rc_type` | Reverse-Charge-Typ |
| `status` | menschenlesbarer Pruefstatus |
| `warnings` | zeilenbezogene Warnungen |
| `suggested_cli` | optionale CLI-Hinweise zur Korrektur |

### A4: Pruefstatus und Warnungen

Der Bericht hebt mindestens hervor:

- fehlende Kategorie
- fehlendes Buchungskonto, wenn ein Kontenrahmen konfiguriert ist und die
  Buchung ohne `ledger_account` erfasst wurde
- fehlender Beleg
- fehlendes Wertstellungsdatum
- fehlendes Rechnungsdatum
- unklassifizierter Reverse-Charge-Typ
- fehlende oder unklare USt-Klassifikation fuer `vat-report`
- negative Einnahmen oder positive Ausgaben, falls solche Daten durch Import
  oder Altbestand existieren

Warnungen sollen die betroffene Buchungs-ID nennen.

### A5: Summary und UStVA im oberen Seitenbereich

Der Bericht zeigt im oberen Seitenbereich verpflichtend die wichtigsten Zahlen
aus `summary` und `vat-report`, soweit sie fuer den gewaehlten Zeitraum
fachlich ableitbar sind.

Summary-/EÜR-Bereich:

- Einnahmen gesamt
- Ausgaben gesamt
- Ergebnis laut erfassten Zahlungen
- Ausgaben nach Kategorie
- Einnahmen nach Kategorie
- Bewirtungsaufwendungen 70/30, falls vorhanden
- Privateinlagen und Privatentnahmen, falls angefordert oder fachlich relevant

UStVA-Bereich:

- Kennzahlen aus Spec 012, z.B. KZ 81/86/87/48, KZ 46/47, KZ 84/85, KZ 66/67
  und KZ 83
- Vorsteuer
- Umsatzsteuer
- USt-Zahllast/Erstattung nach vorhandener Logik
- Warnungen und Diagnosehinweise aus dem UStVA-Report

Diese Zahlen sind Orientierung und Pruefeinstieg. Der Bericht darf nicht den
Eindruck einer steuerlichen Freigabe erzeugen. Die chronologische Detailansicht
unterhalb der Kopfzahlen dient zur Plausibilisierung.

Wichtig: Die Werte muessen aus denselben Services stammen wie CLI-`summary` und
CLI-`vat-report`. Wenn dafuer bestehende CLI-Logik aus `commands/summary.py`
ausgelagert werden muss, ist diese Auslagerung Teil der Implementierung.

### A6: Liquiditaetswerte nur mit klarer Bezeichnung

Wichtig: Ein moeglicher Liquiditaetswert darf nicht als echter
Bank-`Kontostand` bezeichnet werden. Zulaessige Begriffe sind z.B.:

- `Erfasster Netto-Cashflow`
- `Geschaeftlicher Zahlungsueberschuss`
- `Einnahmen minus Ausgaben laut erfassten Zahlungen`

### A7: Datenschutz und lokale Ausfuehrung

Der HTML-Bericht enthaelt sensible Geschaeftsdaten.

Pflichten:

- keine externen Assets
- keine eingebetteten Remote-Fonts
- keine Telemetrie
- keine automatischen Uploads
- alle dynamischen Inhalte per `html.escape()` oder gleichwertiger Funktion
  escapen
- JSON-Daten im HTML sicher einbetten, falls clientseitige Filter genutzt werden

### A8: Tests

Mindestens zu testen:

- `euer report --year YYYY` erzeugt eine HTML-Datei
- vorhandene HTML-Datei fuer denselben Zeitraum wird durch erneuten CLI-Aufruf
  ueberschrieben
- HTML enthaelt Summary- und UStVA-Bereiche vor der Detailansicht
- HTML enthaelt chronologisch sortierte Einnahmen, Ausgaben und Privatvorgaenge
- fehlende Belege und fehlende Wertstellungsdaten werden markiert
- HTML escaped Sonderzeichen aus Lieferant, Quelle, Notizen und Belegnamen
- keine Schreiboperationen werden ausgefuehrt
- Output-Verzeichnis aus Config wird respektiert

## Empfohlene Implementierungsschritte

1. `ReviewReport`-Dataclasses und `build_review_report()` im Service Layer
   anlegen.
2. Bestehende Listen- und Privattransfer-Services fuer Datenbeschaffung
   wiederverwenden.
3. Summary-Berechnung aus `commands/summary.py` in einen Service auslagern,
   damit CLI und HTML dieselben EÜR-Kopfzahlen nutzen.
4. `build_vat_report()` aus Spec 012 fuer den UStVA-Bereich wiederverwenden.
5. HTML-Renderer mit Standardbibliothek implementieren (`html.escape`,
   einfache Templates als Python-Funktionen oder dedizierte Modulstruktur).
6. `euer report` in `euercli/cli.py` registrieren.
7. CLI-Integrationstests und Service-Tests ergaenzen.
8. Doku in `docs/USER_GUIDE.md`, `docs/skills/euer-buchhaltung/SKILL.md`,
   `docs/templates/onboarding-prompt.md`, `README.md` und
   `docs/RELEASE_NOTES.md` aktualisieren, sobald die Spec implementiert wird.

## Offene Fragen

- Soll die erste Version nur ein Jahresfilter sein oder auch `--month` und
  `--quarter` analog zu `vat-report` anbieten?
- Soll der Bericht automatisch im Browser geoeffnet werden koennen, z.B.
  `--open`, oder bleibt das aus Sicherheits- und Plattformgruenden ausserhalb
  des MVP?
- Soll der UStVA-Bereich im HTML-Bericht nur den Jahresbericht zeigen oder
  zusaetzlich Quartals-/Monatsabschnitte anbieten?
- Wie stark sollen CLI-Korrekturhinweise generiert werden, ohne eine zweite
  Regel-Engine fuer Reparaturvorschlaege zu bauen?

## Verwandte Specs

- Spec 002: Beleg-Management
- Spec 006: Rechnungs-/Wertstellungsdatum
- Spec 008: Privateinlagen & Privatentnahmen
- Spec 010: Kontenrahmen
- Spec 011: Reverse-Charge-Typ
- Spec 012: `vat-report`
- Spec 013: Belegordner Jahr zuerst
