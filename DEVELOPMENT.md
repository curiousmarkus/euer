# Developer Guide

Dieses Dokument richtet sich an Maintainer und Beitragende. Es beschreibt die
Entwicklungsumgebung, Architektur, verbindliche Änderungsregeln und den Release-Prozess.
Der Einstieg für Pull Requests steht in [CONTRIBUTING.md](CONTRIBUTING.md), die
Teststrategie in [TESTING.md](TESTING.md).

## Setup

### macOS und Linux

```bash
make install
make test
make lint
```

Die Entwicklungsumgebung enthält Ruff, Coverage, das Build-Werkzeug und die optionale
XLSX-Unterstützung. `make` nutzt `.venv/bin/python`; aktiviere die Umgebung nur,
wenn du `euer` direkt aufrufen möchtest. Für einen CLI-Test ohne Installation kannst
du das Modul aus dem Repository starten:

```bash
python3 -m euercli --help
```

Arbeite für Buchungstests in einem temporären Buchhaltungsordner. `euer init --create`
legt eine neue SQLite-Datei im aktuellen Buchhaltungsordner an und gehört nicht zum
Setup des Repositorys.

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,xlsx]"
python -m unittest discover -s tests
python -m ruff check .
python -m ruff format --check .
```

`make` ist für die gezeigten macOS-/Linux-Befehle vorgesehen; unter Windows gelten
die PowerShell-Befehle oben.

## Projektstruktur (Kurzüberblick)

```
euer/
├── .github/workflows/      # Automatisierte Tests und Qualitätsprüfungen
├── euercli/                 # Core Package
│   ├── cli.py               # CLI Parser + Dispatch
│   ├── commands/            # Command Implementierungen
│   ├── services/            # Service Layer (Fachlogik und Validierung)
│   ├── db.py                # DB Helpers
│   ├── schema.py            # DB Schema + Seeds
│   ├── migrations.py        # Versionierte DB-Migrationen
│   ├── importers.py         # Import Normalisierung
│   ├── config.py            # Globale Einstellungen laden/speichern
│   └── project_config.py    # DB-Pfad pro Buchhaltungsordner
├── tests/                   # CLI- und Service-Tests (unittest)
├── specs/                   # Anforderungen, Status und offene Change Requests
├── docs/
│   ├── CONCEPTS.md           # Konzept und Produktgrenzen
│   ├── USER_JOURNEY.md       # Ablauf von Onboarding bis Jahresabschluss
│   ├── RELEASE_NOTES.md      # Upgrade-Hinweise für bestehende lokale Instanzen
│   ├── skills/               # AI Agent Skills
│   └── templates/            # Agent-Konfigurationsvorlagen
├── CONTRIBUTING.md          # Einstieg für Beiträge und Pull Requests
├── DEVELOPMENT.md           # Diese Datei
└── TESTING.md               # Teststrategie
```

## Architektur

### Agenten-Onboarding pflegen

`docs/skills/euer-buchhaltung/SKILL.md` enthält die Zustandsprüfung und verweist bei
fehlender Einrichtung auf `references/onboarding.md` im selben Skill-Ordner.
Dieser Leitfaden ist die gemeinsame Quelle für Interview, Dossier und Setup;
die Dossier-Vorlage liegt unter `assets/Agents-Template.md` im Skill-Bundle.
`docs/templates/onboarding-prompt.md` dient als Einstieg für separate LLM-Chats.
Keine zweite Interview-Anleitung im Prompt pflegen. Bei Skill-Updates müssen auch
die Referenzen verteilt werden. Das Routing ist eine Agenten-Anweisung, keine
technische Sperre in der CLI. Änderungen daran gehören in die Release Notes.

### Schichtenmodell

```
┌─────────────────────────────────────────────┐
│  CLI Layer (euercli/cli.py + commands/)      │  argparse, Ausgabe, sys.exit
├─────────────────────────────────────────────┤
│  Service Layer (euercli/services/)           │  Business-Logik, Validierung, Audit
├─────────────────────────────────────────────┤
│  Data Layer (db.py, schema.py, migrations.py) │  DB-Zugriff, Schema, Migration
├─────────────────────────────────────────────┤
│  SQLite (euer.db)                            │  Persistenz
└─────────────────────────────────────────────┘
```

- **CLI Entry Point**: `euercli/cli.py` (argparse + Dispatch).
- **Commands**: je Feature in `euercli/commands/` (View-Controller, keine Logik).
- **Service Layer**: `euercli/services/` als stabile API (keine Prints, keine argparse-Abhängigkeit).
- **DB-Zugriff**: Verbindungen über `get_db_connection()` in `euercli/db.py`;
  Abfragen mit Parametern. Die Verbindung setzt `sqlite3.Row` und Fremdschlüsselprüfung.
- **Schema/Seeds**: `euercli/schema.py`; bestehende Datenbanken über
  `euercli/migrations.py` und `euer init` aktualisieren.
- **Config**: `euercli/config.py` (`~/.config/euer/config.toml`) für allgemeine
  Einstellungen; `euercli/project_config.py` (`.euer/config.toml`) für den
  projektbezogenen DB-Pfad. `--db` hat Vorrang und bleibt ohne `--save-db-path`
  auf einen Aufruf beschränkt.
- **Import**: `euercli/importers.py` (CSV/JSONL Normalisierung).
- **Plugins**: CLI lädt Entry Points `euer.commands` und ruft `setup(subparsers)`.

### Service Layer: Pflichtregeln

> **Jede Schreiboperation (INSERT, UPDATE, DELETE) auf `expenses`, `income` oder
> `private_transfers` MUSS über den Service Layer laufen.**

Der Service Layer (`euercli/services/`) ist die einzige Stelle für:

1. **Validierung** (Beträge, Datumsformate, Pflichtfelder)
2. **Geschäftslogik** (Steuerberechnung, Private Klassifikation, Hash-Duplikatprüfung)
3. **Audit-Logging** (jede Mutation wird protokolliert)
4. **Datenrückgabe** (typisierte Dataclasses, keine dicts)

**Vertrag:**

| Eigenschaft | Service Layer | Commands |
|-------------|--------------|----------|
| SQL INSERT/UPDATE/DELETE | ✅ Erlaubt | ❌ Verboten |
| SQL SELECT (einfach) | ✅ Erlaubt | ✅ Erlaubt (nur Lesen) |
| `print()` / `sys.exit()` | ❌ Verboten | ✅ Erlaubt |
| `args` (argparse) | ❌ Verboten | ✅ Erlaubt |
| Fachliche Exceptions | Werfen (`ValidationError`, `RecordNotFoundError`) | Fangen und in deutsche Ausgabe übersetzen |
| Transaktionen | Operation samt Audit-Eintrag abschließen | Batch-Ablauf steuern, keine Fachlogik duplizieren |

Ein neues Command ruft eine Service-Funktion auf, behandelt deren Ergebnis oder
Fehler und schließt die Verbindung. Direkte SQL-Schreibzugriffe im Command umgehen
Validierung und Audit-Log und sind für Buchungen verboten. Mutationen an
`expenses`, `income` und `private_transfers` müssen einschließlich Audit-Eintrag
in derselben Transaktion abgeschlossen werden. Die bestehenden Services in
`euercli/services/` sind die Vorlage für Signaturen und Commit-Verhalten.

## Implementierte Funktionen (Überblick)

Dieser Abschnitt hilft Contributor:innen, bestehende Features zu verstehen,
damit Erweiterungen konsistent und risikoarm umgesetzt werden können.

- **Core CLI**: `init`, `setup`, `config show`, `list categories`.
- **Buchungen**: `add`, `list`, `update`, `delete`, `restore` und `undo` für
  Ausgaben, Einnahmen und Privatvorgänge.
- **Audit-Log**: Jede Änderung (INSERT/UPDATE/DELETE) wird protokolliert.
- **Service Layer**: Logik ist typisiert (Dataclasses) und nutzt Exceptions statt `sys.exit()`.
- **Import**: CSV/JSONL mit Normalisierung, Duplikat-Schutz (Hash).
- **Incomplete**: unvollständige Buchungen werden live aus `expenses`/`income` berechnet.
- **Summary**: Jahreszusammenfassung inkl. RC/Steuerlogik und Hinweis auf
  unklassifizierte RC-Altbuchungen.
- **VAT Report**: ELSTER-naher UStVA-Arbeitsbericht (`vat-report`) mit
  Kennzahlen, periodengenauer Selektion, Warnungen sowie CSV/XLSX-Export.
- **Export**: CSV (immer), XLSX optional via `openpyxl`.
- **Kontenrahmen**: Optionaler `[[ledger_accounts]]`-Kontenrahmen in der Config mit
  automatischer Kategorieauflösung bei `add`/`update`/`import`.
- **Receipts**: Jahrzentrierte Belegpfade (`root/{year}/Typ`), `receipt check`
  und `receipt open`.
- **Steuermodi**: `small_business` und `standard` (RC Handling inkl. USt/VoSt).
- **Persistierte USt-Klassifikation**: `vat_rate` und `vat_code` an
  Ausgaben/Einnahmen für auditierbare UStVA-Reports.
- **Formularjahr-Metadaten**: fachliche `eur_key`-Zuordnung für geprüfte EÜR-Felder;
  CLI-Berichte zeigen Zeilen nur für lokal mitgelieferte Formularjahre.
- **Bewirtung**: ein Zahlungsvorgang mit belegter Vorsteuer, Trinkgeldangabe,
  gespeichertem Prüfstatus und centgenauer 70/30-Aufteilung.
- **RC-Typ**: Reverse-Charge-Ausgaben speichern `none`, `eu`,
  `third_country` oder den Migrationszustand `unclassified`.
- **Diagnose und Migration**: `doctor` prüft Installation und Buchhaltungsordner;
  `init --dry-run` zeigt den Migrationsplan vor Änderungen.

## Datenmodell (Überblick)

Die vollständigen DDLs stehen in `euercli/schema.py`.

- **categories**: UUID, Name, Legacy-Zeilenfeld, stabiler fachlicher `eur_key`, Typ (expense/income).
- **expenses**: UUID, Ausgaben inkl. Beleg und optionaler Rechnungsnummer, Konto, Fremdwährung, RC‑Typ,
  Steuern, USt-Klassifikation, Private Klassifikation.
- **income**: UUID, Einnahmen inkl. Beleg und optionaler Rechnungsnummer, Fremdwährung, Umsatzsteuer,
  USt-Klassifikation.
- **private_transfers**: UUID, Privateinlagen/-entnahmen, Betrag, optionale Referenz auf Expense.
- **audit_log**: Protokolliert INSERT/UPDATE/DELETE inkl. Vorher/Nachher + `record_uuid`.

`euer init --create` legt eine neue Datenbank an. `euer init --dry-run` zeigt
bei vorhandenen Datenbanken anstehende Migrationen und ihre Auswirkungen;
`euer init` führt sie nach Prüfung aus. Migrationen liegen in
`euercli/migrations.py` und werden in `_schema_migrations` protokolliert.

## Audit‑Logging (Pflicht)

Jede Änderung an `expenses`, `income` und `private_transfers` muss in `audit_log`
landen. Verwende `log_audit()` bei INSERT/UPDATE/DELETE innerhalb derselben
Transaktion; übergib die UUID als `record_uuid`. Das gilt auch für Soft Deletes,
Restore und Undo.

## Steuer‑Logik

Der Modus wird aus der Config gelesen (`[tax].mode`).

- `small_business` (Default): keine Vorsteuer; RC erzeugt Umsatzsteuer‑Zahllast.
- `standard`: Vorsteuer wird erfasst; RC bucht USt und VorSt gleichzeitig.
- Einnahmen speichern für UStVA-Zwecke `vat_rate` und `vat_code`; im
  Standardmodus ist der Default für neue Einnahmen `19 %`, sofern keine
  steuerfreie Behandlung gesetzt wird.
- RC-Ausgaben werden per `--rc eu` oder `--rc third-country` erfasst; intern
  wird `third-country` als `third_country` gespeichert.

## Import & Incomplete

Der Import akzeptiert CSV/JSONL. Benötigt werden `party`, `amount_eur` und
mindestens `payment_date` oder `invoice_date`; `type` wird gegebenenfalls aus
dem Vorzeichen des Betrags abgeleitet. Die CLI akzeptiert auch dokumentierte
Feld-Aliasse wie `date`, `vendor` und `source`.

Fehlende Pflichtfelder brechen den Import ab. Unvollständige Buchungen werden
über `euer incomplete list` live aus aktiven Buchungen berechnet. Geprüft werden
je nach Buchung und Steuermodus etwa Zahlungs- und Rechnungsdatum, Kategorie,
Beleg, Konto, Umsatzsteuer und RC-Klassifikation. Die genaue Logik steht in
`euercli/commands/incomplete.py`; der Nutzerablauf in
[User Journey](docs/USER_JOURNEY.md).

Der Import akzeptiert zusätzlich UStVA-Klassifikationsfelder (`vat_rate`,
`vat_code`, `tax_free`) für round-trip-fähige Exporte und Reports.

## Neue Commands hinzufügen

1. **Service-Funktion** in `euercli/services/` implementieren (Dataclass-Return, Exceptions).
2. **Command** `cmd_<name>(args)` in `euercli/commands/` als View-Controller implementieren.
   - Command ruft Service-Funktionen auf, keine direkten SQL-INSERTs/UPDATEs/DELETEs.
   - Command fängt `ValidationError` / `RecordNotFoundError` und gibt Fehlermeldung aus.
3. **Parser** in `euercli/cli.py` registrieren.
4. `set_defaults(func=cmd_<name>)` setzen.
5. **Tests** in `tests/test_cli_*.py` (CLI-Integration) und ggf. `tests/test_services_*.py` (Service-Unit-Tests) ergänzen.
6. Betroffene **Spec** in `specs/` prüfen und bei nicht trivialen Features
   ergänzen oder anlegen. Nach Umsetzung `## Status` und die Tabelle unten
   aktualisieren.

