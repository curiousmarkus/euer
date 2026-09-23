# Spec 017: Nicht eingebuchte Belege erkennen (`receipt unbooked`)

## Status

Offen

## Ziel und Aussagegrenze

`euer receipt unbooked` findet unterstützte Belegdateien im konfigurierten
Jahresordner, denen keine Buchung in `expenses` oder `income` über eine auflösbare
`receipt_name`-Referenz zugeordnet ist.

Der Command ergänzt die vorhandene Prüfrichtung:

- `receipt check`: DB → Dateisystem: Fehlt zu einer Buchung die Belegdatei?
- `receipt unbooked`: Dateisystem → DB: Welche Belegdateien sind nicht zugeordnet?

Der Name `unbooked` ist eine Kurzform. Ein Treffer beweist nicht, dass der Vorgang
noch nicht gebucht wurde: Eine bestehende Buchung kann ohne Belegreferenz oder
mit einem falschen Belegnamen erfasst sein. Deshalb lautet die nutzerseitige
Bezeichnung **„Belegdateien ohne zugeordnete Buchung“**.

Auch ein Scan ohne Treffer bestätigt nur die Zuordnung der berücksichtigten
Dateien. Er bestätigt weder die Vollständigkeit der Buchhaltung noch die
inhaltliche Richtigkeit oder vollständige Erfassung eines Belegs.

## Motivation und Agenten-Workflow

Beim Monats- oder Jahresabschluss sollen übersehene Dateien auffallen, ohne
Doppelbuchungen durch eine pauschale Aufforderung zum Einbuchen zu fördern.

1. Belege im zum Zahlungsjahr passenden Typordner ablegen.
2. `receipt unbooked --year JAHR --format json` ausführen.
3. Für jeden Treffer zuerst bestehende Buchungen prüfen. Falls der Vorgang bereits
   erfasst ist, den Beleg mit `update ... --receipt ...` zuordnen bzw. eine falsche
   Ablage korrigieren.
4. Nur wenn noch keine passende Buchung existiert, nach Prüfung des Belegs und
   der Zahlung eine neue Buchung mit `add` anlegen.
5. Den Scan wiederholen und zusätzlich `receipt check` sowie die Prüfung auf
   unvollständige Buchungen nutzen.

## Jahreszuordnung: Zahlungsdatum ist maßgeblich

Die Ablage folgt der Zahlungsjahres-Konvention aus
[Spec 013](013-belegordner-jahr-zuerst.md): Ausgaben werden nach Zahlungsabgang,
Einnahmen nach Zahlungseingang zugeordnet (`payment_date`). Das Rechnungsdatum
bestimmt weder den Ablageordner noch den Jahresfilter dieses Commands.

Beispiel: Eine Rechnung vom Dezember 2026 wird im Januar 2027 bezahlt. Der Beleg
gehört unter `<root>/2027/Ausgaben/`, auch wenn sein Dateiname mit `2026-12-...`
beginnt. Die Buchung mit `payment_date` in 2027 ordnet diese Datei beim Scan für
2027 zu. Aus Dateiname und Änderungszeit wird kein Buchungsjahr abgeleitet.

Liegt dieselbe Datei stattdessen unter `2026/Ausgaben/`, wird sie dort als nicht
zugeordnet gemeldet. Ein bloßer Namensgleichlauf mit einer Buchung von 2027 darf
sie nicht als korrekt zugeordnet markieren. Vor einer Neubuchung muss der Agent
auch eine falsche Jahresablage prüfen.

Buchungen ohne `payment_date` sind gesondert zu behandeln:

- Sie werden unabhängig vom Rechnungsdatum für den Referenzabgleich geladen.
- Wie in Spec 013 erlaubt, wird das ausdrücklich gewählte Scan-Jahr als
  `fallback_year` an den Resolver übergeben.
- Eine so gefundene Datei gilt für diesen Scan als referenziert: Der Vorgang ist
  bereits erfasst und soll nicht erneut zur Buchung vorgeschlagen werden.
