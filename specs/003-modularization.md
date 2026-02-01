# Modularisierung - Spezifikation

## Status
**Implemented** (2026-02-01)

## Zusammenfassung

Plan zur Aufteilung der CLI in ein `euercli`-Package.

**Autor:** Markus Keller  
**Zielgruppe:** Coding Agent / LLM  
**Stand:** 2026-02-01  
**Status:** Implementiert

**Hinweis (2026-02-01):** Modularisierung ist umgesetzt. Das CLI läuft über das
Console-Script `euer` (via `pyproject.toml`) oder alternativ `python -m euercli`.
`euer.py` wurde entfernt.

---

## Trigger für Modularisierung (historisch)

Modularisierung wurde am 2026-02-01 durchgeführt (explizite Entscheidung durch Maintainer).
Diese Kriterien galten als mögliche Auslöser:

- [ ] `euer.py` überschreitet 2500 Zeilen
- [ ] Mehr als 1 aktiver Entwickler
- [ ] Komponenten sollen in anderen Projekten wiederverwendet werden
- [ ] Test-Coverage wird durch Monolith erschwert
- [x] Explizite Entscheidung durch Maintainer

---

## Historische Struktur (vor Modularisierung)

```
euer.py
├── Imports & Konstanten (1-50)
├── Schema (53-115)
├── Hilfsfunktionen (118-260)
│   ├── compute_hash()
│   ├── get_db_connection()
│   ├── format_amount()
│   ├── log_audit()
│   ├── get_category_id()
│   ├── get_category_name_with_line()
│   ├── row_to_dict()
│   ├── load_config()
│   ├── resolve_receipt_path()
│   └── warn_missing_receipt()
├── Commands (261-1390)
│   ├── cmd_init()
│   ├── cmd_add_expense(), cmd_add_income()
│   ├── cmd_list_expenses(), cmd_list_income(), cmd_list_categories()
│   ├── cmd_update_expense(), cmd_update_income()
│   ├── cmd_delete_expense(), cmd_delete_income()
│   ├── cmd_export()
│   ├── cmd_summary()
│   ├── cmd_audit()
│   ├── cmd_config_show()
│   ├── cmd_receipt_check(), cmd_receipt_open()
└── main() + CLI-Parser (1391-Ende)
```

---

## Ziel-Struktur (umgesetzt)

```
euer/
├── pyproject.toml           # Console-Script: euer -> euercli.cli:main
├── euercli/
│   ├── __init__.py          # VERSION
│   ├── __main__.py          # python -m euercli
│   ├── cli.py               # CLI-Parser + Dispatch
│   ├── constants.py         # DEFAULT_* + CONFIG_PATH
│   ├── schema.py            # SQL-Schema & Seed-Daten
│   ├── db.py                # Datenbank-Funktionen
│   ├── config.py            # Config & Beleg-Pfade
│   ├── utils.py             # Formatierung, Hashing
│   ├── importers.py         # Import-Parsing
│   └── commands/
│       ├── __init__.py      # Exportiert alle cmd_* Funktionen
│       ├── init.py          # cmd_init
│       ├── setup.py         # cmd_setup
│       ├── import_data.py   # cmd_import
│       ├── incomplete.py    # cmd_incomplete_list
│       ├── add.py           # cmd_add_expense, cmd_add_income
│       ├── list.py          # cmd_list_expenses, cmd_list_income, cmd_list_categories
│       ├── update.py        # cmd_update_expense, cmd_update_income
│       ├── delete.py        # cmd_delete_expense, cmd_delete_income
│       ├── export.py        # cmd_export
│       ├── summary.py       # cmd_summary
│       ├── audit.py         # cmd_audit
│       ├── config.py        # cmd_config_show
│       └── receipt.py       # cmd_receipt_check, cmd_receipt_open
├── tests/
├── skills/
├── specs/
└── README.md
```

---

## Modul-Aufteilung

### `euercli/db.py`

Datenbank-Operationen, keine CLI-Abhängigkeit.

```python
# Funktionen
get_db_connection(db_path: Path) -> sqlite3.Connection
log_audit(conn, table_name, record_id, action, old_data, new_data, user)
get_category_id(conn, name, cat_type) -> Optional[int]
get_category_name_with_line(conn, category_id) -> str
row_to_dict(row) -> dict
```

