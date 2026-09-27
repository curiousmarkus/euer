import sqlite3
from contextlib import closing
from unittest.mock import patch

from euercli.backup import create_database_backup
from tests.cli_test_base import BaseCLITestCase


class DailyBackupTestCase(BaseCLITestCase):
    def test_failed_publication_leaves_no_backup_file(self):
        backup_dir = self.root / "failed_backups"
        with patch("euercli.backup.os.link", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                create_database_backup(self.db_path, backup_dir=backup_dir)
        self.assertEqual(list(backup_dir.iterdir()), [])

    def test_first_mutation_is_backed_up_once_per_day(self):
        backup_dir = self.expected_config_path().parent / "backups"
        self.add_expense(vendor="First", amount="-10.00")
        backups = list(backup_dir.glob("euer_daily_*.db"))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0])) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0], 0)

        self.add_expense(vendor="Second", amount="-20.00")
        self.assertEqual(len(list(backup_dir.glob("euer_daily_*.db"))), 1)
