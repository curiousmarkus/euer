"""Command init: Datenbank initialisieren oder transparent migrieren (Spec 020)."""

import json
import sys
from pathlib import Path

from ..backup import create_database_backup
from ..config import get_export_dir, load_config
from ..constants import DEFAULT_EXPORT_DIR
from ..db import get_db_connection
from ..migrations import MIGRATIONS, get_migration_plan, init_migration_table


def cmd_init(args) -> None:
    """Initialisiert oder aktualisiert die Datenbank."""
    db_path = Path(args.db)
    is_explicit = getattr(args, "is_explicit_db", False)
    allow_create = getattr(args, "create", False)
    is_dry_run = getattr(args, "dry_run", False)
    is_json = getattr(args, "json", False)

    db_exists = db_path.exists()

    # 1. Pfad-Guardrail (Spec 016 §2.4, Spec 020 §7):
    # Expliziter Pfad existiert nicht und kein --create übergeben
    if is_explicit and not db_exists and not allow_create:
        msg = f"Datenbank existiert nicht: {db_path}. Nutze --create zur Neuanlage."
        if is_json:
            print(json.dumps({"status": "error", "error": msg}, ensure_ascii=False))
        else:
            print(f"Fehler: {msg}", file=sys.stderr)
        sys.exit(1)

    # 2. Neuanlage einer Datenbank
    if not db_exists:
        target_schema = MIGRATIONS[-1].id if MIGRATIONS else "001_initial_schema"
        if is_dry_run:
            if is_json:
                data = {
                    "status": "dry_run",
                    "action": "create",
                    "db_path": str(db_path.resolve()),
                    "exists": False,
                    "target_schema": target_schema,
                    "pending_migrations": [
                        {
                            "id": m.id,
                            "name": m.name,
                            "affected_count": 0,
                            "affected_ids": [],
                            "description": "Initiale Erstellung",
                            "next_steps": [],
                        }
                        for m in MIGRATIONS
                    ],
                    "actions_required": [],
                }
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print("=== euer init: Migrationsplan (Dry-Run) ===")
                print(f"Datenbank: {db_path.resolve()}")
                print("Status: Datei existiert noch nicht (Neuanlage geplant).")
                print(f"Ziel-Schemastand: {target_schema}")
                print(f"\nAnstehende Migrationen ({len(MIGRATIONS)}):")
                for i, m in enumerate(MIGRATIONS, 1):
                    print(f"  {i}. [{m.id}] {m.name}")
                print("\nHinweis: Dry-Run abgeschlossen. Keine Änderungen vorgenommen.")
            return

        # Echte Neuanlage
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(db_path)
        init_migration_table(conn)

        try:
            with conn:
                for m in MIGRATIONS:
                    m.apply(conn)
                    conn.execute(
                        "INSERT INTO _schema_migrations (version, name) VALUES (?, ?)",
                        (m.id, m.name),
                    )
        except Exception as exc:
            print(f"Fehler bei Neuanlage der Datenbank: {exc}", file=sys.stderr)
            conn.close()
            try:
                db_path.unlink()
            except OSError:
                pass
            sys.exit(1)

        conn.close()

        config = load_config()
        export_dir = get_export_dir(config)
        export_path = Path(export_dir) if export_dir else DEFAULT_EXPORT_DIR
        export_path.mkdir(parents=True, exist_ok=True)

        if is_json:
            data = {
                "status": "success",
                "action": "create",
                "db_path": str(db_path.resolve()),
                "new_schema": target_schema,
                "applied_migrations": [m.id for m in MIGRATIONS],
                "export_dir": str(export_path.resolve()),
                "affected_records": {"count": 0, "ids": [], "details": []},
                "next_steps": [],
            }
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("=== Neuanlage-Bericht ===")
            print(f"Datenbank neu angelegt: {db_path.resolve()}")
            print(f"Schemastand: {target_schema}")
            print(f"Export-Verzeichnis: {export_path.resolve()}")
            print("Status: Erfolgreich initialisiert.")
        return

    # 3. Bestehende Datenbank: Pre-Flight & Migration
    conn = get_db_connection(db_path)
    current_schema, target_schema, pending, legacy_stamps = get_migration_plan(conn)

    # 3a. Dry-Run auf bestehender DB
    if is_dry_run:
        conn.close()
        if is_json:
            data = {
                "status": "dry_run",
                "action": "upgrade" if pending else "none",
                "db_path": str(db_path.resolve()),
                "exists": True,
                "current_schema": current_schema,
                "target_schema": target_schema,
                "pending_migrations": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "affected_count": impact.affected_count,
                        "affected_ids": impact.affected_ids,
                        "description": impact.description,
                        "next_steps": impact.next_steps,
                    }
                    for m, impact in pending
                ],
                "actions_required": [step for _, impact in pending for step in impact.next_steps],
            }
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("=== euer init: Migrationsplan (Dry-Run) ===")
            print(f"Datenbank: {db_path.resolve()}")
            print(f"Aktueller Schemastand: {current_schema}")
            print(f"Ziel-Schemastand: {target_schema}")

            if not pending:
                print("\nKeine anstehenden Migrationen. Datenbank ist bereits aktuell.")
            else:
                print(f"\nAnstehende Migrationen ({len(pending)}):")
                for i, (m, impact) in enumerate(pending, 1):
                    print(f"  {i}. [{m.id}] {m.name}")
                    if impact.description:
                        print(f"     Beschreibung: {impact.description}")
                    if impact.affected_ids:
                        print(
                            f"     Betroffene Buchungen ({impact.affected_count}): IDs {impact.affected_ids}"
                        )
                    if impact.next_steps:
                        for step in impact.next_steps:
                            print(f"     Nächster Schritt: {step}")
            print(
                "\nHinweis: Dry-Run abgeschlossen. Keine Änderungen vorgenommen, kein Backup erstellt."
            )
        return

    # 3b. Keine anstehenden Migrationen
    if not pending:
        if legacy_stamps:
            # Bestehende Legacy-DB ohne Marker: Stempel eintragen
            with conn:
                for m_id in legacy_stamps:
                    m_obj = next((m for m in MIGRATIONS if m.id == m_id), None)
                    name = m_obj.name if m_obj else "Legacy Schema"
                    conn.execute(
                        "INSERT OR IGNORE INTO _schema_migrations (version, name) VALUES (?, ?)",
                        (m_id, f"{name} (abgeleitet)"),
                    )

        conn.close()
        if is_json:
            data = {
                "status": "success",
                "action": "none",
                "db_path": str(db_path.resolve()),
                "current_schema": current_schema,
                "applied_migrations": [],
                "affected_records": {"count": 0, "ids": []},
                "next_steps": [],
            }
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"Datenbank ist bereits auf dem aktuellen Schemastand: {current_schema}.")
            print("Keine Migrationen erforderlich.")
        return

    # 3c. Echte Migration mit Pre-Flight, Backup und Transaktion
    if not is_json:
        print(f"Initialisiere / aktualisiere Datenbank: {db_path.resolve()}")
        print(f"Aktueller Schemastand: {current_schema}")
        print(f"Anstehende Migrationen ({len(pending)}):")
        for m, impact in pending:
            print(f"  - {m.id}: {m.name}")
            if impact.affected_ids:
                print(
                    f"    Achtung: {impact.affected_count} Buchung(en) betroffen (IDs: {impact.affected_ids})"
                )

    # Backup erstellen (Spec 016 §1.1, Spec 020 §4)
    if not is_json:
        print("Erstelle Sicherheits-Backup vor Migration...")
    try:
        backup_path = create_database_backup(conn)
        if not is_json:
            print(f"Backup gespeichert unter: {backup_path}")
    except Exception as exc:
        conn.close()
        msg = f"Sicherheits-Backup fehlgeschlagen: {exc}. Migration abgebrochen."
        if is_json:
            print(json.dumps({"status": "error", "error": msg}, ensure_ascii=False))
        else:
            print(f"Fehler: {msg}", file=sys.stderr)
        sys.exit(1)

    # Transaktionale Durchführung aller anstehenden Migrationen
    applied_ids = []
    all_affected_ids = []
    all_next_steps = []
    for m, impact in pending:
        if impact.affected_ids:
            all_affected_ids.extend(impact.affected_ids)
        if impact.next_steps:
            for step in impact.next_steps:
                if step not in all_next_steps:
                    all_next_steps.append(step)

    conn.isolation_level = None
    conn.execute("BEGIN IMMEDIATE")
    try:
        for m_id in legacy_stamps:
            conn.execute(
                "INSERT OR IGNORE INTO _schema_migrations (version, name) VALUES (?, ?)",
                (m_id, "Legacy Schema (abgeleitet)"),
            )
        for m, _ in pending:
            m.apply(conn)
            conn.execute(
                "INSERT INTO _schema_migrations (version, name) VALUES (?, ?)",
                (m.id, m.name),
            )
            applied_ids.append(m.id)
        conn.execute("COMMIT")
    except Exception as exc:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        conn.close()
        err_msg = (
            f"FEHLER bei Migration: {exc}\n"
            "Transaktion wurde zurückgerollt. Die Datenbank ist unverändert.\n"
            f"Vorab-Sicherung vorhanden unter: {backup_path}"
        )
        if is_json:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "error": str(exc),
                        "rollback": True,
                        "backup_path": str(backup_path),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(err_msg, file=sys.stderr)
        sys.exit(1)

    conn.close()

    config = load_config()
    export_dir = get_export_dir(config)
    export_path = Path(export_dir) if export_dir else DEFAULT_EXPORT_DIR
    export_path.mkdir(parents=True, exist_ok=True)

    # Abschlussbericht
    if is_json:
        data = {
            "status": "success",
            "action": "upgrade",
            "db_path": str(db_path.resolve()),
            "backup_path": str(backup_path),
            "previous_schema": current_schema,
            "new_schema": target_schema,
            "applied_migrations": applied_ids,
            "affected_records": {
                "count": len(all_affected_ids),
                "ids": all_affected_ids,
            },
            "next_steps": all_next_steps,
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("\n=== Upgrade-Bericht ===")
        print(f"Datenbank: {db_path.resolve()}")
        print(f"Backup: {backup_path}")
        print(f"Schemastand: {current_schema} -> {target_schema}")
        print(f"Angewendete Migrationen ({len(applied_ids)}): {', '.join(applied_ids)}")
        if all_affected_ids:
            print(
                f"Betroffene Buchungen ({len(all_affected_ids)}): IDs {all_affected_ids} als 'needs_review' markiert."
            )
        else:
            print("Betroffene Buchungen: 0")
        if all_next_steps:
            print("Nächste Prüfschritte:")
            for i, step in enumerate(all_next_steps, 1):
                print(f"  {i}. {step}")
        print("Status: Erfolgreich aktualisiert.")