### Plugins (Entry Points)

Plugins registrieren Commands über `euer.commands`. Der Entry Point muss entweder
eine callable sein oder ein Objekt mit `setup(subparsers)`.

## Code- und Sprachkonventionen

Python 3.11+, moderne Typannotationen und Standardbibliothek bevorzugen;
`openpyxl` bleibt optional. CLI-Argumente nach Möglichkeit abwärtskompatibel
halten. Ausführliche Regeln stehen in [AGENTS.md](AGENTS.md).

Das Projekt folgt einer klaren Zweiteilung:

| Schicht | Sprache | Beispiel |
|---------|---------|----------|
| **CLI-Ausgabe** (Fehlermeldungen, Prompts, Labels, Tabellen-Header, Zusammenfassungen) | **Deutsch** | `"Keine Ausgaben gefunden."`, `"Wertstellung"`, `"Kategorie"` |
| **Code-Interna** (Funktionen, Variablen, Klassen, Module) | **Englisch** | `create_expense()`, `expense_total`, `PrivateTransfer` |
| **Konstanten** (Namen) | **Englisch** | `ENTERTAINMENT_CATEGORY`, `DEFAULT_DB_PATH` |
| **DB-Schema** (Tabellen, Spalten, Indizes, Enum-Werte) | **Englisch** | `expenses`, `payment_date`, `is_private_paid` |
| **Kategorienamen** (`SEED_CATEGORIES`) | **Deutsch** | Bilden offizielle ELSTER-Positionen ab |
| **CLI-Commands & Flags** | **Englisch** | `add`, `--vendor`, `--amount` |
| **Docstrings & Kommentare** | **Deutsch** | `"""Erzeugt einen eindeutigen Hash."""` |
| **Dokumentation** (README, Specs, Skill-Referenzen) | **Deutsch** | Zielgruppe sind deutschsprachige Nutzer |
| **Tests** (Methodennamen, Klassen) | **Englisch** | `test_create_expense()`, `ExpenseServiceTestCase` |

