import sqlite3
import unittest
import uuid

from euercli.schema import SCHEMA, SEED_CATEGORIES
from euercli.services.duplicates import DuplicateAction
from euercli.services.errors import ValidationError
from euercli.services.income import (
    create_income,
    delete_income,
    list_income,
    update_income,
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


class IncomeServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = make_connection()

    def tearDown(self) -> None:
        self.conn.close()

    def test_create_list_update_delete_income(self) -> None:
        income = create_income(
            self.conn,
            date="2026-01-20",
            source="TestClient",
            amount_eur=1500.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            receipt_name="invoice.pdf",
            notes="Note",
            vat=None,
            tax_mode="standard",
            audit_user="tester",
        )
        self.assertEqual(income.id, 1)
        self.assertTrue(income.uuid)
        self.assertIsNone(income.vat_output)

        rows = list_income(self.conn, year=2026)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].source, "TestClient")

        updated = update_income(
            self.conn,
            record_id=income.id,
            amount_eur=1750.0,
            notes="Korrigiert",
            vat=100.0,
            tax_mode="standard",
            audit_user="tester",
        )
        self.assertEqual(updated.amount_eur, 1750.0)
        self.assertEqual(updated.notes, "Korrigiert")
        self.assertEqual(updated.vat_output, 100.0)

        delete_income(self.conn, record_id=income.id, audit_user="tester")
        remaining = list_income(self.conn)
        self.assertEqual(len(remaining), 0)

    def test_duplicate_detection(self) -> None:
        create_income(
            self.conn,
            date="2026-01-20",
            source="TestClient",
            amount_eur=1500.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            tax_mode="standard",
            audit_user="tester",
        )
        with self.assertRaises(ValidationError) as ctx:
            create_income(
                self.conn,
                date="2026-01-20",
                source="TestClient",
                amount_eur=1500.0,
                category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
                tax_mode="standard",
                audit_user="tester",
            )
        self.assertEqual(ctx.exception.code, "duplicate")

    def test_duplicate_skip_returns_none(self) -> None:
        create_income(
            self.conn,
            date="2026-01-20",
            source="TestClient",
            amount_eur=1500.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            tax_mode="standard",
            audit_user="tester",
        )
        duplicate = create_income(
            self.conn,
            date="2026-01-20",
            source="TestClient",
            amount_eur=1500.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            tax_mode="standard",
            audit_user="tester",
            on_duplicate=DuplicateAction.SKIP,
        )
        self.assertIsNone(duplicate)

    def test_create_income_auto_commit_false_rolls_back(self) -> None:
        create_income(
            self.conn,
            date="2026-01-20",
            source="NoCommit",
            amount_eur=1500.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            tax_mode="standard",
            audit_user="tester",
            auto_commit=False,
        )
        before_rollback = self.conn.execute("SELECT COUNT(*) AS cnt FROM income").fetchone()
        self.assertIsNotNone(before_rollback)
        assert before_rollback is not None
        self.assertEqual(before_rollback["cnt"], 1)
        self.conn.rollback()
        after_rollback = self.conn.execute("SELECT COUNT(*) AS cnt FROM income").fetchone()
        self.assertIsNotNone(after_rollback)
        assert after_rollback is not None
        self.assertEqual(after_rollback["cnt"], 0)

    def test_create_income_allows_explicit_vat_output_in_small_business(self) -> None:
        income = create_income(
            self.conn,
            date="2026-01-20",
            source="KuVat",
            amount_eur=1500.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            vat_output=20.0,
            tax_mode="small_business",
            audit_user="tester",
        )
        self.assertIsNotNone(income)
        assert income is not None
        self.assertEqual(income.vat_output, 20.0)

    def test_audit_log_includes_uuid(self) -> None:
        income = create_income(
            self.conn,
            date="2026-01-20",
            source="TestClient",
            amount_eur=1500.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            tax_mode="standard",
            audit_user="tester",
        )
        row = self.conn.execute(
            "SELECT record_uuid FROM audit_log WHERE table_name = 'income' AND record_id = ?",
            (income.id,),
        ).fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["record_uuid"], income.uuid)

    def test_create_income_with_invoice_date_only(self) -> None:
        income = create_income(
            self.conn,
            invoice_date="2026-01-11",
            source="InvoiceOnly",
            amount_eur=500.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            tax_mode="standard",
            audit_user="tester",
        )
        self.assertIsNone(income.payment_date)
        self.assertEqual(income.invoice_date, "2026-01-11")

    def test_create_income_requires_any_date(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            create_income(
                self.conn,
                source="NoDate",
                amount_eur=500.0,
                category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
                tax_mode="standard",
                audit_user="tester",
            )
        self.assertEqual(ctx.exception.code, "missing_dates")


if __name__ == "__main__":
    unittest.main()
