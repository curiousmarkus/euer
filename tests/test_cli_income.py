import unittest

from tests.cli_test_base import BaseCLITestCase


class CLIIncomeTestCase(BaseCLITestCase):
    def test_add_income_and_list_csv(self):
        add_result = self.add_income(receipt="invoice.pdf")
        self.assertEqual(add_result.returncode, 0, msg=add_result.stderr)
        self.assertIn("Einnahme #1 hinzugefügt", add_result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(len(rows), 2)
        # ID, Wertstellung, Rechnung, Quelle, Kategorie, EUR, Beleg, Status, Fremdwährung, Bemerkung, Umsatzsteuer
        (
            rec_id,
            payment_date,
            invoice_date,
            source,
            category,
            amount,
            receipt,
            status,
            foreign,
            notes,
            vat_output,
        ) = rows[1]
        self.assertEqual(payment_date, "2026-01-20")
        self.assertEqual(invoice_date, "")
        self.assertEqual(source, "TestClient")
        self.assertEqual(category, "(15) Umsatzsteuerpflichtige Betriebseinnahmen")
        self.assertEqual(amount, "1500.00")
        self.assertEqual(receipt, "invoice.pdf")
        self.assertIn("Zahlung erfolgt", status)
        self.assertEqual(foreign, "")
        self.assertEqual(notes, "")
        self.assertEqual(vat_output, "")

    def test_update_income(self):
        self.add_income()
        result = self.run_cli(
            ["update", "income", "1", "--amount", "1750.00", "--notes", "Korrigiert"],
            check=True,
        )
        self.assertIn("Einnahme #1 aktualisiert", result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(rows[1][5], "1750.00")
        self.assertEqual(rows[1][9], "Korrigiert")

    def test_update_income_with_ledger_account_updates_category(self):
        self.write_config(
            """
[[ledger_accounts]]
key = "erloese-19"
name = "Erlöse 19% USt"
category = "Umsatzsteuerpflichtige Betriebseinnahmen"
account_number = "8400"
""".strip()
            + "\n"
        )
        self.add_income(
            category="Betriebseinnahmen als Kleinunternehmer",
            amount="500.00",
        )

        result = self.run_cli(
            ["update", "income", "1", "--ledger-account", "erloese-19"],
            check=True,
        )
        self.assertIn("Einnahme #1 aktualisiert", result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(rows[1][4], "(15) Umsatzsteuerpflichtige Betriebseinnahmen")

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "ledger_account",
                "FROM",
                "income",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        query_rows = self.parse_csv(query.stdout)
        self.assertEqual(query_rows[1][0], "erloese-19")

    def test_delete_income_confirm(self):
        self.add_income()
        result = self.run_cli(["delete", "income", "1"], input="j\n", check=True)
        self.assertIn("Einnahme #1 gelöscht", result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(len(rows), 1)

    def test_list_income_table(self):
        self.add_income()
        list_result = self.run_cli(["list", "income", "--year", "2026"], check=True)
        self.assertIn("Quelle", list_result.stdout)
        self.assertIn("USt", list_result.stdout)
        self.assertIn("(15)", list_result.stdout)
        self.assertNotIn("Notiz", list_result.stdout)
        self.assertIn("GESAMT", list_result.stdout)

    def test_list_income_table_shows_vat_value(self):
        self.run_cli(["setup"], input="\n\n\n\n\nstandard\n", check=True)
        self.add_income(source="VAT Kunde", vat="285.00")
        list_result = self.run_cli(["list", "income", "--year", "2026"], check=True)
        self.assertIn("USt", list_result.stdout)
        self.assertIn("285.00", list_result.stdout)

    def test_list_income_table_full_shows_notes(self):
        self.add_income(source="Notiz Kunde", notes="Abo verlängert")
        list_result = self.run_cli(
            ["list", "income", "--year", "2026", "--full"],
            check=True,
        )
        self.assertIn("USt", list_result.stdout)
        self.assertIn("Notiz", list_result.stdout)
        self.assertIn("Abo verlängert", list_result.stdout)

    def test_add_income_vat_rate_persists_classification(self):
        self.run_cli(["setup"], input="\n\n\n\n\nstandard\n", check=True)
        result = self.add_income(amount="107.00", vat_rate="7")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        query = self.run_cli(
            ["query", "SELECT vat_rate, vat_code, vat_output FROM income WHERE id = 1"],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1][0], "7.0")
        self.assertEqual(rows[1][1], "output_reduced_7")
        self.assertEqual(rows[1][2], "7.0")

    def test_add_income_tax_free_conflicts_with_vat(self):
        result = self.add_income(vat="10.00", tax_free=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--tax-free", result.stderr)


if __name__ == "__main__":
    unittest.main()
