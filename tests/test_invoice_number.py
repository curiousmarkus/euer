import csv
import json
import sqlite3
from contextlib import closing

from tests.cli_test_base import BaseCLITestCase


class InvoiceNumberTestCase(BaseCLITestCase):
    def test_add_update_list_and_export(self):
        for kind, party_flag, party, amount, category in (
            ("expense", "--vendor", "Lieferant", "-20", "Arbeitsmittel"),
            (
                "income",
                "--source",
                "Kunde",
                "20",
                "Umsatzsteuerpflichtige Betriebseinnahmen",
            ),
        ):
            self.run_cli(
                [
                    "add",
                    kind,
                    "--date",
                    "2026-01-15",
                    party_flag,
                    party,
                    "--category",
                    category,
                    "--amount",
                    amount,
                    "--invoice-number",
                    "  R-17  ",
                ],
                check=True,
            )
            table = "expenses" if kind == "expense" else "income"
            with closing(sqlite3.connect(self.db_path)) as conn:
                self.assertEqual(
                    conn.execute(f"SELECT invoice_number FROM {table}").fetchone()[0], "R-17"
                )
                data = conn.execute(
                    "SELECT new_data FROM audit_log WHERE table_name = ? AND action = 'INSERT'",
                    (table,),
                ).fetchone()[0]
                self.assertEqual(json.loads(data)["invoice_number"], "R-17")
            rows = self.parse_csv(
                self.run_cli(
                    ["list", table, "--year", "2026", "--format", "csv"], check=True
                ).stdout
            )
            self.assertEqual(rows[0][-1], "Rechnungsnummer")
            self.assertEqual(rows[1][-1], "R-17")

            self.run_cli(["update", kind, "1", "--invoice-number", "R-18"], check=True)
            with closing(sqlite3.connect(self.db_path)) as conn:
                self.assertEqual(
                    conn.execute(f"SELECT invoice_number FROM {table}").fetchone()[0], "R-18"
                )

        output = self.root / "exports"
        output.mkdir()
        self.run_cli(["export", "--output", str(output)], check=True)
        for suffix in ("Ausgaben", "Einnahmen"):
            with (output / f"EÜR_{suffix}.csv").open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.reader(file))
            self.assertEqual(rows[0][-1], "Rechnungsnummer")
            self.assertEqual(rows[1][-1], "R-18")

        self.run_cli(["update", "expense", "1", "--invoice-number", ""], check=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.assertIsNone(conn.execute("SELECT invoice_number FROM expenses").fetchone()[0])

    def test_import_invoice_number(self):
        source = self.root / "invoice.csv"
        source.write_text(
            "type,date,party,category,amount_eur,Rechnungsnummer\n"
            "expense,2026-02-01,Anbieter,Arbeitsmittel,-12.00,RE-99\n",
            encoding="utf-8",
        )
        self.run_cli(["import", "--file", str(source), "--format", "csv"], check=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.assertEqual(
                conn.execute("SELECT invoice_number FROM expenses").fetchone()[0], "RE-99"
            )
