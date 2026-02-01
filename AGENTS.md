# AGENTS.md - Coding Agent Guidelines

Guidelines for AI coding agents working in this repository.

## Project Overview

EÜR (Einnahmenüberschussrechnung) - SQLite-based bookkeeping CLI for German freelancers.
Modular Python CLI (package `euercli`), no external dependencies except optional `openpyxl`.

## Build & Run Commands

```bash
# Install (dev, for console script)
python -m pip install -e .

# Initialize database (creates euer.db + exports/)
euer init

# Run CLI
euer <command>

# Test CLI works
euer --help
euer list categories

# Test with custom database
euer --db test.db init
euer --db test.db list expenses
```

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

```python
import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Optional third-party
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
```

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

1. Create function `cmd_<name>(args)`
2. Add parser in `main()` under appropriate subparser
3. Set defaults: `parser.set_defaults(func=cmd_<name>)`

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

## File Structure

```
euer/
├── euercli/             # Core package
│   ├── cli.py           # CLI parser/dispatch
│   └── schema.py        # DB schema + seeds
├── tests/               # CLI integration tests
├── exports/             # CSV/XLSX exports
├── skills/              # AI agent skills
├── specs/               # Feature specs + backlog items
├── README.md            # Project overview
├── USER_GUIDE.md        # User documentation
├── DEVELOPMENT.md       # Developer documentation
├── TESTING.md           # Test strategy
└── AGENTS.md            # This file
```

## Key References

- Skill for agents: `skills/euer-buchhaltung/SKILL.md`
- DB schema: `euercli/schema.py`
- Developer guide: `DEVELOPMENT.md`
- User guide: `USER_GUIDE.md`
- Incomplete import design note: `technical-documentation/INCOMPLETE_ENTRIES_APPROACH.md`
