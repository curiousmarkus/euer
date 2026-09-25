"""Projektbezogene DB-Pfade und Guardrails bei fehlender Datenbank."""

import os
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ProjectDbPathTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.home)
        self.env["USERPROFILE"] = str(self.home)
        self.env["APPDATA"] = str(self.home / "AppData")
        self.env["PYTHONPATH"] = str(REPO_ROOT)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_cli(self, *args: str, check: bool = False):
        result = subprocess.run(
            [sys.executable, "-m", "euercli", *args],
            cwd=self.project,
            env=self.env,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(f"{args}: {result.stdout}\n{result.stderr}")
        return result

    def configured_path(self) -> str:
        with (self.project / ".euer" / "config.toml").open("rb") as file:
            return tomllib.load(file)["database"]["path"]

    def test_default_create_registers_relative_path_and_booking_uses_it(self):
        missing = self.run_cli("add", "expense")
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse((self.project / "euer.db").exists())
        self.assertNotEqual(self.run_cli("init").returncode, 0)

        create = self.run_cli("init", "--create", check=True)
        self.assertIn("Projekt-Config:", create.stdout)
        self.assertEqual(self.configured_path(), "euer.db")
        self.run_cli(
            "add",
            "expense",
            "--date",
            "2026-01-01",
            "--vendor",
            "Vendor",
            "--category",
            "Arbeitsmittel",
            "--amount",
            "-10",
            check=True,
        )
        with sqlite3.connect(self.project / "euer.db") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0], 1)

    def test_existing_default_db_is_registered_by_init(self):
        self.run_cli("init", "--create", check=True)
        (self.project / ".euer" / "config.toml").unlink()
        self.run_cli("init", check=True)
        self.assertEqual(self.configured_path(), "euer.db")

    def test_relative_binding_survives_project_move(self):
        self.run_cli("init", "--create", check=True)
        relocated = self.root / "relocated"
        self.project.rename(relocated)
        self.project = relocated
        self.assertEqual(self.configured_path(), "euer.db")
        self.assertEqual(self.run_cli("list", "expenses").returncode, 0)

    def test_explicit_path_is_one_off_until_saved(self):
        external = self.root / "external.db"
        self.run_cli("--db", str(external), "init", "--create", check=True)
        self.assertFalse((self.project / ".euer" / "config.toml").exists())
        self.run_cli("--db", str(external), "init", "--save-db-path", check=True)
        self.assertEqual(self.configured_path(), str(external.resolve()))
        self.assertFalse((self.project / "euer.db").exists())
        self.assertEqual(self.run_cli("list", "expenses").returncode, 0)

    def test_missing_configured_db_blocks_booking_and_can_be_rebound(self):
        self.run_cli("init", "--create", check=True)
        moved = self.root / "moved.db"
        (self.project / "euer.db").rename(moved)

        result = self.run_cli("list", "expenses")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--save-db-path", result.stderr)
        self.assertFalse((self.project / "euer.db").exists())

        self.run_cli("--db", str(moved), "init", "--save-db-path", check=True)
        self.assertEqual(self.configured_path(), str(moved.resolve()))
        self.assertEqual(self.run_cli("list", "expenses").returncode, 0)

    def test_dry_run_does_not_write_project_config(self):
        self.run_cli("init", "--create", "--dry-run", check=True)
        self.assertFalse((self.project / ".euer").exists())
        self.assertFalse((self.project / "euer.db").exists())

        external = self.root / "external.db"
        self.run_cli("--db", str(external), "init", "--create", check=True)
        self.run_cli("--db", str(external), "init", "--save-db-path", "--dry-run", check=True)
        self.assertFalse((self.project / ".euer").exists())

        external.rename(self.project / "euer.db")
        self.run_cli("init", "--dry-run", check=True)
        self.assertFalse((self.project / ".euer").exists())

    def test_invalid_project_config_fails_without_creating_database(self):
        config_path = self.project / ".euer" / "config.toml"
        config_path.parent.mkdir()
        config_path.write_text('[database]\npath = ""\n', encoding="utf-8")
        result = self.run_cli("init", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('"status": "error"', result.stdout)
        self.assertFalse((self.project / "euer.db").exists())

    def test_config_setup_and_import_schema_work_without_database(self):
        shown = self.run_cli("config", "show", check=True)
        self.assertIn("Datenbank:", shown.stdout)
        self.assertIn("fehlt", shown.stdout)
        self.run_cli("setup", "--set", "safety.amount_threshold", "6000", check=True)
        self.run_cli("import", "--schema", check=True)
        self.assertNotEqual(self.run_cli("setup").returncode, 0)
        self.assertFalse((self.project / "euer.db").exists())
