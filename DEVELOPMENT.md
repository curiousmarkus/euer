# Developer Guide

Dieses Dokument richtet sich an Maintainer und Beitragende. Es beschreibt Aufbau,
Architektur und Entwicklungs‑Workflows.

## Setup

```bash
python -m pip install -e .

# Datenbank lokal anlegen
euer init
```

Ohne Installation:

```bash
python -m euercli <command>
```

## Projektstruktur (Kurzüberblick)

```
euer/
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
├── skills/                  # AI Agent Skills
├── USER_GUIDE.md            # Nutzer:innen-Doku
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
damit Erweiterungen konsistent und risikoarm umgesetzt werden koennen.

- **Core CLI**: `init`, `setup`, `config show`, `list categories`.
- **Buchungen**: `add`, `list`, `update`, `delete` fuer `expenses` und `income`.
- **Audit-Log**: Jede Aenderung (INSERT/UPDATE/DELETE) wird protokolliert.
- **Service Layer**: Logik ist typisiert (Dataclasses) und nutzt Exceptions statt `sys.exit()`.
- **Import**: CSV/JSONL mit Normalisierung, Duplikat-Schutz (Hash).
- **Incomplete**: unvollstaendige Buchungen werden live aus `expenses`/`income` berechnet.
- **Summary**: Jahreszusammenfassung inkl. RC/Steuerlogik.
- **Export**: CSV (immer), XLSX optional via `openpyxl`.
- **Receipts**: Belegpfade in Config, Check + Open.
- **Steuermodi**: `small_business` und `standard` (RC Handling inkl. USt/VoSt).

Wenn du ein Feature erweiterst, beachte:
- **Konventionen**: deutschsprachige Ausgaben, parametrisierte SQL, Audit-Log.
- **Kompatibilitaet**: CLI-Argumente sollten abwaertskompatibel bleiben.
- **Tests**: Passe `tests/test_cli.py` an oder erweitere es bei Feature-Aenderungen.
- **Service Layer**: Alle Schreiboperationen gehören in `euercli/services/` (siehe Pflichtregeln oben).

## Datenmodell (Überblick)

Die vollständigen DDLs stehen in `euercli/schema.py`.

- **categories**: UUID, Name, EÜR‑Zeile, Typ (expense/income).
- **expenses**: UUID, Ausgaben inkl. Beleg, Konto, Fremdwährung, RC‑Flags, Steuern, Private Klassifikation.
- **income**: UUID, Einnahmen inkl. Beleg, Fremdwährung, Umsatzsteuer.
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

## Import & Incomplete

Der Import akzeptiert CSV/JSONL. Pflichtfelder:
`type`, `date`, `party`, `amount_eur`.

Fehlende Pflichtfelder brechen den Import ab. Unvollständige Buchungen werden
über `euer incomplete list` live berechnet (fehlende `category`, `receipt`,
`vat`, `account`). Details siehe
`technical-documentation/INCOMPLETE_ENTRIES_APPROACH.md`.

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

## Tests

```bash
python -m unittest discover -s tests
```

Zusätzliche Unit-Tests liegen in `tests/test_services_*.py` und laufen gegen
eine In-Memory SQLite DB.

Weitere Details: `TESTING.md`.

## Beiträge

- Kleine, fokussierte PRs bevorzugt.
- Bitte relevante Doku aktualisieren (`README.md`, `docs/USER_GUIDE.md`, `DEVELOPMENT.md`).
- User‑Facing Texte auf Deutsch halten.

## Checkliste vor dem Entwickeln

Bevor du Code schreibst oder änderst:

- [ ] `DEVELOPMENT.md` gelesen (dieses Dokument)
- [ ] Betroffene Service-Funktionen in `euercli/services/` identifiziert
- [ ] Keine direkten SQL-Writes in `euercli/commands/` geplant
- [ ] Bestehende Tests laufen: `python -m unittest discover -s tests`
- [ ] Bei Schema-Änderungen: `euercli/schema.py` + Migration in `commands/init.py`
- [ ] Bei neuen Features: Spec in `specs/` angelegt oder bestehendes Spec erweitert

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
| 006 | Rechnungs-/Wertstellungsdatum | Offen |
| 007 | Windows-Kompatibilität | Implementiert |
| 008 | Privateinlagen & Privatentnahmen | Implementiert |
| 009 | Service-Layer-Architektur (Import) | Offen |
