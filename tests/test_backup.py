"""Tests für den SQLite-Backup-Service (Spec 016 §1.1, Spec 020 §4)."""

import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from euercli.backup import create_database_backup, get_backup_dir, rotate_backups


class BackupTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.orig_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.home)
        self.db_path = self.root / "test.db"
        self.backup_dir = self.root / "backups"
        self.backup_dir.mkdir()

        # Erstelle Test-DB mit WAL-Modus
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        self.conn.execute("INSERT INTO items (name) VALUES ('Item A')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        if self.orig_home is not None:
            os.environ["HOME"] = self.orig_home
        self.temp_dir.cleanup()

    def test_backup_creates_consistent_standalone_copy(self):
        # Transaktion mit uncommitted/committed Daten
        self.conn.execute("INSERT INTO items (name) VALUES ('Item B')")
        self.conn.commit()

        backup_path = create_database_backup(
            self.conn,
            backup_dir=self.backup_dir,
            prefix="test_backup",
        )

        self.assertTrue(backup_path.exists())
        self.assertTrue(backup_path.is_file())
        self.assertEqual(backup_path.parent, self.backup_dir.resolve())

        # Sicherung in isolierter Verbindung öffnen
        dest_conn = sqlite3.connect(backup_path)
        rows = dest_conn.execute("SELECT name FROM items ORDER BY id").fetchall()
        dest_conn.close()

        self.assertEqual([r[0] for r in rows], ["Item A", "Item B"])

    def test_backup_from_file_path(self):
        backup_path = create_database_backup(
            self.db_path,
            backup_dir=self.backup_dir,
            prefix="path_backup",
        )
        self.assertTrue(backup_path.exists())

        dest_conn = sqlite3.connect(backup_path)
        rows = dest_conn.execute("SELECT name FROM items").fetchall()
        dest_conn.close()
        self.assertEqual(len(rows), 1)

    def test_backup_rotation_keeps_max_keep(self):
        # 12 Backups erzeugen
        for i in range(12):
            p = self.backup_dir / f"rot_{i:02d}.db"
            p.write_text("dummy")
            # Sicherstellen, dass mtime unterschiedlich ist
            mtime = time.time() - (100 - i)
            os.utime(p, (mtime, mtime))

        existing_before = list(self.backup_dir.glob("rot_*.db"))
        self.assertEqual(len(existing_before), 12)

        removed = rotate_backups(self.backup_dir, max_keep=5, prefix="rot")
        self.assertEqual(len(removed), 7)

        remaining = list(self.backup_dir.glob("rot_*.db"))
        self.assertEqual(len(remaining), 5)
        # Die ältesten (00 bis 06) wurden gelöscht
        remaining_names = [p.name for p in remaining]
        self.assertIn("rot_11.db", remaining_names)
        self.assertIn("rot_10.db", remaining_names)
        self.assertNotIn("rot_00.db", remaining_names)

    def test_get_backup_dir_fallback_and_config(self):
        default_dir = get_backup_dir()
        self.assertTrue(default_dir.exists())

        custom = self.root / "custom_backups"
        cfg_dir = get_backup_dir({"backups": {"directory": str(custom)}})
        self.assertEqual(cfg_dir, custom)
        self.assertTrue(custom.exists())