**Kurzregel:** Alles, was der Nutzer sieht → Deutsch. Alles im Code → Englisch.
Ausnahme: Kategorienamen und Fachbegriffe in User-Strings bleiben Deutsch (ELSTER-Bezug).

## Tests

```bash
make test
make lint
make coverage
```

Zusätzliche Unit-Tests liegen in `tests/test_services_*.py` und laufen gegen
eine In-Memory SQLite DB.

Die CI prüft Python 3.11 auf Linux, macOS und Windows sowie Python 3.14 auf Linux.
Ein zusätzlicher Job testet die optionalen XLSX-Exporte und erstellt einen
Coverage-Bericht. Die aktuelle Matrix steht in `.github/workflows/ci.yml`.

Weitere Details: `TESTING.md`.

## Checkliste vor dem Entwickeln

Bevor du Code schreibst oder änderst:

- [ ] `DEVELOPMENT.md` gelesen (dieses Dokument)
- [ ] Betroffene Service-Funktionen in `euercli/services/` identifiziert
- [ ] Keine direkten SQL-Writes in `euercli/commands/` geplant
- [ ] Bestehende Tests laufen: `make test`
- [ ] Bei Schema-Änderungen: `euercli/schema.py` und Migration in
  `euercli/migrations.py` geplant
- [ ] Bei neuen Features: Spec in `specs/` angelegt oder bestehendes Spec erweitert
- [ ] Bei implementierten Specs: `docs/RELEASE_NOTES.md` auf nötige Upgrade-Hinweise prüfen

