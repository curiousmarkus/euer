"""Tests für transparente Migrationen, Guardrails und Init (Spec 020, Spec 016 §1.1/§2.4)."""

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from euercli.cli import main
from euercli.migrations import (
    MIGRATIONS,
    Migration,
    MigrationImpact,
    detect_legacy_schema_state,
)


class MigrationsAndInitTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.orig_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.home)
        self.db_path = self.root / "test.db"

    def tearDown(self):
        if self.orig_home is not None:
            os.environ["HOME"] = self.orig_home
        self.temp_dir.cleanup()

    def test_explicit_nonexistent_db_fails_without_create(self):
        # Pfad existiert nicht, kein --create
        with self.assertRaises(SystemExit) as cm:
            main(["--db", str(self.db_path), "init"])
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.db_path.exists())

    def test_explicit_nonexistent_db_fails_without_create_json(self):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f), self.assertRaises(SystemExit) as cm:
            main(["--db", str(self.db_path), "init", "--json"])
        self.assertEqual(cm.exception.code, 1)
        data = json.loads(f.getvalue())
        self.assertEqual(data["status"], "error")
        self.assertIn("--create", data["error"])

    def test_explicit_nonexistent_db_succeeds_with_create(self):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            main(["--db", str(self.db_path), "init", "--create", "--json"])
        self.assertTrue(self.db_path.exists())
        data = json.loads(f.getvalue())
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "create")
        self.assertEqual(data["new_schema"], MIGRATIONS[-1].id)

    def test_dry_run_create_does_not_create_file(self):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            main(["--db", str(self.db_path), "init", "--create", "--dry-run", "--json"])
        self.assertFalse(self.db_path.exists())
        data = json.loads(f.getvalue())
        self.assertEqual(data["status"], "dry_run")
        self.assertEqual(data["action"], "create")
        self.assertFalse(data["exists"])

    def test_legacy_schema_detection_and_stamping(self):
        # Erstelle eine DB mit dem vollen Schema, aber ohne _schema_migrations
        conn = sqlite3.connect(self.db_path)
        from euercli.schema import SCHEMA

        conn.executescript(SCHEMA)
        conn.close()

        conn = sqlite3.connect(self.db_path)
        desc, satisfied = detect_legacy_schema_state(conn)
        conn.close()
        self.assertIn("008_soft_delete", desc)
        self.assertIn("001_initial_schema", satisfied)
        self.assertIn("007_category_eur_key", satisfied)
        self.assertIn("008_soft_delete", satisfied)

        # Führe init aus -> registriert Legacy-Stempel ohne Fehler
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            main(["--db", str(self.db_path), "init", "--json"])
        data = json.loads(f.getvalue())
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "upgrade")
        self.assertTrue(Path(data["backup_path"]).exists())

        # Prüfe, dass _schema_migrations existiert und gefüllt ist
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT version, name FROM _schema_migrations").fetchall()
        conn.close()
        self.assertTrue(len(rows) >= 8)
        self.assertIn("001_initial_schema", [r[0] for r in rows])

    def test_existing_db_dry_run_does_not_create_migration_table(self):
        import io
        from contextlib import redirect_stdout

        from euercli.schema import SCHEMA

        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        conn.close()

        with redirect_stdout(io.StringIO()):
            main(["--db", str(self.db_path), "init", "--dry-run", "--json"])

        conn = sqlite3.connect(self.db_path)
        marker = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = '_schema_migrations'"
        ).fetchone()
        conn.close()
        self.assertIsNone(marker)

    def test_initial_schema_rolls_back_if_later_migration_fails(self):
        import io
        from contextlib import redirect_stdout

        # Existing empty DB exercises _apply_001 inside the upgrade transaction.
        sqlite3.connect(self.db_path).close()

        def failing_apply(conn):
            raise RuntimeError("Injected failure after base schema")

        fake_migration = Migration(
            id="001z_failure",
            name="Injected failure",
            preflight=lambda conn: MigrationImpact(),
            apply=failing_apply,
        )
        migrations = [MIGRATIONS[0], fake_migration, *MIGRATIONS[1:]]
        with (
            patch("euercli.migrations.MIGRATIONS", migrations),
            patch("euercli.commands.init.MIGRATIONS", migrations),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            main(["--db", str(self.db_path), "init", "--json"])

        conn = sqlite3.connect(self.db_path)
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        conn.close()
        self.assertNotIn("categories", tables)
        self.assertNotIn("_schema_migrations", tables)

    def test_rebuild_keeps_private_transfer_expense_reference(self):
        import io
        from contextlib import redirect_stdout

        from euercli.schema import SCHEMA

        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        conn.execute("ALTER TABLE expenses ADD COLUMN is_rc INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE income ADD COLUMN date DATE")
        conn.execute(
            "INSERT INTO expenses (id, uuid, payment_date, vendor, amount_eur, "
            "entertainment_tip_eur, entertainment_vat_status, deleted_at, hash) "
            "VALUES (1, 'e1', '2026-01-01', 'Vendor', -10, 1.5, 'deductible', "
            "'2026-02-01', 'h1')"
        )
        conn.execute(
            "INSERT INTO income (id, uuid, payment_date, source, amount_eur, deleted_at, hash) "
            "VALUES (1, 'i1', '2026-01-01', 'Source', 10, '2026-02-02', 'h3')"
        )
        conn.execute(
            "INSERT INTO private_transfers "
            "(id, uuid, date, type, amount_eur, description, related_expense_id, hash) "
            "VALUES (1, 'p1', '2026-01-01', 'deposit', 10, 'Deposit', 1, 'h2')"
        )
        conn.execute(
            "CREATE TABLE _schema_migrations (version TEXT PRIMARY KEY, name TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO _schema_migrations (version, name) VALUES ('001_initial_schema', 'Initial')"
        )
        conn.commit()
        conn.close()

        with redirect_stdout(io.StringIO()):
            main(["--db", str(self.db_path), "init", "--json"])

        conn = sqlite3.connect(self.db_path)
        self.assertEqual(
            conn.execute(
                "SELECT related_expense_id FROM private_transfers WHERE id = 1"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(
            conn.execute(
                "SELECT entertainment_tip_eur, entertainment_vat_status, deleted_at "
                "FROM expenses WHERE id = 1"
            ).fetchone(),
            (1.5, "deductible", "2026-02-01"),
        )
        self.assertEqual(
            conn.execute("SELECT deleted_at FROM income WHERE id = 1").fetchone()[0],
            "2026-02-02",
        )
        conn.close()

    def test_legacy_detection_does_not_stamp_partial_soft_delete(self):
        from euercli.schema import SCHEMA

        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        conn.execute("ALTER TABLE private_transfers RENAME TO private_transfers_old")
        conn.execute(
            "CREATE TABLE private_transfers AS SELECT id, uuid, date, type, amount_eur, "
            "description, notes, related_expense_id, created_at, hash "
            "FROM private_transfers_old"
        )
        conn.execute("DROP TABLE private_transfers_old")
        _, satisfied = detect_legacy_schema_state(conn)
        self.assertNotIn("008_soft_delete", satisfied)
        conn.close()

    def test_entertainment_impact_detection_and_reporting(self):
        # Erstelle DB im Stand v0.9 (ohne Bewirtungsspalten)
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            """
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                eur_line INTEGER,
                type TEXT NOT NULL
            );
            CREATE TABLE expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                payment_date DATE,
                invoice_date DATE,
                vendor TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id),
                amount_eur REAL NOT NULL,
                account TEXT,
                ledger_account TEXT,
                foreign_amount TEXT,
                notes TEXT,
                rc_type TEXT NOT NULL DEFAULT 'none',
                vat_input REAL,
                vat_output REAL,
                vat_rate REAL,
                vat_code TEXT,
                is_private_paid INTEGER NOT NULL DEFAULT 0,
                private_classification TEXT NOT NULL DEFAULT 'none',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hash TEXT UNIQUE NOT NULL
            );
            CREATE TABLE income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                payment_date DATE,
                invoice_date DATE,
                source TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id),
                amount_eur REAL NOT NULL,
                ledger_account TEXT,
                foreign_amount TEXT,
                notes TEXT,
                vat_output REAL,
                vat_rate REAL,
                vat_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hash TEXT UNIQUE NOT NULL
            );
            INSERT INTO categories (uuid, name, eur_line, type) VALUES ('cat-1', 'Bewirtungsaufwendungen', 64, 'expense');
            INSERT INTO expenses (uuid, payment_date, vendor, category_id, amount_eur, hash)
            VALUES ('e1', '2026-02-01', 'Restaurant A', 1, -120.0, 'h1'),
                   ('e2', '2026-03-01', 'Restaurant B', 1, -85.0, 'h2');
            """
        )
        conn.close()

        # 1. Dry-Run: Prüfe Vorab-Meldung der beiden betroffenen Buchungen
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            main(["--db", str(self.db_path), "init", "--dry-run", "--json"])
        data = json.loads(f.getvalue())
        self.assertEqual(data["status"], "dry_run")
        self.assertEqual(data["action"], "upgrade")
        pending_ids = [m["id"] for m in data["pending_migrations"]]
        self.assertIn("006_entertainment_fields", pending_ids)
        m006 = next(m for m in data["pending_migrations"] if m["id"] == "006_entertainment_fields")
        self.assertEqual(m006["affected_count"], 2)
        self.assertEqual(m006["affected_ids"], [1, 2])

        # 2. Echte Migration durchführen
        f_real = io.StringIO()
        with redirect_stdout(f_real):
            main(["--db", str(self.db_path), "init", "--json"])
        data_real = json.loads(f_real.getvalue())
        self.assertEqual(data_real["status"], "success")
        self.assertEqual(data_real["action"], "upgrade")
        self.assertTrue(Path(data_real["backup_path"]).exists())
        self.assertEqual(data_real["affected_records"]["count"], 2)
        self.assertEqual(data_real["affected_records"]["ids"], [1, 2])

        # Verifiziere DB: Status auf needs_review gesetzt
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT id, entertainment_vat_status FROM expenses ORDER BY id"
        ).fetchall()
        conn.close()
        self.assertEqual(rows, [(1, "needs_review"), (2, "needs_review")])

    def test_migration_failure_triggers_rollback(self):
        # Erstelle DB mit Basistabellen
        main(["--db", str(self.db_path), "init", "--create"])

        # Simuliere eine fehlerhafte Migration
        def failing_apply(conn):
            conn.execute("CREATE TABLE test_temp (id INT)")
            raise RuntimeError("Injected migration failure")

        fake_migration = Migration(
            id="999_failing_migration",
            name="Fehlerhafte Test-Migration",
            preflight=lambda conn: MigrationImpact(),
            apply=failing_apply,
        )

        with (
            patch("euercli.migrations.MIGRATIONS", MIGRATIONS + [fake_migration]),
            patch("euercli.commands.init.MIGRATIONS", MIGRATIONS + [fake_migration]),
        ):
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f), self.assertRaises(SystemExit) as cm:
                main(["--db", str(self.db_path), "init", "--json"])
            self.assertEqual(cm.exception.code, 1)
            data = json.loads(f.getvalue())
            self.assertEqual(data["status"], "error")
            self.assertTrue(data["rollback"])
            self.assertTrue(Path(data["backup_path"]).exists())

            # Prüfe, dass test_temp NICHT in DB existiert (Rollback war erfolgreich)
            conn = sqlite3.connect(self.db_path)
            temp_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='test_temp'"
            ).fetchone()
            conn.close()
            self.assertIsNone(temp_exists)
