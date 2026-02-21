# 005 - Refactoring für Open Core (Lightweight Architecture)

## Status

Implementiert

## Strategischer Kontext

Dieses Dokument beschreibt das Refactoring von `euercli`, um das Projekt von einem "Single-User Tool" zu einem "Open Core Produkt" zu transformieren.

**Wichtig:** Der Charakter des Tools als **leichtgewichtiges CLI-Tool ohne externe Dependencies** muss erhalten bleiben!

### Was wir NICHT wollen
*   Wir bauen **keinen** MCP-Server.
*   Wir bauen **keine** REST-API.
*   Wir fügen **keine** schweren Dependencies hinzu.

---

## Technische Spezifikation (Update)

### 1. Scope: Vollständiges Refactoring
Wir stellen die gesamte Architektur in einem Zug um, um einen Hybrid-Zustand zu vermeiden.

**Betroffene Module:**
1.  **Expenses** (`cmd_add_expense`, `cmd_list_expenses`, etc.)
2.  **Income** (`cmd_add_income`, `cmd_list_income`, etc.)
3.  **Categories** (`cmd_list_categories`, `cmd_add_category` falls existent)

### 2. Service Layer API (Python)
Der Service Layer ist die API für Plugins. Er muss stabil und typisiert sein.

*   **Datenstrukturen:** Nutze `dataclasses` für Rückgabewerte (statt roher Dicts).
    ```python
    @dataclass
    class Expense:
        id: int | None      # Legacy ID
        uuid: str           # Neue Sync-ID
        date: str
        vendor: str
        amount_cents: int
        category: str
        # ...
    ```
*   **Exceptions:**
    *   Basis-Klasse: `EuerError(Exception)`
    *   Sub-Klassen: `ValidationError`, `RecordNotFoundError`.
    *   Der Service wirft diese Errors. Der CLI-Layer fängt sie und macht `sys.exit(1)`.
*   **Signaturen:**
    ```python
    def create_expense(conn: Connection, ...) -> Expense:
    def create_income(conn: Connection, ...) -> Income:
    def get_category_list(conn: Connection, ...) -> list[Category]:
    ```

### 3. Datenbank & UUIDs
*   **Schema:** Anpassung in `schema.py`.
    *   Neue Spalte `uuid` (TEXT UNIQUE NOT NULL) in **allen** Entitäts-Tabellen (`expenses`, `income`, `categories`).
    *   Der Service Layer **muss** die UUID generieren (`str(uuid.uuid4())`) und beim INSERT mitgeben.
*   **Audit Log:**
    *   Neue Spalte `record_uuid` (TEXT) in `audit_log`.
    *   Der Service muss beim Loggen die UUID mitschreiben.
*   **Migration:**
    *   Keine Migrations-Skripte. User starten mit frischer DB oder patchen manuell.

### 4. Plugin System (Entry Points)
*   **Definition:** In `pyproject.toml` definieren Plugins Entry Points.
*   **Implementation:** In `euercli/cli.py` muss der Loader hinzugefügt werden, der `entry_points(group='euer.commands')` scannt und deren `setup(subparsers)` aufruft.

### 5. CLI & Output
*   **Invariante:** Der Output (stdout) aller bestehenden Befehle darf sich **nicht** ändern.
*   Die CLI-Funktionen (`commands/*.py`) werden zu reinen "View-Controllern", die Argumente parsen, den Service rufen und das Ergebnis formatieren.

### 6. Testing
*   Erstelle Unit-Tests für alle neuen Services:
    *   `tests/test_services_expenses.py`
    *   `tests/test_services_income.py`
    *   `tests/test_services_categories.py`
*   Teste direkt gegen In-Memory DB.

## Quellenlage
Diese Datei (`005-refactoring-for-open-core.md`) ist die alleinige Quelle der Wahrheit.