## Dokumentations-Checkliste vor Abschluss

Bei jeder nutzerwirksamen Änderung die folgenden Dokumente auf Betroffenheit
prüfen und nötige Anpassungen im selben Change durchführen:

- [ ] `docs/skills/euer-buchhaltung/references/cli_reference.md`: CLI-Aufrufe, Felder und Produktgrenzen aktualisiert.
- [ ] `docs/USER_JOURNEY.md`: betroffene Schritte vom Onboarding über Belegerfassung,
  Rückfragen und Monatsabgleich bis UStVA, Jahresabschluss und Upgrade aktualisiert.
  Aufgaben von Nutzer und Agent, vorläufige Ergebnisse und Übergabe an ELSTER prüfen.
- [ ] `docs/skills/euer-buchhaltung/references/domain_rules.md`: bestehende Antworten abgeglichen; wiederkehrende Fragen und
  fehleranfällige Sonderfälle bei Bedarf ergänzt und aus der Journey verlinkt.
- [ ] Skill, Referenzen und Agenten-/Onboarding-Templates auf konsistente Regeln geprüft.
- [ ] `README.md`, Spec-Status und diese Dokumentation abgeglichen.
- [ ] `docs/RELEASE_NOTES.md`: nutzerrelevante Änderungen und Upgrade-Schritte unter
  `Unveröffentlicht` oder der nächsten Version dokumentiert.

