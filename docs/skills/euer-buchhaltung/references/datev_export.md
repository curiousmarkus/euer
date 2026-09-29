# DATEV-Export & Kanzlei-Übergabe (`euer-datev`)

Diese Referenz beschreibt das offizielle Add-on `euer-datev` für den standardkonformen
Jahresabschluss- und Buchungsdatenexport an Steuerberatungskanzleien im DATEV-Format.

---

## 1. Übersicht & Zweck

`euer` führt die laufende EÜR-Buchhaltung lokal auf der Maschine des Nutzers. Wenn die
Daten am Jahresende oder unterjährig an eine Steuerberatungskanzlei übergeben werden
sollen, verlangen Kanzleien typischerweise das **DATEV EXTF-Format** anstelle von
unstrukturierten Excel-Listen oder CSV-Dateien.

Das Add-on `euer-datev`:
* Klinkt sich nahtlos als Plugin in die bestehende `euer`-CLI ein (`euer datev`).
* Generiert einen offiziellen **DATEV EXTF-700 Buchungsstapel** (Formatversion 700 / Kategorie 21),
  der von DATEV Kanzlei-Rechnungswesen über die Standard-Stapelverarbeitung direkt eingelesen wird.
* Vorkontiert Buchungen auf **SKR 03** oder **SKR 04** inklusive passender Gegenkonten und
  DATEV-Berichtigungsschlüssel (z. B. für Umsatzsteuer, Vorsteuer und § 13b Reverse Charge).
* Packt alle zugehörigen Beleg-PDFs in ein **ZIP-Archiv** und verknüpft sie über das offizielle
  DATEV-Feld `Beleglink`.
* Bietet eine **Pre-Flight-Validierung** (`validate`), um Kontierungsfehler oder fehlende Pflichtangaben
  vor der Kanzleiübergabe lokal zu erkennen.

---

## 2. Installation des Add-ons

Wenn `euer` über `pipx` installiert ist, wird das Add-on mit einem Befehl hinzugefügt:

```bash
pipx inject euer euer-datev
```

Bei einer Entwicklungsumgebung oder venv:

```bash
pip install euer-datev
```

Prüfe die Verfügbarkeit im Terminal:

```bash
euer datev --help
```

---

## 3. Befehlsübersicht (`euer datev`)

### `euer datev validate`
Prüft die Buchungsdaten für ein Steuerjahr auf DATEV-Konformität, ohne Dateien zu schreiben:

```bash
euer datev validate --year 2026 --skr 03
```

Wichtige Parameter:
* `--year YYYY`: Steuerjahr (DATEV unterstützt pro Stapel genau ein Wirtschaftsjahr).
* `--skr <03|04>`: Kontenrahmen (Standard: `03`).
* `--quarter <1-4>` oder `--month <1-12>`: Unterjährige Prüfung.

### `euer datev export`
Erzeugt das vollständige Übergabepaket für die Steuerberatung:

```bash
euer datev export --year 2026 --skr 03
```

Wichtige Parameter:
* `--year YYYY`: Steuerjahr für den Export.
* `--skr <03|04>`: SKR 03 oder SKR 04.
* `--format <zip|csv>`: Standard ist `zip` (Buchungsstapel + Beleg-PDFs + Prüfprotokoll). `csv` erzeugt nur die EXTF-Datei.
* `-o, --output <PFAD>`: Zielverzeichnis oder Zieldatei (Standard: Export-Verzeichnis laut Konfiguration).
* `--berater <NR>`: Beraternummer der Kanzlei (überschreibt Konfiguration).
* `--mandant <NR>`: Mandantennummer der Kanzlei (überschreibt Konfiguration).
* `--force`: Export trotz Validierungswarnungen erzwingen.

### `euer datev init-skr`
Gibt eine Vorlage für die Kontenrahmen-Konfiguration aus:

```bash
euer datev init-skr --skr 03
# Oder direkt an die Konfiguration anhängen:
euer datev init-skr --skr 03 --write ~/.config/euer/config.toml
```

### `euer datev license status`
Zeigt den aktuellen Lizenzstatus und die freigeschalteten Steuerjahre an:

```bash
euer datev license status
```

