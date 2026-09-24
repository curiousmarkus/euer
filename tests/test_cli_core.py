import tomllib
import unittest

from euercli import VERSION
from tests.cli_test_base import BaseCLITestCase


class CLICoreTestCase(BaseCLITestCase):
    def test_version_flag(self) -> None:
        result = self.run_cli(["--version"])

        self.assertEqual(0, result.returncode)
        self.assertEqual(f"{VERSION}\n", result.stdout)

    def test_init_and_list_categories(self):
        result = self.run_cli(["list", "categories"], check=True)
        self.assertIn("Telekommunikation", result.stdout)
        self.assertIn("Arbeitsmittel", result.stdout)

    def test_query_select(self):
        self.add_expense(vendor="QueryTest")
        result = self.run_cli(
            ["query", "SELECT", "id", "vendor", "FROM", "expenses", "LIMIT", "1"],
            check=True,
        )
        rows = self.parse_csv(result.stdout)
        self.assertGreaterEqual(len(rows), 2)
        self.assertIn("vendor", rows[0])

    def test_query_rejects_write(self):
        result = self.run_cli(["query", "UPDATE", "expenses", "SET", "vendor='X'"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Nur SELECT", result.stderr)

    def test_audit_log(self):
        self.add_expense()
        self.run_cli(["update", "expense", "1", "--amount", "-12.00"], check=True)
        self.run_cli(["delete", "expense", "1", "--force"], check=True)

        audit_result = self.run_cli(["audit", "1", "--table", "expenses"], check=True)
        self.assertIn("INSERT", audit_result.stdout)
        self.assertIn("UPDATE", audit_result.stdout)
        self.assertIn("DELETE", audit_result.stdout)

    def test_config_show_when_missing(self):
        result = self.run_cli(["config", "show"], check=True)
        self.assertIn("nicht vorhanden", result.stdout)
        self.assertIn("euer setup", result.stdout)

    def test_setup_writes_config(self):
        receipts_root = self.root / "receipts"
        export_dir = self.root / "exports"
        input_data = f"{receipts_root}\n\n\n\n{export_dir}\n"

        result = self.run_cli(["setup"], input=input_data, check=True)
        self.assertIn("Konfiguration gespeichert", result.stdout)

        config_path = self.expected_config_path()
        content = config_path.read_text(encoding="utf-8")
        config = tomllib.loads(content)
        self.assertEqual(config.get("receipts", {}).get("root"), str(receipts_root))
        self.assertEqual(config.get("receipts", {}).get("year_dir"), "{year}")
        self.assertEqual(config.get("receipts", {}).get("expenses_dir"), "Ausgaben")
        self.assertEqual(config.get("receipts", {}).get("income_dir"), "Einnahmen")
        self.assertEqual(config.get("exports", {}).get("directory"), str(export_dir))
        self.assertEqual(config.get("tax", {}).get("mode"), "small_business")
        self.assertEqual(config.get("accounts", {}).get("private"), ["privat"])

    def test_setup_writes_ledger_accounts(self):
        receipts_root = self.root / "receipts"
        export_dir = self.root / "exports"
        input_data = (
            f"{receipts_root}\n"
            "\n"
            "\n"
            "\n"
            f"{export_dir}\n"
            "\n"
            "\n"
            "\n"
            "j\n"
            "hosting\n"
            "Hosting & Cloud-Dienste\n"
            "9\n"
            "4940\n"
            "n\n"
        )

        result = self.run_cli(["setup"], input=input_data, check=True)
        self.assertIn("Konfiguration gespeichert", result.stdout)

        config = tomllib.loads(self.expected_config_path().read_text(encoding="utf-8"))
        self.assertEqual(len(config.get("ledger_accounts", [])), 1)
        self.assertEqual(config["ledger_accounts"][0]["key"], "hosting")
        self.assertEqual(config["ledger_accounts"][0]["account_number"], "4940")

    def test_list_ledger_accounts(self):
        self.write_config(
            """
[[ledger_accounts]]
key = "hosting"
name = "Hosting & Cloud-Dienste"
category = "Laufende EDV-Kosten"
account_number = "4940"

[[ledger_accounts]]
key = "saas"
name = "Software / SaaS-Abos"
category = "Laufende EDV-Kosten"
""".strip()
            + "\n"
        )

        result = self.run_cli(["list", "ledger-accounts"], check=True)
        self.assertIn("Kontenrahmen", result.stdout)
        self.assertIn("Laufende EDV-Kosten", result.stdout)
        self.assertIn("hosting", result.stdout)
        self.assertIn("4940", result.stdout)

    def test_setup_set_accounts_private(self):
        result = self.run_cli(
            ["setup", "--set", "accounts.private", "privat, Sparkasse Kreditkarte"],
            check=True,
        )
        self.assertIn("Konfiguration gespeichert", result.stdout)

        config_path = self.expected_config_path()
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(
            config.get("accounts", {}).get("private"),
            ["privat", "Sparkasse Kreditkarte"],
        )

    def test_setup_set_receipt_root_normalizes_quotes_and_home(self):
        result = self.run_cli(
            ["setup", "--set", "receipts.root", "'~/Buchhaltung'"],
            check=True,
        )
        self.assertIn("Konfiguration gespeichert", result.stdout)

        config = tomllib.loads(self.expected_config_path().read_text(encoding="utf-8"))
        self.assertEqual(
            config.get("receipts", {}).get("root"),
            str(self.home / "Buchhaltung"),
        )

    def test_setup_set_receipt_year_dir_validates_pattern(self):
        result = self.run_cli(
            ["setup", "--set", "receipts.year_dir", "Buchhaltung {year}"],
            check=True,
        )
        self.assertIn("Konfiguration gespeichert", result.stdout)

        config = tomllib.loads(self.expected_config_path().read_text(encoding="utf-8"))
        self.assertEqual(config.get("receipts", {}).get("year_dir"), "Buchhaltung {year}")

        invalid = self.run_cli(["setup", "--set", "receipts.year_dir", "Buchhaltung"])
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("{year}", invalid.stderr)

        empty = self.run_cli(["setup", "--set", "receipts.year_dir", ""])
        self.assertNotEqual(empty.returncode, 0)
        self.assertIn("darf nicht leer sein", empty.stderr)

    def test_setup_writes_tax_mode_standard(self):
        receipts_root = self.root / "receipts"
        export_dir = self.root / "exports"
        input_data = f"{receipts_root}\n\n\n\n{export_dir}\nstandard\n"

        self.run_cli(["setup"], input=input_data, check=True)

        config_path = self.expected_config_path()
        content = config_path.read_text(encoding="utf-8")
        config = tomllib.loads(content)
        self.assertEqual(config.get("tax", {}).get("mode"), "standard")

    def test_incomplete_list_from_bookings(self):
        self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-01-10",
                "--vendor",
                "Vendor A",
                "--amount",
                "-20.00",
            ],
            check=True,
        )

        incomplete_result = self.run_cli(["incomplete", "list", "--format", "csv"], check=True)
        rows = self.parse_csv(incomplete_result.stdout)
        self.assertEqual(len(rows), 2)
        self.assertIn("category", incomplete_result.stdout)
        self.assertIn("receipt", incomplete_result.stdout)
        self.assertIn("account", incomplete_result.stdout)


if __name__ == "__main__":
    unittest.main()