Bei Steuer- und Formularänderungen Geltungsjahr und amtliche Quellen nennen.
BMF-Formularzuordnung und verifizierte Mein-ELSTER-Oberfläche auseinanderhalten;
keine ungeprüften Jahresnummern fortschreiben. Beispiele gegen die aktuelle CLI
prüfen und relative Dokumentationslinks kontrollieren.

## Backlog & Spezifikationen

`specs/` enthält Feature-Specs mit standardisierten Status-Werten.

**Status-Werte:** `Offen` · `Implementiert`

Offene Change Requests werden innerhalb der jeweiligen Spec dokumentiert.

| Spec | Titel | Status |
|------|-------|--------|
| 001 | Init & Core CLI | Implementiert |
| 002 | Beleg-Management | Implementiert |
| 003 | Modularisierung | Implementiert |
| 004 | Steuerlogik (KU/Standard) | Implementiert |
| 005 | Refactoring Open Core | Implementiert |
| 006 | Rechnungs-/Wertstellungsdatum | Implementiert |
| 007 | Windows-Kompatibilität | Implementiert |
| 008 | Privateinlagen & Privatentnahmen | Implementiert |
| 009 | Service-Layer-Architektur (Import) | Implementiert |
| 010 | Kontenrahmen (Buchungskonten je Kategorie) | Implementiert |
| 011 | Reverse-Charge-Typ (EU vs. Drittland) | Implementiert |
| 012 | `vat-report` | Implementiert |
| 013 | Belegordner Jahr zuerst | Implementiert |
| 014 | HTML-Prüfbericht für Buchungen | Offen |
| 015 | Multi-Channel-Distribution (PyPI, GitHub Releases, Homebrew) | Implementiert |
| 016 | Agent-Safety & Guardrails (Schutz vor destruktiven Aktionen & Plausibilität) | Implementiert |
| 017 | Nicht eingebuchte Belege erkennen (`receipt unbooked`) | Offen |
| 018 | Bewirtungsaufwendungen, Vorsteuer und EÜR-Zuordnung (inkl. Review-Korrekturen) | Implementiert |
| 019 | `euer doctor` (Umgebungs- und Pre-Flight-Diagnose) | Implementiert |
| 020 | Transparente und sichere DB-Migrationen | Implementiert |
| 021 | Versionierte Exportläufe mit Manifest | Offen |
| 022 | Versionierter Skill als primäre Dokumentation und Bestätigung in der Config | Implementiert |
| 023 | Nachvollziehbarer Entscheidungsnachweis für Buchungen | Offen |
| 024 | Versionierter Regelkatalog für Entscheidungsnachweise | Offen |
| 025 | Optionale Rechnungsnummer | Implementiert |