- Jede solche Zuordnung erzeugt eine Warnung `missing_payment_date` mit
  Buchungstyp, Buchungs-ID und Dateipfad. Der Jahreskontext ist vorläufig und
  bestätigt keine Zahlung. Die Warnung wird auch bei null Treffern ausgegeben.
- Ohne Zahlungsdatum kann derselbe Name in mehreren Jahresordnern vorläufig
  passen. Der Command trifft keine jahresübergreifende Zuordnungsentscheidung;
  nach Ergänzung des tatsächlichen Zahlungsdatums ist die Ablage erneut zu prüfen.

## CLI-Design

```bash
euer receipt unbooked [--year JAHR] [--type {expense,income}] [--format {table,csv,json}]
```

| Argument | Standard | Bedeutung |
|----------|----------|-----------|
| `--year` | Aktuelles Kalenderjahr | Zu scannendes Ablagejahr; gültig: 1–9999 |
| `--type` | Beide | Auswahl des Ausgaben- oder Einnahmenordners |
| `--format` | `table` | Ausgabe als Tabelle, CSV oder JSON |

Das vorhandene globale `--db` bleibt nutzbar. Es gibt keine interaktiven Prompts.
`receipt check --include-unbooked` ist nicht Bestandteil dieser ersten Version.
Das bestehende CLI-Verhalten von `receipt check` und `receipt open` bleibt erhalten.

## Scan und Abgleich

### 1. Verzeichnisse ermitteln

Konfiguration über `get_receipt_config()` laden und validieren:

```text
<receipts.root>/<receipts.year_dir.format(year=year)>/<receipts.expenses_dir>
<receipts.root>/<receipts.year_dir.format(year=year)>/<receipts.income_dir>
```

Nur die ausgewählten Typordner scannen. Kein Scan anderer Jahre oder beliebiger
Nachbarordner. Fehlender Root, fehlender ausgewählter Typordner und ein Pfad,
der kein Verzeichnis ist, gelten als Prüffehler. Ein existierender leerer Ordner
ist dagegen ein gültiges Ergebnis mit null Dateien. Wer nur Ausgaben ablegt,
kann mit `--type expense` ausschließlich diesen Ordner prüfen.

### 2. Dateien erfassen

- Immer rekursiv innerhalb der ausgewählten Typordner; kein zusätzlicher
  Konfigurationsschalter für Rekursion.
- Reguläre Dateien mit folgenden Endungen berücksichtigen, ohne Beachtung der
  Groß-/Kleinschreibung: `.pdf`, `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`.
- Dateien und Verzeichnisse mit Namen beginnend mit `.` oder `~$` ignorieren;
  ebenso `Thumbs.db`, `desktop.ini` und Dateien mit Endung `.tmp` (jeweils
  ohne Beachtung der Groß-/Kleinschreibung).
- Symbolische Links unterhalb der Scan-Verzeichnisse nicht verfolgen, auch keine
  Datei-Symlinks. Ausgelassene Links sichtbar ausweisen. Ein konfigurierter Root
  darf selbst ein Symlink sein; die Scan-Grenze ist dessen aufgelöster Zielpfad.
- Ignorierte Verzeichnisse nicht betreten. Ihre Inhalte werden nicht gezählt.
- Nicht unterstützte oder ignorierte Dateien sowie übersprungene Verzeichnisse
  und Links mit relativem Pfad und Grund in `skipped_entries` erfassen.
- Lesefehler beim Verzeichniszugriff oder bei Dateimetadaten und während des
  Scans verschwundene Dateien als Fehler erfassen; nicht still überspringen.

Der Scan liest Namen und Metadaten, keine Beleginhalte. Er berechnet keine
Dateihashes und benötigt weder OCR noch zusätzliche Bibliotheken. Er ist eine
Bestandsaufnahme, keine atomare Momentaufnahme eines parallel veränderten Ordners.

### 3. Buchungsreferenzen laden

Für jeden ausgewählten Typ Buchungen mit nicht leerem `receipt_name` laden:

