# Spec 013: Belegordner Jahr zuerst

## Status

Offen

## Ziel

`euer` soll Belege kanonisch in einer jahrzentrierten Ordnerstruktur finden:

```text
<beleg-root>/<Jahr>/<Typ>/<Belegname>
```

Beispiel:

```text
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.pdf
/Users/max/Dropbox/Buchhaltung/2026/Einnahmen/2026-01-20_Rechnung_001.pdf
```

Die bisherige Annahme `Ausgaben/<Jahr>/...` bzw. `Einnahmen/<Jahr>/...` wird
abgelöst. Die Config muss zukünftig der neuen Struktur entsprechen.

## Motivation

Die aktuelle Implementierung speichert getrennte Basis-Pfade:

```toml
[receipts]
expenses = "/.../Ausgaben"
income = "/.../Einnahmen"
```

`resolve_receipt_path()` sucht daraus nur:

```text
<expenses>/<Jahr>/<Belegname>
<expenses>/<Belegname>
```

Das passt zu `Typ/Jahr`, aber nicht zu einer natürlichen Jahresablage. Für
persönliche Buchhaltung ist `Jahr/Typ` praktischer:

- alle Unterlagen eines Steuerjahres liegen beieinander
- Ausgaben, Einnahmen, Kontoauszüge und Exporte können pro Jahr gebündelt
  werden
- Archivierung und Weitergabe an Steuerberatung/Finanzamt sind einfacher
- das Onboarding fragt bereits nach der Ordnerstruktur, aber die Runtime nutzt
  diese Information aktuell nicht

## Produktentscheidung

Die neue Standardstruktur ist:

```text
<receipts.root>/<receipts.year_dir>/<receipts.expenses_dir>/<receipt_name>
<receipts.root>/<receipts.year_dir>/<receipts.income_dir>/<receipt_name>
```

Standardwerte:

```toml
[receipts]
root = "/pfad/zu/Buchhaltung"
year_dir = "{year}"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"
```

`year_dir` ist ein Format-String für den Jahresordner. Er muss den Platzhalter
`{year}` enthalten. Damit sind neben einfachen Jahresordnern auch Strukturen wie
`"Buchhaltung {year}"`, `"Steuer {year}"` oder `"{year} Unterlagen"` möglich.

## Nicht-Ziele

- keine automatische Dateiindexierung über den gesamten Beleg-Root
- keine heuristische Suche in beliebigen Unterordnern
- keine automatische Migration durch Verschieben von Nutzerdateien
- keine Speicherung vollständiger Belegpfade in `expenses.receipt_name` oder
  `income.receipt_name`

## Config-Design

### Neue Config

```toml
[receipts]
root = "/Users/max/Dropbox/Buchhaltung"
year_dir = "{year}"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"
```

Semantik:

| Key | Pflicht | Default | Bedeutung |
|-----|---------|---------|-----------|
| `receipts.root` | ja | leer | Gemeinsamer Root für Belegablage |
| `receipts.year_dir` | nein | `{year}` | Format des Jahresordners |
| `receipts.expenses_dir` | nein | `Ausgaben` | Typ-Unterordner für Ausgaben |
| `receipts.income_dir` | nein | `Einnahmen` | Typ-Unterordner für Einnahmen |

Leerer `receipts.root` bedeutet: Belegprüfung ist nicht konfiguriert.
`receipts.year_dir` muss den Platzhalter `{year}` enthalten. Ungültige
Jahresordner-Patterns sollen als Config-Fehler behandelt werden, weil sonst
Belege still in falschen Jahren gesucht werden können.

Beispiele:

| `year_dir` | Ergebnis für 2026 |
|------------|--------------------|
| `{year}` | `2026` |
| `Buchhaltung {year}` | `Buchhaltung 2026` |
| `Steuer {year}` | `Steuer 2026` |
| `{year} Unterlagen` | `2026 Unterlagen` |

