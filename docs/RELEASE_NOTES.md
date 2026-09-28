# Release Notes

Diese Hinweise richten sich an Nutzer:innen mit bestehenden lokalen Instanzen.
Für Installationen ab 0.8.1 ergänzen sie die normale Update-Sequenz aus der
[Installationsreferenz](skills/euer-buchhaltung/references/installation_and_setup.md):

```bash
pipx upgrade euer
euer doctor
# Skill vollständig aus dem Bundle-Pfad installieren und neu laden
euer setup --set skill.version "1.1.2"
euer init
euer incomplete list
euer summary --year 2026
```

Bei einer bestehenden `euercli`-Installation zuerst die einmalige Migration im
Abschnitt `0.8.1` ausführen. Beim Wechsel von pipx zu Homebrew zuerst den
[Upgrade-Leitfaden](skills/euer-buchhaltung/references/installation_and_setup.md#von-pipx-zu-homebrew-wechseln) lesen. Der
Homebrew-Tap übernimmt PyPI-Releases zeitversetzt (geplant spätestens innerhalb
von sechs Stunden). `brew info euer` zeigt die Tap-Version; `euer --version`
zeigt die tatsächlich gestartete Installation. Die historischen Abschnitte
darunter behalten bewusst ihre ursprünglichen Upgrade-Befehle.

Bei Releases mit Agenten-Änderungen müssen lokal kopierte Agenten-Dateien
zusätzlich aktualisiert werden. Das betrifft insbesondere:

- `docs/skills/euer-buchhaltung/SKILL.md`
- `docs/templates/accountant-role.md` (früher `accountant-agent.md`)
- gezielte Änderungen am persönlichen Mandanten-Dossier, falls in der jeweiligen
  Release Note ausdrücklich genannt

Den Skill vollständig aus dem lokalen Bundle ersetzen und neu laden;
Rollen- und Agenten-Vorlagen vor einem Austausch mit lokalen Kopien vergleichen.
Die persönliche `AGENTS.md` darf nie automatisch ersetzt werden, weil sie individuelle
Pfade, Konten, Lieferanten-Mappings und steuerliche Stammdaten enthält.
Bei jedem neuen Release steht der konkrete Handlungsbedarf für Skill, Rolle,
Agenten-Adapter und Mandanten-Dossier direkt im Versionsabschnitt unter
„Agenten-Dateien“. Die wiederkehrende Prozedur beschreibt der
[Installationsreferenz](skills/euer-buchhaltung/references/installation_and_setup.md#agenten-dateien-aktualisieren).

## Unveröffentlicht

- Ausgaben und Einnahmen können eine optionale Rechnungsnummer speichern.
  `add`/`update` verwenden `--invoice-number`; CSV-/JSONL-Import erkennt
  `invoice_number` und `Rechnungsnummer`. Listen-CSV und CSV-/XLSX-Exporte
  ergänzen die Spalte; im Export steht sie direkt hinter dem Rechnungsdatum.
  Gleiche Nummer, Gegenpartei und Betrag lösen auch über größere Datumsabstände
  eine Dublettenprüfung aus (`--allow-duplicate` für belegte Ausnahmen).
  Wenn nur eine Buchung eine Nummer hat, können auch Rechnungsdatum oder
  Belegname bei gleicher Gegenpartei und gleichem Betrag ein Duplikat anzeigen.
  Der technische Buchungs-Hash berücksichtigt neue Rechnungsnummern; für
  bestehende Buchungen ohne Nummer bleibt der bisherige Hash gültig.
- **Upgrade:** Paket aktualisieren und im Buchhaltungsordner `euer init`
  ausführen (vorher bei Bedarf `euer init --dry-run`). Migration 009 ergänzt
  beide Tabellen ohne Änderung bestehender Buchungen. Alte Nummern werden
  nicht automatisch aus Belegdateien übernommen. Keine Config-Migration.
- **Agenten-Dateien:** Skill und Referenzen auf 1.1.2 aktualisieren, neu laden
  und mit `euer setup --set skill.version "1.1.2"` bestätigen. Das persönliche
  Mandanten-Dossier bleibt unverändert.

## 0.11.1

Der Tag `v0.11.0` löste wegen eines fehlgeschlagenen Windows-CI-Tests keine
Paketveröffentlichung aus. `0.11.1` ist die erste veröffentlichte Version nach
`0.10.2`; die folgenden Upgrade-Schritte gelten daher für bestehende Installationen.

### Agenten-Dateien

| Bereich | Änderung | Aktion nach diesem Release |
|---|---|---|
| Skill | Unversionierter Stand → 1.1.1; Buchhalter-Grundregeln und Arbeitsablauf sind enthalten. CLI- und Fachreferenzen verlangen Belegprüfung vor Ausnahmen und geben keine pauschale Prepaid-/Cashback-Einstufung mehr vor. Die bereinigte Dossier-Vorlage liegt jetzt unter `assets/Agents-Template.md` im Bundle | Skill vollständig aus `skill.bundle_path` ersetzen, neu laden und Version bestätigen; vorhandene persönliche `AGENTS.md` nicht überschreiben |
| Rolle | `accountant-agent.md` heißt jetzt `accountant-role.md` und ist ein optionaler kurzer Einstieg; die allgemeinen Regeln liegen im Skill | Nur bei eigens konfigurierten Buchhaltungsagenten die lokale Rollen-Datei nach Diff anpassen |
| Agenten-Adapter | Noch keine plattformspezifischen Dateien im Release | Keine automatische Änderung an `SOUL.md`, `CLAUDE.md` oder `AGENTS.md` |
| Mandanten-Dossier | Keine automatische Migration; keine festen EÜR-Zeilennummern in Lieferantenregeln | Bestehende Regeln prüfen und Änderungen nur als Vorschlag übernehmen |

Der Buchungs- und Kontoauszugsablauf steht direkt in `SKILL.md`.
`cli_reference.md` enthält nur noch Core-Befehle, Optionen und knappe
Ein-/Ausgabehinweise. Konfiguration und Ablage stehen in
`references/installation_and_setup.md`, fachliche Prüfungen und Privatregeln in
`references/domain_rules.md`. Nach dem Update den vollständigen Skill-Ordner
ersetzen und neu laden. An Datenbank und persönlichem Mandanten-Dossier ist für
diese Dokumentationsänderung nichts zu migrieren.
Die Onboarding-Referenz verweist auf die mitgelieferte Dossier-Vorlage und
führt bei vorhandenen Datenbanken vor `init` durch dessen `--dry-run`-Vorschau.

Der Skill ist nun mit Version 1.1.1 im CLI-Paket enthalten. Nach dem Paketupdate
`euer doctor` ausführen, den Ordner aus dem Bundle-Pfad vollständig
in das Agentensystem übernehmen, die Anweisungen neu laden und erst dann mit
`euer setup --set skill.version "1.1.1"` bestätigen. Die bisher unversionierte
Skill-Kopie wird ersetzt; die persönliche `AGENTS.md` bleibt erhalten. Die
Rolle und Agenten-Adapter werden bei Bedarf gezielt geprüft, nicht automatisch
ersetzt. Keine Datenbankmigration erforderlich; die globale Config erhält
`[skill] version = "1.1.1"`. Bei fehlenden Update-Rechten kann
`--ignore-skill-version` einen einzelnen Aufruf freigeben.

Für bestehende Agenten-Installationen ist der vollständige Austausch des Skills
einschließlich `references/` nötig. Geprüfte Buchungen werden dadurch nicht
automatisch umklassifiziert; offene Prepaid-, Cashback- und Privatvorgänge
anhand der Belege erneut prüfen. Keine zusätzliche Datenbankmigration für diese
Referenzänderungen.

### Weitere Änderungen

- README, Konzept, User Journey und Repository-`AGENTS.md` beschreiben die
  Grenzen von CLI-Prüfungen und Agenten-Einordnungen genauer. Vor der
  steuerlichen Abgabe bleiben offene Fälle und Berichte zu prüfen; für diese
  Textänderungen ist keine Migration nötig.
- **Transparente und sichere DB-Migrationen (Spec 020, Spec 016 §1.1/§2.4):**
  - Automatisches WAL-sicheres Online-Backup via SQLite-Backup-API nach `~/.config/euer/backups/euer_YYYY-MM-DD_HHMMSS.db` vor Schema-Migrationen.
  - Vor dem ersten schreibenden CLI-Befehl pro Datenbank und Tag wird ein zusätzlicher Snapshot mit Datenbankkennung im Dateinamen erstellt.
  - Transaktionales Schema-Versionstracking (`_schema_migrations`) mit automatischem Rollback im Fehlerfall.
  - Preflight-Bericht in `euer init`: Pfadanzeige, Schemaversion, anstehende Migrationen und Auswirkungsanalyse (`incomplete_impact`).
  - Neue Flags für `euer init`: `--dry-run` zur gefahrlosen Simulation, `--json` für maschinenlesbare Ausgaben, Pflichtflag `--create` zur Neuanlage einer Datenbank.
  - `.euer/config.toml` bindet den DB-Pfad an den Buchhaltungsordner. `euer init` registriert eine vorhandene `./euer.db`; `euer init --create` registriert eine neue. Eine DB an anderem Ort mit `euer --db PFAD init --save-db-path` verbinden. `--db` allein gilt nur für einen Aufruf. Bei fehlender konfigurierter DB stoppen Buchungsbefehle, ohne eine leere DB anzulegen.
- **Agent-Safety & Guardrails (Spec 016):**
  - Soft-Delete by default für `expenses`, `income` und `private_transfers` via `deleted_at`.
  - Physisches Löschen nur noch mit explizitem `--purge`.
  - Neuer Papierkorb-Befehl: `euer trash list` und `euer trash empty [--force]`.
  - Wiederherstellung: `euer restore <id> [--table ...]`.
  - Atomares Undo: `euer undo [--force]` rollt die jeweils letzte Mutation (INSERT, UPDATE, DELETE) basierend auf dem Audit-Log zurück.
  - Export-Überschreibschutz: `euer export` blockiert Überschreiben im Zielordner ohne `--force`, schreibt zuerst temporäre Dateien und setzt bei Austauschfehlern bereits ersetzte Dateien nach Möglichkeit zurück.
  - Validierungs-Guardrails: Mathematische Brutto-USt-Prüfung (Toleranz 0,02 €), strikte Ablehnung von Zukunftszahlungen, Betragsschwelle > 5.000 € (`--force`), unscharfe Duplikaterkennung im Zeitfenster von ±2 Tagen (`--allow-duplicate`).
- **Pre-Flight- und Umgebungsdiagnose mit `euer doctor` (Spec 019):**
  - Neuer Diagnosebefehl `euer doctor` mit strukturierter Terminal- und maschinenlesbarer `--json`-Ausgabe.
  - Prüft Version, Interpreter, Installationsquelle (Homebrew, pipx, venv, editable) und durchsucht den `$PATH` nach kollidierenden Installationen.
  - Sichere, rein lesende DB-Prüfung: Ermittelt den effektiven DB-Pfad (CLI-Flag, Projekt-Config oder Standard), prüft Existenz ohne Dateierzeugung, Dateigröße, Berechtigungen, Integrität (`PRAGMA quick_check`) und offene Migrationen.
  - Validiert `config.toml`, `.euer/config.toml`, Belege- und Exportverzeichnisse sowie die Verfügbarkeit von `openpyxl`.
- Upgrade-Dokumentation für den Wechsel von pipx/`euercli` zu Homebrew,
  PATH-Prüfung und zeitversetzte Tap-Aktualisierung ergänzt.
- Agenten-Dokumentation trennt allgemeine Skill-Regeln von persönlichen
  Mandantenregeln und empfiehlt jahresbezogene EÜR-Zeilenabfragen.
- Geplant, noch nicht implementiert: versionierte Exportläufe mit Manifest (Spec 021).
- Export-Spec und CLI-Referenz grenzen den geplanten Manifestmodus ausdrücklich
  von GoBD-Konformität und rechtlich revisionssicherer Archivierung ab.
- Das Accountant-Template beschreibt die Unterscheidung zwischen privat
  bezahlter Betriebsausgabe, Ausgleich und reiner Kapitalbewegung genauer.
- Die gemeinsame Rollen-Vorlage heißt nun `accountant-role.md`. Bestehende
  Agentendateien bleiben bestehen; neue Rollenregeln nach Diff gezielt
  übernehmen. `accountant-agent.md` bleibt als Verweis für ältere Links.

## 0.10.2

### Bewirtungen und Formularjahr-Zuordnungen

User Journey und FAQ beschreiben nun die Bewirtungserfassung, offene Belegprüfungen,
Jahreszuordnung und Nachpflege alter Buchungen. Die Entwickler-Checkliste und
Repository-`AGENTS.md` verlangen künftig auch die Prüfung dieser beiden Dokumente.
Diese Dokumentationsergänzung benötigt keine zusätzliche Datenbank- oder
Konfigurationsmigration.

Bewirtungen werden als ein Zahlungsvorgang mit belegter Vorsteuer und optionalem,
im Zahlbetrag enthaltenem Trinkgeld erfasst. `summary` berechnet die 70/30-Aufteilung
aus Zahlbetrag abzüglich Vorsteuer; der volle belegte Vorsteuerbetrag bleibt im
`vat-report` erhalten. Standardmodus-Buchungen ohne angegebene Vorsteuer werden als
prüfbedürftig markiert. Kleinunternehmerbuchungen speichern den fehlenden
Vorsteuerabzug pro Buchung. Exportierte Einzelstatus bleiben beim Import auch
nach einem Wechsel des globalen Steuermodus erhalten.

EÜR-Zeilen werden anhand lokal versionierter Formularjahre aus stabilen fachlichen
Kategorie-Schlüsseln ermittelt. Die Zuordnungen für 2025 und 2026 korrigieren unter
anderem Bewirtung, Vorsteuer, Zahlungen ans Finanzamt, die übrigen Seed-Kategorien
und Privateinlagen/-entnahmen. Das Zeile-13-Feld wird als Unterfeld nicht noch einmal
zu den Betriebseinnahmen addiert. Für nicht mitgelieferte Formularjahre wird keine
Zeilennummer behauptet.

**Review-Korrekturen:** Reverse-Charge-Vorsteuer wird in der EÜR nicht vom
Zahlbetrag abgezogen oder als bezahlte Rechnungs-Vorsteuer ausgewiesen. Neue
Bewirtungen mit Reverse Charge werden abgelehnt; historische RC-Bewirtungen und
Erstattungen bleiben ausdrücklich ungeprüft und werden nicht als normale
Bewirtungskosten berechnet. Das Zeile-13-Unterfeld lässt auch bei Updates keine
Umsatzsteuer zu. XLSX enthält die neuen Bewirtungsbeträge als numerische Zellen.
Bei bestehenden RC-Bewirtungen werden auch reine Metadatenänderungen (z. B. Notizen
oder Belegdaten) abgelehnt, solange die Buchung als RC-Bewirtung klassifiziert bleibt.
Bereits erzeugte Berichte und Exporte bei betroffenen Buchungen neu erstellen.
Lokal kopierten Buchhaltungs-Skill und Accountant-Template aktualisieren.

**Upgrade:** `euer init` ergänzt die Datenbank additiv um Kategorie-Schlüssel,
Trinkgeld und Bewirtungs-Vorsteuerstatus. Bestehende Beträge und Vorsteuerwerte
bleiben unverändert; alte Bewirtungen werden als `needs_review` markiert und mit
`euer incomplete list` angezeigt. Belegprüfung und Nachpflege erfolgen je Buchung
über `euer update expense <ID> --vat ... [--tip ...]` oder einen passenden
`--entertainment-vat-status`. Es ist keine Konfigurationsmigration erforderlich.
Kategoriezeilen in Exporten/Listen beziehen sich auf das angegebene Berichtsjahr.
Die Änderung ist ein abwärtskompatibles Feature und gehört beim Release in einen
MINOR-Bump. Die Website-Beispiele liegen im Schwester-Repository und wurden dort
auf die 2026-Zuordnungen (Zeile 64/58) aktualisiert.

## 0.9.0

### Onboarding direkt im Buchhaltungs-Skill

Der Skill prüft vor Buchungsaufträgen die vorhandene Einrichtung und lädt bei Bedarf
`references/onboarding.md`. Er fragt nur fehlende Angaben ab und übernimmt bereits
vorhandene Mandantendaten. Der separate Onboarding-Prompt bleibt als Einstieg für
einen normalen LLM-Chat erhalten und nutzt denselben Leitfaden.

**Upgrade:** Den vollständigen Ordner `docs/skills/euer-buchhaltung/` einschließlich
`references/` in der KI-Anwendung aktualisieren; nur `SKILL.md` zu kopieren reicht
nicht mehr. Auch die lokale Kopie von `docs/templates/accountant-agent.md`
aktualisieren, sofern genutzt. Die persönliche `AGENTS.md` erhalten; fehlende
Angaben gezielt ergänzen lassen. Ein erneutes Vollinterview ist nicht nötig.
Es gibt keine Datenbank- oder Config-Migration und keinen neuen CLI-Befehl.
Ein Paketupdate allein aktualisiert lokal kopierte Agenten-Dateien nicht.

### User Journey und ELSTER-Abschluss

Die neue User Journey dokumentiert den Weg vom Onboarding über Buchungsalltag und
Monatsabgleich bis zum Jahresabschluss. Sie zeigt, wie Nutzer:innen die EÜR-Berichte
anhand ihrer Zeilennummern und Buchungsexporte prüfen und die Werte selbst nach
ELSTER übertragen. Die Journey benennt außerdem den Berichtsumfang und offene
Buchungsfragen.

**Upgrade:** Keine Datenbank- oder Config-Migration erforderlich. Die Journey steht
im Repository und ist von README und Benutzerhandbuch aus verlinkt.

## 0.8.1

### Warum relevant?

`euer` wird ab diesem Release als Paket über PyPI veröffentlicht. Die reguläre
Installation erfolgt damit ohne Git-Checkout:

```bash
pipx install euer
pipx install "euer[xlsx]"
```

Zusätzlich steht das unveränderte Release-Artefakt im GitHub Release bereit und der
Homebrew-Tap übernimmt neue PyPI-Releases automatisch. Die Basisinstallation bleibt
ohne `openpyxl`; das optionale Extra und Homebrew bringen die XLSX-Unterstützung mit.

### Einmalige Migration von `euercli` zu `euer`

Bestehende Installationen aus dem GitHub-Repository müssen einmalig umgestellt werden:

```bash
pipx uninstall euercli
pipx install euer
```

Für XLSX-Unterstützung gilt anschließend:

```bash
pipx install "euer[xlsx]"
```

Prüfe vor und nach der Umstellung mit `pipx list`, dass kein zweiter `euer`-Entry-Point
aus einer alten Umgebung aktiv bleibt. Die lokale SQLite-Datenbank und die Konfiguration
werden durch den Distributionsnamen nicht verändert. Führe danach im Buchhaltungsordner
weiterhin `euer init` aus, damit eventuelle Schema-Migrationen des jeweiligen Releases
ausgeführt werden.

### Homebrew

Auf macOS und Linux kann `euer` alternativ über den Tap installiert und aktualisiert
werden:

```bash
brew install curiousmarkus/euer/euer
brew upgrade euer
```

Der Tap verwendet ausschließlich das PyPI-sdist und aktualisiert sich eventual-consistent
innerhalb von höchstens sechs Stunden nach einem PyPI-Release.

## 0.7.1

### Fehlerbehebungen

- CSV-Ausgaben auf Windows verwenden jetzt explizit `\n` als Zeilenende und enthalten
  dadurch keine zusätzlichen Leerzeilen mehr.
- UTF-8-Ausgaben, Umlaute und temporäre Windows-Pfade werden durch die
  Windows-Integrationstests zuverlässig abgedeckt.

### Nach dem Upgrade

Es sind keine Datenbank- oder Konfigurationsmigrationen erforderlich. Ein normales
Upgrade mit `pipx upgrade euercli` genügt.

## 0.7.0

### Warum relevant?

Die Belegablage nutzt jetzt standardmäßig eine jahrzentrierte Struktur:

```text
<Beleg-Root>/<Jahr>/<Typ>/<Belegname>
```

Beispiele:

```text
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.pdf
/Users/max/Dropbox/Buchhaltung/2026/Einnahmen/2026-01-20_Rechnung_001.pdf
```

Die alten Config-Keys `receipts.expenses` und `receipts.income` werden für die
Belegprüfung nicht mehr verwendet. Belegdateien werden beim Upgrade nicht
automatisch verschoben.

### Nach dem Upgrade

1. Backup der bestehenden `~/.config/euer/config.toml` erstellen.
2. Neue Beleg-Config setzen:

```toml
[receipts]
root = "/Users/max/Dropbox/Buchhaltung"
year_dir = "{year}"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"
```

3. Alternativ per CLI setzen:

```bash
euer setup --set receipts.root "/Users/max/Dropbox/Buchhaltung"
euer setup --set receipts.year_dir "{year}"
euer setup --set receipts.expenses_dir "Ausgaben"
euer setup --set receipts.income_dir "Einnahmen"
```

4. `exports.directory` bei Bedarf separat prüfen: Es ist ein konkreter Ordner
   und unterstützt keinen `{year}`-Platzhalter. Für jahresweise Exportordner
   `--output` mit einem konkreten Pfad verwenden, z.B.
   `euer export --year 2026 --output "/Users/max/Dropbox/Buchhaltung/2026/Exporte"`.
5. Bestehende Belege bei Bedarf manuell nach `Jahr/Typ` verschieben.
6. Migration prüfen:

```bash
euer receipt check --year 2026
```

7. Lokale Kopien von `SKILL.md`, `accountant-agent.md` und der persönlichen
   `AGENTS.md` auf die neue `Jahr/Typ`-Struktur aktualisieren.

## 0.6.0

### Warum relevant?

`euer` enthält jetzt einen ELSTER-nahen USt-Voranmeldungs-Report:

```bash
euer vat-report --year 2026
euer vat-report --year 2026 --quarter 1
euer vat-report --year 2026 --month 3 --format csv --output exports/
```

Dafür speichern `expenses` und `income` neue UStVA-Klassifikationsfelder:

- `vat_rate`
- `vat_code`

Neue Einnahmen bekommen im Modus `standard` standardmäßig `19 %`, sofern nicht
`--vat-rate 7`, `--vat-rate 0` oder `--tax-free` gesetzt wird. `amount_eur`
bleibt weiterhin der tatsächliche Brutto-Zahlfluss; die USt wird für Einnahmen
aus dem Bruttobetrag herausgerechnet oder über `--vat` manuell gesetzt.

### Nach dem Upgrade

1. Backup der lokalen Datenbank erstellen.
2. `pipx upgrade euercli` ausführen.
3. Im Buchhaltungsordner `euer init` ausführen. Dadurch werden `vat_rate` und
   `vat_code` in bestehenden Datenbanken ergänzt.
4. Mit `euer vat-report --year <JAHR>` Warnungen prüfen.
5. Alte Einnahmen ohne `vat_code` bei Bedarf nachklassifizieren:

```bash
euer update income <ID> --vat-rate 19
euer update income <ID> --vat-rate 7
euer update income <ID> --vat-rate 0
euer update income <ID> --tax-free
```

6. Reverse-Charge-Altbuchungen mit `unclassified` weiter per
   `euer update expense <ID> --rc eu|third-country` nachpflegen.
7. Lokale Kopien von `SKILL.md`, `accountant-agent.md` und ggf. der
   persönlichen `AGENTS.md` um die neuen UStVA-Regeln ergänzen.

### Agenten-Regeln

Für regelbesteuerte Mandate sollen Agenten Einnahmen künftig mit passender
USt-Klassifikation buchen:

```bash
euer add income ... --vat-rate 19
euer add income ... --vat-rate 7
euer add income ... --tax-free
```

Für Ausgaben bleibt `--vat` der manuelle Vorsteuerbetrag; Reverse Charge bleibt
`--rc eu|third-country`.

## 0.5.0

### Warum relevant?

Reverse-Charge-Ausgaben speichern jetzt keinen Boolean mehr, sondern einen
konkreten RC-Typ:

- `none`
- `eu`
- `third_country`
- `unclassified` für migrierte Altbuchungen ohne bekannte Jurisdiktion

Dadurch können spätere UStVA-Auswertungen EU-Leistungen und Drittland-Leistungen
sauber trennen.

### Nach dem Upgrade

1. Backup der lokalen Datenbank erstellen.
2. `pipx upgrade euercli` ausführen.
3. Im Buchhaltungsordner `euer init` ausführen.
4. Mit `euer incomplete list` und `euer summary --year 2026` offene Nacharbeiten prüfen.
5. Lokale Kopien von `SKILL.md` und `accountant-agent.md` durch die Version aus diesem Release ersetzen.
6. Bestehende RC-Buchungen mit `unclassified` prüfen und nachpflegen:

```bash
euer update expense <ID> --rc eu
euer update expense <ID> --rc third-country
```

### AGENTS.md

Die persönliche `AGENTS.md` muss nicht komplett neu erzeugt werden. Prüfe aber,
ob dort Reverse-Charge-Anbieter oder Buchungsregeln stehen. Diese Regeln sollten
jetzt zwischen EU und Drittland unterscheiden und `--rc eu` bzw.
`--rc third-country` nennen.

Wenn du unsicher bist, führe den aktuellen `docs/templates/onboarding-prompt.md`
erneut aus oder bitte deinen Agenten um ein gezieltes Update:

```text
Aktualisiere meine AGENTS.md für euer 0.5.0. Übernimm nur die neuen
Reverse-Charge-Regeln aus docs/RELEASE_NOTES.md und docs/templates/onboarding-prompt.md.
Erhalte alle persönlichen Pfade, Konten, Lieferanten-Mappings und Steuerdaten.
```