- `payment_date` liegt im gewählten Jahr, **oder**
- `payment_date` fehlt; Behandlung wie im Abschnitt zur Jahreszuordnung.

Kein `COALESCE(payment_date, invoice_date)` als Jahresfilter. Leere bzw. nur aus
Leerzeichen bestehende Referenzen stellen keine Zuordnung her. Nicht leere
Dateinamen dürfen nicht durch pauschales Trimmen verändert werden.

Bis zur Umsetzung von Spec 016 gelten alle vorhandenen Datensätze als aktiv.
Der spätere Soft-Delete-Filter ist im Abschnitt „Abhängigkeit zu Spec 016“ geregelt.

### 4. Dateien eindeutig zuordnen

`resolve_receipt_path()` bleibt die gemeinsame Auflösungslogik für Belegreferenzen.
Der neue Service vergleicht die tatsächlich aufgelösten Pfade mit den gescannten
Dateien; er baut keinen unabhängigen Basename- oder Stammnamenabgleich.

- Relative Unterpfade bleiben erhalten: `Lieferant-A/rechnung.pdf` ist nicht
  `Lieferant-B/rechnung.pdf`.
- Einnahmen und Ausgaben werden getrennt abgeglichen. Eine Einnahmenreferenz
  markiert keine Ausgabendatei als zugeordnet.
- Absolute Referenzen, `..`-Pfadkomponenten und Referenzen über übersprungene
  Symlinks stellen für diesen Scan keine Zuordnung her; als Warnung
  `invalid_receipt_reference` mit Buchungs-ID ausgeben.
- Dateinamen nicht pauschal kleinschreiben oder anhand ähnlicher Schreibweise
  zusammenführen. Für die Pfadauflösung gilt die Semantik des Dateisystems.
- Endungslose DB-Referenzen nutzen die bestehende Resolver-Reihenfolge: exakter
  Name, danach `.pdf`, `.jpg`, `.jpeg`, `.png`. Nur der vom Resolver tatsächlich
  gewählte Treffer gilt als zugeordnet; weitere Dateien desselben Stamms nicht.
- Scan-Endungen und implizite Resolver-Endungen haben unterschiedliche Zwecke:
  `.tif`, `.tiff`, `.webp` sind mit expliziter Endung referenzierbar. Diese Spec
  erweitert die bestehende implizite Endungssuche nicht. Eine nicht auflösbare
  Referenz darf nicht durch einen eigenen Fallback des Scanners ersetzt werden.
- Mehrere Buchungen dürfen dieselbe Datei referenzieren. Sie zählt trotzdem nur
  einmal als referenzierte Datei; eine Prüfung auf Doppelbuchungen erfolgt nicht.

Nicht auflösbare Referenzen werden weiterhin durch `receipt check` geprüft.
Der neue Command meldet die dadurch nicht zugeordneten vorhandenen Dateien.

## Abhängigkeit zu Spec 016: keine Implementierungsblockade

[Spec 016](016-agent-safety-und-guardrails.md) plant Soft-Delete über `deleted_at`,
ist aber noch offen. Spec 017 benötigt weder diese Spalte noch eine eigene
Schema-Migration und kann davor implementiert und veröffentlicht werden.

Sobald Soft-Delete verfügbar ist:

- Der Referenzabgleich berücksichtigt ausschließlich `deleted_at IS NULL`.
- Wird die letzte aktive Referenz gelöscht, erscheint die Datei erneut als nicht
  zugeordnet. Wiederherstellen der Buchung ordnet sie wieder zu.
- Bleibt eine weitere aktive Referenz bestehen, bleibt die Datei zugeordnet.
- Eine Referenz ausschließlich in gelöschten Buchungen berechtigt den Agenten
  nicht zur ungeprüften Neubuchung; der bestehende Prüfworkflow gilt weiterhin.

