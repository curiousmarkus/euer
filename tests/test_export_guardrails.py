import unittest
from types import SimpleNamespace
from unittest.mock import patch

from euercli.commands.export import cmd_export
from tests.cli_test_base import BaseCLITestCase


class ExportGuardrailsTestCase(BaseCLITestCase):
    def test_failed_replace_restores_previous_export_files(self):
        export_dir = self.root / "exports_rollback"
        export_dir.mkdir()
        self.add_expense(vendor="Before", amount="-10.00")
        self.run_cli(["export", "--format", "csv", "--output", str(export_dir)], check=True)
        before = {p.name: p.read_bytes() for p in export_dir.iterdir()}
        self.add_expense(vendor="After", amount="-20.00")

        import os

        real_replace = os.replace
        replacements = 0

        def fail_second_install(src, dst):
            nonlocal replacements
            if ".tmp." in str(src):
                replacements += 1
                if replacements == 2:
                    raise OSError("simulierter Schreibfehler")
            return real_replace(src, dst)

        args = SimpleNamespace(
            db=str(self.db_path), output=str(export_dir), year=None, format="csv", force=True
        )
        with patch("euercli.commands.export.os.replace", side_effect=fail_second_install):
            with self.assertRaises(OSError):
                cmd_export(args)
        self.assertEqual(before, {p.name: p.read_bytes() for p in export_dir.iterdir()})

    def test_export_aborts_when_files_exist_without_force(self):
        export_dir = self.root / "exports"
        export_dir.mkdir()

        # Erste Ausgabe anlegen und erfolgreich exportieren
        self.add_expense(vendor="Export Vendor 1", amount="-100.00")
        self.run_cli(
            ["export", "--year", "2026", "--format", "csv", "--output", str(export_dir)],
            check=True,
        )

        target_file = export_dir / "EÜR_2026_Ausgaben.csv"
        self.assertTrue(target_file.exists())
        initial_content = target_file.read_text(encoding="utf-8-sig")
        self.assertIn("Export Vendor 1", initial_content)

        # Zweite Ausgabe anlegen
        self.add_expense(vendor="Export Vendor 2", amount="-200.00")

        # Zweiter Export ohne --force muss mit Fehler abbrechen
        res = self.run_cli(
            ["export", "--year", "2026", "--format", "csv", "--output", str(export_dir)],
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Zieldatei(en) existieren bereits", res.stderr + res.stdout)
        self.assertIn("--force", res.stderr + res.stdout)

        # Dateiinhalt darf NICHT verändert worden sein (Transaktionsschutz)
        unmodified_content = target_file.read_text(encoding="utf-8-sig")
        self.assertEqual(initial_content, unmodified_content)
        self.assertNotIn("Export Vendor 2", unmodified_content)

        # Keine temporären .tmp-Dateien im Verzeichnis
        tmp_files = list(export_dir.glob("*.tmp*"))
        self.assertEqual(len(tmp_files), 0)

    def test_export_succeeds_with_force(self):
        export_dir = self.root / "exports_force"
        export_dir.mkdir()

        self.add_expense(vendor="Vendor First", amount="-50.00")
        self.run_cli(
            ["export", "--year", "2026", "--format", "csv", "--output", str(export_dir)],
            check=True,
        )

        self.add_expense(vendor="Vendor Second", amount="-150.00")
        res = self.run_cli(
            ["export", "--year", "2026", "--format", "csv", "--output", str(export_dir), "--force"],
            check=True,
        )
        self.assertIn("Exportiert:", res.stdout)

        target_file = export_dir / "EÜR_2026_Ausgaben.csv"
        content = target_file.read_text(encoding="utf-8-sig")
        self.assertIn("Vendor Second", content)

    def test_export_excludes_soft_deleted_records(self):
        export_dir = self.root / "exports_deleted"
        export_dir.mkdir()

        self.add_expense(vendor="Active Vendor", amount="-60.00")
        self.add_expense(vendor="Deleted Vendor", amount="-70.00")
        self.add_income(source="Active Income", amount="100.00")
        self.add_income(source="Deleted Income", amount="200.00")

        # Datensätze löschen (Soft-Delete)
        self.run_cli(["delete", "expense", "2", "--force"], check=True)
        self.run_cli(["delete", "income", "2", "--force"], check=True)

        self.run_cli(
            ["export", "--year", "2026", "--format", "csv", "--output", str(export_dir)],
            check=True,
        )

        exp_file = export_dir / "EÜR_2026_Ausgaben.csv"
        inc_file = export_dir / "EÜR_2026_Einnahmen.csv"

        exp_content = exp_file.read_text(encoding="utf-8-sig")
        inc_content = inc_file.read_text(encoding="utf-8-sig")

        self.assertIn("Active Vendor", exp_content)
        self.assertNotIn("Deleted Vendor", exp_content)

        self.assertIn("Active Income", inc_content)
        self.assertNotIn("Deleted Income", inc_content)


if __name__ == "__main__":
    unittest.main()
