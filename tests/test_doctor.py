"""Tests für 'euer doctor' (Spec 019)."""

import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from euercli.cli import main
from euercli.migrations import MIGRATIONS, init_migration_table
from euercli.services.doctor import (
    check_path_binaries,
    detect_install_source,
    run_doctor,
)


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.db_path = self.project_root / "euer.db"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _init_healthy_db(self) -> Path:
        conn = sqlite3.connect(self.db_path)
        init_migration_table(conn)
        for m in MIGRATIONS:
            m.apply(conn)
            conn.execute(
                "INSERT INTO _schema_migrations (version, name) VALUES (?, ?)",
                (m.id, m.name),
            )
        conn.commit()
        conn.close()
        return self.db_path

    def test_install_source_detection(self):
        # Homebrew
        self.assertEqual(
            detect_install_source("/opt/homebrew/bin/python3", "/opt/homebrew/bin/euer"),
            "homebrew",
        )
        self.assertEqual(
            detect_install_source("/usr/local/Cellar/python/bin/python3", "/usr/local/bin/euer"),
            "homebrew",
        )

        # pipx
        self.assertEqual(
            detect_install_source("/home/user/.local/pipx/venvs/euer/bin/python", "/home/user/.local/bin/euer"),
            "pipx",
        )

        # Fallback / venv
        with patch("sys.prefix", "/some/venv"), patch("sys.base_prefix", "/usr"):
            self.assertEqual(
                detect_install_source("/some/venv/bin/python", "/some/venv/bin/euer"),
                "venv",
            )

    def test_path_duplicates_detection(self):
        bin_dir1 = Path(self.temp_dir) / "bin1"
        bin_dir2 = Path(self.temp_dir) / "bin2"
        bin_dir1.mkdir()
        bin_dir2.mkdir()

        exe1 = bin_dir1 / "euer"
        exe2 = bin_dir2 / "euer"
        exe1.write_text("#!/bin/sh\n")
        exe2.write_text("#!/bin/sh\n")
        exe1.chmod(0o755)
        exe2.chmod(0o755)

        with patch.dict(os.environ, {"PATH": f"{bin_dir1}{os.pathsep}{bin_dir2}"}):
            dups = check_path_binaries(str(exe1))
            self.assertEqual(len(dups), 2)
            self.assertEqual(dups[0]["path"], str(exe1))
            self.assertTrue(dups[0]["is_active"])
            self.assertEqual(dups[1]["path"], str(exe2))
            self.assertFalse(dups[1]["is_active"])

    def test_case_1_standard_setup_healthy_db(self):
        self._init_healthy_db()

        # Run doctor service
        report = run_doctor(self.project_root, self.db_path, source="--db")

        self.assertEqual(report["database"]["status"], "ok")
        self.assertEqual(report["database"]["quick_check"], "ok")
        self.assertEqual(report["database"]["pending_migrations"], [])
        self.assertTrue(report["database"]["exists"])
        self.assertTrue(report["database"]["size_bytes"] > 0)

    def test_case_2_path_collision_reported(self):
        self._init_healthy_db()
        bin_dir1 = Path(self.temp_dir) / "pipx_bin"
        bin_dir2 = Path(self.temp_dir) / "brew_bin"
        bin_dir1.mkdir()
        bin_dir2.mkdir()

        exe1 = bin_dir1 / "euer"
        exe2 = bin_dir2 / "euer"
        exe1.write_text("#!/bin/sh\n")
        exe2.write_text("#!/bin/sh\n")
        exe1.chmod(0o755)
        exe2.chmod(0o755)

        with patch.dict(os.environ, {"PATH": f"{bin_dir1}{os.pathsep}{bin_dir2}"}):
            report = run_doctor(self.project_root, self.db_path, source="--db")
            self.assertIn("warning", report["status"])
            self.assertTrue(len(report["path_duplicates"]) >= 2)
            self.assertTrue(any("Kollidierende Installationen" in rec for rec in report["recommendations"]))

    def test_case_3_missing_db_not_created(self):
        non_existent_db = self.project_root / "non_existent.db"
        self.assertFalse(non_existent_db.exists())

        report = run_doctor(self.project_root, non_existent_db, source="Standard")

        # Database must NOT be created by doctor!
        self.assertFalse(non_existent_db.exists())
        self.assertFalse(report["database"]["exists"])
        self.assertEqual(report["database"]["status"], "not_found")
        self.assertIn("warning", report["status"])
        self.assertTrue(any("Keine Datenbank gefunden" in r for r in report["recommendations"]))

    def test_case_4_missing_openpyxl(self):
        self._init_healthy_db()

        with patch("euercli.services.doctor.diagnose_features", return_value={"openpyxl": {"available": False, "version": None}}):
            report = run_doctor(self.project_root, self.db_path, source="--db")
            self.assertFalse(report["features"]["openpyxl"]["available"])
            self.assertIn("warning", report["status"])
            self.assertTrue(any("XLSX-Export ist nicht verfügbar" in r for r in report["recommendations"]))

    def test_case_5_pending_migrations(self):
        # Create DB and only run first migration
        conn = sqlite3.connect(self.db_path)
        from euercli.migrations import MIGRATIONS, init_migration_table
        init_migration_table(conn)
        MIGRATIONS[0].apply(conn)
        conn.execute(
            "INSERT INTO _schema_migrations (version, name) VALUES (?, ?)",
            (MIGRATIONS[0].id, MIGRATIONS[0].name),
        )
        conn.commit()
        conn.close()

        report = run_doctor(self.project_root, self.db_path, source="--db")
        self.assertTrue(len(report["database"]["pending_migrations"]) > 0)
        self.assertEqual(report["database"]["status"], "warning")
        self.assertTrue(any("ausstehende Migration" in r for r in report["recommendations"]))

    def test_case_6_corrupted_db(self):
        # Write corrupted garbage to db file
        self.db_path.write_bytes(b"THIS IS NOT A SQLITE DATABASE FILE 1234567890")

        report = run_doctor(self.project_root, self.db_path, source="--db")
        self.assertEqual(report["database"]["status"], "error")
        self.assertEqual(report["status"], "error")
        self.assertTrue(any("Integritätsprüfung" in r or "Datenbank-Fehler" in r for r in report["recommendations"]))

    def test_case_7_invalid_system_config(self):
        self._init_healthy_db()
        dummy_cfg = Path(self.temp_dir) / "config.toml"
        dummy_cfg.write_text("broken toml [")

        with patch("euercli.services.doctor.CONFIG_PATH", dummy_cfg):
            with patch("euercli.services.doctor.load_config", side_effect=Exception("Invalid TOML syntax")):
                report = run_doctor(self.project_root, self.db_path, source="--db")
                self.assertFalse(report["config"]["system_config"]["valid"])
                self.assertEqual(report["status"], "error")
                self.assertTrue(any("Syntaxfehler in System-Config" in r for r in report["recommendations"]))

    def test_cli_doctor_json_output(self):
        self._init_healthy_db()

        import io
        from contextlib import redirect_stdout

        out = io.StringIO()
        with redirect_stdout(out):
            with self.assertRaises(SystemExit) as cm:
                main(["--db", str(self.db_path), "doctor", "--json"])
            self.assertEqual(cm.exception.code, 0)

        data = json.loads(out.getvalue())
        self.assertIn("status", data)
        self.assertIn("version", data)
        self.assertIn("database", data)
        self.assertEqual(data["database"]["status"], "ok")
        self.assertEqual(data["database"]["quick_check"], "ok")

    def test_cli_doctor_text_output(self):
        self._init_healthy_db()

        import io
        from contextlib import redirect_stdout

        out = io.StringIO()
        with redirect_stdout(out):
            with self.assertRaises(SystemExit) as cm:
                main(["--db", str(self.db_path), "doctor"])
            self.assertEqual(cm.exception.code, 0)

        output_str = out.getvalue()
        self.assertIn("=== EÜR Doctor: System- und Umgebungsdiagnose ===", output_str)
        self.assertIn("Laufzeitumgebung:", output_str)
        self.assertIn("Datenbank:", output_str)
        self.assertIn("PRAGMA quick_check", output_str)


if __name__ == "__main__":
    unittest.main()