## Pfad-Auflösung

`resolve_receipt_path(receipt_name, date, receipt_type, config)` bleibt die
zentrale API für Commands und spätere Berichte.

Regeln:

1. `receipt_type` ist weiterhin `"expenses"` oder `"income"`.
2. Das Jahr für den Ordner wird aus `payment_date` abgeleitet. Das entspricht
   dem Zufluss-/Abflussprinzip der Einnahmenüberschussrechnung: Für die
   Jahreszuordnung ist der Zahlungsfluss maßgeblich, nicht das Rechnungsdatum.
3. Wenn `payment_date` fehlt, kann `resolve_receipt_path()` keinen
   jahresbezogenen Pfad sicher ableiten. Commands mit explizitem Jahreskontext
   dürfen dieses Jahr als Fallback übergeben; andernfalls sollen keine
   Kandidatenpfade geraten werden.
4. `year_dir` wird mit dem abgeleiteten Jahr formatiert.
5. Für `receipt_type = "expenses"` wird `expenses_dir` genutzt, für
   `"income"` `income_dir`.
6. Wenn `receipt_name` keine Dateiendung hat, werden wie bisher `.pdf`, `.jpg`,
   `.jpeg` und `.png` versucht.
7. Geprüfte Kandidaten werden in stabiler Reihenfolge zurückgegeben.
8. Es wird nicht mehr automatisch `<base>/<Belegname>` geprüft.

Beispiel-Kandidaten:

```text
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.pdf
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.jpg
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.jpeg
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.png
```

Hinweis zur Reihenfolge: Wenn keine Endung angegeben wurde, kann die exakte
Namensvariante zuerst bleiben. Danach folgen die bekannten Erweiterungen.

## Betroffene Implementierung

### `euercli/config.py`

Anpassen:

- `resolve_receipt_path()`
- `warn_missing_receipt()`
- neue Helper für die Beleg-Konfiguration, z.B.
  `get_receipt_config(config)` oder `get_receipt_root(config)`
- Validierung von `receipts.year_dir`

Die Helper sollen keine `print()`-Ausgaben erzeugen. Deutsche Fehlermeldungen
gehören in die Commands oder in Exceptions, die dort übersetzt werden.

### `euercli/commands/setup.py`

Interaktives Setup:

- nicht mehr getrennt nach "Beleg-Pfad für Ausgaben" und
  "Beleg-Pfad für Einnahmen" fragen
- stattdessen fragen:
  - `Beleg-Root`
  - `Jahresordner-Format` mit Default `{year}`
  - `Ausgaben-Unterordner` mit Default `Ausgaben`
  - `Einnahmen-Unterordner` mit Default `Einnahmen`

`setup --set`:

- neue Keys akzeptieren:
  - `receipts.root`
  - `receipts.year_dir`
  - `receipts.expenses_dir`
  - `receipts.income_dir`

### `euercli/commands/receipt.py`

Anpassen:

- `receipt check` muss `receipts.root` als Konfigurationsvoraussetzung nutzen
- Fehler bei fehlender Config auf neue Struktur beziehen
- die ausgegebenen fehlenden Pfade müssen `Jahr/Typ` zeigen

### `euercli/commands/add.py` und `euercli/commands/update.py`

Keine Business-Logik-Änderung, aber Warnungen nach `--receipt` müssen über
die neue Pfad-Auflösung laufen.

### `euercli/commands/config.py`

Falls `config show` Strukturhinweise ausgibt, müssen sie die neuen Keys zeigen.

## Tests

Neue bzw. geänderte Tests in `tests/test_cli.py` oder fokussierten
Service-/Config-Tests:

1. `setup` schreibt neue Keys `root`, `year_dir`, `expenses_dir`, `income_dir`.
2. `setup --set receipts.root ...` normalisiert `~` und Quotes wie bisher.
3. `setup --set receipts.year_dir "Buchhaltung {year}"` validiert und speichert
   das Pattern.
