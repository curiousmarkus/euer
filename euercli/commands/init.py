import uuid
from pathlib import Path

from ..config import get_export_dir, load_config
from ..constants import DEFAULT_EXPORT_DIR
from ..db import get_db_connection
from ..schema import SCHEMA, SEED_CATEGORIES


def ensure_expenses_private_columns(conn) -> None:
    """Ergänzt fehlende private-Spalten in bestehenden Datenbanken."""
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
    }
    if "is_private_paid" not in columns:
        conn.execute(
            """ALTER TABLE expenses ADD COLUMN
               is_private_paid INTEGER NOT NULL DEFAULT 0 CHECK(is_private_paid IN (0, 1))"""
        )
    if "private_classification" not in columns:
        conn.execute(
            """ALTER TABLE expenses ADD COLUMN
               private_classification TEXT NOT NULL DEFAULT 'none'"""
        )


def cmd_init(args):
    """Initialisiert die Datenbank."""
    db_path = Path(args.db)

    print(f"Initialisiere Datenbank: {db_path}")

    conn = get_db_connection(db_path)
    conn.executescript(SCHEMA)
    ensure_expenses_private_columns(conn)

    # Kategorien seeden (nur wenn leer)
    existing = conn.execute("SELECT COUNT(*) as cnt FROM categories").fetchone()["cnt"]
    if existing == 0:
        print("Seede Kategorien...")
        for name, eur_line, cat_type in SEED_CATEGORIES:
            conn.execute(
                "INSERT INTO categories (uuid, name, eur_line, type) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), name, eur_line, cat_type),
            )
        conn.commit()
        print(f"  {len(SEED_CATEGORIES)} Kategorien angelegt")
    else:
        print(f"  Kategorien existieren bereits ({existing})")

    conn.close()

    config = load_config()
    export_dir = get_export_dir(config)
    if export_dir:
        export_path = Path(export_dir)
        export_path.mkdir(exist_ok=True)
        print(f"Export-Verzeichnis: {export_path}")
    else:
        DEFAULT_EXPORT_DIR.mkdir(exist_ok=True)
        print(f"Export-Verzeichnis: {DEFAULT_EXPORT_DIR}")

    print("Fertig.")
