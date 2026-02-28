# AGENTS.md - Coding Agent Guidelines

Guidelines for AI coding agents working in this repository.

> **PFLICHTLEKTÜRE VOR JEDER CODE-ÄNDERUNG:**
> Lies `DEVELOPMENT.md` bevor du Code schreibst oder änderst.
> Insbesondere den Abschnitt **Service Layer: Pflichtregeln** — alle
> Schreiboperationen auf DB-Tabellen MÜSSEN über den Service Layer laufen.
> Prüfe auch `specs/` auf offene Change Requests, die dein Feature betreffen.

## Project Overview

euer is a SQLite-based bookkeeping CLI for German Freelancers helping them create a EÜR (Einnahmenüberschussrechnung).


Modular Python CLI (package `euercli`), no external dependencies except optional `openpyxl`.


### Tests

```bash
python -m unittest discover -s tests
```

### Linting (Optional)

```bash
# If ruff is installed
ruff check euercli
ruff format euercli
```

---

## Code Style Guidelines

### Python Version

- **Minimum:** Python 3.11 (uses `tomllib` from standard library)
- Use modern type hints: `list[str]`, `dict[str, int]`, `X | None`

### Imports

Order imports as follows:
1. Standard library (alphabetical)
2. Third-party (after blank line)
3. Local modules (after blank line)


### Formatting

- **Line length:** ~100 characters (flexible)
- **Indentation:** 4 spaces
- **Quotes:** Double quotes for strings
- **Trailing commas:** Yes, in multi-line structures
- **Blank lines:** 2 between top-level functions, 1 within functions

### Type Hints

Use type hints for function signatures:

```python
def compute_hash(
    date: str, vendor_or_source: str, amount_eur: float, receipt_name: str = ""
) -> str:

def resolve_receipt_path(
    receipt_name: str,
    date: str,
    receipt_type: str,
    config: dict,
) -> tuple[Path | None, list[Path]]:
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Functions | `snake_case` | `get_db_connection()` |
| Variables | `snake_case` | `record_id`, `cat_id` |
| Constants | `UPPER_SNAKE` | `DEFAULT_DB_PATH`, `SCHEMA` |
| CLI commands | `cmd_<name>` | `cmd_add_expense()`, `cmd_list_income()` |

### Error Handling

- Print errors to `sys.stderr`
- Use `sys.exit(1)` for fatal errors
- Warnings don't exit (exit code 0)

```python
if not row:
    print(f"Fehler: Ausgabe #{args.id} nicht gefunden.", file=sys.stderr)
    sys.exit(1)

# Warning (no exit)
print(f"! Beleg '{receipt_name}' nicht gefunden:", file=sys.stderr)
```

### Database Access

- Always use `get_db_connection()` for connections
- Use `conn.row_factory = sqlite3.Row` for dict-like access
- Close connections after use
- Use parameterized queries (never string formatting!)

```python
conn = get_db_connection(db_path)
row = conn.execute("SELECT * FROM expenses WHERE id = ?", (args.id,)).fetchone()
conn.close()
```

### Audit Logging

All INSERT, UPDATE, DELETE operations must log to `audit_log`:

```python
log_audit(conn, "expenses", record_id, "INSERT", new_data=new_data)
log_audit(conn, "expenses", args.id, "UPDATE", old_data=old_data, new_data=new_data)
log_audit(conn, "expenses", args.id, "DELETE", old_data=old_data)
```

---

## Adding New Features

### New Command Pattern

> **Wichtig:** Lies zuerst `DEVELOPMENT.md` → Abschnitt „Service Layer: Pflichtregeln“
> und „Neue Commands hinzufügen“. Commands dürfen keine direkten SQL-INSERTs/UPDATEs/DELETEs
> enthalten — alle Schreiboperationen müssen über `euercli/services/` laufen.

1. Create service function in `euercli/services/` (Dataclass return, Exceptions)
2. Create `cmd_<name>(args)` in `euercli/commands/` as view-controller
3. Add parser in `main()` under appropriate subparser
4. Set defaults: `parser.set_defaults(func=cmd_<name>)`

```python
def cmd_new_feature(args):
    """Docstring describing the command."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    # ... implementation ...
    conn.close()

# In main():
new_parser = subparsers.add_parser("newcmd", help="Description")
new_parser.add_argument("--option", help="Option description")
new_parser.set_defaults(func=cmd_new_feature)
```

### Output Format

- German language for user-facing messages
- Use `format_amount()` for EUR values (German number format)
- Table output: Fixed-width columns with headers

```python
print(f"{'ID':<5} {'Datum':<12} {'Lieferant':<20} {'EUR':>10}")
print("-" * 50)
print(f"{row['id']:<5} {row['date']:<12} {row['vendor'][:20]:<20} {row['amount_eur']:>10.2f}")
```

---

## Key References

- **Developer guide: `DEVELOPMENT.md`** — Architektur, Service-Layer-Regeln, Checkliste (PFLICHTLEKTÜRE)
- Active specs: `specs/` — offene Change Requests und Backlog
- Skill for agents: `docs/skills/euer-buchhaltung/SKILL.md`
- DB schema: `euercli/schema.py`
- User guide: `docs/USER_GUIDE.md`
- Agent templates: `docs/templates/`

---

## Spec-Status pflegen

Jede Spec in `specs/` hat ein `## Status`-Feld mit einem der Werte:
`Offen` · `Implementiert`

**Pflicht:** Aktualisiere den Status und die Tabelle in `DEVELOPMENT.md` wenn:
- Eine neue Spec angelegt wird → Status `Offen`, neue Zeile in Tabelle
- Eine Spec fertig implementiert ist → Status `Implementiert`
- Change Requests hinzukommen → innerhalb der Spec dokumentieren und Status ggf. auf `Offen` zurücksetzen

## Dokumentation nach Implementierung

Nach jeder abgeschlossenen Feature-Implementierung müssen die betroffenen Dokumente
geprüft und ggf. aktualisiert werden:

- `docs/USER_GUIDE.md` — neue Befehle, Optionen, Workflows dokumentieren
- `docs/skills/euer-buchhaltung/SKILL.md` — Buchungsbeispiele und Regeln für AI-Agenten
- `docs/templates/onboarding-prompt.md` — falls neue Interview-Fragen nötig sind
- `README.md` — falls sich der Feature-Überblick ändert
- `DEVELOPMENT.md` — Architektur, Datenmodell, Spec-Tabelle und Versionierung aktualisieren
