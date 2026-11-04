import json
import sqlite3
from unittest.mock import patch

from euercli import VERSION
from euercli.commands.export import HAS_OPENPYXL
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
            with self.assertRaises(OSError):
                cmd_export(args)

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
