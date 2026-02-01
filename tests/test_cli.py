import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, "-m", "euercli"]


class EuerCLITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.db_path = self.root / "test.db"
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.home)
        self.env["PYTHONIOENCODING"] = "utf-8"
        self.run_cli(["init"], check=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, args: list[str], input: str | None = None, check: bool = False):
        result = subprocess.run(
            CLI + ["--db", str(self.db_path)] + args,
            input=input,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
            env=self.env,
        )
        if check and result.returncode != 0:
            self.fail(
                "Command failed: "
                f"{args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def parse_csv(self, output: str) -> list[list[str]]:
        return list(csv.reader(io.StringIO(output)))

    def add_expense(self, **overrides):
        data = {
            "date": "2026-01-15",
            "vendor": "TestVendor",
            "category": "Arbeitsmittel",
            "amount": "-10.00",
        }
        data.update(overrides)
        args = [
            "add",
            "expense",
            "--date",
            data["date"],
            "--vendor",
            data["vendor"],
            "--category",
            data["category"],
            "--amount",
            str(data["amount"]),
        ]
        if "account" in data:
            args += ["--account", data["account"]]
        if "foreign" in data:
            args += ["--foreign", data["foreign"]]
        if "receipt" in data:
            args += ["--receipt", data["receipt"]]
        if "notes" in data:
            args += ["--notes", data["notes"]]
        if data.get("rc"):
            args.append("--rc")
        if "vat" in data:
            args += ["--vat", str(data["vat"])]
        return self.run_cli(args)

    def add_income(self, **overrides):
        data = {
            "date": "2026-01-20",
            "source": "TestClient",
            "category": "Umsatzsteuerpflichtige Betriebseinnahmen",
            "amount": "1500.00",
        }
        data.update(overrides)
        args = [
            "add",
            "income",
            "--date",
            data["date"],
            "--source",
            data["source"],
            "--category",
            data["category"],
            "--amount",
            str(data["amount"]),
        ]
        if "foreign" in data:
            args += ["--foreign", data["foreign"]]
        if "receipt" in data:
            args += ["--receipt", data["receipt"]]
        if "notes" in data:
            args += ["--notes", data["notes"]]
        return self.run_cli(args)

    def list_expenses_csv(self):
        result = self.run_cli(["list", "expenses", "--year", "2026", "--format", "csv"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return self.parse_csv(result.stdout)

    def list_income_csv(self):
        result = self.run_cli(["list", "income", "--year", "2026", "--format", "csv"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return self.parse_csv(result.stdout)

    def test_init_and_list_categories(self):
        result = self.run_cli(["list", "categories"], check=True)
        self.assertIn("Telekommunikation", result.stdout)
        self.assertIn("Arbeitsmittel", result.stdout)

    def test_add_expense_and_list_csv(self):
        add_result = self.add_expense(account="Bank", receipt="receipt.pdf")
        self.assertEqual(add_result.returncode, 0, msg=add_result.stderr)
        self.assertIn("Ausgabe #1 hinzugefügt", add_result.stdout)

        rows = self.list_expenses_csv()
        self.assertEqual(len(rows), 2)
        # ID, Datum, Lieferant, Kategorie, EUR, Konto, Beleg, Fremdwährung, Bemerkung, RC, Vorsteuer, Umsatzsteuer
        rec_id, date, vendor, category, amount, account, receipt, foreign, notes, rc, vat_input, vat_output = rows[1]
        self.assertEqual(date, "2026-01-15")
        self.assertEqual(vendor, "TestVendor")
        self.assertEqual(category, "Arbeitsmittel (52)")
        self.assertEqual(amount, "-10.00")
        self.assertEqual(account, "Bank")
        self.assertEqual(receipt, "receipt.pdf")
        self.assertEqual(foreign, "")
        self.assertEqual(notes, "")
        self.assertEqual(rc, "")
        self.assertEqual(vat_input, "")
        self.assertEqual(vat_output, "")

    def test_add_income_and_list_csv(self):
        add_result = self.add_income(receipt="invoice.pdf")
        self.assertEqual(add_result.returncode, 0, msg=add_result.stderr)
        self.assertIn("Einnahme #1 hinzugefügt", add_result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(len(rows), 2)
        # ID, Datum, Quelle, Kategorie, EUR, Beleg, Fremdwährung, Bemerkung, Umsatzsteuer
        rec_id, date, source, category, amount, receipt, foreign, notes, vat_output = rows[1]
        self.assertEqual(date, "2026-01-20")
        self.assertEqual(source, "TestClient")
        self.assertEqual(category, "Umsatzsteuerpflichtige Betriebseinnahmen (14)")
        self.assertEqual(amount, "1500.00")
        self.assertEqual(receipt, "invoice.pdf")
        self.assertEqual(foreign, "")
        self.assertEqual(notes, "")
        self.assertEqual(vat_output, "")


    def test_duplicate_detection(self):
        first = self.add_expense()
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        second = self.add_expense()
        self.assertEqual(second.returncode, 0, msg=second.stderr)
        self.assertIn("Warnung: Duplikat erkannt", second.stderr)

        rows = self.list_expenses_csv()
        self.assertEqual(len(rows), 2)

    def test_update_expense(self):
        self.add_expense()
        result = self.run_cli(
            ["update", "expense", "1", "--amount", "-15.50", "--notes", "Korrigiert"],
            check=True,
        )
        self.assertIn("Ausgabe #1 aktualisiert", result.stdout)

        rows = self.list_expenses_csv()
        self.assertEqual(rows[1][4], "-15.50")
        self.assertEqual(rows[1][8], "Korrigiert")

    def test_update_income(self):
        self.add_income()
        result = self.run_cli(
            ["update", "income", "1", "--amount", "1750.00", "--notes", "Korrigiert"],
            check=True,
        )
        self.assertIn("Einnahme #1 aktualisiert", result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(rows[1][4], "1750.00")
        self.assertEqual(rows[1][7], "Korrigiert")

    def test_delete_expense_force(self):
        self.add_expense()
        result = self.run_cli(["delete", "expense", "1", "--force"], check=True)
        self.assertIn("Ausgabe #1 gelöscht", result.stdout)

        rows = self.list_expenses_csv()
        self.assertEqual(len(rows), 1)

    def test_delete_income_confirm(self):
        self.add_income()
        result = self.run_cli(["delete", "income", "1"], input="j\n", check=True)
        self.assertIn("Einnahme #1 gelöscht", result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(len(rows), 1)

    def test_list_expenses_table_with_vat(self):
        result = self.add_expense(
            vendor="OpenAI",
            category="Laufende EDV-Kosten",
            amount="-100.00",
            rc=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        list_result = self.run_cli(["list", "expenses", "--year", "2026"], check=True)
        self.assertIn("USt", list_result.stdout)
        self.assertIn("OpenAI", list_result.stdout)

    def test_list_income_table(self):
        self.add_income()
        list_result = self.run_cli(["list", "income", "--year", "2026"], check=True)
        self.assertIn("Quelle", list_result.stdout)
        self.assertIn("GESAMT", list_result.stdout)

    def test_export_csv(self):
        self.add_expense()
        self.add_income()
        export_dir = self.root / "exports"
        export_dir.mkdir()

        result = self.run_cli(
            [
                "export",
                "--year",
                "2026",
                "--format",
                "csv",
                "--output",
                str(export_dir),
            ],
            check=True,
        )
        self.assertIn("Exportiert:", result.stdout)

        exported = [
            line.split("Exportiert: ", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("Exportiert: ")
        ]
        self.assertEqual(len(exported), 2)
        exp_file = Path(exported[0])
        inc_file = Path(exported[1])
        self.assertTrue(exp_file.exists())
        self.assertTrue(inc_file.exists())

        exp_header = exp_file.read_text(encoding="utf-8-sig").splitlines()[0]
        inc_header = inc_file.read_text(encoding="utf-8-sig").splitlines()[0]
        self.assertIn("Belegname", exp_header)
        self.assertIn("Belegname", inc_header)

    def test_summary_and_rc(self):
        self.add_expense(
            vendor="OpenAI",
            category="Laufende EDV-Kosten",
            amount="-100.00",
            rc=True,
        )
        self.add_income(amount="1000.00")
        result = self.run_cli(["summary", "--year", "2026"], check=True)
        self.assertIn("GESAMT Ausgaben", result.stdout)
        self.assertIn("GESAMT Einnahmen", result.stdout)
        self.assertIn("Umsatzsteuer (Kleinunternehmer)", result.stdout)

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
        expenses_dir = self.root / "receipts" / "expenses"
        income_dir = self.root / "receipts" / "income"
        export_dir = self.root / "exports"
        input_data = f"{expenses_dir}\n{income_dir}\n{export_dir}\n"

        result = self.run_cli(["setup"], input=input_data, check=True)
        self.assertIn("Konfiguration gespeichert", result.stdout)

        config_path = self.home / ".config" / "euer" / "config.toml"
        content = config_path.read_text(encoding="utf-8")
        self.assertIn("[receipts]", content)
        self.assertIn(f'expenses = "{expenses_dir}"', content)
        self.assertIn(f'income = "{income_dir}"', content)
        self.assertIn("[exports]", content)
        self.assertIn(f'directory = "{export_dir}"', content)

    def test_receipt_check_requires_config(self):
        result = self.run_cli(["receipt", "check"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Keine Beleg-Pfade konfiguriert", result.stderr)

    def test_receipt_check_missing_file(self):
        expenses_dir = self.root / "receipts" / "expenses"
        expenses_dir.mkdir(parents=True)
        self.run_cli(["setup"], input=f"{expenses_dir}\n\n", check=True)
        self.add_expense(receipt="missing.pdf")

        result = self.run_cli(["receipt", "check", "--year", "2026", "--type", "expense"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Fehlende Belege (Ausgaben)", result.stdout)

    def test_receipt_open_missing_file(self):
        expenses_dir = self.root / "receipts" / "expenses"
        expenses_dir.mkdir(parents=True)
        self.run_cli(["setup"], input=f"{expenses_dir}\n\n", check=True)
        self.add_expense(receipt="missing.pdf")

        result = self.run_cli(["receipt", "open", "1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nicht gefunden", result.stderr)

    def test_bulk_import_and_incomplete_list(self):
        import_file = self.root / "import.csv"
        import_file.write_text(
            "\n".join(
                [
                    "type,date,party,category,amount_eur,receipt_name,notes",
                    "expense,2026-01-10,Vendor A,Arbeitsmittel,-20.00,rec1.pdf,Note",
                    "income,2026-01-12,Client A,Umsatzsteuerpflichtige Betriebseinnahmen,200.00,inv1.pdf,",
                    ",2026-01-13,Vendor B,Arbeitsmittel,,missing.pdf,",
                    ",2026-01-14,Client B,Umsatzsteuerpflichtige Betriebseinnahmen,300.00,,",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cli(
            ["import", "--file", str(import_file), "--format", "csv"], check=True
        )
        self.assertIn("Import abgeschlossen", result.stdout)
        self.assertIn("Ausgaben angelegt: 1", result.stdout)
        self.assertIn("Einnahmen angelegt: 2", result.stdout)
        self.assertIn("Unvollständig: 1", result.stdout)

        expenses = self.list_expenses_csv()
        income = self.list_income_csv()
        self.assertEqual(len(expenses), 2)
        self.assertEqual(len(income), 3)

        incomplete_result = self.run_cli(
            ["incomplete", "list", "--format", "csv"], check=True
        )
        rows = self.parse_csv(incomplete_result.stdout)
        self.assertEqual(len(rows), 2)
        self.assertIn("missing.pdf", incomplete_result.stdout)


if __name__ == "__main__":
    unittest.main()
