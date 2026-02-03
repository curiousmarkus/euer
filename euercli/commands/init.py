import uuid
from pathlib import Path

from ..config import get_export_dir, load_config
from ..constants import DEFAULT_EXPORT_DIR
from ..db import get_db_connection
from ..schema import SCHEMA, SEED_CATEGORIES


def cmd_init(args):
    """Initialisiert die Datenbank."""
    db_path = Path(args.db)

    print(f"Initialisiere Datenbank: {db_path}")

    conn = get_db_connection(db_path)
    conn.executescript(SCHEMA)

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