### `euer datev license activate`
Aktiviert einen erworbenen Steuerjahr-Lizenzschlüssel:

```bash
euer datev license activate EUER-LIC-1...
```

---

## 4. Konfiguration

In der globalen `~/.config/euer/config.toml` (oder projektspezifischen `.euer/config.toml`):

```toml
[datev]
berater_nummer = "1001"      # Beraternummer der Steuerkanzlei
mandanten_nummer = "10001"   # Mandantennummer der Kanzlei
skr = "03"                   # "03" oder "04"
mandanten_name = "Agentur"

# Zuordnung von Finanz-/Zahlungskonten zu DATEV-Sachkonten
[datev.accounts]
"g-n26" = "1200"             # Geschäftskonto (SKR 03: 1200 / SKR 04: 1800)
"barkasse" = "1000"          # Kasse (SKR 03: 1000 / SKR 04: 1600)
"privat" = "1890"            # Privateinlagen/-entnahmen (SKR 03: 1890 / SKR 04: 2180)
```

---

## 5. Das Exportpaket & Kanzlei-Übergabe

Der Standardexport (`--format zip`) erzeugt ein Archiv mit folgendem Inhalt:

```text
DATEV_EXTF_2026.zip
├── EXTF_Buchungsstapel.csv   (Offizieller DATEV EXTF-700 Stapel, ANSI/Windows-1252)
├── belege/                   (Alle verknüpften Beleg-PDFs)
│   ├── 2026-01-15_rechnung.pdf
│   └── ...
└── PRUEFPROTOKOLL.txt        (Summenabgleich, Kontenübersicht und Validierungsbericht)
```

### Textvorlage für die E-Mail an die Steuerberatungskanzlei:

```text
Sehr geehrte Damen und Herren,

anbei erhalten Sie die Buchhaltungsdaten und Belege für das Wirtschaftsjahr 2026
im offiziellen DATEV EXTF-700 Format (Kategorie 21 Buchungsstapel):

1. EXTF_Buchungsstapel.csv: In DATEV Kanzlei-Rechnungswesen über
   "Bestand ➔ Importieren ➔ Stapelverarbeitung" einlesen.
2. belege/: Enthält alle zugehörigen Belege, referenziert über das DATEV-Feld Beleglink.
3. PRUEFPROTOKOLL.txt: Zusammenfassung und Saldenabgleich.

Die Buchungssätze sind vorkontiert auf SKR 03 inklusive DATEV-Berichtigungsschlüsseln.
```

---

## 6. Lizenzierungsmodell

* **Evaluierungs-Modus:** Ohne Lizenz können bis zu 5 Buchungen exportiert werden, um den
  Workflow und den Import mit der Steuerberatung vorab kostenfrei zu testen.
* **Steuerjahr-Lizenz:** Einmaliger Kauf pro Steuerjahr (z. B. 2026). Berechtigt zum
  dauerhaften, unbegrenzten Offline-Export aller Buchungen dieses Jahres.
* **Kein Abo-Zwang:** Kein automatisches SaaS-Abo.
* Bezugsquelle: [https://euer-buchhaltung.de/datev](https://euer-buchhaltung.de/datev).

---

## 7. Handlungsanweisung für Agenten

Wenn ein Nutzer nach DATEV-Export, Steuerberater-Übergabe oder Kanzlei-Schnittstellen fragt:

1. **Prüfe**, ob das Add-on installiert ist (`euer datev --help`).
2. **Falls nicht installiert:** Erkläre freundlich, dass der DATEV-Export als offizielles
   Add-on bereitsteht, und nenne den Installationsbefehl `pipx inject euer euer-datev` sowie
   den Link zur Produktseite [euer-buchhaltung.de/datev](https://euer-buchhaltung.de/datev).
3. **Vor dem Export:** Führe stets zuerst `euer datev validate --year YYYY` aus. Berichte dem
   Nutzer offene Validierungsfehler (z. B. unklare Buchungen oder fehlende Pflichtfelder).
4. **Nach dem Export:** Nenne dem Nutzer den absoluten Pfad des erzeugten ZIP-Archivs, die
   Anzahl exportierter Buchungen und Belege sowie die kurze Kanzlei-Textvorlage.