Die Integration und entsprechenden Tests gehören zur Umsetzung von Spec 016,
falls Spec 017 zuerst umgesetzt wird. Falls 016 bereits implementiert ist, nutzt
017 direkt deren Aktivfilter. Keine SQL-Abfrage darf vor Einführung der Spalte
`deleted_at` voraussetzen; keine spekulative Migration durch diesen Lese-Command.

## Ausgabe und Exit-Codes

### Gemeinsamer Vertrag

- Stabile Sortierung nach `type`, dann relativem `path`, unabhängig von der
  Reihenfolge der Dateisystemeinträge. Listen für Fehler und Warnungen ebenfalls
  deterministisch sortieren.
- `path`: relativ zu `receipts.root`, einschließlich Jahres- und Typordner.
- `receipt_name`: relativ zum jeweiligen Typordner; direkt als `--receipt` nutzbar.
- Relative Pfade in JSON/CSV verwenden `/` als Trenner.
- `modified_at`: ISO-8601 in UTC mit `Z`; reine Dateimetadaten, kein Buchungsdatum.
- `total_files` zählt nur berücksichtigte Belegdateien, keine ignorierten Einträge.
- `referenced_files` zählt zugeordnete Dateien, keine Buchungen.
- Bei vollständig durchgeführtem Scan gilt:
  `total_files = referenced_files + unbooked_count` und
  `unbooked_count = len(unbooked_files)`.
- `skipped_count = len(skipped_entries)`; nicht betretene Verzeichnisinhalte sind
  darin nicht enthalten.

| Exit-Code | Bedeutung |
|-----------|-----------|
| `0` | Prüfung vollständig; keine nicht zugeordneten Belegdateien gefunden |
| `1` | Prüfung vollständig; mindestens eine nicht zugeordnete Belegdatei gefunden |
| `2` | Ungültige Argumente oder Prüfung fehlgeschlagen/unvollständig |

Fehler haben Vorrang vor Treffern. Warnungen und regelgerecht übersprungene
Einträge allein ändern den Exit-Code nicht, werden aber sichtbar ausgegeben.
„Prüfung vollständig“ bezieht sich ausschließlich auf den definierten Scanumfang.

### Tabelle

```text
Belegdateien ohne zugeordnete Buchung 2027 (Ausgaben)
==================================================
2027/Ausgaben/2026-12-12_strato_server.pdf       142 KB
2027/Ausgaben/2027-01-09_deutsche_bahn.pdf        89 KB

Berücksichtigte Belegdateien: 15
Davon referenziert:          13
Ohne Zuordnung:               2
Übersprungene Einträge:       0
Prüfstatus: vollständig

Prüfe zuerst bestehende Buchungen und die Ablage im Zahlungsjahr.
Ordne vorhandenen Buchungen den Beleg mit 'update ... --receipt ...' zu.
Lege nur für noch nicht erfasste Vorgänge eine neue Buchung an.
```

Warnungen und übersprungene Einträge werden mit Grund und Pfad aufgelistet.
Bei Fehlern ist das Ergebnis ausdrücklich als unvollständig zu kennzeichnen.

### JSON

Das Top-Level-Feld `types` enthält `['expense']`, `['income']` oder
`['expense', 'income']` (in JSON jeweils mit doppelten Anführungszeichen).
Jeder Dateieintrag enthält seinen Typ; die Zähler aggregieren die ausgewählten
Typen. `root` ist der absolute konfigurierte Root nach Pfadnormalisierung.

```json
{
  "year": 2027,
  "types": ["expense", "income"],
  "root": "/home/max/Buchhaltung",
  "scan_complete": true,
  "total_files": 15,
  "referenced_files": 13,
  "unbooked_count": 2,
  "skipped_count": 0,
  "unbooked_files": [
    {
      "type": "expense",
      "path": "2027/Ausgaben/2026-12-12_strato_server.pdf",
      "receipt_name": "2026-12-12_strato_server.pdf",
      "size_bytes": 145408,
      "modified_at": "2027-01-15T09:14:00Z"
    },
    {
      "type": "income",
      "path": "2027/Einnahmen/2027-01-09_rechnung_001.pdf",
      "receipt_name": "2027-01-09_rechnung_001.pdf",
      "size_bytes": 91136,
      "modified_at": "2027-01-16T10:00:00Z"
    }
  ],
  "skipped_entries": [],
  "warnings": [],
  "errors": []
}
```

