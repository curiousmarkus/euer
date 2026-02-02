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

- **CLI Entry Point**: `euercli/cli.py` (argparse + Dispatch).
- **Commands**: je Feature in `euercli/commands/`.
- **DB Zugriff**: zentral in `euercli/db.py` und `get_db_connection()`.
- **Schema/Seeds**: `euercli/schema.py`.
- **Config**: `euercli/config.py` (`~/.config/euer/config.toml`).
- **Import**: `euercli/importers.py` (CSV/JSONL Normalisierung).

## Implementierte Funktionalitaeten (Kurzueberblick)

Dieser Abschnitt hilft Contributor:innen, bestehende Features zu verstehen,
damit Erweiterungen konsistent und risikoarm umgesetzt werden koennen.

- **Core CLI**: `init`, `setup`, `config show`, `list categories`.
- **Buchungen**: `add`, `list`, `update`, `delete` fuer `expenses` und `income`.
- **Audit-Log**: Jede Aenderung (INSERT/UPDATE/DELETE) wird protokolliert.
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

## Datenmodell (Überblick)

Die vollständigen DDLs stehen in `euercli/schema.py`.

- **categories**: Name, EÜR‑Zeile, Typ (expense/income).
- **expenses**: Ausgaben inkl. Beleg, Konto, Fremdwährung, RC‑Flags, Steuern.
- **income**: Einnahmen inkl. Beleg, Fremdwährung, Umsatzsteuer.
- **audit_log**: Protokolliert INSERT/UPDATE/DELETE inkl. Vorher/Nachher.

## Audit‑Logging (Pflicht)

Jede Änderung an `expenses` oder `income` muss in `audit_log` landen.
Verwende `log_audit()` nach INSERT/UPDATE/DELETE.

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

1. `cmd_<name>(args)` in `euercli/commands/` implementieren.
2. Parser in `euercli/cli.py` registrieren.
3. `set_defaults(func=cmd_<name>)` setzen.

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

Weitere Details: `TESTING.md`.

## Beiträge

- Kleine, fokussierte PRs bevorzugt.
- Bitte relevante Doku aktualisieren (`README.md`, `USER_GUIDE.md`, `DEVELOPMENT.md`).
- User‑Facing Texte auf Deutsch halten.

## Backlog & Spezifikationen

`specs/` enthält historische Implementierungs‑Specs und zukünftige Backlog‑Items.
Neue Features sollten dort kurz beschrieben werden.
