# Spec 011: Reverse-Charge-Jurisdiktion (EU vs. Drittland)

## Status

Offen

## Motivation

`euer` speichert Reverse-Charge-Ausgaben aktuell nur als boolesches Flag `is_rc`.
Damit lässt sich zwar die bestehende Steuerlogik aus Spec 004 anwenden, aber nicht
sauber unterscheiden, ob eine Leistung für die USt-Voranmeldung in:

- **KZ 46 / 47** als Leistung aus dem übrigen Gemeinschaftsgebiet oder
- **KZ 84 / 85** als andere Leistung aus einem Drittland

einzuordnen ist.

Für Nutzer führt das heute zu manueller Nacharbeit:

1. RC-Buchungen einzeln prüfen
2. Anbieter steuerlich als EU oder nicht-EU einordnen
3. Beträge manuell auf ELSTER-Kennzahlen verteilen

Das ist fehleranfällig, nicht gut auditierbar und blockiert Spec 012
(`vat-report`).

## Fachliche Entscheidung

### Ziel dieser Spec

Diese Spec ergänzt RC-Ausgaben um eine **persistierte Jurisdiktion**. Sie dient
der späteren UVA-Auswertung und verbessert die Nachvollziehbarkeit bestehender
RC-Buchungen.

### Was genau gespeichert wird

Für RC-Ausgaben wird gespeichert, ob die Leistung steuerlich aus:

- `eu` kommt oder
- `third_country` kommt

`third_country` bedeutet in dieser Spec ausdrücklich: **steuerlich nicht EU**.
Die Anwendung leitet diese Zuordnung nicht selbst aus Land oder Anbieter ab; der
Anwender muss die korrekte Auswahl treffen.

### Was diese Spec bewusst nicht tut

- Sie entscheidet **nicht**, ob ein Vorgang überhaupt Reverse Charge ist.
  Das bleibt eine separate Nutzerentscheidung über `--rc`.
- Sie implementiert **nicht** die vollständige UVA-Ausgabe. Das ist Aufgabe von
  Spec 012.

## ELSTER-Bezug

| Jurisdiktion | Bedeutung | ELSTER |
|---|---|---|
| `eu` | Sonstige Leistung eines im übrigen Gemeinschaftsgebiet ansässigen Unternehmers | KZ 46 / 47 |
| `third_country` | Andere Leistung aus steuerlich nicht-EU | KZ 84 / 85 |

## Geltungsbereich

- Betrifft **nur `expenses`**
- Betrifft **nur Buchungen mit `is_rc = 1`**
- Betrifft `add expense`, `update expense`, `import`, `list`, `export`, `summary`
- Ist Voraussetzung für Spec 012 (`vat-report`)

`income` ist nicht betroffen.

## Anforderungen

### A1: Datenmodell

Die Tabelle `expenses` erhält eine neue nullable Spalte:

```sql
rc_jurisdiction TEXT
    CHECK(rc_jurisdiction IN ('eu', 'third_country'))
```

Regeln:

- `NULL` ist ausschließlich der Legacy-/Unvollständigkeitszustand.
- Für **neu angelegte** RC-Buchungen ist `NULL` nicht erlaubt.
- Für bestehende Altbestände bleibt `NULL` zulässig, damit keine Pflichtmigration
  nötig ist.
- Für Nicht-RC-Buchungen (`is_rc = 0`) soll `rc_jurisdiction` immer `NULL` sein.
- Neue Datenbanken sollen zusätzlich per Schema absichern:

```sql
CHECK(is_rc = 1 OR rc_jurisdiction IS NULL)
```

Für bestehende Datenbanken reicht die Service-Layer-Invariante. `euer init`
ergänzt nur die Spalte und erzwingt keine vollständige Tabellenmigration.

### A2: Service-Modelle

`Expense` in `euercli/services/models.py` wird um `rc_jurisdiction: str | None`
erweitert.

Alle Service-Funktionen, die Ausgaben lesen oder zurückgeben, liefern diesen Wert
mit aus.

### A3: `add expense`

Das CLI wird um ein neues Flag erweitert:

```bash
euer add expense --rc --rc-jurisdiction eu
euer add expense --rc --rc-jurisdiction third-country
```

CLI-Regeln:

- `--rc` bleibt ein boolesches Flag.
- `--rc-jurisdiction` ist ein eigenes Flag.
- Erlaubte CLI-Werte:
  - `eu`
  - `third-country`
- Intern wird `third-country` als `third_country` gespeichert.
- Fehler werden wie bei bestehenden Commands als deutsche Meldung auf `stderr`
  ausgegeben.

Validierung:

