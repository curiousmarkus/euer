import unittest

from tests.cli_test_base import BaseCLITestCase


class CLIIncomeTestCase(BaseCLITestCase):
    def test_add_income_and_list_csv(self):
        add_result = self.add_income(receipt="invoice.pdf")
        self.assertEqual(add_result.returncode, 0, msg=add_result.stderr)
        self.assertIn("Einnahme #1 hinzugefügt", add_result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(len(rows), 2)
        # ID, Wertstellung, Rechnung, Quelle, Kategorie, EUR, Konto, Beleg, Status, Fremdwährung, Bemerkung, Umsatzsteuer, Rechnungsnummer
        (
            rec_id,
            payment_date,
            invoice_date,
            source,
            category,
            amount,
            account,
            receipt,
            status,
            foreign,
            notes,
            vat_output,
            invoice_number,
        ) = rows[1]
        self.assertEqual(payment_date, "2026-01-20")
        self.assertEqual(invoice_date, "")
        self.assertEqual(source, "TestClient")
        self.assertEqual(category, "(15) Umsatzsteuerpflichtige Betriebseinnahmen")
        self.assertEqual(amount, "1500.00")
        self.assertEqual(account, "")
        self.assertEqual(receipt, "invoice.pdf")
        self.assertIn("Zahlung erfolgt", status)
        self.assertEqual(foreign, "")
        self.assertEqual(notes, "")
        self.assertEqual(vat_output, "")
        self.assertEqual(invoice_number, "")

    def test_update_income(self):
        self.add_income()
        result = self.run_cli(
            ["update", "income", "1", "--amount", "1750.00", "--notes", "Korrigiert"],
            check=True,
        )
        self.assertIn("Einnahme #1 aktualisiert", result.stdout)

        rows = self.list_income_csv()
        self.assertEqual(rows[1][5], "1750.00")
        self.assertEqual(rows[1][10], "Korrigiert")

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

    def test_add_income_with_account(self):
        result = self.add_income(extra_args=["--account", "N26-Giro"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        rows = self.list_income_csv()
        self.assertEqual(rows[1][6], "n26-giro")

        query = self.run_cli(["query", "SELECT account FROM income WHERE id = 1"], check=True)
        q_rows = self.parse_csv(query.stdout)
        self.assertEqual(q_rows[1][0], "n26-giro")

    def test_add_income_uses_default_account(self):
        self.write_config("[accounts]\ndefault = 'Girokonto'\n")
        result = self.add_income()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        query = self.run_cli(["query", "SELECT account FROM income WHERE id = 1"], check=True)
        q_rows = self.parse_csv(query.stdout)
        self.assertEqual(q_rows[1][0], "girokonto")

    def test_add_income_explicit_account_overrides_default(self):
        self.write_config("[accounts]\ndefault = 'Girokonto'\n")
        result = self.add_income(extra_args=["--account", "Stripe"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        query = self.run_cli(["query", "SELECT account FROM income WHERE id = 1"], check=True)
        q_rows = self.parse_csv(query.stdout)
        self.assertEqual(q_rows[1][0], "stripe")

    def test_add_income_rejects_reserved_private_account(self):
        result = self.add_income(extra_args=["--account", "privat"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Einnahmen auf Privatkonten", result.stderr)

    def test_add_income_rejects_configured_private_account(self):
        self.write_config("[accounts]\nprivate = ['cc-private']\n")
        result = self.add_income(extra_args=["--account", "CC-Private"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Einnahmen auf Privatkonten", result.stderr)

    def test_update_income_account_and_clear(self):
        self.add_income(extra_args=["--account", "Bank"])
        # Update to another account
        self.run_cli(["update", "income", "1", "--account", "PayPal"], check=True)
        query = self.run_cli(["query", "SELECT account FROM income WHERE id = 1"], check=True)
        self.assertEqual(self.parse_csv(query.stdout)[1][0], "paypal")

        # Clear account with empty string
        self.run_cli(["update", "income", "1", "--account", ""], check=True)
        query = self.run_cli(["query", "SELECT account FROM income WHERE id = 1"], check=True)
        self.assertEqual(self.parse_csv(query.stdout)[1][0], "")

    def test_update_income_rejects_private_account(self):
        self.add_income(extra_args=["--account", "Bank"])
        result = self.run_cli(["update", "income", "1", "--account", "privatentnahme"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Einnahmen auf Privatkonten", result.stderr)

    def test_list_income_filter_by_account(self):
        self.add_income(source="Kunde A", amount="100.00", extra_args=["--account", "n26"])
        self.add_income(source="Kunde B", amount="200.00", extra_args=["--account", "stripe"])

        res_n26 = self.run_cli(
            ["list", "income", "--account", "N26", "--format", "csv"], check=True
        )
        rows_n26 = self.parse_csv(res_n26.stdout)
        self.assertEqual(len(rows_n26), 2)
        self.assertEqual(rows_n26[1][3], "Kunde A")

        res_stripe = self.run_cli(
            ["list", "income", "--account", "stripe", "--format", "csv"], check=True
        )
        rows_stripe = self.parse_csv(res_stripe.stdout)
        self.assertEqual(len(rows_stripe), 2)
        self.assertEqual(rows_stripe[1][3], "Kunde B")

    def test_list_income_table_full_shows_account(self):
        self.add_income(source="Kunde A", extra_args=["--account", "giro"])
        res = self.run_cli(["list", "income", "--full"], check=True)
        self.assertIn("Konto", res.stdout)
        self.assertIn("giro", res.stdout)

    def test_list_income_table_standard_shows_account(self):
        self.add_income(source="Kunde A", extra_args=["--account", "giro"])
        res = self.run_cli(["list", "income"], check=True)
        self.assertIn("Konto", res.stdout)
        self.assertIn("giro", res.stdout)

    def test_list_income_filter_unicode_and_whitespace(self):
        self.add_income(source="Kunde Ü", amount="150.00", extra_args=["--account", "  BÜROBANK  "])
        res_upper = self.run_cli(
            ["list", "income", "--account", "BÜROBANK", "--format", "csv"], check=True
        )
        rows_upper = self.parse_csv(res_upper.stdout)
        self.assertEqual(len(rows_upper), 2)
        self.assertEqual(rows_upper[1][3], "Kunde Ü")
        self.assertEqual(rows_upper[1][6], "bürobank")

        res_lower = self.run_cli(
            ["list", "income", "--account", "bürobank", "--format", "csv"], check=True
        )
        rows_lower = self.parse_csv(res_lower.stdout)
        self.assertEqual(len(rows_lower), 2)
        self.assertEqual(rows_lower[1][3], "Kunde Ü")


if __name__ == "__main__":
    unittest.main()
