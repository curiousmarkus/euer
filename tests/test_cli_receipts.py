import unittest

from tests.cli_test_base import BaseCLITestCase


class CLIReceiptsTestCase(BaseCLITestCase):
    def test_receipt_check_requires_config(self):
        result = self.run_cli(["receipt", "check"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Kein Beleg-Root konfiguriert", result.stderr)

    def test_receipt_check_missing_file(self):
        receipts_root = self.root / "receipts"
        receipts_root.mkdir(parents=True)
        self.write_config(f"[receipts]\nroot = '{receipts_root}'\n")
        self.add_expense(receipt="missing.pdf")

        result = self.run_cli(["receipt", "check", "--year", "2026", "--type", "expense"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Fehlende Belege (Ausgaben)", result.stdout)
        self.assertIn(str(receipts_root / "2026" / "Ausgaben" / "missing.pdf"), result.stdout)

    def test_receipt_open_missing_file(self):
        receipts_root = self.root / "receipts"
        receipts_root.mkdir(parents=True)
        self.write_config(f"[receipts]\nroot = '{receipts_root}'\n")
        self.add_expense(receipt="missing.pdf")

        result = self.run_cli(["receipt", "open", "1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nicht gefunden", result.stderr)
        self.assertIn(str(receipts_root / "2026" / "Ausgaben" / "missing.pdf"), result.stderr)

    def test_receipt_open_without_payment_date_explains_missing_year_context(self):
        receipts_root = self.root / "receipts"
        receipts_root.mkdir(parents=True)
        self.write_config(f"[receipts]\nroot = '{receipts_root}'\n")
        self.run_cli(
            [
                "add",
                "expense",
                "--invoice-date",
                "2026-01-16",
                "--vendor",
                "InvoiceOnly",
                "--amount",
                "-22.99",
                "--receipt",
                "invoice-only.pdf",
            ],
            check=True,
        )

        result = self.run_cli(["receipt", "open", "1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Ohne Wertstellungsdatum", result.stderr)
        self.assertIn("update expense 1 --payment-date", result.stderr)
        self.assertNotIn("2026/Ausgaben", result.stderr)

    def test_receipt_check_finds_extension(self):
        receipts_root = self.root / "receipts"
        receipt_dir = receipts_root / "2026" / "Ausgaben"
        receipt_dir.mkdir(parents=True)
        self.write_config(f"[receipts]\nroot = '{receipts_root}'\n")

        receipt_name = "2026-01-15_TestVendor"
        (receipt_dir / f"{receipt_name}.pdf").write_text("dummy", encoding="utf-8")
        self.add_expense(receipt=receipt_name)

        result = self.run_cli(["receipt", "check", "--year", "2026", "--type", "expense"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_receipt_check_finds_income_receipt(self):
        receipts_root = self.root / "receipts"
        receipt_dir = receipts_root / "2026" / "Einnahmen"
        receipt_dir.mkdir(parents=True)
        self.write_config(f"[receipts]\nroot = '{receipts_root}'\n")

        receipt_name = "2026-01-20_Rechnung_001.pdf"
        (receipt_dir / receipt_name).write_text("dummy", encoding="utf-8")
        self.add_income(receipt=receipt_name)

        result = self.run_cli(["receipt", "check", "--year", "2026", "--type", "income"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_receipt_check_uses_custom_year_dir(self):
        receipts_root = self.root / "receipts"
        receipt_dir = receipts_root / "Buchhaltung 2026" / "Ausgaben"
        receipt_dir.mkdir(parents=True)
        self.write_config(
            f"[receipts]\nroot = '{receipts_root}'\nyear_dir = \"Buchhaltung {{year}}\"\n"
        )

        receipt_name = "2026-01-15_TestVendor.pdf"
        (receipt_dir / receipt_name).write_text("dummy", encoding="utf-8")
        self.add_expense(receipt=receipt_name)

        result = self.run_cli(["receipt", "check", "--year", "2026", "--type", "expense"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_add_receipt_warning_uses_new_candidate_paths(self):
        receipts_root = self.root / "receipts"
        receipts_root.mkdir(parents=True)
        self.write_config(f"[receipts]\nroot = '{receipts_root}'\n")

        result = self.add_expense(receipt="missing")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(str(receipts_root / "2026" / "Ausgaben" / "missing.pdf"), result.stderr)

    def test_add_receipt_warning_does_not_use_invoice_date_as_year(self):
        receipts_root = self.root / "receipts"
        receipts_root.mkdir(parents=True)
        self.write_config(f"[receipts]\nroot = '{receipts_root}'\n")

        result = self.run_cli(
            [
                "add",
                "expense",
                "--invoice-date",
                "2026-01-16",
                "--vendor",
                "InvoiceOnly",
                "--amount",
                "-22.99",
                "--receipt",
                "invoice-only.pdf",
            ],
            check=True,
        )
        self.assertNotIn("Beleg 'invoice-only.pdf' nicht gefunden", result.stderr)
        self.assertNotIn("2026/Ausgaben", result.stderr)


if __name__ == "__main__":
    unittest.main()