Zusätzliche Listen haben folgende Felder:

- `skipped_entries`: `type`, `path`, `reason`; Gründe: `ignored_name`,
  `unsupported_extension`, `symlink`, `non_regular_file`.
- `warnings`: `code`, `message`, `type`, `record_id`, `path` (gegebenenfalls `null`).
- `errors`: `code`, `message`, `type`, `path`; nicht anwendbare Felder sind `null`.
  Stabile Codes: `invalid_config`, `directory_missing`, `not_a_directory`,
  `scan_io_error`, `database_error`.

Bei Laufzeitfehlern bleibt stdout ein einzelnes gültiges JSON-Objekt mit
`scan_complete: false` und mindestens einem Fehler. Nicht ermittelbare Angaben
wie `root` dürfen `null` sein. Ergebniszähler sind bei unvollständigem Scan `null`;
`unbooked_files` bleibt leer, damit Teilergebnisse keine Buchungsaktionen auslösen.
Bereits ermittelte Warnungen und übersprungene Einträge dürfen erhalten bleiben.
Parserfehler folgen dem bestehenden argparse-Verhalten (stderr, Exit-Code 2).

### CSV und Ausgabekanäle

CSV enthält ausschließlich Treffer mit diesen Spalten in dieser Reihenfolge:

```text
type,path,receipt_name,size_bytes,modified_at
```

UTF-8, Komma als Trennzeichen, korrektes CSV-Quoting; bei null Treffern nur die
Kopfzeile. Zusammenfassung, Warnungen und übersprungene Einträge gehen bei CSV
an stderr. Bei fehlgeschlagener Prüfung keine CSV-Teilergebnisse ausgeben;
Fehlermeldung auf stderr und Exit-Code 2.

JSON enthält keine zusätzlichen Statuszeilen auf stdout. Laufzeitdiagnosen stehen
in seinen strukturierten Feldern. Tabellenfehler werden auf stderr ausgegeben.

## Architektur und betroffene Komponenten

- `euercli/services/receipts.py`: Scan, Referenzabgleich, typisierte
  Ergebnis-Dataclasses für Dateien, Zähler, Warnungen und Fehler. Keine Prints,
  keine argparse-Abhängigkeit, keine `sys.exit()`-Aufrufe.
- `euercli/config.py`: vorhandene Konfigurations- und Pfadhelper wiederverwenden;
  bei Bedarf gemeinsame Hilfsfunktionen extrahieren, keine zweite Pfadsemantik.
- `euercli/commands/receipt.py`: `cmd_receipt_unbooked()` als View-Controller;
  Service aufrufen, Ergebnis formatieren, Exit-Code setzen.
- `euercli/commands/__init__.py` und `euercli/cli.py`: Export und Registrierung.
- `tests/test_services_receipts.py` und `tests/test_cli.py`: Service- und CLI-Tests.

DB-Zugriff über `get_db_connection()`, parametrisierte Queries. Der Command ist
rein lesend: keine Buchungsänderungen, Audit-Einträge, Verzeichniserstellung oder
Schema-Migrationen. Eine fehlende DB als Fehler melden und nicht neu anlegen.

## Nicht-Ziele

- Kein automatisches Einbuchen, OCR oder Erraten von Beträgen und Zahlungsdaten.
- Kein Löschen, Verschieben oder Umbenennen von Dateien.
- Keine inhaltliche Duplikaterkennung oder Vollständigkeitsprüfung einzelner Belege.
- Keine Suche außerhalb des gewählten Jahres und der gewählten Typordner.
- Kein persistierter Dateikatalog und keine neue Ignore-Konfiguration.
- Keine Änderung der steuerlichen Jahresermittlung anderer Commands.

