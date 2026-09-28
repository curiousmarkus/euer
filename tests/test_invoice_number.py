import csv
import hashlib
import json
import sqlite3
from contextlib import closing

from tests.cli_test_base import BaseCLITestCase


class InvoiceNumberTestCase(BaseCLITestCase):
    def test_import_rolls_back_on_suspicious_invoice_number(self):
        self.run_cli(
            [
                "add", "expense", "--date", "2026-01-10", "--vendor", "Anbieter",
                "--category", "Arbeitsmittel", "--amount", "-25",
                "--invoice-number", "RE-7",
            ],
            check=True,
        )
        source = self.root / "suspicious.csv"
        source.write_text(
            "type,date,party,category,amount_eur,invoice_number\n"
            "expense,2026-02-10,Neu,Arbeitsmittel,-10,NEU-1\n"
            "expense,2026-03-10,Anbieter,Arbeitsmittel,-25,RE-7\n",
            encoding="utf-8",
        )
        result = self.run_cli(["import", "--file", str(source), "--format", "csv"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Zeile 2", result.stderr)
        self.assertIn("Rechnungsnummer RE-7", result.stderr)
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0], 1)

    def test_hash_distinguishes_receipt_delimiter_and_legacy_numbered_rows(self):
        base = [
            "add", "expense", "--date", "2026-01-10", "--vendor", "Anbieter",
            "--category", "Arbeitsmittel", "--amount", "-25",
        ]
        self.run_cli(base + ["--receipt", "beleg|R-1"], check=True)
        self.run_cli(
            base + ["--receipt", "beleg", "--invoice-number", "R-1", "--allow-duplicate"],
            check=True,
        )
        old_base = [
            "add", "expense", "--date", "2026-02-10", "--vendor", "Anbieter",
            "--category", "Arbeitsmittel", "--amount", "-25",
            "--receipt", "alt", "--invoice-number", "R-2",
        ]
        self.run_cli(old_base, check=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            legacy_hash = hashlib.sha256(
                "2026-02-10|Anbieter|-25.00|alt|R-2".encode("utf-8")
            ).hexdigest()
            # Ein bestehender Datensatz aus der ersten Umsetzung behält seinen Hash.
            conn.execute("UPDATE expenses SET hash = ? WHERE id = 3", (legacy_hash,))
            conn.commit()
        duplicate = self.run_cli(old_base)
        self.assertEqual(duplicate.returncode, 0)
        self.assertIn("Duplikat erkannt", duplicate.stderr)
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0], 3)

    def test_invoice_number_duplicate_guardrail(self):
        for kind, party_flag, category, amount in (
            ("expense", "--vendor", "Arbeitsmittel", "-25"),
            ("income", "--source", "Umsatzsteuerpflichtige Betriebseinnahmen", "25"),
        ):

            def add(date, party, value, number, *extra):
                return self.run_cli(
                    [
                        "add",
                        kind,
                        "--date",
                        date,
                        party_flag,
                        party,
                        "--category",
                        category,
                        "--amount",
                        value,
                        "--invoice-number",
                        number,
                        *extra,
                    ]
                )

            self.assertEqual(add("2026-01-10", "Anbieter", amount, "RE-7").returncode, 0)
            duplicate = add("2026-03-10", "Anbieter", amount, "RE-7")
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("Rechnungsnummer RE-7", duplicate.stderr)
            self.assertEqual(
                add(
                    "2026-03-10", "Anbieter", "-10" if kind == "expense" else "10", "RE-7"
                ).returncode,
                0,
            )
            self.assertEqual(add("2026-03-10", "Anderer Anbieter", amount, "RE-7").returncode, 0)
            self.assertEqual(add("2026-06-10", "Anbieter", amount, "RE-8").returncode, 0)

            changed = self.run_cli(["update", kind, "4", "--invoice-number", "RE-7"])
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("Rechnungsnummer RE-7", changed.stderr)
            self.assertEqual(
                add("2026-03-10", "Anbieter", amount, "RE-7", "--allow-duplicate").returncode,
                0,
            )
            self.assertEqual(
                add("2026-03-10", "Anbieter", amount, "RE-9", "--allow-duplicate").returncode,
                0,
            )
            self.assertEqual(
                self.run_cli(
                    [
                        "add",
                        kind,
                        "--date",
                        "2026-04-10",
                        party_flag,
                        "Altbestand",
                        "--category",
                        category,
                        "--amount",
                        amount,
                    ]
                ).returncode,
                0,
            )
            legacy_duplicate = add("2026-04-10", "Altbestand", amount, "RE-10")
            self.assertEqual(legacy_duplicate.returncode, 0)
            self.assertIn("Duplikat erkannt", legacy_duplicate.stderr)
            self.assertIn("überspringe", legacy_duplicate.stderr)

    def test_duplicate_when_only_one_booking_has_invoice_number(self):
        for kind, party_flag, category, amount in (
            ("expense", "--vendor", "Arbeitsmittel", "-31"),
            ("income", "--source", "Umsatzsteuerpflichtige Betriebseinnahmen", "31"),
        ):

            def add(payment, invoice, party, number=None):
                args = [
                    "add",
                    kind,
                    "--payment-date",
                    payment,
                    "--invoice-date",
                    invoice,
                    party_flag,
                    party,
                    "--category",
                    category,
                    "--amount",
                    amount,
                ]
                if number:
                    args += ["--invoice-number", number]
                return self.run_cli(args)

            self.assertEqual(add("2026-01-10", "2026-01-02", "Ohne Nummer").returncode, 0)
            result = add("2026-04-10", "2026-01-02", "Ohne Nummer", "R-31")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Mögliches Duplikat", result.stderr)

            self.assertEqual(add("2026-01-12", "2026-01-03", "Mit Nummer", "R-32").returncode, 0)
            result = add("2026-04-12", "2026-01-03", "Mit Nummer")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Mögliches Duplikat", result.stderr)

            first = self.run_cli(
                [
                    "add",
                    kind,
                    "--date",
                    "2026-01-14",
                    party_flag,
                    "Gleicher Beleg",
                    "--category",
                    category,
                    "--amount",
                    amount,
                    "--receipt",
                    "rechnung-31.pdf",
                    "--invoice-number",
                    "R-33",
                ]
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            second = self.run_cli(
                [
                    "add",
                    kind,
                    "--date",
                    "2026-04-14",
                    party_flag,
                    "Gleicher Beleg",
                    "--category",
                    category,
                    "--amount",
                    amount,
                    "--receipt",
                    "rechnung-31.pdf",
                ]
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("Mögliches Duplikat", second.stderr)

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
            self.assertEqual(rows[0][3], "Rechnungsnummer")
            self.assertEqual(rows[1][3], "R-18")

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
