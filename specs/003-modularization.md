# Modularisierung - Spezifikation

## Zusammenfassung

Plan zur Aufteilung von `euer.py` in Module, wenn die Codebasis >2500 Zeilen erreicht oder andere Trigger erfüllt sind.

**Autor:** Markus Keller  
**Zielgruppe:** Coding Agent / LLM  
**Stand:** 2026-01-31  
**Status:** Geplant (nicht aktiv)

---

## Trigger für Modularisierung

Modularisieren wenn EINES dieser Kriterien erfüllt:

- [ ] `euer.py` überschreitet 2500 Zeilen
- [ ] Mehr als 1 aktiver Entwickler
- [ ] Komponenten sollen in anderen Projekten wiederverwendet werden
- [ ] Test-Coverage wird durch Monolith erschwert
- [ ] Explizite Entscheidung durch Maintainer

---

## Aktuelle Struktur (Stand: ~1600 Zeilen)

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

## Ziel-Struktur

```
euer/
├── euer.py                  # Entry-point (nur CLI-Parser + main)
├── euer/
│   ├── __init__.py          # Package, exportiert VERSION
│   ├── db.py                # Datenbank-Funktionen
│   ├── config.py            # Config & Beleg-Pfade
│   ├── schema.py            # SQL-Schema & Seed-Daten
│   ├── utils.py             # Formatierung, Hashing
│   └── commands/
│       ├── __init__.py      # Exportiert alle cmd_* Funktionen
│       ├── init.py          # cmd_init
│       ├── add.py           # cmd_add_expense, cmd_add_income
│       ├── list.py          # cmd_list_expenses, cmd_list_income, cmd_list_categories
│       ├── update.py        # cmd_update_expense, cmd_update_income
│       ├── delete.py        # cmd_delete_expense, cmd_delete_income
│       ├── export.py        # cmd_export, cmd_summary
│       ├── audit.py         # cmd_audit
│       └── receipt.py       # cmd_config_show, cmd_receipt_check, cmd_receipt_open
├── tests/
│   ├── __init__.py
│   ├── test_db.py
│   ├── test_config.py
│   └── test_commands/
│       └── ...
├── skills/
├── specs/
└── README.md
```

---

## Modul-Aufteilung

### `euer/db.py`

Datenbank-Operationen, keine CLI-Abhängigkeit.

```python
# Funktionen
get_db_connection(db_path: Path) -> sqlite3.Connection
log_audit(conn, table_name, record_id, action, old_data, new_data, user)
get_category_id(conn, name, cat_type) -> Optional[int]
get_category_name_with_line(conn, category_id) -> str
row_to_dict(row) -> dict
```

### `euer/config.py`

Konfiguration und Beleg-Verwaltung.

```python
# Konstanten
CONFIG_PATH = Path.home() / ".config" / "euer" / "config.toml"

# Funktionen
load_config() -> dict
resolve_receipt_path(receipt_name, date, receipt_type, config) -> tuple[Path | None, list[Path]]
warn_missing_receipt(receipt_name, date, receipt_type, config) -> None
```

### `euer/schema.py`

SQL-Schema und Seed-Daten.

```python
# Konstanten
SCHEMA = """..."""
SEED_CATEGORIES = [...]
DEFAULT_DB_PATH = Path(__file__).parent.parent / "euer.db"
DEFAULT_EXPORT_DIR = Path(__file__).parent.parent / "exports"
DEFAULT_USER = "markus"
```

### `euer/utils.py`

Reine Utility-Funktionen ohne Seiteneffekte.

```python
compute_hash(date, vendor_or_source, amount_eur, receipt_name) -> str
format_amount(amount: float) -> str
```

### `euer/commands/*.py`

Jede Datei enthält verwandte Commands.

```python
# Beispiel: euer/commands/add.py
from euer.db import get_db_connection, log_audit, get_category_id
from euer.config import load_config, warn_missing_receipt
from euer.utils import compute_hash, format_amount
from euer.schema import DEFAULT_DB_PATH

def cmd_add_expense(args):
    ...

def cmd_add_income(args):
    ...
```

### `euer.py` (Entry-Point)

Nur noch CLI-Parser und Dispatch.

```python
#!/usr/bin/env python3
"""EÜR - Einnahmenüberschussrechnung CLI"""

import argparse
from euer.schema import DEFAULT_DB_PATH, DEFAULT_EXPORT_DIR
from euer.commands import (
    cmd_init,
    cmd_add_expense, cmd_add_income,
    cmd_list_expenses, cmd_list_income, cmd_list_categories,
    cmd_update_expense, cmd_update_income,
    cmd_delete_expense, cmd_delete_income,
    cmd_export, cmd_summary,
    cmd_audit,
    cmd_config_show, cmd_receipt_check, cmd_receipt_open,
)

def main():
    parser = argparse.ArgumentParser(...)
    # ... Parser-Setup ...
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
```

---

## Migrations-Schritte

### Phase 1: Vorbereitung

1. [ ] Tests schreiben für kritische Funktionen (vor Refactoring)
2. [ ] `euer/` Package-Verzeichnis erstellen
3. [ ] `euer/__init__.py` mit VERSION anlegen

### Phase 2: Utils & Schema extrahieren

4. [ ] `euer/utils.py` erstellen (compute_hash, format_amount)
5. [ ] `euer/schema.py` erstellen (SCHEMA, SEED_CATEGORIES, Konstanten)
6. [ ] Tests laufen lassen

### Phase 3: DB & Config extrahieren

7. [ ] `euer/db.py` erstellen
8. [ ] `euer/config.py` erstellen
9. [ ] Tests laufen lassen

### Phase 4: Commands extrahieren

10. [ ] `euer/commands/__init__.py` erstellen
11. [ ] Commands einzeln extrahieren (init → add → list → update → delete → export → audit → receipt)
12. [ ] Nach jedem Command: Tests laufen lassen

### Phase 5: Entry-Point

13. [ ] `euer.py` auf Imports + main() reduzieren
14. [ ] Vollständiger Test-Durchlauf
15. [ ] README.md aktualisieren (falls nötig)

---

## Kompatibilität

### Beibehaltene Schnittstellen

- `python euer.py <command>` funktioniert unverändert
- Alle CLI-Argumente bleiben gleich
- Datenbank-Format unverändert
- Config-Pfad unverändert

### Breaking Changes

Keine für Endnutzer. Nur interne Struktur ändert sich.

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