### Agenten-Dateien und Mandantendaten

`euer` ist konsequent für KI-Agenten als primäre Nutzer gebaut: Der Mensch hinter dem
Agenten bedient die CLI in der Regel nicht selbst, sondern delegiert die Buchhaltung
mit dem Ziel einer möglichst fehlerfreien, autonomen Erfassung.

Der Buchhaltungs-Skill beschreibt die allgemeine euer-Bedienung, Prüfabläufe und das
Onboarding. Da moderne KI-Agenten eine im Projektordner hinterlegte `AGENTS.md`
automatisch berücksichtigen, fungiert die persönliche `AGENTS.md` im Buchhaltungsordner
als **Mandanten-Dossier** und enthält ausschließlich betriebliche und steuerliche Angaben
(Steuerstatus, Konten, Pfade, Lieferantenregeln und Sonderfälle) — **keine Coding-Anweisungen**.
Die Repository-`AGENTS.md` bleibt hingegen eine reine Entwickleranweisung für die Software selbst.
Skill- oder Paketupdates dürfen das persönliche Dossier nicht automatisch ersetzen.
Die kanonische Skill-Quelle liegt in `docs/skills/euer-buchhaltung/`; der Build
kopiert sie nach `euercli/assets/skill/`. Änderungen am Skill erhöhen dessen
`metadata.version` unabhängig von `euercli.VERSION`. Der Agent bestätigt die
geladene Version mit `euer setup --set skill.version VERSION`.
EÜR-Zeilennummern sind jahrabhängige Formularmetadaten und werden für ein
konkretes Jahr mit `euer list categories --year YYYY` abgefragt, nicht als
dauerhafte Lieferantenregel gespeichert.
Der Skill enthält Rolle, Grundregeln und den Beleg- und Kontoauszugsablauf auch
für allgemeine Agenten.
`docs/templates/accountant-role.md` ist ein optionaler kurzer Einstieg für
spezialisierte Agenten.
Ändern sich Skill, Rolle, Agenten-Adapter oder Onboarding, erhält der nächste
unveröffentlichte Versionsabschnitt in `docs/RELEASE_NOTES.md` einen Block
„Agenten-Dateien“ mit konkretem Update- und Prüfbedarf pro Bereich.

## Versionierung

