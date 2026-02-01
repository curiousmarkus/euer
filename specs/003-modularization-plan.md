# Modularisierung - Technischer Plan (Stand 2026-02-01)

Hinweis: Umsetzung abgeschlossen. CLI läuft über `euer` (Console-Script) oder
`python -m euercli`. `euer.py` wurde entfernt.

## Ziele
- `euer.py` in klar abgegrenzte Module aufteilen, ohne funktionale Aenderungen.
- Imports und Abhaengigkeiten so strukturieren, dass zirkulaere Imports vermieden werden.
- CLI-Entry-Point stabil halten (Tests und README muessen weiter funktionieren).

## Nicht-Ziele
- Keine neuen Features, keine Datenmigrationen, keine Veraenderung der DB-Struktur.
- Keine Aenderung der CLI-Argumente oder Ausgaben (nur refactor).

## Entscheidungsbedarf (vor Start klaeren)
1) **Namenskonflikt Entry-Point vs Package**
   - Problem: Ein `euer.py` neben einem `euer/` Package verhindert `from euer import ...`.
   - Empfehlung: Entry-Point umbenennen (z.B. `euer_cli.py`) und `python -m euer` via
     `euer/__main__.py` anbieten.
   - Alternative: Package-Namen aendern (z.B. `euerlib/`), `euer.py` beibehalten.
2) **Default-Pfade (DB/exports)**
   - Heute: Pfade relativ zum Repo (`Path(__file__).parent`).
   - Entscheidung: Repo-relativ beibehalten oder in User-Datenverzeichnis wechseln.
3) **Optionales `openpyxl`**
   - Import moeglichst in `commands/export.py` kapseln, damit der Rest ohne Import funktioniert.

## Aktualisierte Zielstruktur (Vorschlag)
```
euer/
├── euer_cli.py              # neuer Entry-Point (oder euer.py, falls Paketname aendert)
├── euer/
│   ├── __init__.py          # VERSION
│   ├── __main__.py          # python -m euer
│   ├── constants.py         # DEFAULT_* , CONFIG_PATH
│   ├── schema.py            # SCHEMA, SEED_CATEGORIES
│   ├── db.py                # DB-Helpers + log_audit
│   ├── config.py            # TOML, setup helpers, receipt paths
│   ├── utils.py             # compute_hash, format_amount, parse_*
│   ├── importers.py         # import helpers (CSV/JSON), normalize_import_row
│   └── commands/
│       ├── __init__.py
│       ├── init.py          # cmd_init
│       ├── setup.py         # cmd_setup
│       ├── import_data.py   # cmd_import (kein "import.py" wegen Keyword)
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
│   └── test_cli.py
└── README.md
```

## Abhaengigkeitsregeln (import graph)
- `constants.py` enthaelt nur Konstanten, keine Imports aus anderen Modulen.
- `schema.py` importiert nur `constants.py`.
- `db.py` importiert `constants.py` (fuer DEFAULT_USER) und `schema.py` nur falls noetig.
- `config.py`, `utils.py`, `importers.py` importieren keine `commands`.
- `commands/*` importieren aus `db.py`, `config.py`, `utils.py`, `schema.py`, `importers.py`.

## Technischer Ablauf (inkrementell)
### Phase 0 - Baseline
1) Tests als Ausgangsbasis laufen lassen (`python -m unittest tests/test_cli.py`).
2) Entscheidung zu Entry-Point vs Package treffen und dokumentieren.

### Phase 1 - Package-Skeleton
1) `euer/` anlegen, `__init__.py` (VERSION) und `__main__.py` erstellen.
2) `constants.py` erstellen (DEFAULT_DB_PATH, DEFAULT_EXPORT_DIR, DEFAULT_USER, CONFIG_PATH).
3) `schema.py` erstellen (SCHEMA, SEED_CATEGORIES).
4) Entry-Point anpassen (je nach Entscheidung):
   - Neuer `euer_cli.py` nutzt `from euer.commands import ...`
   - Oder Package umbenennen und `euer.py` bleibt Entry-Point.
5) README/TESTING anpassen, falls Entry-Point-Name aendert.

### Phase 2 - Utils + Importer
1) `utils.py`: compute_hash, format_amount, parse_bool, parse_amount, format_missing_fields.
2) `importers.py`: get_row_value, parse_import_type, get_tax_config,
   normalize_import_row, iter_import_rows.
3) Tests laufen lassen.

### Phase 3 - Config
1) `config.py`: load_config, save_config, dump_toml, toml_* helpers,
   prompt_path, normalize_receipt_path, resolve_receipt_path, warn_missing_receipt.
2) Tests laufen lassen.

### Phase 4 - DB Layer
1) `db.py`: get_db_connection, log_audit, get_category_id,
   get_category_name_with_line, row_to_dict.
2) Tests laufen lassen.

### Phase 5 - Commands extrahieren
1) Pro Datei eine Command-Gruppe auslagern, nach jedem Schritt Tests laufen lassen.
2) Reihenfolge (empfohlen):
   - init -> setup -> import_data -> incomplete -> add -> list -> update
   - delete -> export -> summary -> audit -> config -> receipt
3) `commands/__init__.py` pflegen, um Imports im Entry-Point stabil zu halten.

### Phase 6 - Aufraeumen
1) `euer.py` (oder `euer_cli.py`) auf reinen Parser + Dispatch reduzieren.
2) Doppelte/alte Funktionen in `euer.py` entfernen.
3) README/TESTING/AGENTS aktualisieren (Befehle, Dateistruktur).
4) Finale Tests.

## Teststrategie (manuell)
- Minimum: `python -m unittest tests/test_cli.py`
- Optional: `ruff check euer.py` (oder neuer Entry-Point) + relevante Module.

## Risiken & Gegenmassnahmen
- **Namenskonflikt Package/Entry-Point**: vor Start entscheiden, sonst Importfehler.
- **Zirkulaere Imports**: Abhaengigkeitsregeln strikt einhalten.
- **Pfad-Semantik**: Default-DB/Export-Pfade explizit definieren und dokumentieren.
