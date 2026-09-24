import csv
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path

from tests.cli_test_base import BaseCLITestCase


class CLIImportExportTestCase(BaseCLITestCase):
    def test_export_csv(self):
        self.write_config(
            """
[[ledger_accounts]]
key = "hosting"
name = "Hosting & Cloud-Dienste"
category = "Laufende EDV-Kosten"
account_number = "4940"

[[ledger_accounts]]
key = "erloese-19"
name = "Erlöse 19% USt"
category = "Umsatzsteuerpflichtige Betriebseinnahmen"
account_number = "8400"
""".strip()
            + "\n"
        )
        self.add_expense(category=None, ledger_account="hosting")
        self.add_income(category=None, ledger_account="erloese-19")
        self.add_private_deposit()
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
        self.assertEqual(len(exported), 4)
        exp_file = Path(exported[0])
        inc_file = Path(exported[1])
        private_file = Path(exported[2])
        sache_file = Path(exported[3])
        self.assertTrue(exp_file.exists())
        self.assertTrue(inc_file.exists())
        self.assertTrue(private_file.exists())
        self.assertTrue(sache_file.exists())

        exp_header = exp_file.read_text(encoding="utf-8-sig").splitlines()[0]
        inc_header = inc_file.read_text(encoding="utf-8-sig").splitlines()[0]
        private_header = private_file.read_text(encoding="utf-8-sig").splitlines()[0]
        sache_header = sache_file.read_text(encoding="utf-8-sig").splitlines()[0]
        self.assertIn("Belegname", exp_header)
        self.assertIn("Buchungskonto", exp_header)
        self.assertIn("Kontonummer", exp_header)
        self.assertIn("Belegname", inc_header)
        self.assertIn("Buchungskonto", inc_header)
        self.assertIn("Kontonummer", inc_header)
        self.assertIn("Typ", private_header)
        self.assertIn("expense_id", sache_header)

        exp_rows = list(csv.reader(exp_file.read_text(encoding="utf-8-sig").splitlines()))
        inc_rows = list(csv.reader(inc_file.read_text(encoding="utf-8-sig").splitlines()))
        self.assertEqual(exp_rows[1][7], "hosting")
        self.assertEqual(exp_rows[1][8], "4940")
        self.assertEqual(inc_rows[1][6], "erloese-19")
        self.assertEqual(inc_rows[1][7], "8400")

    def test_export_csv_includes_rc_type(self):
        self.add_expense(
            vendor="OpenAI",
            category="Laufende EDV-Kosten",
            amount="-100.00",
            rc="third-country",
        )
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
        exp_file = Path(
            next(
                line.split("Exportiert: ", 1)[1]
                for line in result.stdout.splitlines()
                if line.startswith("Exportiert: ") and "Ausgaben" in line
            )
        )
        rows = list(csv.reader(exp_file.read_text(encoding="utf-8-sig").splitlines()))
        self.assertIn("RC", rows[0])
        self.assertEqual(rows[1][11], "third-country")

    def test_export_csv_all_years_default(self):
        self.add_expense(date="2025-12-31", vendor="Alt")
        self.add_expense(date="2026-01-15", vendor="Neu")
        self.add_income(date="2025-12-05", source="Alt")
        self.add_income(date="2026-02-01", source="Neu")
        self.add_private_deposit(date="2025-12-20", amount="100.00", description="Alt")
        self.add_private_deposit(date="2026-02-20", amount="200.00", description="Neu")
        export_dir = self.root / "exports"
        export_dir.mkdir()

        result = self.run_cli(["export", "--output", str(export_dir)], check=True)
        self.assertIn("Exportiert:", result.stdout)

        exported = [
            line.split("Exportiert: ", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("Exportiert: ")
        ]
        self.assertEqual(len(exported), 4)
        exp_file = Path(exported[0])
        inc_file = Path(exported[1])
        private_file = Path(exported[2])
        self.assertTrue(exp_file.exists())
        self.assertTrue(inc_file.exists())
        self.assertTrue(private_file.exists())

        exp_rows = list(csv.reader(exp_file.read_text(encoding="utf-8-sig").splitlines()))
        inc_rows = list(csv.reader(inc_file.read_text(encoding="utf-8-sig").splitlines()))
        private_rows = list(csv.reader(private_file.read_text(encoding="utf-8-sig").splitlines()))

        exp_dates = {row[1] for row in exp_rows[1:]}
        inc_dates = {row[1] for row in inc_rows[1:]}
        self.assertIn("2025-12-31", exp_dates)
        self.assertIn("2026-01-15", exp_dates)
        self.assertIn("2025-12-05", inc_dates)
        self.assertIn("2026-02-01", inc_dates)
        private_dates = {row[1] for row in private_rows[1:]}
        self.assertIn("2025-12-20", private_dates)
        self.assertIn("2026-02-20", private_dates)

    def test_import_accepts_export_headers(self):
        self.write_config(
            """
[[ledger_accounts]]
key = "hosting"
name = "Hosting & Cloud-Dienste"
category = "Arbeitsmittel"
account_number = "4940"
""".strip()
            + "\n"
        )
        import_file = self.root / "import_export_headers.csv"
        import_file.write_text(
            "\n".join(
                [
                    "Belegname,Datum,Lieferant,Kategorie,EUR,Konto,Buchungskonto,"
                    "Kontonummer,Fremdwährung,Bemerkung,RC,Vorsteuer,Umsatzsteuer",
                    "2026-01-10_1und1,2026-01-10,1und1,Arbeitsmittel (51),"
                    "-39.99,Bank,hosting,4940,,Note,eu,0.00,0.00",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cli(["import", "--file", str(import_file), "--format", "csv"], check=True)
        self.assertIn("Ausgaben angelegt: 1", result.stdout)

        rows = self.list_expenses_csv()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][4], "(52) Arbeitsmittel")
        self.assertEqual(rows[1][3], "1und1")

    def test_import_accepts_vat_classification_fields(self):
        self.run_cli(["setup"], input="\n\n\n\n\nstandard\n", check=True)
        import_file = self.root / "import_vat_fields.csv"
        import_file.write_text(
            "\n".join(
                [
                    "type,date,party,category,amount_eur,vat_rate",
                    "income,2026-01-10,Kunde,Umsatzsteuerpflichtige Betriebseinnahmen,107.00,7%",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        self.run_cli(["import", "--file", str(import_file), "--format", "csv"], check=True)
        query = self.run_cli(
            ["query", "SELECT vat_rate, vat_code, vat_output FROM income WHERE id = 1"],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1][0], "7.0")
        self.assertEqual(rows[1][1], "output_reduced_7")
        self.assertEqual(rows[1][2], "7.0")

    def test_import_legacy_rc_boolean_requires_jurisdiction(self):
        import_file = self.root / "import_missing_rc_type.csv"
        import_file.write_text(
            "\n".join(
                [
                    "type,date,party,category,amount_eur,rc",
                    "expense,2026-01-10,Vendor A,Arbeitsmittel,-20.00,true",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cli(["import", "--file", str(import_file), "--format", "csv"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rc_type", result.stderr)

    def test_init_migrates_legacy_rc_columns_to_rc_type(self):
        self.db_path.unlink()
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    eur_line INTEGER,
                    type TEXT NOT NULL CHECK(type IN ('expense', 'income'))
                );
                CREATE TABLE expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    receipt_name TEXT,
                    payment_date DATE,
                    invoice_date DATE,
                    vendor TEXT NOT NULL,
                    category_id INTEGER REFERENCES categories(id),
                    amount_eur REAL NOT NULL,
                    account TEXT,
                    ledger_account TEXT,
                    foreign_amount TEXT,
                    notes TEXT,
                    is_rc INTEGER NOT NULL DEFAULT 0,
                    vat_input REAL,
                    vat_output REAL,
                    is_private_paid INTEGER NOT NULL DEFAULT 0,
                    private_classification TEXT NOT NULL DEFAULT 'none',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hash TEXT UNIQUE NOT NULL,
                    CHECK(invoice_date IS NOT NULL OR payment_date IS NOT NULL)
                );
                CREATE TABLE income (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    receipt_name TEXT,
                    payment_date DATE,
                    invoice_date DATE,
                    source TEXT NOT NULL,
                    category_id INTEGER REFERENCES categories(id),
                    amount_eur REAL NOT NULL,
                    ledger_account TEXT,
                    foreign_amount TEXT,
                    notes TEXT,
                    vat_output REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hash TEXT UNIQUE NOT NULL,
                    CHECK(invoice_date IS NOT NULL OR payment_date IS NOT NULL)
                );
                CREATE TABLE audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    table_name TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    record_uuid TEXT,
                    action TEXT NOT NULL,
                    old_data TEXT,
                    new_data TEXT,
                    user TEXT NOT NULL DEFAULT 'default'
                );
                """
            )
            conn.execute(
                """INSERT INTO expenses
                   (uuid, payment_date, vendor, amount_eur, is_rc, vat_input,
                    vat_output, hash)
                   VALUES (?, ?, ?, ?, 1, 0.0, 19.0, ?)""",
                (
                    "legacy-rc",
                    "2026-01-15",
                    "Legacy SaaS",
                    -100.0,
                    "legacy-rc-hash",
                ),
            )

        self.run_cli(["init"], check=True)
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()}
            income_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(income)").fetchall()
            }
            rc_type = conn.execute(
                "SELECT rc_type FROM expenses WHERE uuid = ?",
                ("legacy-rc",),
            ).fetchone()[0]
        self.assertIn("rc_type", columns)
        self.assertIn("vat_rate", columns)
        self.assertIn("vat_code", columns)
        self.assertIn("vat_rate", income_columns)
        self.assertIn("vat_code", income_columns)
        self.assertNotIn("is_rc", columns)
        self.assertNotIn("rc_jurisdiction", columns)
        self.assertEqual(rc_type, "unclassified")

    def test_import_missing_required_fails(self):
        import_file = self.root / "import_missing.csv"
        import_file.write_text(
            "\n".join(
                [
                    "type,date,party,category,amount_eur,receipt_name,notes",
                    "expense,2026-01-10,Vendor A,Arbeitsmittel,-20.00,rec1.pdf,Note",
                    ",2026-01-13,Vendor B,Arbeitsmittel,,missing.pdf,",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cli(["import", "--file", str(import_file), "--format", "csv"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pflichtfelder fehlen", result.stderr)


if __name__ == "__main__":
    unittest.main()
