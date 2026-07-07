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
abgeloest. Alte Configs muessen nicht kompatibel bleiben; die Migration soll
aber klar dokumentiert und fuer bestehende lokale Instanzen einfach sein.

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

Das passt zu `Typ/Jahr`, aber nicht zu einer natuerlichen Jahresablage. Fuer
persoenliche Buchhaltung ist `Jahr/Typ` praktischer:

- alle Unterlagen eines Steuerjahres liegen beieinander
- Ausgaben, Einnahmen, Kontoauszuege und Exporte koennen pro Jahr gebuendelt
  werden
- Archivierung und Weitergabe an Steuerberatung/Finanzamt sind einfacher
- das Onboarding fragt bereits nach der Ordnerstruktur, aber die Runtime nutzt
  diese Information aktuell nicht

## Produktentscheidung

Die neue Standardstruktur ist:

```text
<receipts.root>/<year>/<receipts.expenses_dir>/<receipt_name>
<receipts.root>/<year>/<receipts.income_dir>/<receipt_name>
```

Standardwerte:

```toml
[receipts]
root = "/pfad/zu/Buchhaltung"
layout = "year_type"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"
```

`layout` wird in der ersten Version nur mit dem Wert `"year_type"` unterstuetzt.
Das Feld bleibt bewusst in der Config, damit spaeter weitere Layouts oder
Templates ergaenzt werden koennen, ohne die Config-Struktur erneut umzubauen.

Die alten Keys `receipts.expenses` und `receipts.income` werden nicht mehr als
primaere Runtime-Konfiguration verwendet. Wenn sie vorhanden sind, soll `euer`
eine klare Fehlermeldung bzw. Migrationshilfe ausgeben, statt stillschweigend
alte Pfade zu pruefen.

## Nicht-Ziele

- keine automatische Dateiindexierung ueber den gesamten Beleg-Root
- keine heuristische Suche in beliebigen Unterordnern
- keine automatische Migration durch Verschieben von Nutzerdateien
- keine Speicherung vollstaendiger Belegpfade in `expenses.receipt_name` oder
  `income.receipt_name`
- keine Rueckwaertskompatibilitaet fuer alte Configs als harte Anforderung

## Config-Design

### Neue Config

```toml
[receipts]
root = "/Users/max/Dropbox/Buchhaltung"
layout = "year_type"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"
```

Semantik:

| Key | Pflicht | Default | Bedeutung |
|-----|---------|---------|-----------|
| `receipts.root` | ja | leer | Gemeinsamer Root fuer Belegablage |
| `receipts.layout` | nein | `year_type` | Ordnerlayout; zunaechst nur `year_type` |
| `receipts.expenses_dir` | nein | `Ausgaben` | Typ-Unterordner fuer Ausgaben |
| `receipts.income_dir` | nein | `Einnahmen` | Typ-Unterordner fuer Einnahmen |

Leerer `receipts.root` bedeutet: Belegpruefung ist nicht konfiguriert.

### Migration alter Config

Alte Config:

```toml
[receipts]
expenses = "/Users/max/Dropbox/Buchhaltung/Ausgaben"
income = "/Users/max/Dropbox/Buchhaltung/Einnahmen"
```

Neue Config:

```toml
[receipts]
root = "/Users/max/Dropbox/Buchhaltung"
layout = "year_type"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"
```

Wenn alte Keys erkannt werden und `root` fehlt, sollen betroffene Commands
ausgeben:

```text
Fehler: Alte Beleg-Konfiguration erkannt.
Bitte migriere [receipts] auf root/layout/expenses_dir/income_dir.
Beispiel:
  receipts.root = "/pfad/zu/Buchhaltung"
  receipts.layout = "year_type"
  receipts.expenses_dir = "Ausgaben"
  receipts.income_dir = "Einnahmen"
```

## Pfad-Aufloesung

`resolve_receipt_path(receipt_name, date, receipt_type, config)` bleibt die
zentrale API fuer Commands und spaetere Berichte.

Regeln:

1. `receipt_type` ist weiterhin `"expenses"` oder `"income"`.
2. Das Jahr wird aus `invoice_date` bevorzugt, sonst aus `payment_date`
   abgeleitet. Die aufrufenden Commands uebergeben bereits dieses Datum.
3. Fuer `receipt_type = "expenses"` wird `expenses_dir` genutzt, fuer
   `"income"` `income_dir`.
4. Wenn `receipt_name` keine Dateiendung hat, werden wie bisher `.pdf`, `.jpg`,
   `.jpeg` und `.png` versucht.
5. Gepruefte Kandidaten werden in stabiler Reihenfolge zurueckgegeben.
6. Es wird nicht mehr automatisch `<base>/<Belegname>` geprueft.

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
- neue Helper fuer die Beleg-Konfiguration, z.B.
  `get_receipt_config(config)` oder `get_receipt_root(config)`
- Validierung von `receipts.layout`
- Erkennung alter Keys `receipts.expenses` / `receipts.income`

Die Helper sollen keine `print()`-Ausgaben erzeugen. Deutsche Fehlermeldungen
gehoeren in die Commands oder in Exceptions, die dort uebersetzt werden.

### `euercli/commands/setup.py`

