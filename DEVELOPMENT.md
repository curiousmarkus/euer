# Developer Guide

Dieses Dokument richtet sich an Maintainer und Beitragende. Es beschreibt Aufbau,
Architektur und Entwicklungs‑Workflows.

## Setup

### macOS und Linux

```bash
make install

# Datenbank lokal anlegen
.venv/bin/euer init
```

Die Entwicklungsumgebung enthält Ruff, Coverage, das Build-Werkzeug und die optionale
XLSX-Unterstützung. Ohne Installation kann die CLI über das System-Python gestartet
werden:

```bash
python3 -m euercli <command>
```

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,xlsx]"
python -m euercli init
```

## Projektstruktur (Kurzüberblick)

```
euer/
├── .github/workflows/      # Automatisierte Tests und Qualitätsprüfungen
├── euercli/                 # Core Package
│   ├── cli.py               # CLI Parser + Dispatch
│   ├── commands/            # Command Implementierungen
│   ├── services/            # Service Layer (Business-Logik, Plugin-API)
│   ├── db.py                # DB Helpers
│   ├── schema.py            # DB Schema + Seeds
│   ├── importers.py         # Import Normalisierung
│   └── config.py            # Config Laden/Speichern
├── tests/                   # CLI Integrationstests (unittest)
├── specs/                   # Historische Anforderungen + Backlog Items
├── docs/
│   ├── USER_GUIDE.md         # Nutzer:innen-Doku
│   ├── RELEASE_NOTES.md      # Upgrade-Hinweise für bestehende lokale Instanzen
│   ├── skills/               # AI Agent Skills
│   └── templates/            # Agent-Konfigurationsvorlagen
├── CONTRIBUTING.md          # Einstieg für Beiträge und Pull Requests
├── DEVELOPMENT.md           # Diese Datei
└── TESTING.md               # Teststrategie
```

## Architektur

### Schichtenmodell

```
┌─────────────────────────────────────────────┐
│  CLI Layer (euercli/cli.py + commands/)      │  argparse, Ausgabe, sys.exit
├─────────────────────────────────────────────┤
│  Service Layer (euercli/services/)           │  Business-Logik, Validierung, Audit
├─────────────────────────────────────────────┤
│  Data Layer (euercli/db.py, schema.py)       │  DB-Zugriff, Schema, Helpers
├─────────────────────────────────────────────┤
│  SQLite (euer.db)                            │  Persistenz
└─────────────────────────────────────────────┘
```

- **CLI Entry Point**: `euercli/cli.py` (argparse + Dispatch).
- **Commands**: je Feature in `euercli/commands/` (View-Controller, keine Logik).
- **Service Layer**: `euercli/services/` als stabile API (keine Prints, keine argparse-Abhängigkeit).
- **DB Zugriff**: zentral in `euercli/db.py` und `get_db_connection()`.
- **Schema/Seeds**: `euercli/schema.py`.
- **Config**: `euercli/config.py` (`~/.config/euer/config.toml`).
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
| Exceptions werfen | ✅ `ValidationError`, `RecordNotFoundError` | ❌ Fangen und in Ausgabe übersetzen |
| `conn.commit()` | ✅ Nach einzelner Operation | ⚠️ Nur bei Batch-Steuerung |

**Beispiel (korrekt):**
```python
# commands/add.py — delegiert an Service
def cmd_add_expense(args):
    conn = get_db_connection(db_path)
    expense = create_expense(conn, date=args.date, vendor=args.vendor, ...)
    print(f"Ausgabe #{expense.id} angelegt.")
    conn.close()
```

**Anti-Pattern (VERBOTEN):**
```python
# commands/import_data.py — NICHT SO! Direkte SQL-INSERTs umgehen den Service Layer
def cmd_import(args):
    conn.execute("INSERT INTO expenses (...) VALUES (...)", (...))
    log_audit(conn, ...)  # Audit manuell → fehleranfällig
