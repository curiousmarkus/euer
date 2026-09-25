"""Command init: Datenbank initialisieren oder transparent migrieren (Spec 020)."""

import json
import sqlite3
import sys
from pathlib import Path

from ..backup import create_database_backup
from ..config import get_export_dir, load_config
from ..constants import DEFAULT_EXPORT_DIR
from ..db import get_db_connection
from ..migrations import MIGRATIONS, get_migration_plan, init_migration_table
from ..project_config import project_config_path, save_project_db_path


def _should_save_project_binding(args) -> bool:
    return getattr(args, "save_db_path", False) or (
        not getattr(args, "is_explicit_db", False)
        and not getattr(args, "db_from_project_config", False)
    )


def _save_project_binding(args, db_path: Path, is_json: bool) -> Path | None:
    """Persistiert den Default-Pfad oder einen explizit freigegebenen --db-Pfad."""
    if not _should_save_project_binding(args):
        return None
    try:
        return save_project_db_path(args.project_root, db_path)
    except (OSError, ValueError) as exc:
        msg = (
            f"Datenbank unter {db_path.resolve()} ist bereit, aber der Pfad konnte nicht "
            f"in der Projekt-Config gespeichert werden: {exc}"
        )
        if is_json:
            print(
                json.dumps(
                    {"status": "error", "database_status": "ready", "error": msg},
                    ensure_ascii=False,
                )
            )
        else:
            print(f"Fehler: {msg}", file=sys.stderr)
        sys.exit(1)


def cmd_init(args) -> None:
    """Initialisiert oder aktualisiert die Datenbank."""
    db_path = Path(args.db)
    allow_create = getattr(args, "create", False)
    is_dry_run = getattr(args, "dry_run", False)
    is_json = getattr(args, "json", False)
    planned_binding = (
        str(project_config_path(args.project_root)) if _should_save_project_binding(args) else None
    )

    db_exists = db_path.exists()

    # 1. Pfad-Guardrail (Spec 016 §2.4, Spec 020 §7):
    # A missing configured or default DB must never be created by accident.
    if not db_exists and not allow_create:
        msg = (
            f"Datenbank existiert nicht: {db_path.resolve()}. "
            "Vorhandene DB mit 'euer --db PFAD init --save-db-path' verbinden "
            "oder mit 'euer init --create' eine neue DB anlegen."
        )
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
                    "project_config_to_write": planned_binding,
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
                if planned_binding:
                    print(f"Projekt-Config würde gespeichert: {planned_binding}")
                print(f"\nAnstehende Migrationen ({len(MIGRATIONS)}):")
                for i, m in enumerate(MIGRATIONS, 1):
                    print(f"  {i}. [{m.id}] {m.name}")
                print("\nHinweis: Dry-Run abgeschlossen. Keine Änderungen vorgenommen.")
            return

        # Echte Neuanlage
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(db_path)
        conn.isolation_level = None
        try:
            conn.execute("BEGIN IMMEDIATE")
            init_migration_table(conn)
            for m in MIGRATIONS:
                m.apply(conn)
                conn.execute(
                    "INSERT INTO _schema_migrations (version, name) VALUES (?, ?)",
                    (m.id, m.name),
                )
            conn.execute("COMMIT")
        except Exception as exc:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            print(f"Fehler bei Neuanlage der Datenbank: {exc}", file=sys.stderr)
            conn.close()
            try:
                db_path.unlink()
            except OSError:
                pass
            sys.exit(1)

        conn.close()
        binding_path = _save_project_binding(args, db_path, is_json)

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
                "project_config_path": str(binding_path) if binding_path else None,
                "affected_records": {"count": 0, "ids": [], "details": []},
                "next_steps": [],
            }
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("=== Neuanlage-Bericht ===")
            print(f"Datenbank neu angelegt: {db_path.resolve()}")
            print(f"Schemastand: {target_schema}")
            print(f"Export-Verzeichnis: {export_path.resolve()}")
            if binding_path:
                print(f"Projekt-Config: {binding_path}")
            print("Status: Erfolgreich initialisiert.")
        return

    # 3. Bestehende Datenbank: Pre-Flight & Migration
    conn = get_db_connection(db_path)
    try:
        current_schema, target_schema, pending, legacy_stamps = get_migration_plan(conn)
    except (ValueError, sqlite3.DatabaseError) as exc:
        conn.close()
        msg = f"Migrationsplan nicht ermittelbar: {exc}"
        if is_json:
            print(json.dumps({"status": "error", "error": msg}, ensure_ascii=False))
        else:
            print(f"Fehler: {msg}", file=sys.stderr)
        sys.exit(1)

    # 3a. Dry-Run auf bestehender DB
    if is_dry_run:
        conn.close()
        if is_json:
            data = {
                "status": "dry_run",
                "action": "upgrade" if pending or legacy_stamps else "none",
                "db_path": str(db_path.resolve()),
                "exists": True,
                "current_schema": current_schema,
                "target_schema": target_schema,
                "project_config_to_write": planned_binding,
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
            if planned_binding:
                print(f"Projekt-Config würde gespeichert: {planned_binding}")

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
    if not pending and not legacy_stamps:
        conn.close()
        binding_path = _save_project_binding(args, db_path, is_json)
        if is_json:
            data = {
                "status": "success",
                "action": "none",
                "db_path": str(db_path.resolve()),
                "current_schema": current_schema,
                "applied_migrations": [],
                "affected_records": {"count": 0, "ids": []},
                "next_steps": [],
                "project_config_path": str(binding_path) if binding_path else None,
            }
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"Datenbank ist bereits auf dem aktuellen Schemastand: {current_schema}.")
            print("Keine Migrationen erforderlich.")
            if binding_path:
                print(f"DB-Pfad in Projekt-Config gespeichert: {binding_path}")
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
    rebuild_legacy_tables = any(m.id == "002_payment_invoice_dates" for m, _ in pending)
    if rebuild_legacy_tables:
        # RENAME must not rewrite private_transfers' FK target to expenses_old.
        # SQLite ignores foreign_keys changes after BEGIN, so configure first.
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("PRAGMA legacy_alter_table = ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        init_migration_table(conn)
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
        invalid_references = conn.execute("PRAGMA foreign_key_check").fetchall()
        if invalid_references:
            raise RuntimeError("Fremdschlüsselprüfung nach Migration fehlgeschlagen")
        conn.execute("COMMIT")
    except Exception as exc:
        try:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
        except Exception:
            pass
        if rebuild_legacy_tables:
            conn.execute("PRAGMA legacy_alter_table = OFF")
            conn.execute("PRAGMA foreign_keys = ON")
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

    if rebuild_legacy_tables:
        conn.execute("PRAGMA legacy_alter_table = OFF")
        conn.execute("PRAGMA foreign_keys = ON")

    conn.close()
    binding_path = _save_project_binding(args, db_path, is_json)

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
            "project_config_path": str(binding_path) if binding_path else None,
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("\n=== Upgrade-Bericht ===")
        print(f"Datenbank: {db_path.resolve()}")
        print(f"Backup: {backup_path}")
        print(f"Schemastand: {current_schema} -> {target_schema}")
        if binding_path:
            print(f"DB-Pfad in Projekt-Config gespeichert: {binding_path}")
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
