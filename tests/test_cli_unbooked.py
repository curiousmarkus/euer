import json

from tests.cli_test_base import BaseCLITestCase


class CLIUnbookedTestCase(BaseCLITestCase):
    def setUp(self):
        super().setUp()
        self.receipts = self.root / "receipts"
        self.expenses = self.receipts / "2026" / "Ausgaben"
        self.income = self.receipts / "2026" / "Einnahmen"
        self.expenses.mkdir(parents=True)
        self.income.mkdir()
        self.write_config(f"[receipts]\nroot = '{self.receipts.as_posix()}'\n")

    def scan(self, *options):
        response = self.run_cli(
            ["receipt", "unbooked", "--year", "2026", "--format", "json", *options]
        )
        return response, json.loads(response.stdout)

    def test_unbooked_and_referenced_files_are_distinct(self):
        (self.expenses / "linked.pdf").write_bytes(b"linked")
        (self.expenses / "free.pdf").write_bytes(b"free")
        self.add_expense(receipt="linked")
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 1)
        self.assertEqual(
            (data["total_files"], data["referenced_files"], data["unbooked_count"]), (2, 1, 1)
        )
        self.assertEqual(data["unbooked_files"][0]["receipt_name"], "free.pdf")
        self.assertTrue(data["unbooked_files"][0]["modified_at"].endswith("Z"))

    def test_year_uses_payment_date_and_missing_payment_date_warns(self):
        (self.expenses / "old-invoice.pdf").write_bytes(b"1")
        (self.expenses / "pending.pdf").write_bytes(b"2")
        self.run_cli(
            [
                "add",
                "expense",
                "--invoice-date",
                "2025-12-15",
                "--payment-date",
                "2026-01-15",
                "--vendor",
                "Vendor",
                "--amount",
                "-10",
                "--receipt",
                "old-invoice.pdf",
            ],
            check=True,
        )
        self.run_cli(
            [
                "add",
                "expense",
                "--invoice-date",
                "2025-12-16",
                "--vendor",
                "Pending",
                "--amount",
                "-20",
                "--receipt",
                "pending.pdf",
            ],
            check=True,
        )
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 0)
        self.assertEqual(data["referenced_files"], 2)
        self.assertEqual(data["warnings"][0]["code"], "missing_payment_date")

    def test_soft_deleted_reference_and_duplicate_reference(self):
        (self.expenses / "shared.pdf").write_bytes(b"x")
        self.add_expense(receipt="shared.pdf")
        self.add_expense(date="2026-01-16", vendor="Other", receipt="shared.pdf")
        _, data = self.scan("--type", "expense")
        self.assertEqual(data["referenced_files"], 1)
        self.run_cli(["delete", "expense", "1", "--force"], check=True)
        _, data = self.scan("--type", "expense")
        self.assertEqual(data["referenced_files"], 1)
        self.run_cli(["delete", "expense", "2", "--force"], check=True)
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 1)
        self.assertEqual(data["unbooked_count"], 1)
        self.run_cli(["restore", "1", "--table", "expenses"], check=True)
        _, data = self.scan("--type", "expense")
        self.assertEqual(data["referenced_files"], 1)

    def test_ignored_symlink_subfolder_and_type_filter(self):
        (self.expenses / "nested").mkdir()
        (self.expenses / "nested" / "file.PDF").write_bytes(b"x")
        (self.expenses / ".hidden.pdf").write_bytes(b"x")
        (self.expenses / "notes.txt").write_bytes(b"x")
        (self.expenses / "link.pdf").symlink_to(self.expenses / "nested" / "file.PDF")
        (self.income / "incoming.pdf").write_bytes(b"x")
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 1)
        self.assertEqual(data["total_files"], 1)
        self.assertEqual(data["unbooked_files"][0]["receipt_name"], "nested/file.PDF")
        self.assertEqual(
            {item["reason"] for item in data["skipped_entries"]},
            {
                "ignored_name",
                "unsupported_extension",
                "symlink",
            },
        )

    def test_invalid_reference_does_not_claim_file(self):
        (self.expenses / "file.pdf").write_bytes(b"x")
        self.add_expense(receipt="../Ausgaben/file.pdf")
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 1)
        self.assertEqual(data["warnings"][0]["code"], "invalid_receipt_reference")
        self.assertEqual(data["unbooked_count"], 1)

    def test_missing_directory_and_db_are_incomplete(self):
        (self.receipts / "2026" / "Einnahmen").rmdir()
        response, data = self.scan()
        self.assertEqual(response.returncode, 2)
        self.assertFalse(data["scan_complete"])
        self.assertIsNone(data["total_files"])
        self.assertEqual(data["errors"][0]["code"], "directory_missing")
        self.assertEqual(data["unbooked_files"], [])
        self.assertFalse(self.run_cli(["receipt", "unbooked", "--year", "10000"]).returncode == 0)
        self.db_path.unlink()
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 2)
        self.assertEqual(data["errors"][0]["code"], "database_error")
        self.assertFalse(self.db_path.exists())

    def test_csv_only_contains_rows_and_diagnostics_use_stderr(self):
        (self.expenses / 'a,"b.pdf').write_bytes(b"x")
        response = self.run_cli(
            ["receipt", "unbooked", "--year", "2026", "--type", "expense", "--format", "csv"]
        )
        self.assertEqual(response.returncode, 1)
        rows = self.parse_csv(response.stdout)
        self.assertEqual(rows[0], ["type", "path", "receipt_name", "size_bytes", "modified_at"])
        self.assertEqual(rows[1][2], 'a,"b.pdf')
        self.assertIn("ohne Zuordnung: 1", response.stderr)

    def test_custom_year_dir_and_root_symlink(self):
        alias = self.root / "receipt-alias"
        alias.symlink_to(self.receipts, target_is_directory=True)
        custom = self.receipts / "Buchhaltung 2026" / "Kosten"
        custom.mkdir(parents=True)
        (custom / "invoice.webp").write_bytes(b"x")
        self.write_config(
            f"[receipts]\nroot = '{alias.as_posix()}'\nyear_dir = 'Buchhaltung {{year}}'\n"
            "expenses_dir = 'Kosten'\n"
        )
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 1)
        self.assertEqual(data["unbooked_files"][0]["path"], "Buchhaltung 2026/Kosten/invoice.webp")

    def test_empty_folder_is_complete_and_invalid_config_is_structured(self):
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 0)
        self.assertTrue(data["scan_complete"])
        self.assertEqual(data["total_files"], 0)
        self.write_config("[receipts]\nroot = 'somewhere'\nyear_dir = 'wrong'\n")
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 2)
        self.assertEqual(data["errors"][0]["code"], "invalid_config")

    def test_unreadable_database_is_structured(self):
        self.db_path.write_bytes(b"not a database")
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 2)
        self.assertEqual(data["errors"][0]["code"], "database_error")
        self.assertIsNone(data["total_files"])

    def test_symlinked_subdirectory_is_skipped(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "external.pdf").write_bytes(b"x")
        (self.expenses / "shortcut").symlink_to(outside, target_is_directory=True)
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 0)
        self.assertEqual(data["total_files"], 0)
        self.assertEqual(data["skipped_entries"][0]["reason"], "symlink")

    def test_table_format_output_with_hits_and_zero_hits(self):
        (self.expenses / "test_doc.pdf").write_bytes(b"x" * 2048)
        response = self.run_cli(
            ["receipt", "unbooked", "--year", "2026", "--type", "expense", "--format", "table"]
        )
        self.assertEqual(response.returncode, 1)
        self.assertIn("Belegdateien ohne zugeordnete Buchung 2026 (Ausgaben)", response.stdout)
        self.assertIn("2026/Ausgaben/test_doc.pdf", response.stdout)
        self.assertIn("2 KB", response.stdout)
        self.assertIn("Berücksichtigte Belegdateien: 1", response.stdout)
        self.assertIn("Ohne Zuordnung:              1", response.stdout)
        self.assertIn("Prüfe zuerst bestehende Buchungen", response.stdout)

        # Buchung hinzufügen -> 0 Treffer
        self.add_expense(receipt="test_doc.pdf")
        response_zero = self.run_cli(
            ["receipt", "unbooked", "--year", "2026", "--type", "expense", "--format", "table"]
        )
        self.assertEqual(response_zero.returncode, 0)
        self.assertIn("Berücksichtigte Belegdateien: 1", response_zero.stdout)
        self.assertIn("Davon referenziert:          1", response_zero.stdout)
        self.assertIn("Ohne Zuordnung:              0", response_zero.stdout)
        self.assertNotIn("Prüfe zuerst bestehende Buchungen", response_zero.stdout)

    def test_case_insensitive_filesystem_and_extensionless_matching(self):
        probe = self.root / ".fs_probe"
        probe.write_text("x")
        is_case_insensitive = (self.root / ".FS_PROBE").exists()
        probe.unlink(missing_ok=True)
        if not is_case_insensitive:
            self.skipTest("Dateisystem unterscheidet Groß-/Kleinschreibung")

        (self.expenses / "2026-01-15_Telekom.PDF").write_bytes(b"telekom")
        self.add_expense(receipt="2026-01-15_Telekom")
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 0)
        self.assertEqual(data["referenced_files"], 1)
        self.assertEqual(data["unbooked_count"], 0)

    def test_reference_over_symlink_warns(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "invoice.pdf").write_bytes(b"content")
        (self.expenses / "sublink").symlink_to(outside, target_is_directory=True)
        self.add_expense(receipt="sublink/invoice.pdf")
        response, data = self.scan("--type", "expense")
        self.assertEqual(response.returncode, 0)
        self.assertEqual(data["total_files"], 0)
        warning_codes = [w["code"] for w in data["warnings"]]
        self.assertIn("invalid_receipt_reference", warning_codes)


if __name__ == "__main__":
    import unittest

    unittest.main()