- `--rc` **ohne** `--rc-jurisdiction` ist ein Fehler.
- `--rc-jurisdiction` **ohne** `--rc` ist ein Fehler.
- Bei erfolgreicher RC-Anlage muss `rc_jurisdiction` persistiert werden.
- Bei Nicht-RC-Buchungen darf kein Jurisdiktionswert gespeichert werden.

Begründung:

Die explizite Form `--rc --rc-jurisdiction ...` ist klarer und belastbarer als
ein überladenes `--rc eu`.

### A4: `update expense`

Das Update-CLI wird symmetrisch erweitert:

```bash
euer update expense 42 --rc --rc-jurisdiction eu
euer update expense 42 --rc-jurisdiction third-country
euer update expense 42 --no-rc
```

Neue Flags:

- `--rc`
- `--no-rc`
- `--rc-jurisdiction`

Regeln:

- `--rc` und `--no-rc` sind gegenseitig exklusiv.
- Wird eine Buchung auf Nicht-RC gesetzt (`--no-rc`), muss
  `rc_jurisdiction` auf `NULL` zurückgesetzt werden.
- Wird eine Buchung von Nicht-RC auf RC umgestellt, muss in demselben Aufruf
  eine Jurisdiktion angegeben werden.
- Bestehende Legacy-RC-Buchungen mit `NULL` dürfen weiterhin in anderen Feldern
  bearbeitet werden; sie werden nicht blockiert.
- Legacy-RC-Buchungen müssen per `update expense --rc-jurisdiction ...`
  nachklassifiziert werden können.
- `--rc-jurisdiction` ohne `--rc` ist erlaubt, wenn die bestehende Buchung
  bereits RC ist. Dadurch bleibt die Nachpflege kurz und verständlich.
- `--rc-jurisdiction` ohne `--rc` ist ein Fehler, wenn die bestehende Buchung
  keine RC-Buchung ist.
- Es gibt kein separates `--clear-rc-jurisdiction`. Der Wert wird ausschließlich
  durch `--no-rc` entfernt. Das vermeidet ein redundantes Flag, weil eine aktive
  RC-Buchung fachlich nicht bewusst "ohne Jurisdiktion" gesetzt werden soll.

Implementierungshinweis:

- `update_expense()` braucht für RC ein Tri-State-Signal:
  - `is_rc=True`: RC explizit setzen
  - `is_rc=False`: RC explizit entfernen
  - `is_rc=None`: RC unverändert lassen

### A5: Service-Layer-Validierung

`create_expense()` und `update_expense()` werden um `rc_jurisdiction` erweitert.

Die Validierung erfolgt ausschließlich im Service Layer.

Mindestregeln:

- Wenn `is_rc = True`, muss `rc_jurisdiction` für **neue RC-Erfassungen**
  gesetzt sein.
- Wenn `is_rc = False`, muss `rc_jurisdiction = None` sein.
- Nur `eu` und `third_country` sind zulässige persistierte Werte.
- CLI und Import dürfen keine abweichenden Varianten direkt in die DB schreiben.
- Für Updates darf eine bestehende Legacy-RC-Buchung mit
  `rc_jurisdiction = NULL` unverändert bleiben, solange der Aufruf RC nicht neu
  aktiviert.
- Wird bei einem Update `is_rc=False` gesetzt, wird `rc_jurisdiction` immer auf
  `NULL` normalisiert.
- Wird bei einem Update nur `rc_jurisdiction` gesetzt, gilt das als
  Nachklassifizierung einer bereits aktiven RC-Buchung.

Empfohlene Fehlerfälle:

- `rc_jurisdiction_required`
- `rc_jurisdiction_without_rc`
- `invalid_rc_jurisdiction`

### A6: Import

Der Import wird um `rc_jurisdiction` erweitert.

Akzeptierte Import-Feldnamen:

- `rc_jurisdiction`
- `rc-jurisdiction`
- `RC-Jurisdiktion`

Akzeptierte Werte:

- `eu`
- `third-country`
- `third_country`

Regeln:

- `rc=true` ohne Jurisdiktion ist ein Fehler.
- Jurisdiktion ohne `rc=true` ist ein Fehler.
- Importierte Werte werden auf die persistierten DB-Werte normalisiert.
- Importfehler sollen zeilenbezogen gemeldet werden und den Import wie andere
  Pflichtfeldfehler vollständig abbrechen.

### A7: List- und Export-Ausgabe

Die neue Information muss sichtbar und round-trip-fähig sein.

Deshalb:

- `list expenses --format csv` erhält eine zusätzliche Spalte
  `RC-Jurisdiktion`
- Tabellenansichten mit RC-Details sollen die Jurisdiktion ebenfalls anzeigen,
  wenn RC-relevante Spalten angezeigt werden