```

## Implementierte Funktionalitaeten (Kurzueberblick)

Dieser Abschnitt hilft Contributor:innen, bestehende Features zu verstehen,
damit Erweiterungen konsistent und risikoarm umgesetzt werden können.

- **Core CLI**: `init`, `setup`, `config show`, `list categories`.
- **Buchungen**: `add`, `list`, `update`, `delete` für `expenses` und `income`.
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
- **Receipts**: Jahrzentrierte Belegpfade (`root/{year}/Typ`), Check + Open.
- **Steuermodi**: `small_business` und `standard` (RC Handling inkl. USt/VoSt).
- **Persistierte USt-Klassifikation**: `vat_rate` und `vat_code` an
  Ausgaben/Einnahmen für auditierbare UStVA-Reports.
- **RC-Typ**: Reverse-Charge-Ausgaben speichern `none`, `eu`,
  `third_country` oder den Migrationszustand `unclassified`.

## Versionierung

Das Projekt verwendet [Semantic Versioning](https://semver.org/lang/de/) (`MAJOR.MINOR.PATCH`).

Die Version wird an **zwei Stellen** gepflegt — beide MÜSSEN synchron aktualisiert werden:

| Datei | Feld |
|-------|------|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `euercli/__init__.py` | `VERSION = "X.Y.Z"` |

### Automatisierung

Ein Skript `scripts/bump-version.sh` automatisiert das Erhöhen der Version an beiden Stellen.
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
2. Version in `pyproject.toml` und `euercli/__init__.py` erhöhen (bevorzugt via Script/Make).
3. Sicherstellen, dass beide Dateien den **identischen** Versionsstring haben.
4. Einen neuen Abschnitt in `docs/RELEASE_NOTES.md` anlegen; niemals einen bereits
   veröffentlichten Abschnitt um neue Änderungen ergänzen.
5. Bei Nutzer-, Schema-, CLI-, Import-/Export-, Steuerlogik- oder Agenten-Änderungen
   konkrete Upgrade- und Migrationsschritte ergänzen.
6. Alle Tests und Qualitätsprüfungen müssen grün sein (`make test` und `make lint`; unter
   Windows `python -m unittest discover -s tests`).

## Entwicklungs-Richtlinien

Wenn du ein Feature erweiterst, beachte:
- **Konventionen**: deutschsprachige Ausgaben, parametrisierte SQL, Audit-Log.
- **Kompatibilität**: CLI-Argumente sollten abwärtskompatibel bleiben.
- **Tests**: Passe `tests/test_cli.py` an oder erweitere es bei Feature-Änderungen.
- **Service Layer**: Alle Schreiboperationen gehören in `euercli/services/` (siehe Pflichtregeln oben).

## Datenmodell (Überblick)

Die vollständigen DDLs stehen in `euercli/schema.py`.

- **categories**: UUID, Name, EÜR‑Zeile, Typ (expense/income).
- **expenses**: UUID, Ausgaben inkl. Beleg, Konto, Fremdwährung, RC‑Typ,
  Steuern, USt-Klassifikation, Private Klassifikation.
- **income**: UUID, Einnahmen inkl. Beleg, Fremdwährung, Umsatzsteuer,
  USt-Klassifikation.
- **private_transfers**: UUID, Privateinlagen/-entnahmen, Betrag, optionale Referenz auf Expense.
- **audit_log**: Protokolliert INSERT/UPDATE/DELETE inkl. Vorher/Nachher + `record_uuid`.

Hinweis: `euer init` legt fehlende Tabellen/Spalten an.

## Audit‑Logging (Pflicht)

Jede Änderung an `expenses` oder `income` muss in `audit_log` landen.
Verwende `log_audit()` nach INSERT/UPDATE/DELETE und schreibe `record_uuid`.

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

Der Import akzeptiert CSV/JSONL. Pflichtfelder:
`type`, `date`, `party`, `amount_eur`.

Fehlende Pflichtfelder brechen den Import ab. Unvollständige Buchungen werden
über `euer incomplete list` live berechnet (fehlende `category`, `receipt`,
`vat`, `account`). Details siehe
`technical-documentation/INCOMPLETE_ENTRIES_APPROACH.md`.

Der Import akzeptiert zusätzlich UStVA-Klassifikationsfelder (`vat_rate`,
`vat_code`, `tax_free`) für round-trip-fähige Exporte und Reports.

## Neue Commands hinzufügen

1. **Service-Funktion** in `euercli/services/` implementieren (Dataclass-Return, Exceptions).
2. **Command** `cmd_<name>(args)` in `euercli/commands/` als View-Controller implementieren.
   - Command ruft Service-Funktionen auf, keine direkten SQL-INSERTs/UPDATEs/DELETEs.
   - Command fängt `ValidationError` / `RecordNotFoundError` und gibt Fehlermeldung aus.
3. **Parser** in `euercli/cli.py` registrieren.
4. `set_defaults(func=cmd_<name>)` setzen.
5. **Tests** in `tests/test_cli.py` (CLI-Integration) und ggf. `tests/test_services_*.py` (Service-Unit-Tests) ergänzen.
6. **Spec** in `specs/` dokumentieren, falls das Feature nicht-trivial ist.

### Plugins (Entry Points)

Plugins registrieren Commands über `euer.commands`. Der Entry Point muss entweder
eine callable sein oder ein Objekt mit `setup(subparsers)`.

## Code‑Konventionen (Kurzfassung)

- Python 3.11+, Typ‑Hints in Signaturen.
- Standard‑Library bevorzugen; `openpyxl` optional.
- Parametrisierte SQL‑Queries.
- User‑Facing Text auf Deutsch.

Ausführliche Guidelines: `AGENTS.md`.

### Sprachkonvention: Deutsch vs. Englisch

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
| **Dokumentation** (README, Specs, User Guide) | **Deutsch** | Zielgruppe sind deutschsprachige Nutzer |
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

Die CI prüft Python 3.11 auf Linux, macOS und Windows sowie die aktuelle unterstützte
Python-Version auf Linux. Ein zusätzlicher Job testet die optionalen XLSX-Exporte und
erstellt einen Coverage-Bericht.

Weitere Details: `TESTING.md`.

## Beiträge

- Der allgemeine Ablauf für Beiträge und Pull Requests steht in `CONTRIBUTING.md`.
- Kleine, fokussierte PRs bevorzugt.
- Bitte relevante Doku aktualisieren (`README.md`, `docs/USER_GUIDE.md`,
  `docs/RELEASE_NOTES.md`, `DEVELOPMENT.md`).
- User‑Facing Texte auf Deutsch halten.

## Checkliste vor dem Entwickeln

Bevor du Code schreibst oder änderst:

- [ ] `DEVELOPMENT.md` gelesen (dieses Dokument)
- [ ] Betroffene Service-Funktionen in `euercli/services/` identifiziert
- [ ] Keine direkten SQL-Writes in `euercli/commands/` geplant
- [ ] Bestehende Tests laufen: `make test`
- [ ] Bei Schema-Änderungen: `euercli/schema.py` + Migration in `commands/init.py`
- [ ] Bei neuen Features: Spec in `specs/` angelegt oder bestehendes Spec erweitert
- [ ] Bei implementierten Specs: `docs/RELEASE_NOTES.md` auf nötige Upgrade-Hinweise prüfen

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
| 014 | HTML-Pruefbericht fuer Buchungen | Offen |
| 015 | Multi-Channel-Distribution (PyPI, GitHub Releases, Homebrew) | Offen |