### `euercli/config.py`

Konfiguration und Beleg-Verwaltung.

```python
# Konstanten
CONFIG_PATH = Path.home() / ".config" / "euer" / "config.toml"

# Funktionen
load_config() -> dict
resolve_receipt_path(receipt_name, date, receipt_type, config) -> tuple[Path | None, list[Path]]
warn_missing_receipt(receipt_name, date, receipt_type, config) -> None
```

### `euercli/schema.py`

SQL-Schema und Seed-Daten.

```python
# Konstanten
SCHEMA = """..."""
SEED_CATEGORIES = [...]
DEFAULT_DB_PATH = <project_root> / "euer.db"
DEFAULT_EXPORT_DIR = <project_root> / "exports"
DEFAULT_USER = "markus"
```

### `euercli/utils.py`

Reine Utility-Funktionen ohne Seiteneffekte.

```python
compute_hash(date, vendor_or_source, amount_eur, receipt_name) -> str
format_amount(amount: float) -> str
```

### `euercli/commands/*.py`

Jede Datei enthält verwandte Commands.

```python
# Beispiel: euercli/commands/add.py
from euercli.db import get_db_connection, log_audit, get_category_id
from euercli.config import load_config, warn_missing_receipt
from euercli.utils import compute_hash, format_amount
from euercli.constants import DEFAULT_DB_PATH

def cmd_add_expense(args):
    ...

def cmd_add_income(args):
    ...
```

### CLI Entry-Point (Console Script + Module)

CLI-Parser und Dispatch sind in `euercli/cli.py`.
`pyproject.toml` registriert das Console-Script `euer`.
Zusätzlich funktioniert `python -m euercli`.

```python
euer = euercli.cli:main
```

---

## Migrations-Schritte (abgeschlossen)

### Phase 1: Vorbereitung

1. [x] Tests schreiben für kritische Funktionen (vor Refactoring)
2. [x] `euercli/` Package-Verzeichnis erstellen
3. [x] `euercli/__init__.py` mit VERSION anlegen

### Phase 2: Utils & Schema extrahieren

4. [x] `euercli/utils.py` erstellen (compute_hash, format_amount)
5. [x] `euercli/schema.py` erstellen (SCHEMA, SEED_CATEGORIES, Konstanten)
6. [x] Tests laufen lassen

### Phase 3: DB & Config extrahieren

7. [x] `euercli/db.py` erstellen
8. [x] `euercli/config.py` erstellen
9. [x] Tests laufen lassen

### Phase 4: Commands extrahieren

10. [x] `euercli/commands/__init__.py` erstellen
11. [x] Commands einzeln extrahieren
12. [x] Nach jedem Command: Tests laufen lassen

### Phase 5: Entry-Point

13. [x] Console-Script via `pyproject.toml` anlegen
14. [x] Vollständiger Test-Durchlauf
15. [x] README.md aktualisieren

---

## Kompatibilität

### Beibehaltene Schnittstellen

- Alle CLI-Argumente bleiben gleich
- Datenbank-Format unverändert
- Config-Pfad unverändert

### Breaking Changes

- `python euer.py <command>` entfällt (Datei entfernt).
- Neues Standard-Entry: `euer <command>` oder `python -m euercli <command>`.

---

## Vorteile nach Modularisierung

| Aspekt | Vorher | Nachher |
|--------|--------|---------|
| Testbarkeit | Schwer isolierbar | Unit-Tests pro Modul |
| Lesbarkeit | 1600+ Zeilen scrollen | Fokussierte Dateien |
| Wiederverwendung | Nur als Ganzes | `euer.db` importierbar |
| AI-Agent-Kontext | Alles oder nichts | Gezielte Datei lesen |
| Merge-Konflikte | Wahrscheinlich | Selten (separate Dateien) |

---

## Referenzen

- Python Packaging: https://packaging.python.org/
- Click (Alternative zu argparse): https://click.palletsprojects.com/
- Spec 001: `specs/001-init.md`
- Spec 002: `specs/002-receipts.md`
