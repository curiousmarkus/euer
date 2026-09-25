import unittest

from tests.cli_test_base import BaseCLITestCase


class SoftDeleteAndUndoTestCase(BaseCLITestCase):
    def test_expense_soft_delete_and_trash(self):
        # Ausgabe anlegen
        self.add_expense(vendor="Test SoftDelete GmbH", amount="-150.00")

        # Prüfen: Ist in aktiver Liste
        res = self.run_cli(["list", "expenses"], check=True)
        self.assertIn("Test SoftDelete GmbH", res.stdout)

        # Löschen (Standard = Soft-Delete)
        del_res = self.run_cli(["delete", "expense", "1", "--force"], check=True)
        self.assertIn("in den Papierkorb verschoben", del_res.stdout)

        # Prüfen: Nicht mehr in aktiver Liste
        res_after = self.run_cli(["list", "expenses"], check=True)
        self.assertNotIn("Test SoftDelete GmbH", res_after.stdout)

        # Prüfen: In Papierkorb vorhanden via list expenses --trash
        res_trash = self.run_cli(["list", "expenses", "--trash"], check=True)
        self.assertIn("Test SoftDelete GmbH", res_trash.stdout)

        # Prüfen: In globalem Papierkorb via trash list
        res_global_trash = self.run_cli(["trash", "list"], check=True)
        self.assertIn("Test SoftDelete GmbH", res_global_trash.stdout)
        self.assertIn("Ausgaben", res_global_trash.stdout)

        # Wiederherstellen
        restore_res = self.run_cli(["restore", "1"], check=True)
        self.assertIn("wiederhergestellt", restore_res.stdout)

        # Wieder in aktiver Liste
        res_restored = self.run_cli(["list", "expenses"], check=True)
        self.assertIn("Test SoftDelete GmbH", res_restored.stdout)

    def test_income_soft_delete_and_restore(self):
        # Einnahme anlegen
        self.add_income(source="Kunde Alpha", amount="500.00")

        # Soft-Delete
        del_res = self.run_cli(["delete", "income", "1", "--force"], check=True)
        self.assertIn("in den Papierkorb verschoben", del_res.stdout)

        # Nicht in aktiver Liste
        res_after = self.run_cli(["list", "income"], check=True)
        self.assertNotIn("Kunde Alpha", res_after.stdout)

        # In trash list
        res_trash = self.run_cli(["trash", "list"], check=True)
        self.assertIn("Kunde Alpha", res_trash.stdout)
        self.assertIn("Einnahmen", res_trash.stdout)

        # Wiederherstellen mit explizitem --table
        restore_res = self.run_cli(["restore", "1", "--table", "income"], check=True)
        self.assertIn("wiederhergestellt", restore_res.stdout)

        # Wieder aktiv
        res_active = self.run_cli(["list", "income"], check=True)
        self.assertIn("Kunde Alpha", res_active.stdout)

    def test_purge_permanently_deletes(self):
        self.add_expense(vendor="Purge Vendor", amount="-80.00")

        # Mit --purge löschen
        del_res = self.run_cli(["delete", "expense", "1", "--force", "--purge"], check=True)
        self.assertIn("endgültig gelöscht", del_res.stdout)

        # Weder in aktiver Liste noch im Papierkorb
        self.assertNotIn("Purge Vendor", self.run_cli(["list", "expenses"]).stdout)
        self.assertNotIn("Purge Vendor", self.run_cli(["trash", "list"]).stdout)

        # Physikalisch aus DB entfernt
        q_res = self.run_cli(["query", "SELECT", "COUNT(*)", "FROM", "expenses", "WHERE", "id=1"], check=True)
        rows = self.parse_csv(q_res.stdout)
        self.assertEqual(rows[1][0], "0")

    def test_trash_empty(self):
        self.add_expense(vendor="Trash Exp 1", amount="-10.00")
        self.add_income(source="Trash Inc 1", amount="20.00")

        self.run_cli(["delete", "expense", "1", "--force"], check=True)
        self.run_cli(["delete", "income", "1", "--force"], check=True)

        res_trash = self.run_cli(["trash", "list"], check=True)
        self.assertIn("Trash Exp 1", res_trash.stdout)
        self.assertIn("Trash Inc 1", res_trash.stdout)

        # Papierkorb leeren
        empty_res = self.run_cli(["trash", "empty", "--force"], check=True)
        self.assertIn("endgültig aus dem Papierkorb gelöscht", empty_res.stdout)

        # Papierkorb jetzt leer
        res_after = self.run_cli(["trash", "list"], check=True)
        self.assertIn("Papierkorb ist leer", res_after.stdout)

    def test_undo_insert(self):
        # 1. Expense anlegen
        self.add_expense(vendor="Undo Insert Vendor", amount="-42.00")
        self.assertIn("Undo Insert Vendor", self.run_cli(["list", "expenses"]).stdout)

        # 2. Undo ausführen -> muss das Insert rückgängig machen (soft delete)
        undo_res = self.run_cli(["undo", "--force"], check=True)
        self.assertIn("Rückgängig gemacht", undo_res.stdout)

        # 3. Nicht mehr aktiv
        self.assertNotIn("Undo Insert Vendor", self.run_cli(["list", "expenses"]).stdout)
        # Aber im Papierkorb
        self.assertIn("Undo Insert Vendor", self.run_cli(["trash", "list"]).stdout)

    def test_undo_delete(self):
        # 1. Expense anlegen und löschen
        self.add_expense(vendor="Undo Delete Vendor", amount="-75.00")
        self.run_cli(["delete", "expense", "1", "--force"], check=True)
        self.assertNotIn("Undo Delete Vendor", self.run_cli(["list", "expenses"]).stdout)

        # 2. Undo ausführen -> muss Löschung rückgängig machen
        undo_res = self.run_cli(["undo", "--force"], check=True)
        self.assertIn("Rückgängig gemacht", undo_res.stdout)

        # 3. Wieder in aktiver Liste
        self.assertIn("Undo Delete Vendor", self.run_cli(["list", "expenses"]).stdout)

    def test_undo_update(self):
        # 1. Expense anlegen
        self.add_expense(vendor="Original Vendor AG", amount="-99.00")
        # 2. Update durchführen
        self.run_cli(["update", "expense", "1", "--vendor", "Modified Vendor GmbH"], check=True)
        self.assertIn("Modified Vendor GmbH", self.run_cli(["list", "expenses"]).stdout)

        # 3. Undo ausführen -> muss den originalen Vendor wiederherstellen
        undo_res = self.run_cli(["undo", "--force"], check=True)
        self.assertIn("Rückgängig gemacht", undo_res.stdout)

        list_out = self.run_cli(["list", "expenses"]).stdout
        self.assertIn("Original Vendor AG", list_out)
        self.assertNotIn("Modified Vendor GmbH", list_out)

    def test_restore_ambiguity_handling(self):
        self.add_expense(vendor="Ambiguous Exp", amount="-50.00")
        self.add_income(source="Ambiguous Inc", amount="50.00")

        # Beide Datensätze haben ID 1
        self.run_cli(["delete", "expense", "1", "--force"], check=True)
        self.run_cli(["delete", "income", "1", "--force"], check=True)

        # restore 1 ohne --table muss auf Mehrdeutigkeit hinweisen
        res = self.run_cli(["restore", "1"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Mehrere gelöschte Einträge", res.stderr + res.stdout)
        self.assertIn("--table", res.stderr + res.stdout)

        # Mit --table funktioniert es
        res_exp = self.run_cli(["restore", "1", "--table", "expenses"], check=True)
        self.assertIn("Ausgabe #1 wiederhergestellt", res_exp.stdout)
        self.assertIn("Ambiguous Exp", self.run_cli(["list", "expenses"]).stdout)


if __name__ == "__main__":
    unittest.main()