Das Projekt verwendet [Semantic Versioning](https://semver.org/lang/de/) (`MAJOR.MINOR.PATCH`).

Die Version wird nur in `euercli/__init__.py` gepflegt. `pyproject.toml` übernimmt sie
über Setuptools Dynamic Metadata:

| Datei | Feld |
|-------|------|
| `euercli/__init__.py` | `VERSION = "X.Y.Z"` |
| `pyproject.toml` | `dynamic = ["version"]` und `attr = "euercli.VERSION"` |

### Automatisierung

Ein Skript `scripts/bump-version.sh` automatisiert das Erhöhen der kanonischen Versionsquelle.
Es kann auch bequem über `make bump-patch` (bzw. `bump-minor`, `bump-major`) aufgerufen werden.

### Wann die Version erhöhen?

| Änderungstyp | Release | Beispiel |
|--------------|---------|----------|
| Nutzerwirksamer, abwärtskompatibler Bugfix | PATCH | `0.7.0` → `0.7.1` |
| Neues abwärtskompatibles Feature oder Command | MINOR | `0.7.1` → `0.8.0` |
| Breaking Change an Schema oder CLI-API | MAJOR | `0.8.0` → `1.0.0` |
| Nur CI, Tests, Refactoring oder Entwicklerdoku | Kein eigener Release nötig | Im nächsten Release enthalten |

### Release-Notes-Workflow

1. Vor dem Eintragen einer Änderung klären, welche Version zuletzt **veröffentlicht**
   wurde. Im Zweifel nicht allein aus der obersten Überschrift der Release Notes auf den
   Veröffentlichungsstatus schließen.
2. Abschnitte bereits veröffentlichter Versionen bleiben historisch unverändert. Ein
   später entdeckter Bugfix gehört niemals nachträglich in diesen Abschnitt.
3. Änderungen ohne fest geplanten Release zunächst unter `## Unveröffentlicht`
   dokumentieren. Sobald die Veröffentlichung vorbereitet wird, den Inhalt in einen
   neuen Abschnitt `## X.Y.Z` verschieben.
4. Bei einem unmittelbar geplanten Release kann direkt ein Abschnitt für die nächste
   Version angelegt werden.
5. Release Notes beschreiben primär nutzerrelevante Änderungen. Interne Test- oder
   CI-Details nur erwähnen, wenn sie eine relevante Plattform- oder Qualitätsgarantie
   dokumentieren.
6. Immer angeben, ob bestehende Installationen Datenbank-, Konfigurations- oder andere
   Migrationsschritte benötigen. Falls nicht, dies ausdrücklich festhalten.

### Pflicht vor jedem Release

1. Passenden SemVer-Bump festlegen.
2. Version ausschließlich in `euercli/__init__.py` erhöhen (bevorzugt via Script/Make).
3. Sicherstellen, dass die gebauten Paketmetadaten diese kanonische Version übernehmen.
4. Einen neuen Abschnitt in `docs/RELEASE_NOTES.md` anlegen; niemals einen bereits
   veröffentlichten Abschnitt um neue Änderungen ergänzen.
5. Bei Nutzer-, Schema-, CLI-, Import-/Export-, Steuerlogik- oder Agenten-Änderungen
   konkrete Upgrade- und Migrationsschritte ergänzen.
6. `make test`, `make lint` und `make build` erfolgreich ausführen; anschließend den
   Artefakt-Smoke-Test mit `.venv/bin/python -m scripts.verify_artifacts dist` ausführen.
7. Den Release-Commit auf `main` bringen, einen annotierten Tag passend zur
   kanonischen Version erstellen und lokal mit `make release-check` prüfen:

   ```bash
   release_version=$(.venv/bin/python -c 'from euercli import VERSION; print(VERSION)')
   git tag -a "v${release_version}" -m "Release v${release_version}"
   make release-check
   git push origin "v${release_version}"
   ```

   Das Pushen des geschützten Tags ist die einzige reguläre manuelle Veröffentlichung.
   Die Pipeline validiert den Tag, baut Wheel und sdist genau einmal, prüft dieselben
   Artefakte und veröffentlicht sie über PyPI und GitHub. Das separate Homebrew-Tap
   aktualisiert die Formel aus der veröffentlichten PyPI-Version in seinem geplanten
   oder manuellen Workflow-Lauf.

### Recovery-Runbook

- Schlägt `validate`, `test`, `build` oder `verify-artifacts` fehl, gibt es noch
  keinen externen Upload. Ursache beheben und Release-Prozess mit korrigierter
  Version bzw. korrigiertem Tag erneut vorbereiten.
- Schlägt `github-draft` fehl, darf der Job desselben Laufs wiederholt werden. Ein
  vorhandener Draft wird aktualisiert; ein bereits veröffentlichtes Release wird nie
  überschrieben.
- Nach einem erfolgreichen PyPI-Upload wird `publish-pypi` nicht erneut ausgeführt.
  Schlägt danach GitHub fehl, wird ausschließlich `publish-github` wiederholt und der
  vorhandene Draft veröffentlicht.
- Ein Homebrew-Fehler macht PyPI und GitHub nicht ungültig. Der Tap fragt die noch nicht
  übernommene PyPI-Version beim nächsten Sechs-Stunden-Lauf erneut ab.
- `skip-existing` ist im Produktions-PyPI-Job deaktiviert. Ein unerwarteter doppelter
  Upload muss sichtbar fehlschlagen; korrigiert wird ausschließlich mit einer neuen
  PATCH-Version.
