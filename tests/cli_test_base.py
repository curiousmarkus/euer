import csv
import io
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, "-m", "euercli"]


class BaseCLITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.db_path = self.root / "test.db"
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.home)
        self.env["USERPROFILE"] = str(self.home)
        self.env["APPDATA"] = str(self.home / "AppData" / "Roaming")
        self.env["PYTHONIOENCODING"] = "utf-8"
        self.run_cli(["init"], check=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, args: list[str], input: str | None = None, check: bool = False):
        result = subprocess.run(
            CLI + ["--db", str(self.db_path)] + args,
            input=input,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=REPO_ROOT,
            env=self.env,
        )
        if check and result.returncode != 0:
            self.fail(f"Command failed: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def parse_csv(self, output: str) -> list[list[str]]:
        return list(csv.reader(io.StringIO(output)))

    def expected_config_path(self) -> Path:
        if platform.system() == "Windows":
            return Path(self.env["APPDATA"]) / "euer" / "config.toml"
        return Path(self.env["HOME"]) / ".config" / "euer" / "config.toml"

    def write_config(self, content: str) -> None:
        config_path = self.expected_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(content, encoding="utf-8")

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
            "--amount",
            str(data["amount"]),
        ]
        if data.get("category") is not None:
            args += ["--category", data["category"]]
        if "ledger_account" in data:
            args += ["--ledger-account", data["ledger_account"]]
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
            args.append("eu" if data["rc"] is True else str(data["rc"]))
        if data.get("private_paid"):
            args.append("--private-paid")
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
            "--amount",
            str(data["amount"]),
        ]
        if data.get("category") is not None:
            args += ["--category", data["category"]]
        if "ledger_account" in data:
            args += ["--ledger-account", data["ledger_account"]]
        if "foreign" in data:
            args += ["--foreign", data["foreign"]]
        if "receipt" in data:
            args += ["--receipt", data["receipt"]]
        if "notes" in data:
            args += ["--notes", data["notes"]]
        if "vat" in data:
            args += ["--vat", str(data["vat"])]
        if "vat_rate" in data:
            args += ["--vat-rate", str(data["vat_rate"])]
        if data.get("tax_free"):
            args.append("--tax-free")
        return self.run_cli(args)

    def add_private_deposit(self, **overrides):
        data = {
            "date": "2026-01-10",
            "amount": "500.00",
            "description": "Überweisung Privatkonto",
        }
        data.update(overrides)
        args = [
            "add",
            "private-deposit",
            "--date",
            data["date"],
            "--amount",
            str(data["amount"]),
            "--description",
            data["description"],
        ]
        if "notes" in data:
            args += ["--notes", data["notes"]]
        if "related_expense_id" in data:
            args += ["--related-expense-id", str(data["related_expense_id"])]
        return self.run_cli(args)

    def add_private_withdrawal(self, **overrides):
        data = {
            "date": "2026-01-20",
            "amount": "1000.00",
            "description": "Überweisung Privatkonto",
        }
        data.update(overrides)
        args = [
            "add",
            "private-withdrawal",
            "--date",
            data["date"],
            "--amount",
            str(data["amount"]),
            "--description",
            data["description"],
        ]
        if "notes" in data:
            args += ["--notes", data["notes"]]
        if "related_expense_id" in data:
            args += ["--related-expense-id", str(data["related_expense_id"])]
        return self.run_cli(args)

    def list_expenses_csv(self):
        result = self.run_cli(["list", "expenses", "--year", "2026", "--format", "csv"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return self.parse_csv(result.stdout)

    def list_income_csv(self):
        result = self.run_cli(["list", "income", "--year", "2026", "--format", "csv"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return self.parse_csv(result.stdout)