## Akzeptanzkriterien und Tests

1. Standard- und benutzerdefinierte Jahres-/Typordner werden korrekt gescannt;
   `--type` begrenzt sowohl Scan als auch Referenzabgleich.
2. Rechnung von 2026, Zahlung 2027, Ablage 2027: korrekt zugeordnet. Eine zusätzliche
   Kopie im Ordner 2026 bleibt dort unzugeordnet; `invoice_date` und Dateiname
   beeinflussen den Jahresfilter nicht.
3. Referenz ohne Zahlungsdatum: Auflösung mit Scan-Jahr als Fallback und Warnung
   mit Buchungs-ID, auch bei abweichendem oder fehlendem Rechnungsdatum.
4. Endungslose Referenz findet dieselbe Datei wie der bestehende Resolver.
   Bei `beleg.pdf` und `beleg.png` wird nicht pauschal beides als referenziert markiert.
5. Rekursive Unterpfade und gleiche Basenames in verschiedenen Unterordnern bleiben
   unterscheidbar. Ausgaben- und Einnahmenreferenzen werden nicht vermischt.
6. Mehrere Referenzen auf eine Datei erhöhen `referenced_files` nur einmal.
7. Unterstützte Endungen inklusive Großschreibung, Ignore-Regeln, nicht unterstützte
   Dateien und übersprungene Verzeichnisse werden entsprechend dem Vertrag behandelt.
8. Symlinks werden nicht verfolgt; absolute und ausbrechende DB-Referenzen ordnen
   keine Dateien zu. Ein Symlink als konfigurierter Root funktioniert.
9. Leerer Ordner: vollständiger Scan mit null Treffern. Fehlende Konfiguration,
   fehlender ausgewählter Ordner, Zugriffsfehler, verschwundene Datei und fehlende
   oder unlesbare DB: Exit-Code 2, kein scheinbar sauberes Ergebnis.
10. JSON für einen und beide Typen entspricht dem Vertrag, einschließlich
    Zeitstempeln, Zählern, Warnungen und Laufzeitfehlern. CSV quotiert Sonderzeichen
    und enthält keine Diagnosezeilen. Reihenfolge bleibt stabil.
11. Exit-Codes 0/1/2 entsprechen dem Vertrag; Fehler haben Vorrang vor Treffern.
12. Scan verändert weder Dateien noch Buchungen und funktioniert vor Spec 016
    ohne `deleted_at`. Nach deren Integration: letzte Referenz löschen,
    wiederherstellen und verbleibende aktive Mehrfachreferenz prüfen.
13. Regressionstests für `receipt check/open` und endungslose Referenzen bleiben grün.

## Dokumentation und Veröffentlichung

Bei Implementierung prüfen und aktualisieren:

- `docs/USER_GUIDE.md`: Command, Scanumfang, Zahlungsjahr, Exit-Codes und Ausgabeformate.
- `docs/skills/euer-buchhaltung/SKILL.md`: zuerst bestehende Buchungen und Ablage
  prüfen, danach zuordnen oder neu buchen; Fehler und Warnungen auswerten.
- `docs/templates/onboarding-prompt.md` sowie betroffene Agenten-Templates:
  Ablage im Zahlungsjahr und Abschlussprüfungen konsistent beschreiben.
- `README.md` und `DEVELOPMENT.md`: Funktionsübersicht; Spec-Status nach Umsetzung.
- `docs/RELEASE_NOTES.md`: unter „Unveröffentlicht“ oder der nächsten geplanten
  Version dokumentieren, keine Ergänzung bereits veröffentlichter Abschnitte.

Der neue Command ist ein abwärtskompatibles Feature und benötigt bei
Veröffentlichung einen MINOR-Release. Für Spec 017 allein sind keine DB- oder
Konfigurationsmigrationen erforderlich. Eine spätere Soft-Delete-Migration wird
separat durch Spec 016 beschrieben. Diese reine Spec-Überarbeitung erfordert
keinen Versionsbump und keinen eigenen Release.