Interaktives Setup:

- nicht mehr getrennt nach "Beleg-Pfad fuer Ausgaben" und
  "Beleg-Pfad fuer Einnahmen" fragen
- stattdessen fragen:
  - `Beleg-Root`
  - `Ausgaben-Unterordner` mit Default `Ausgaben`
  - `Einnahmen-Unterordner` mit Default `Einnahmen`
- `receipts.layout = "year_type"` setzen

`setup --set`:

- neue Keys akzeptieren:
  - `receipts.root`
  - `receipts.layout`
  - `receipts.expenses_dir`
  - `receipts.income_dir`
- alte Keys `receipts.expenses` und `receipts.income` mit klarer Fehlermeldung
  ablehnen oder als deprecated markieren und nicht fuer Runtime-Suche nutzen

### `euercli/commands/receipt.py`

Anpassen:

- `receipt check` muss `receipts.root` als Konfigurationsvoraussetzung nutzen
- Fehler bei fehlender oder alter Config auf neue Struktur beziehen
- die ausgegebenen fehlenden Pfade muessen `Jahr/Typ` zeigen

### `euercli/commands/add.py` und `euercli/commands/update.py`

Keine Business-Logik-Aenderung, aber Warnungen nach `--receipt` muessen ueber
die neue Pfad-Aufloesung laufen.

### `euercli/commands/config.py`

Falls `config show` Strukturhinweise ausgibt, muessen sie die neuen Keys zeigen
und alte Keys als migrationsbeduerftig markieren.

### `euercli/commands/report.py` aus Spec 014

Der HTML-Pruefbericht soll fuer Beleglinks dieselbe `resolve_receipt_path()`-API
verwenden. Die Umsetzung von Spec 014 darf keine eigene Pfadlogik einfuehren.

## Tests

Neue bzw. geaenderte Tests in `tests/test_cli.py` oder fokussierten
Service-/Config-Tests:

1. `setup` schreibt neue Keys `root`, `layout`, `expenses_dir`, `income_dir`.
2. `setup --set receipts.root ...` normalisiert `~` und Quotes wie bisher.
3. `receipt check` findet einen Ausgabenbeleg unter
   `<root>/2026/Ausgaben/<name>.pdf`.
4. `receipt check` findet einen Einnahmenbeleg unter
   `<root>/2026/Einnahmen/<name>.pdf`.
5. `receipt check` findet Belege ohne angegebene Endung weiterhin ueber
   `.pdf/.jpg/.jpeg/.png`.
6. `receipt check` meldet bei fehlendem Beleg die neuen Kandidatenpfade.
7. Alte Config mit nur `receipts.expenses`/`receipts.income` erzeugt eine
   deutsche Migrationsmeldung und keinen stillen Fallback.
8. `receipt open` verwendet dieselbe neue Pfadlogik.
9. `warn_missing_receipt()` nach `add expense --receipt ...` zeigt neue
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
- `DEVELOPMENT.md` Spec-Tabelle und Funktionsueberblick

Onboarding muss aus Beispielpfaden `Jahr/Typ` ableiten:

```text
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.pdf
```

daraus:

```text
receipts.root = "/Users/max/Dropbox/Buchhaltung"
receipts.layout = "year_type"
receipts.expenses_dir = "Ausgaben"
```

Die generierten Setup-Befehle sollen entsprechend lauten:

```bash
euer setup --set receipts.root "/Users/max/Dropbox/Buchhaltung"
euer setup --set receipts.layout "year_type"
euer setup --set receipts.expenses_dir "Ausgaben"
euer setup --set receipts.income_dir "Einnahmen"
```

## Release Notes / Upgrade

Diese Spec ist eine Config-Breaking-Change fuer alle bestehenden lokalen
Installationen mit Belegpruefung.

Release Notes muessen enthalten:

1. Backup/Pruefung der bestehenden `~/.config/euer/config.toml`.
2. Beispielmigration von `receipts.expenses`/`receipts.income` auf
   `receipts.root`/`layout`/Typ-Unterordner.
3. Hinweis, dass Belegdateien nicht automatisch verschoben werden.
4. Beispielbefehle zum Setzen der neuen Config.
5. Pruefbefehl nach der Migration:

```bash
euer receipt check --year 2026
```

## Akzeptanzkriterien

- `euer setup` erzeugt standardmaessig eine `Jahr/Typ`-Config.
- `euer receipt check --year 2026` findet Belege unter
  `<root>/2026/Ausgaben` und `<root>/2026/Einnahmen`.
- `euer receipt open <ID>` oeffnet Belege aus der neuen Struktur.
- Warnungen nach `add`/`update` nennen die neue Struktur.
- Alte `receipts.expenses`/`receipts.income`-Configs werden nicht still
  weiterverwendet, sondern mit Migrationshinweis behandelt.
- Doku, Onboarding und Skill beschreiben `Jahr/Typ` konsistent als Standard.
- Alle Tests laufen gruen mit `python -m unittest discover -s tests`.

## Verwandte Specs

- Spec 002: Beleg-Management
- Spec 006: Rechnungs-/Wertstellungsdatum
- Spec 014: HTML-Pruefbericht fuer Buchungen
