import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from euercli.schema import SCHEMA
from euercli.services.errors import ValidationError
from euercli.services.receipts import (
    ScanWarning,
    SkippedEntry,
    UnbookedResult,
    _ignored,
    find_unbooked_receipts,
)


class ServicesReceiptsTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.receipts = self.root / "receipts"
        self.expenses = self.receipts / "2026" / "Ausgaben"
        self.income = self.receipts / "2026" / "Einnahmen"
        self.expenses.mkdir(parents=True)
        self.income.mkdir()
        self.db_path = self.root / "euer.db"
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        self.config = {
            "receipts": {
                "root": str(self.receipts),
                "year_dir": "{year}",
                "expenses_dir": "Ausgaben",
                "income_dir": "Einnahmen",
            }
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ignored_patterns(self):
        self.assertTrue(_ignored(".hidden"))
        self.assertTrue(_ignored(".DS_Store"))
        self.assertTrue(_ignored("~$temp.docx"))
        self.assertTrue(_ignored("Thumbs.db"))
        self.assertTrue(_ignored("thumbs.db"))
        self.assertTrue(_ignored("desktop.ini"))
        self.assertTrue(_ignored("DESKTOP.INI"))
        self.assertTrue(_ignored("something.tmp"))
        self.assertTrue(_ignored("SOMETHING.TMP"))
        self.assertFalse(_ignored("normal.pdf"))
        self.assertFalse(_ignored("temp_file.pdf"))

    def test_invalid_arguments_raise_validation_error(self):
        with self.assertRaises(ValidationError):
            find_unbooked_receipts(self.db_path, self.config, year=0)
        with self.assertRaises(ValidationError):
            find_unbooked_receipts(self.db_path, self.config, year=10000)
        with self.assertRaises(ValidationError):
            find_unbooked_receipts(self.db_path, self.config, year=2026, booking_type="invalid")

    def test_missing_or_invalid_root_config(self):
        # Kein root
        res = find_unbooked_receipts(self.db_path, {}, 2026)
        self.assertFalse(res.scan_complete)
        self.assertEqual(res.errors[0].code, "invalid_config")

        # Root existiert nicht
        res = find_unbooked_receipts(
            self.db_path, {"receipts": {"root": str(self.root / "nonexistent")}}, 2026
        )
        self.assertFalse(res.scan_complete)
        self.assertEqual(res.errors[0].code, "directory_missing")

        # Root ist eine Datei
        file_as_root = self.root / "file_root"
        file_as_root.write_text("dummy", encoding="utf-8")
        res = find_unbooked_receipts(self.db_path, {"receipts": {"root": str(file_as_root)}}, 2026)
        self.assertFalse(res.scan_complete)
        self.assertEqual(res.errors[0].code, "not_a_directory")

    def test_year_dir_escaping_root(self):
        config = {
            "receipts": {
                "root": str(self.receipts),
                "year_dir": "../outside/{year}",
            }
        }
        res = find_unbooked_receipts(self.db_path, config, 2026)
        self.assertFalse(res.scan_complete)
        self.assertEqual(res.errors[0].code, "invalid_config")

    def test_type_directory_is_file_or_symlink(self):
        # expenses_dir ist eine Datei statt Ordner
        (self.receipts / "2027" / "Ausgaben").parent.mkdir(parents=True)
        (self.receipts / "2027" / "Ausgaben").write_text("file", encoding="utf-8")
        (self.receipts / "2027" / "Einnahmen").mkdir()
        res = find_unbooked_receipts(self.db_path, self.config, 2027)
        self.assertFalse(res.scan_complete)
        self.assertEqual(res.errors[0].code, "not_a_directory")

    def test_scan_directory_io_error(self):
        (self.expenses / "file.pdf").write_bytes(b"content")
        with patch("os.scandir", side_effect=OSError("Permission denied")):
            res = find_unbooked_receipts(self.db_path, self.config, 2026)
            self.assertFalse(res.scan_complete)
            self.assertEqual(res.errors[0].code, "scan_io_error")

    def test_non_regular_file_skipped(self):
        (self.expenses / "regular.pdf").write_bytes(b"regular")
        # Simuliere Nicht-Regulärdatei (z.B. FIFO oder Socket)
        with (
            patch("os.DirEntry.is_file", return_value=False),
            patch("os.DirEntry.is_dir", return_value=False),
            patch("os.DirEntry.is_symlink", return_value=False),
        ):
            res = find_unbooked_receipts(self.db_path, self.config, 2026, "expense")
            self.assertEqual(res.total_files, 0)
            self.assertEqual(res.skipped_entries[0].reason, "non_regular_file")

    def test_to_dict_contract(self):
        res = UnbookedResult(
            year=2026,
            types=["expense"],
            root="/path/to/root",
            scan_complete=True,
            total_files=1,
            referenced_files=1,
            unbooked_count=0,
            skipped_count=1,
            unbooked_files=[],
            skipped_entries=[SkippedEntry("expense", "2026/Ausgaben/.hidden", "ignored_name")],
            warnings=[
                ScanWarning(
                    "missing_payment_date", "Vorläufig", "expense", 1, "2026/Ausgaben/a.pdf"
                )
            ],
            errors=[],
        )
        d = res.to_dict()
        self.assertEqual(d["year"], 2026)
        self.assertEqual(d["types"], ["expense"])
        self.assertTrue(d["scan_complete"])
        self.assertEqual(d["skipped_entries"][0]["reason"], "ignored_name")
        self.assertEqual(d["warnings"][0]["code"], "missing_payment_date")


if __name__ == "__main__":
    unittest.main()