- `export` für Ausgaben erhält eine zusätzliche Spalte `RC-Jurisdiktion`
- Der CSV-Export muss weiterhin direkt wieder importierbar sein
- CSV- und Export-Ausgaben verwenden nutzerfreundliche Werte:
  - `eu`
  - `third-country`
- Leere Werte bleiben leer. Legacy-RC-Buchungen mit `NULL` werden nicht
  automatisch interpretiert.

### A8: `summary`

`summary` bleibt **kein** UVA-Report und führt in dieser Spec keine neue
KZ-Aufteilung ein.

Neu ist nur eine Warnung:

- Wenn im betrachteten Jahr RC-Buchungen mit `rc_jurisdiction IS NULL`
  existieren, gibt `summary` einen Hinweis aus.
- Die bestehende Steuerberechnung aus Spec 004 bleibt unverändert.

Beispiel:

```text
Hinweis: 3 Reverse-Charge-Buchung(en) ohne Jurisdiktion.
  → Für die spätere USt-Voranmeldung bitte per `euer update expense <ID> --rc-jurisdiction ...` nachpflegen.
```

Die eigentliche Zuordnung zu KZ 46/47 bzw. KZ 84/85 erfolgt erst in Spec 012.

### A9: Migration / Initialisierung

Es gibt **kein** separates Kommando `euer migrate rc-jurisdiction`.

Stattdessen:

- `euer init` ergänzt die neue Spalte bei bestehenden Datenbanken
- bestehende RC-Buchungen behalten zunächst `rc_jurisdiction = NULL`
- Nachpflege erfolgt über `update expense`

Diese Entscheidung hält den Scope klein und vermeidet ein separates
Migrations-UI.

## UX- und Konsistenzregeln

### Legacy-Verhalten

Altbestände mit `is_rc = 1` und `rc_jurisdiction = NULL` bleiben:

- gültig lesbar
- exportierbar
- in `summary` warnbar
- manuell nachpflegbar

Sie sollen aber **nicht** stillschweigend als `eu` oder `third_country`
interpretiert werden.

### Persistenz vor Konfiguration

Die Jurisdiktion wird direkt an der Buchung gespeichert, nicht in externer
Konfiguration aufgelöst. Dadurch bleiben historische Daten stabil.

## Implementierungshinweise

Betroffene Dateien:

| Datei | Änderung |
|---|---|
| `euercli/schema.py` | Neue Spalte `rc_jurisdiction` in `expenses` |
| `euercli/commands/init.py` | Migration bestehender DBs |
| `euercli/services/models.py` | Feld in `Expense` |
| `euercli/services/expenses.py` | Persistenz, Validierung, Row-Mapping |
| `euercli/cli.py` | Neue Flags für Add/Update |
| `euercli/commands/add.py` | CLI-Weitergabe, User-Fehlertexte |
| `euercli/commands/update.py` | CLI-Weitergabe, `--rc`/`--no-rc`-Logik |
| `euercli/importers.py` | Alias-Parsing und Normalisierung |
| `euercli/commands/import_data.py` | Import-Validierung |
| `euercli/commands/list.py` | Anzeige |
| `euercli/commands/export.py` | Export-Spalte |
| `euercli/commands/summary.py` | Legacy-Warnhinweis |

## Testfälle

Mindestens abzudecken:

1. `add expense --rc` ohne Jurisdiktion schlägt fehl
2. `add expense --rc --rc-jurisdiction eu` speichert korrekt
3. `add expense --rc-jurisdiction eu` ohne `--rc` schlägt fehl
4. `update expense --no-rc` entfernt `rc_jurisdiction`
5. `update expense --rc-jurisdiction eu` auf Nicht-RC-Buchung schlägt fehl
6. Legacy-RC-Buchung mit `NULL` bleibt bearbeitbar
7. `update expense --rc-jurisdiction third-country` klassifiziert Legacy-RC nach
8. Import mit `rc=true` und fehlender Jurisdiktion schlägt fehl
9. Export enthält `RC-Jurisdiktion` mit `third-country` und bleibt re-importierbar
10. `summary` warnt bei RC-Buchungen ohne Jurisdiktion
11. `euer init` ergänzt `rc_jurisdiction` bei bestehenden Datenbanken

## Nicht im Scope

- Automatische Erkennung der Jurisdiktion aus Anbietername, Land oder Domain
- Vollständige USt-Voranmeldungsausgabe
- Länder- oder Steuerrechts-Engine jenseits der zwei Klassifikationen `eu` und
  `third_country`

## Verwandte Specs

- Spec 004: Steuerlogik (KU/Standard)
- Spec 012: `vat-report`
