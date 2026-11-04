import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from euercli import VERSION
from euercli.commands.export import HAS_OPENPYXL, cmd_export
from euercli.db import get_db_connection
from euercli.services.export import compute_db_snapshot_hash, publish_export
from tests.cli_test_base import BaseCLITestCase


class VersionedExportTestCase(BaseCLITestCase):
    def test_versioned_export_creates_folder_and_valid_manifest(self):
        export_dir = self.root / "exports_versioned"
        export_dir.mkdir()

        self.add_expense(vendor="Test Vendor", amount="-50.00")
        self.add_income(source="Client A", amount="100.00")
        self.add_private_deposit(amount="200.00", description="Einlage")

        res = self.run_cli(
            [
                "export",
                "--year",
                "2026",
                "--format",
                "csv",
                "--versioned",
                "--output",
                str(export_dir),
            ],
            check=True,
        )
        self.assertIn("Versionierter Export erfolgreich erstellt:", res.stdout)
        self.assertIn("manifest.json", res.stdout)

        versioned_folders = [p for p in export_dir.iterdir() if p.is_dir()]
        self.assertEqual(len(versioned_folders), 1)
        folder = versioned_folders[0]

        self.assertTrue(folder.name.startswith("export_2026_"))
        self.assertTrue(folder.name.endswith(f"_v{VERSION}"))

        manifest_file = folder / "manifest.json"
        self.assertTrue(manifest_file.exists())

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.assertEqual("1.0", manifest["manifest_version"])
        self.assertEqual("euer", manifest["program"])
        self.assertEqual(VERSION, manifest["euer_version"])
        self.assertEqual(2026, manifest["report_year"])
        self.assertEqual("csv", manifest["parameters"]["format"])
        self.assertEqual(2026, manifest["parameters"]["year"])
        self.assertTrue(manifest["parameters"]["versioned"])

        self.assertIn("snapshot_sha256", manifest["database"])
        self.assertEqual(64, len(manifest["database"]["snapshot_sha256"]))

        files = manifest["files"]
        self.assertEqual(4, len(files))

        names = {f["relative_path"] for f in files}
        expected_names = {
            "EÜR_2026_Ausgaben.csv",
            "EÜR_2026_Einnahmen.csv",
            "EÜR_2026_PrivateTransfers.csv",
            "EÜR_2026_Sacheinlagen.csv",
        }
        self.assertEqual(expected_names, names)

        for f in files:
            path = folder / f["relative_path"]
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_size, f["size_bytes"])
            self.assertEqual(64, len(f["sha256"]))
            self.assertIn("line_count", f)
            lines = len(path.read_text(encoding="utf-8-sig").splitlines())
            self.assertEqual(lines, f["line_count"])

    def test_versioned_export_verify_success(self):
        export_dir = self.root / "exports_verify_ok"
        export_dir.mkdir()

        self.add_expense(vendor="Test Vendor", amount="-50.00")
        self.run_cli(
            [
                "export",
                "--year",
                "2026",
                "--format",
                "csv",
                "--versioned",
                "--output",
                str(export_dir),
            ],
            check=True,
        )

        folder = next(p for p in export_dir.iterdir() if p.is_dir())

        # Prüfung per Ordnerpfad
        res1 = self.run_cli(["export", "--verify", str(folder)], check=True)
        self.assertIn("✓ Manifestprüfung erfolgreich", res1.stdout)
        self.assertIn(f"euer-Version: {VERSION}", res1.stdout)

        # Prüfung per Dateipfad zu manifest.json
        manifest_path = folder / "manifest.json"
        res2 = self.run_cli(["export", "--verify", str(manifest_path)], check=True)
        self.assertIn("✓ Manifestprüfung erfolgreich", res2.stdout)

    def test_versioned_export_verify_detects_tampered_file(self):
        export_dir = self.root / "exports_tampered"
        export_dir.mkdir()

        self.add_expense(vendor="Test Vendor", amount="-50.00")
        self.run_cli(
            [
                "export",
                "--year",
                "2026",
                "--format",
                "csv",
                "--versioned",
                "--output",
                str(export_dir),
            ],
            check=True,
        )

        folder = next(p for p in export_dir.iterdir() if p.is_dir())
        target_csv = folder / "EÜR_2026_Ausgaben.csv"

        # Datei manipulieren (Zeile anhängen)
        with open(target_csv, "a", encoding="utf-8") as f:
            f.write("manipulierter,inhalt,ohne,freigabe\n")

        res = self.run_cli(["export", "--verify", str(folder)])
        self.assertNotEqual(0, res.returncode)
        self.assertIn("Fehler bei der Manifestprüfung:", res.stderr)
        self.assertIn("SHA-256 Prüfsumme weicht ab", res.stderr)

    def test_versioned_export_verify_detects_missing_file(self):
        export_dir = self.root / "exports_missing_file"
        export_dir.mkdir()

        self.add_expense(vendor="Test Vendor", amount="-50.00")
        self.run_cli(
            [
                "export",
                "--year",
                "2026",
                "--format",
                "csv",
                "--versioned",
                "--output",
                str(export_dir),
            ],
            check=True,
        )

        folder = next(p for p in export_dir.iterdir() if p.is_dir())
        target_csv = folder / "EÜR_2026_Ausgaben.csv"
        target_csv.unlink()

        res = self.run_cli(["export", "--verify", str(folder)])
        self.assertNotEqual(0, res.returncode)
        self.assertIn("Exportdatei fehlt: EÜR_2026_Ausgaben.csv", res.stderr)

    def test_versioned_export_aborts_on_collision_without_overwriting(self):
        from types import SimpleNamespace

        from euercli.commands.export import cmd_export

        export_dir = self.root / "exports_collision"
        export_dir.mkdir()

        fixed_folder = export_dir / f"export_2026_20261104T120000+0100_v{VERSION}"
        fixed_folder.mkdir()
        canary = fixed_folder / "canary.txt"
        canary.write_text("original content")

        args = SimpleNamespace(
            db=str(self.db_path),
            output=str(export_dir),
            year=2026,
            format="csv",
            force=False,
            versioned=True,
            verify=None,
        )

        with patch(
            "euercli.commands.export.format_versioned_dir_name",
            return_value=fixed_folder.name,
        ):
            with self.assertRaises(SystemExit) as ctx:
                cmd_export(args)
            self.assertEqual(1, ctx.exception.code)

        self.assertTrue(canary.exists())
        self.assertEqual("original content", canary.read_text())

    def test_versioned_export_error_during_creation_leaves_no_folder(self):
        from types import SimpleNamespace

        from euercli.commands.export import cmd_export

        export_dir = self.root / "exports_error_clean"
        export_dir.mkdir()

        self.add_expense(vendor="Test Vendor", amount="-50.00")

        args = SimpleNamespace(
            db=str(self.db_path),
            output=str(export_dir),
            year=2026,
            format="csv",
            force=False,
            versioned=True,
            verify=None,
        )

        # Fehler beim Schreiben provozieren
        with patch("builtins.open", side_effect=OSError("Simulated disk error")):
            with self.assertRaises(SystemExit) as ctx:
                cmd_export(args)
            self.assertEqual(1, ctx.exception.code)

        # Keine Ordner oder temporäre Verzeichnisse verbleiben im Ausgabeverzeichnis
        remaining = list(export_dir.iterdir())
        self.assertEqual([], remaining)

    def test_versioned_export_wal_mode(self):
        export_dir = self.root / "exports_wal"
        export_dir.mkdir()

        # DB in WAL-Modus schalten
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.commit()
        conn.close()

        self.add_expense(vendor="WAL Vendor", amount="-75.00")

        self.run_cli(
            [
                "export",
                "--year",
                "2026",
                "--format",
                "csv",
                "--versioned",
                "--output",
                str(export_dir),
            ],
            check=True,
        )

        folder = next(p for p in export_dir.iterdir() if p.is_dir())
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        snapshot_hash = manifest["database"]["snapshot_sha256"]
        self.assertEqual(64, len(snapshot_hash))

    def test_versioned_export_xlsx(self):
        if not HAS_OPENPYXL:
            self.skipTest("openpyxl nicht verfügbar")

        export_dir = self.root / "exports_xlsx"
        export_dir.mkdir()

        self.add_expense(vendor="XLSX Vendor", amount="-120.00")
        self.add_income(source="Client B", amount="300.00")

        self.run_cli(
            [
                "export",
                "--year",
                "2026",
                "--format",
                "xlsx",
                "--versioned",
                "--output",
                str(export_dir),
            ],
            check=True,
        )

        folder = next(p for p in export_dir.iterdir() if p.is_dir())
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))

        files = manifest["files"]
        self.assertEqual(3, len(files))
        for f in files:
            # Bei binären XLSX-Dateien darf line_count nicht gesetzt sein
            self.assertNotIn("line_count", f)
            path = folder / f["relative_path"]
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_size, f["size_bytes"])

        # Auch --verify muss für XLSX erfolgreich sein
        res = self.run_cli(["export", "--verify", str(folder)], check=True)
        self.assertIn("✓ Manifestprüfung erfolgreich", res.stdout)

    def export_args(self, output):
        return SimpleNamespace(
            db=str(self.db_path),
            output=str(output),
            year=2026,
            format="csv",
            force=False,
            versioned=True,
            verify=None,
        )

    def test_two_exports_in_same_second_have_distinct_directories(self):
        output = self.root / "two_runs"
        first = datetime(2026, 11, 4, 12, 0, 0, 1, tzinfo=timezone.utc)
        second = first.replace(microsecond=2)
        with (
            patch("euercli.commands.export.datetime") as clock,
            patch("euercli.commands.export.load_config", return_value={}),
        ):
            clock.now.return_value.astimezone.side_effect = [first, second]
            cmd_export(self.export_args(output))
            cmd_export(self.export_args(output))
        folders = list(output.iterdir())
        self.assertEqual(2, len(folders))
        for folder in folders:
            self.assertIn("+0000", folder.name)
            self.run_cli(["export", "--verify", str(folder)], check=True)

    def test_missing_xlsx_extra_creates_no_output(self):
        output = self.root / "missing_xlsx"
        args = self.export_args(output)
        args.format = "xlsx"
        with (
            patch("euercli.commands.export.HAS_OPENPYXL", False),
            patch("euercli.commands.export.load_config", return_value={}),
        ):
            with self.assertRaises(SystemExit) as ctx:
                cmd_export(args)
        self.assertEqual(1, ctx.exception.code)
        self.assertFalse(output.exists())

    def test_wal_writer_cannot_change_export_snapshot_or_hash(self):
        self.add_expense(vendor="Original Vendor", amount="-50.00")
        self.add_income(source="Original Client", amount="100.00")
        writer = sqlite3.connect(self.db_path)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("UPDATE expenses SET notes='Only in WAL'")
        writer.commit()
        self.assertGreater(Path(str(self.db_path) + "-wal").stat().st_size, 0)
        reader = get_db_connection(self.db_path, read_only=True)
        self.addCleanup(reader.close)
        expected_hash = compute_db_snapshot_hash(reader)
        main_hash = hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        self.assertNotEqual(main_hash, expected_hash)
        changed = False

        def concurrent_write(query):
            nonlocal changed
            if "FROM income i" in query and not changed:
                writer.execute("UPDATE expenses SET vendor='Changed Vendor'")
                writer.execute("UPDATE income SET source='Changed Client'")
                writer.commit()
                changed = True

        reader.set_trace_callback(concurrent_write)
        output = self.root / "consistent_wal"
        with (
            patch("euercli.commands.export.get_db_connection", return_value=reader),
            patch("euercli.commands.export.load_config", return_value={}),
        ):
            cmd_export(self.export_args(output))
        self.assertTrue(changed)
        folder = next(output.iterdir())
        expense = (folder / "EÜR_2026_Ausgaben.csv").read_text(encoding="utf-8-sig")
        income = (folder / "EÜR_2026_Einnahmen.csv").read_text(encoding="utf-8-sig")
        self.assertIn("Original Vendor", expense)
        self.assertIn("Only in WAL", expense)
        self.assertIn("Original Client", income)
        self.assertNotIn("Changed", expense + income)
        manifest = json.loads((folder / "manifest.json").read_text())
        self.assertEqual(expected_hash, manifest["database"]["snapshot_sha256"])
        self.assertEqual(
            "Changed Vendor", writer.execute("SELECT vendor FROM expenses").fetchone()[0]
        )

    def test_late_collision_preserves_empty_target_and_removes_staging(self):
        output = self.root / "late_collision"
        target = output / "reserved_run"

        def competing_publish(stage, destination):
            destination.mkdir()
            inode = destination.stat().st_ino
            try:
                publish_export(stage, destination)
            finally:
                self.assertEqual(inode, destination.stat().st_ino)

        with (
            patch("euercli.commands.export.format_versioned_dir_name", return_value=target.name),
            patch("euercli.commands.export.publish_export", side_effect=competing_publish),
            patch("euercli.commands.export.load_config", return_value={}),
        ):
            with self.assertRaises(SystemExit) as ctx:
                cmd_export(self.export_args(output))
        self.assertEqual(1, ctx.exception.code)
        self.assertEqual([target], list(output.iterdir()))
        self.assertEqual([], list(target.iterdir()))

    def test_dangling_symlink_target_is_not_replaced_even_with_force(self):
        output = self.root / "symlink_collision"
        output.mkdir()
        target = output / "reserved_run"
        try:
            target.symlink_to(output / "absent", target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks nicht verfügbar")
        args = self.export_args(output)
        args.force = True
        with (
            patch("euercli.commands.export.format_versioned_dir_name", return_value=target.name),
            patch("euercli.commands.export.load_config", return_value={}),
        ):
            with self.assertRaises(SystemExit):
                cmd_export(args)
        self.assertTrue(target.is_symlink())
        self.assertEqual([target], list(output.iterdir()))

    def test_verify_works_without_database_skill_or_project_config(self):
        output = self.root / "portable"
        self.run_cli(["export", "--versioned", "--output", str(output)], check=True)
        folder = next(output.iterdir())
        self.db_path.unlink()
        project = self.root / ".euer"
        project.mkdir()
        (project / "config.toml").write_text("invalid = [")
        self.write_config("invalid = [")
        result = subprocess.run(
            [sys.executable, "-m", "euercli", "export", "--verify", str(folder)],
            cwd=self.root,
            env={**self.env, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Manifestprüfung erfolgreich", result.stdout)
        self.assertFalse(self.db_path.exists())

    def test_verify_rejects_invalid_file_metadata_and_unreadable_files(self):
        output = self.root / "invalid_manifests"
        self.run_cli(["export", "--versioned", "--output", str(output)], check=True)
        folder = next(output.iterdir())
        manifest_path = folder / "manifest.json"
        original = json.loads(manifest_path.read_text())
        cases = [
            ("sha256", None),
            ("sha256", "invalid"),
            ("size_bytes", None),
            ("size_bytes", True),
            ("size_bytes", -1),
            ("line_count", "1"),
            ("relative_path", "../outside.csv"),
            ("relative_path", str(self.db_path)),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                manifest = json.loads(json.dumps(original))
                if value is None:
                    del manifest["files"][0][key]
                else:
                    manifest["files"][0][key] = value
                manifest_path.write_text(json.dumps(manifest))
                result = self.run_cli(["export", "--verify", str(folder)])
                self.assertEqual(1, result.returncode)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("Manifestprüfung erfolgreich", result.stdout)
        manifest_path.write_text(json.dumps(original))
        target = folder / original["files"][0]["relative_path"]
        target.unlink()
        target.mkdir()
        result = self.run_cli(["export", "--verify", str(folder)])
        self.assertEqual(1, result.returncode)
        self.assertIn("nicht lesbar", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_output_file_instead_of_directory_is_a_cli_error(self):
        output = self.root / "not_a_directory"
        output.write_text("keep")
        result = self.run_cli(["export", "--versioned", "--output", str(output)])
        self.assertEqual(1, result.returncode)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual("keep", output.read_text())

    def test_verify_without_path_uses_latest_completed_run_across_years(self):
        output = self.root / "latest_run"
        self.run_cli(
            ["export", "--year", "2026", "--versioned", "--output", str(output)], check=True
        )
        older = next(output.iterdir())
        self.run_cli(
            ["export", "--year", "2025", "--versioned", "--output", str(output)], check=True
        )
        latest = next(path for path in output.iterdir() if path != older)
        unfinished = output / ".versioned_stage_unfinished"
        shutil.copytree(latest, unfinished)
        (older / "EÜR_2026_Ausgaben.csv").write_text("changed")
        (unfinished / "EÜR_2025_Ausgaben.csv").write_text("unfinished")
        for folder, modified in [(older, 1), (latest, 2), (unfinished, 3)]:
            os.utime(folder / "manifest.json", (modified, modified))
        result = self.run_cli(["export", "--verify", "--output", str(output)], check=True)
        self.assertIn(str(latest), result.stdout)
        self.assertNotIn(str(unfinished), result.stdout)
