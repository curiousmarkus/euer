import unittest

from tests.cli_test_base import BaseCLITestCase


class CLIExpensesTestCase(BaseCLITestCase):
    def test_add_expense_and_list_csv(self):
        add_result = self.add_expense(account="Bank", receipt="receipt.pdf")
        self.assertEqual(add_result.returncode, 0, msg=add_result.stderr)
        self.assertIn("Ausgabe #1 hinzugefügt", add_result.stdout)

        rows = self.list_expenses_csv()
        self.assertEqual(len(rows), 2)
        # ID, Wertstellung, Rechnung, Lieferant, Kategorie, EUR, Konto, Beleg, Status,
        # Fremdwährung, Bemerkung, RC, Vorsteuer, Umsatzsteuer
        (
            rec_id,
            payment_date,
            invoice_date,
            vendor,
            category,
            amount,
            account,
            receipt,
            status,
            foreign,
            notes,
            rc,
            vat_input,
            vat_output,
            *entertainment_fields,
        ) = rows[1]
        self.assertEqual(entertainment_fields, [""] * 5)
        self.assertEqual(payment_date, "2026-01-15")
        self.assertEqual(invoice_date, "")
        self.assertEqual(vendor, "TestVendor")
        self.assertEqual(category, "(52) Arbeitsmittel")
        self.assertEqual(amount, "-10.00")
        self.assertEqual(account, "Bank")
        self.assertEqual(receipt, "receipt.pdf")
        self.assertIn("Zahlung erfolgt", status)
        self.assertEqual(foreign, "")
        self.assertEqual(notes, "")
        self.assertEqual(rc, "")
        self.assertEqual(vat_input, "")
        self.assertEqual(vat_output, "")

    def test_add_expense_with_ledger_account_sets_category(self):
        self.write_config(
            """
[[ledger_accounts]]
key = "hosting"
name = "Hosting & Cloud-Dienste"
category = "Laufende EDV-Kosten"
account_number = "4940"
""".strip()
            + "\n"
        )

        result = self.add_expense(
            vendor="Hetzner",
            category=None,
            ledger_account="hosting",
            amount="-29.00",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        rows = self.list_expenses_csv()
        self.assertEqual(rows[1][3], "Hetzner")
        self.assertEqual(rows[1][4], "(51) Laufende EDV-Kosten")

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "ledger_account",
                "FROM",
                "expenses",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        query_rows = self.parse_csv(query.stdout)
        self.assertEqual(query_rows[1][0], "hosting")

    def test_add_requires_category_or_ledger_account_when_kontenrahmen_exists(self):
        self.write_config(
            """
[[ledger_accounts]]
key = "hosting"
name = "Hosting & Cloud-Dienste"
category = "Laufende EDV-Kosten"
""".strip()
            + "\n"
        )

        result = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-01-16",
                "--vendor",
                "OhneKategorie",
                "--amount",
                "-10.00",
            ]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Kategorie erforderlich", result.stderr)
        self.assertIn("--ledger-account", result.stderr)

    def test_add_expense_with_invoice_date_only(self):
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
            ],
            check=True,
        )
        self.assertIn("Ausgabe #1 hinzugefügt", result.stdout)

        rows = self.list_expenses_csv()
        self.assertEqual(rows[1][1], "")
        self.assertEqual(rows[1][2], "2026-01-16")
        self.assertIn("Zahlung ausstehend", rows[1][8])

    def test_add_expense_requires_any_date(self):
        result = self.run_cli(["add", "expense", "--vendor", "NoDate", "--amount", "-10.00"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("payment_date", result.stderr)

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
        self.assertEqual(rows[1][5], "-15.50")
        self.assertEqual(rows[1][10], "Korrigiert")

    def test_update_expense_can_clear_private_paid(self):
        self.add_expense(private_paid=True)
        before = self.run_cli(["list", "private-deposits", "--year", "2026"], check=True)
        self.assertIn("TestVendor", before.stdout)

        self.run_cli(["update", "expense", "1", "--no-private-paid"], check=True)
        after = self.run_cli(["list", "private-deposits", "--year", "2026"], check=True)
        self.assertIn("Keine Privateinlagen gefunden", after.stdout)

    def test_delete_expense_force(self):
        self.add_expense()
        result = self.run_cli(["delete", "expense", "1", "--force"], check=True)
        self.assertIn("Ausgabe #1 gelöscht", result.stdout)

        rows = self.list_expenses_csv()
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
        self.assertIn("(51)", list_result.stdout)

    def test_add_expense_rc_requires_jurisdiction(self):
        result = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-01-15",
                "--vendor",
                "OpenAI",
                "--category",
                "Laufende EDV-Kosten",
                "--amount",
                "-100.00",
                "--rc",
            ]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--rc", result.stderr)

    def test_add_expense_rc_types_persist(self):
        eu = self.add_expense(
            vendor="EU SaaS",
            category="Laufende EDV-Kosten",
            amount="-100.00",
            rc="eu",
        )
        self.assertEqual(eu.returncode, 0, msg=eu.stderr)
        third_country = self.add_expense(
            date="2026-01-16",
            vendor="US SaaS",
            category="Laufende EDV-Kosten",
            amount="-120.00",
            rc="third-country",
        )
        self.assertEqual(third_country.returncode, 0, msg=third_country.stderr)

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "vendor,rc_type",
                "FROM",
                "expenses",
                "ORDER",
                "BY",
                "id",
            ],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1], ["EU SaaS", "eu"])
        self.assertEqual(rows[2], ["US SaaS", "third_country"])

        list_rows = self.list_expenses_csv()
        self.assertIn("RC", list_rows[0])
        self.assertEqual(list_rows[1][11], "third-country")
        self.assertEqual(list_rows[2][11], "eu")

    def test_update_expense_rc_and_no_rc(self):
        self.add_expense(vendor="Normal")

        set_rc = self.run_cli(
            ["update", "expense", "1", "--rc", "third-country"],
            check=True,
        )
        self.assertIn("Ausgabe #1 aktualisiert", set_rc.stdout)

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "rc_type",
                "FROM",
                "expenses",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1], ["third_country"])

        clear_rc = self.run_cli(["update", "expense", "1", "--no-rc"], check=True)
        self.assertIn("Ausgabe #1 aktualisiert", clear_rc.stdout)
        query = self.run_cli(
            [
                "query",
                "SELECT",
                "rc_type",
                "FROM",
                "expenses",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1], ["none"])

    def test_list_expenses_table_full_shows_receipt_notes_and_foreign(self):
        self.add_expense(
            vendor="Cloudflare",
            category="Laufende EDV-Kosten",
            amount="-39.99",
            account="Bank",
            receipt="cloudflare.pdf",
            foreign="42.50 USD",
            notes="Business Plan",
        )

        default_result = self.run_cli(["list", "expenses", "--year", "2026"], check=True)
        self.assertNotIn("Notiz", default_result.stdout)
        self.assertNotIn("Fremdw.", default_result.stdout)

        full_result = self.run_cli(
            ["list", "expenses", "--year", "2026", "--full"],
            check=True,
        )
        self.assertIn("Beleg", full_result.stdout)
        self.assertIn("Notiz", full_result.stdout)
        self.assertIn("Fremdw.", full_result.stdout)
        self.assertIn("cloudflare.pdf", full_result.stdout)
        self.assertIn("42.50 USD", full_result.stdout)
        self.assertIn("Business Plan", full_result.stdout)

    def test_expense_private_paid_flag_persisted(self):
        self.add_expense(private_paid=True, account="Geschäft")

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "is_private_paid,private_classification",
                "FROM",
                "expenses",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1][0], "1")
        self.assertEqual(rows[1][1], "manual")


if __name__ == "__main__":
    unittest.main()
