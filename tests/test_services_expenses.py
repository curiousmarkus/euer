import sqlite3
import unittest
import uuid

from euercli.schema import SCHEMA, SEED_CATEGORIES
from euercli.services.duplicates import DuplicateAction
from euercli.services.errors import ValidationError
from euercli.services.expenses import (
    create_expense,
    delete_expense,
    list_expenses,
    update_expense,
)


def make_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    for name, eur_line, cat_type in SEED_CATEGORIES:
        conn.execute(
            "INSERT INTO categories (uuid, name, eur_line, type) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), name, eur_line, cat_type),
        )
    conn.commit()
    return conn


class ExpenseServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = make_connection()

    def tearDown(self) -> None:
        self.conn.close()

    def test_create_list_update_delete_expense(self) -> None:
        expense = create_expense(
            self.conn,
            date="2026-01-15",
            vendor="TestVendor",
            amount_eur=-10.0,
            category_name="Arbeitsmittel",
            account="Bank",
            receipt_name="receipt.pdf",
            notes="Note",
            is_rc=False,
            vat=None,
            tax_mode="small_business",
            audit_user="tester",
        )
        self.assertEqual(expense.id, 1)
        self.assertTrue(expense.uuid)

        rows = list_expenses(self.conn, year=2026)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].vendor, "TestVendor")

        updated = update_expense(
            self.conn,
            record_id=expense.id,
            amount_eur=-15.5,
            notes="Korrigiert",
            tax_mode="small_business",
            audit_user="tester",
        )
        self.assertEqual(updated.amount_eur, -15.5)
        self.assertEqual(updated.notes, "Korrigiert")

        delete_expense(self.conn, record_id=expense.id, audit_user="tester")
        remaining = list_expenses(self.conn)
        self.assertEqual(len(remaining), 0)

    def test_duplicate_detection(self) -> None:
        create_expense(
            self.conn,
            date="2026-01-15",
            vendor="TestVendor",
            amount_eur=-10.0,
            category_name="Arbeitsmittel",
            tax_mode="small_business",
            audit_user="tester",
        )
        with self.assertRaises(ValidationError) as ctx:
            create_expense(
                self.conn,
                date="2026-01-15",
                vendor="TestVendor",
                amount_eur=-10.0,
                category_name="Arbeitsmittel",
                tax_mode="small_business",
                audit_user="tester",
            )
        self.assertEqual(ctx.exception.code, "duplicate")

    def test_duplicate_skip_returns_none(self) -> None:
        create_expense(
            self.conn,
            date="2026-01-15",
            vendor="TestVendor",
            amount_eur=-10.0,
            category_name="Arbeitsmittel",
            tax_mode="small_business",
            audit_user="tester",
        )
        duplicate = create_expense(
            self.conn,
            date="2026-01-15",
            vendor="TestVendor",
            amount_eur=-10.0,
            category_name="Arbeitsmittel",
            tax_mode="small_business",
            audit_user="tester",
            on_duplicate=DuplicateAction.SKIP,
        )
        self.assertIsNone(duplicate)

    def test_create_expense_auto_commit_false_rolls_back(self) -> None:
        create_expense(
            self.conn,
            date="2026-01-15",
            vendor="NoCommit",
            amount_eur=-10.0,
            category_name="Arbeitsmittel",
            tax_mode="small_business",
            audit_user="tester",
            auto_commit=False,
        )
        before_rollback = self.conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()
        self.assertIsNotNone(before_rollback)
        assert before_rollback is not None
        self.assertEqual(before_rollback["cnt"], 1)
        self.conn.rollback()
        after_rollback = self.conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()
        self.assertIsNotNone(after_rollback)
        assert after_rollback is not None
        self.assertEqual(after_rollback["cnt"], 0)

    def test_create_expense_vat_overrides_keep_import_semantics(self) -> None:
        expense = create_expense(
            self.conn,
            date="2026-01-15",
            vendor="RcVat",
            amount_eur=-100.0,
            category_name="Arbeitsmittel",
            is_rc=True,
            vat_input=5.0,
            tax_mode="standard",
            audit_user="tester",
        )
        self.assertIsNotNone(expense)
        assert expense is not None
        self.assertEqual(expense.vat_input, 5.0)
        self.assertEqual(expense.vat_output, 19.0)

    def test_create_expense_skip_vat_auto(self) -> None:
        expense = create_expense(
            self.conn,
            date="2026-01-15",
            vendor="SkipVat",
            amount_eur=-10.0,
            category_name="Arbeitsmittel",
            tax_mode="standard",
            audit_user="tester",
            skip_vat_auto=True,
        )
        self.assertIsNotNone(expense)
        assert expense is not None
        self.assertIsNone(expense.vat_input)
        self.assertIsNone(expense.vat_output)

    def test_audit_log_includes_uuid(self) -> None:
        expense = create_expense(
            self.conn,
            date="2026-01-15",
            vendor="TestVendor",
            amount_eur=-10.0,
            category_name="Arbeitsmittel",
            tax_mode="small_business",
            audit_user="tester",
        )
        row = self.conn.execute(
            "SELECT record_uuid FROM audit_log WHERE table_name = 'expenses' AND record_id = ?",
            (expense.id,),
        ).fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["record_uuid"], expense.uuid)

    def test_create_expense_with_invoice_date_only(self) -> None:
        expense = create_expense(
            self.conn,
            invoice_date="2026-01-10",
            vendor="InvoiceOnly",
            amount_eur=-12.0,
            category_name="Arbeitsmittel",
            tax_mode="small_business",
            audit_user="tester",
        )
        self.assertIsNone(expense.payment_date)
        self.assertEqual(expense.invoice_date, "2026-01-10")

    def test_create_expense_requires_any_date(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            create_expense(
                self.conn,
                vendor="NoDate",
                amount_eur=-12.0,
                category_name="Arbeitsmittel",
                tax_mode="small_business",
                audit_user="tester",
            )
        self.assertEqual(ctx.exception.code, "missing_dates")


if __name__ == "__main__":
    unittest.main()
