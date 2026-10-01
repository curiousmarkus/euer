# DATEV-Export und Kanzleiübergabe (`euer-datev`)

Das optionale Add-on erzeugt einen EXTF-700-Buchungsstapel für SKR 03 oder 04 und auf Wunsch ein ZIP mit Belegen und `PRUEFPROTOKOLL.txt`. Import und steuerliche Wirkung sind in der Zielversion der Kanzlei zu prüfen.

## Installation und Diagnose

Bei getrennter pipx-Installation müssen beide Programme im `PATH` liegen:

```bash
pipx install euer
pipx install euer-datev
euer datev --help
euer datev doctor --year 2026 --format json
```

Eine gemeinsame pipx-Installation per `pipx inject euer euer-datev` nutzt das Plugin. Das Plugin hat Vorrang, wenn zusätzlich ein externes `euer-datev` im `PATH` liegt. Homebrew verwendet `curiousmarkus/euer/euer` und `curiousmarkus/euer/euer-datev`. Bei uv lautet der gemeinsame Weg `uv tool install --with euer-datev euer`. `uv` ist ein Installationswerkzeug, kein eigenes DATEV-Programm.

`euer doctor` meldet die Erkennung des optionalen Add-ons. Die fachliche Diagnose liefert `euer datev doctor`; sie zeigt Config-Herkunft, DB und Schema, Steuermodus, Belegroot, fehlende Stammdaten, Kontenzuordnungen und Lizenzabdeckung für das angefragte Jahr. Sie gibt keinen Lizenzschlüssel aus. Informationsbefehle benötigen keine eingerichtete DB.

## Einrichtung

`euer datev init-skr --skr 03` zeigt eine Vorlage. Nach Prüfung übernimmt `euer datev init-skr --skr 03 --write PFAD` sie atomar in eine Config. Wiederholtes Schreiben erhält individuelle Zuordnungen und fremde Tabellen. Beispiel für **eigene, bestätigte** Werte:

```toml
[datev]
berater_nummer = "2222"
mandanten_nummer = "33333"
mandanten_name = "Beispielbetrieb"
skr = "03"

[datev.accounts]
"Geschäftskonto" = "1200"
"Barkasse" = "1000"
```

Nummern und Namen sind Beispiele. Die tatsächlichen Daten stammen von der Kanzlei und aus dem Mandantenkontext. `[datev.accounts]` ist der kanonische Abschnitt für Zahlungskonten. Bestands-Aliase werden gelesen und Konflikte gemeldet. Ohne `--config` werden globale Einstellungen und Projektwerte feldweise zusammengeführt; Projektwerte haben Vorrang. Ein explizites `--config PFAD` ist eine vollständige alternative Config. Befehlsargumente haben die höchste Priorität. Globale relative Belegpfade beziehen sich weiterhin auf den Arbeitsordner, Projektpfade auf den Projektroot, Pfade einer expliziten Datei auf deren Dateiordner. `doctor` zeigt die absoluten Resultate.

## Prüfen und exportieren

1. `euer datev doctor --year 2026 --format json` ausführen und fehlende Stammdaten, Konto- und Belegpfade klären.
2. `euer datev validate --year 2026 --format json` ausführen. Unterjährig sind `--month`, `--quarter`, `--from-date` und `--to-date` verfügbar. Dieselben Filter und Overrides anschließend beim Export verwenden. `--db` und `--config` sind vor oder nach dem Unterbefehl möglich; Pfade mit Leerzeichen als ein Argument übergeben.
3. Bei `ready` mit `euer datev export --year 2026 --format zip --report-format json -o DATEV_EXTF_2026.zip` exportieren.
4. JSON-Bericht, CSV-Zeilen und tatsächliche ZIP-Mitglieder prüfen. Kanzleidaten, Konten, Soll/Haben, Steuerfälle, Beträge und Belege mit den Quelldaten abgleichen und offene Punkte benennen.

