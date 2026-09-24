import unittest

from tests.cli_test_base import BaseCLITestCase


class CLIPrivateTransfersTestCase(BaseCLITestCase):
    def test_add_private_deposit(self):
        result = self.add_private_deposit(amount="250.00", description="Eigenkapital")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Privateinlage #1 hinzugefügt", result.stdout)

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "type,amount_eur,description",
                "FROM",
                "private_transfers",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1][0], "deposit")
        self.assertIn(rows[1][1], {"250.0", "250.00", "250"})
        self.assertEqual(rows[1][2], "Eigenkapital")

    def test_add_private_withdrawal(self):
        result = self.add_private_withdrawal(amount="125.00", description="Privat")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Privatentnahme #1 hinzugefügt", result.stdout)

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "type,amount_eur,description",
                "FROM",
                "private_transfers",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1][0], "withdrawal")
        self.assertIn(rows[1][1], {"125.0", "125.00", "125"})
        self.assertEqual(rows[1][2], "Privat")

    def test_add_private_withdrawal_with_related_expense(self):
        self.add_expense()
        result = self.add_private_withdrawal(
            amount="10.00",
            description="Ausgleich",
            related_expense_id=1,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "related_expense_id",
                "FROM",
                "private_transfers",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1][0], "1")

    def test_list_private_transfers(self):
        self.add_private_deposit(amount="100.00", description="Direkt")
        self.add_expense(account="privat", amount="-25.00", vendor="Sacheinlage")
        self.add_private_withdrawal(amount="40.00", description="Entnahme")

        result = self.run_cli(
            ["list", "private-transfers", "--year", "2026"],
            check=True,
        )
        self.assertIn("Privateinlagen & Privatentnahmen 2026", result.stdout)
        self.assertIn("Direkt", result.stdout)
        self.assertIn("Sacheinlage", result.stdout)
        self.assertIn("Entnahme", result.stdout)

    def test_import_with_private_classification(self):
        import_file = self.root / "import_private.jsonl"
        import_file.write_text(
            (
                '{"type":"expense","date":"2026-02-03","party":"Tool","'
                'category":"Arbeitsmittel","amount_eur":-30.00,'
                '"private_paid":true}\n'
            ),
            encoding="utf-8",
        )

        result = self.run_cli(
            ["import", "--file", str(import_file), "--format", "jsonl"],
            check=True,
        )
        self.assertIn("Ausgaben angelegt: 1", result.stdout)

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

    def test_private_summary_command(self):
        self.add_expense(account="privat", amount="-25.00")
        self.add_private_deposit(amount="500.00", description="Einlage")
        self.add_private_withdrawal(amount="100.00", description="Entnahme")
        result = self.run_cli(["private-summary", "--year", "2026"], check=True)
        self.assertIn("GESAMT Privateinlagen", result.stdout)
        self.assertIn("525.00 EUR", result.stdout)
        self.assertIn("100.00 EUR", result.stdout)
        self.assertIn("SALDO (Einlagen - Entnahmen)", result.stdout)
        self.assertIn("425.00 EUR", result.stdout)

    def test_private_totals_unchanged_after_config_edit(self):
        self.add_expense(account="privat", amount="-50.00")
        first = self.run_cli(["private-summary", "--year", "2026"], check=True)
        self.assertIn("50.00 EUR", first.stdout)

        config_path = self.expected_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('[accounts]\nprivate = ["completely_other"]\n', encoding="utf-8")

        second = self.run_cli(["private-summary", "--year", "2026"], check=True)
        self.assertIn("50.00 EUR", second.stdout)

    def test_reconcile_private_updates_and_logs(self):
        self.write_config('[accounts]\nprivate = ["privat"]\n')
        self.add_expense(account="Sparkasse Kreditkarte", amount="-35.00")

        before = self.run_cli(
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
        before_rows = self.parse_csv(before.stdout)
        self.assertEqual(before_rows[1][0], "0")
        self.assertEqual(before_rows[1][1], "none")

        self.write_config('[accounts]\nprivate = ["Sparkasse Kreditkarte"]\n')
        result = self.run_cli(
            ["reconcile", "private", "--year", "2026"],
            check=True,
        )
        self.assertIn("Geändert: 1", result.stdout)

        after = self.run_cli(
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
        after_rows = self.parse_csv(after.stdout)
        self.assertEqual(after_rows[1][0], "1")
        self.assertEqual(after_rows[1][1], "account_rule")

        audit = self.run_cli(
            [
                "query",
                "SELECT",
                "COUNT(*)",
                "as",
                "cnt",
                "FROM",
                "audit_log",
                "WHERE",
                "table_name",
                "=",
                "'expenses'",
                "AND",
                "record_id",
                "=",
                "1",
                "AND",
                "action",
                "=",
                "'MIGRATE'",
            ],
            check=True,
        )
        audit_rows = self.parse_csv(audit.stdout)
        self.assertEqual(audit_rows[1][0], "1")

    def test_reconcile_private_dry_run_changes_nothing(self):
        self.write_config('[accounts]\nprivate = ["privat"]\n')
        self.add_expense(account="Kreditkarte Privat", amount="-45.00")
        self.write_config('[accounts]\nprivate = ["Kreditkarte Privat"]\n')

        result = self.run_cli(
            ["reconcile", "private", "--year", "2026", "--dry-run"],
            check=True,
        )
        self.assertIn("Dry-Run", result.stdout)
        self.assertIn("Geändert: 1", result.stdout)

        row = self.run_cli(
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
        rows = self.parse_csv(row.stdout)
        self.assertEqual(rows[1][0], "0")
        self.assertEqual(rows[1][1], "none")

    def test_reconcile_private_keeps_manual_classification(self):
        self.add_expense(account="Geschäft", private_paid=True, amount="-18.00")
        self.write_config('[accounts]\nprivate = ["anderes konto"]\n')

        result = self.run_cli(["reconcile", "private", "--year", "2026"], check=True)
        self.assertIn("Übersprungen (manuell): 1", result.stdout)

        row = self.run_cli(
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
        rows = self.parse_csv(row.stdout)
        self.assertEqual(rows[1][0], "1")
        self.assertEqual(rows[1][1], "manual")

    def test_update_private_transfer_cli(self):
        self.add_expense()
        self.add_private_withdrawal(related_expense_id=1, amount="100.00")

        result = self.run_cli(
            [
                "update",
                "private-transfer",
                "1",
                "--amount",
                "110.00",
                "--description",
                "Korrigiert",
                "--clear-related-expense",
            ],
            check=True,
        )
        self.assertIn("Privatvorgang #1 aktualisiert", result.stdout)

        query = self.run_cli(
            [
                "query",
                "SELECT",
                "amount_eur,description,related_expense_id",
                "FROM",
                "private_transfers",
                "WHERE",
                "id",
                "=",
                "1",
            ],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1][1], "Korrigiert")
        self.assertEqual(rows[1][2], "")
        self.assertIn(rows[1][0], {"110.0", "110.00", "110"})

    def test_delete_private_transfer_cli(self):
        self.add_private_deposit(amount="100.00", description="Einlage")

        result = self.run_cli(
            ["delete", "private-transfer", "1", "--force"],
            check=True,
        )
        self.assertIn("Privatvorgang #1 gelöscht", result.stdout)

        query = self.run_cli(
            ["query", "SELECT", "COUNT(*)", "as", "cnt", "FROM", "private_transfers"],
            check=True,
        )
        rows = self.parse_csv(query.stdout)
        self.assertEqual(rows[1][0], "0")


if __name__ == "__main__":
    unittest.main()