4. `receipt check` findet einen Ausgabenbeleg unter
   `<root>/2026/Ausgaben/<name>.pdf`.
5. `receipt check` findet einen Einnahmenbeleg unter
   `<root>/2026/Einnahmen/<name>.pdf`.
6. `receipt check` findet einen Beleg unter
   `<root>/Buchhaltung 2026/Ausgaben/<name>.pdf`, wenn
   `year_dir = "Buchhaltung {year}"` gesetzt ist.
7. `receipt check` findet Belege ohne angegebene Endung weiterhin über
   `.pdf/.jpg/.jpeg/.png`.
8. `receipt check` meldet bei fehlendem Beleg die neuen Kandidatenpfade.
9. Bei fehlendem `payment_date` wird für die Pfad-Auflösung kein
    Rechnungsdatum als Jahresersatz verwendet.
10. `receipt open` verwendet dieselbe neue Pfadlogik.
11. `warn_missing_receipt()` nach `add expense --receipt ...` zeigt neue
   Kandidatenpfade.

## Dokumentation

Bei Implementierung aktualisieren:

- `docs/USER_GUIDE.md`
- `docs/skills/euer-buchhaltung/SKILL.md`
- `docs/templates/onboarding-prompt.md`
- `docs/templates/accountant-agent.md`
- `docs/templates/Agents-Template.md`
- `docs/RELEASE_NOTES.md`
- `README.md`, falls Schnellstart oder Beispiele Belegpfade nennen
- `DEVELOPMENT.md` Spec-Tabelle und Funktionsüberblick

Onboarding muss aus Beispielpfaden `Jahr/Typ` ableiten:

```text
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.pdf
```

daraus:

```text
receipts.root = "/Users/max/Dropbox/Buchhaltung"
receipts.year_dir = "{year}"
receipts.expenses_dir = "Ausgaben"
```

Die generierten Setup-Befehle sollen entsprechend lauten:

```bash
euer setup --set receipts.root "/Users/max/Dropbox/Buchhaltung"
euer setup --set receipts.year_dir "{year}"
euer setup --set receipts.expenses_dir "Ausgaben"
euer setup --set receipts.income_dir "Einnahmen"
```

## Release Notes / Upgrade

Diese Spec ist eine Config-Breaking-Change für alle bestehenden lokalen
Installationen mit Belegprüfung.

Release Notes müssen enthalten:

1. Backup/Prüfung der bestehenden `~/.config/euer/config.toml`.
2. Beispiel für die neue `[receipts]`-Config mit
   `receipts.root`/`year_dir`/Typ-Unterordner.
3. Hinweis, dass Belegdateien nicht automatisch verschoben werden.
4. Beispielbefehle zum Setzen der neuen Config.
5. Prüfbefehl nach der Migration:

```bash
euer receipt check --year 2026
```

## Akzeptanzkriterien

- `euer setup` erzeugt standardmäßig eine `Jahr/Typ`-Config mit
  `year_dir = "{year}"`.
- `euer receipt check --year 2026` findet Belege unter
  `<root>/2026/Ausgaben` und `<root>/2026/Einnahmen`.
- `year_dir = "Buchhaltung {year}"` wird korrekt zu
  `<root>/Buchhaltung 2026/...` aufgelöst.
- Das Jahr für Belegpfade basiert auf `payment_date`; `invoice_date` wird nicht
  als Jahresgrundlage für Belegordner bevorzugt.
- `euer receipt open <ID>` öffnet Belege aus der neuen Struktur.
- Warnungen nach `add`/`update` nennen die neue Struktur.
- Doku, Onboarding und Skill beschreiben `Jahr/Typ` konsistent als Standard.
- Alle Tests laufen grün mit `python -m unittest discover -s tests`.

## Verwandte Specs

- Spec 002: Beleg-Management
- Spec 006: Rechnungs-/Wertstellungsdatum