`validate` schreibt keine Exportdatei. `export --format csv` erzeugt nur den Buchungsstapel. `export --format zip` erzeugt zusätzlich gefundene Belege und `PRUEFPROTOKOLL.txt`. `--berater`, `--mandant`, `--skr` und `--year` überschreiben die Config für den Aufruf. `--demo` nutzt markierte Beispiel-Kanzleidaten für einen Testexport und macht problematische Vorgänge nicht fachlich gültig. `--force` wird abgewiesen. `--allow-incomplete` akzeptiert ausschließlich dokumentierte Warnungen zu fehlenden Belegen, markiert das Paket als unvollständig und gibt Exit 2. Andere Warnungen und Fehler verhindern den Export.

| Exit | Status | Bedeutung |
| --- | --- | --- |
| 0 | `ready` | Freigegebenes Prüfergebnis oder Export |
| 1 | `invalid` | Fehler; kein freigegebener Export |
| 2 | `needs_review`/`empty` | Offener Prüfbedarf, Teilpaket oder keine Buchungen |

Bei `--format json` für `validate`/`doctor` beziehungsweise `--report-format json` für `export` steht genau ein JSON-Dokument auf stdout. Es enthält `schema_version`, Status, Config-Herkunft, Zeitraum, Quell-IDs, Anzahl Quellvorgänge und DATEV-Zeilen, Summen, Belegstatus, Ausschlüsse, Issues mit Quell-ID und gegebenenfalls Artefaktpfade. Laufzeitfehler haben `error_code` und Exit 1. Falsche CLI-Syntax behandelt `argparse` mit Exit 2 und einer Meldung auf stderr; dann gibt es kein JSON-Dokument. Lizenzhinweise und menschliche Meldungen stehen bei JSON-Ausgabe auf stderr.

Fehlen viele Belege, zuerst `doctor` und den effektiven Belegroot prüfen. Dann die Core-Auflösung im Zahlungsjahr mit `euer receipt check --year 2026` vergleichen. Warnungen sind kein Beweis für verlorene Dateien. Vorgänge ohne Zahlungsdatum werden mit Ausschlussgrund gezeigt; gelöschte und außerhalb des Zeitraums liegende Vorgänge ebenfalls.

## Bericht und Belegübergabe

Ein Quellvorgang kann mehrere DATEV-Zeilen erzeugen, etwa eine Bewirtung mit abziehbarem und nicht abziehbarem Anteil. Der Bericht unterscheidet deshalb Quellvorgänge, DATEV-Zeilen, Quellvolumen, DATEV-Zeilenvolumen und EÜR-Ergebnis. Im synthetischen Kleinunternehmer-Beispiel stehen 56 Quellvorgänge mit 1.240,93 EUR absolutem Quellvolumen 57 DATEV-Zeilen gegenüber: 735,02 EUR Ausgaben, 0,42 EUR Einnahmen, 500,00 EUR Einlage, 5,49 EUR Entnahme. Die 187,96 EUR privat bezahlten Ausgaben sind Teil der 735,02 EUR. Nach 9,39 EUR nicht abziehbarer Bewirtung ergeben sich 725,63 EUR EÜR-Ausgaben und −725,21 EUR Ergebnis. Für nicht vollständig geprüfte Steuerfälle steht ausdrücklich „nicht berechnet“.

Die ZIP enthält `EXTF_Buchungsstapel.csv`, `PRUEFPROTOKOLL.txt` und vorhandene Dateien unter `belege/`. Das Feld `Beleglink` enthält relative ZIP-Pfade als Zuordnungshilfe für die manuelle Übergabe. Daraus folgt keine automatische Verknüpfung mit DATEV DMS oder Unternehmen online. Die Kanzlei muss Import und Belegzuordnung im eigenen Zielsystem prüfen. Ein CSV-only-Export enthält keinen Belegordner.

Ohne Lizenz ist ein Probeexport von höchstens fünf **Quellvorgängen** möglich. Eine Jahreslizenz gilt nur für die abgedeckten Jahre; das Programm prüft die tatsächlich enthaltenen Buchungsjahre auch ohne `--year`.

Beim Upgrade von `euer-datev 0.2.0` müssen betroffene Exporte neu erzeugt und schon importierte Stapel mit der Kanzlei geprüft werden. Bereits importierte Daten nicht blind erneut importieren. Änderungen an Exit-Codes, Config-Vorrang und `--force` können bestehende Agentenabläufe beeinflussen.
