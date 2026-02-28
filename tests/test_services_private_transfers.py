import sqlite3
import unittest
import uuid

from euercli.schema import SCHEMA, SEED_CATEGORIES
from euercli.services.errors import RecordNotFoundError, ValidationError
from euercli.services.expenses import create_expense
from euercli.services.private_transfers import (
    create_private_transfer,
    delete_private_transfer,
    get_private_summary,
    get_private_transfer_list,
    get_private_paid_expenses,
    update_private_transfer,
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


class PrivateTransfersServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = make_connection()

    def tearDown(self) -> None:
        self.conn.close()

    def test_create_deposit(self) -> None:
        transfer = create_private_transfer(
            self.conn,
            date="2026-01-15",
            transfer_type="deposit",
            amount_eur=500.0,
            description="Einlage",
            audit_user="tester",
        )
        self.assertEqual(transfer.id, 1)
        self.assertEqual(transfer.type, "deposit")

    def test_create_withdrawal(self) -> None:
        transfer = create_private_transfer(
            self.conn,
            date="2026-01-20",
            transfer_type="withdrawal",
            amount_eur=100.0,
            description="Entnahme",
            audit_user="tester",
        )
        self.assertEqual(transfer.type, "withdrawal")

    def test_amount_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            create_private_transfer(
                self.conn,
                date="2026-01-20",
                transfer_type="withdrawal",
                amount_eur=0.0,
                description="Entnahme",
                audit_user="tester",
            )
        self.assertEqual(ctx.exception.code, "invalid_amount")

    def test_related_expense_reference_valid(self) -> None:
        expense = create_expense(
            self.conn,
            date="2026-01-10",
            vendor="Adobe",
            amount_eur=-20.0,
            category_name="Laufende EDV-Kosten",
            account="privat",
            private_accounts=["privat"],
            tax_mode="small_business",
            audit_user="tester",
        )
        transfer = create_private_transfer(
            self.conn,
            date="2026-01-20",
            transfer_type="withdrawal",
            amount_eur=20.0,
            description="Ausgleich",
            related_expense_id=expense.id,
            audit_user="tester",
        )
        self.assertEqual(transfer.related_expense_id, expense.id)

    def test_list_by_type(self) -> None:
        create_private_transfer(
            self.conn,
            date="2026-01-01",
            transfer_type="deposit",
            amount_eur=10.0,
            description="D1",
            audit_user="tester",
        )
        create_private_transfer(
            self.conn,
            date="2026-01-02",
            transfer_type="withdrawal",
            amount_eur=5.0,
            description="W1",
            audit_user="tester",
        )
        deposits = get_private_transfer_list(self.conn, transfer_type="deposit", year=2026)
        self.assertEqual(len(deposits), 1)
        self.assertEqual(deposits[0].type, "deposit")

    def test_list_by_year(self) -> None:
        create_private_transfer(
            self.conn,
            date="2025-12-31",
            transfer_type="deposit",
            amount_eur=1.0,
            description="Alt",
            audit_user="tester",
        )
        create_private_transfer(
            self.conn,
            date="2026-01-01",
            transfer_type="deposit",
            amount_eur=2.0,
            description="Neu",
            audit_user="tester",
        )
        rows = get_private_transfer_list(self.conn, year=2026)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].description, "Neu")

    def test_duplicate_detection(self) -> None:
        create_private_transfer(
            self.conn,
            date="2026-01-15",
            transfer_type="deposit",
            amount_eur=500.0,
            description="Einlage",
            audit_user="tester",
        )
        with self.assertRaises(ValidationError) as ctx:
            create_private_transfer(
                self.conn,
                date="2026-01-15",
                transfer_type="deposit",
                amount_eur=500.0,
                description="Einlage",
                audit_user="tester",
            )
        self.assertEqual(ctx.exception.code, "duplicate")

    def test_update(self) -> None:
        transfer = create_private_transfer(
            self.conn,
            date="2026-01-15",
            transfer_type="deposit",
            amount_eur=100.0,
            description="Einlage",
            audit_user="tester",
        )
        updated = update_private_transfer(
            self.conn,
            transfer.id,
            amount_eur=120.0,
            description="Korrigiert",
            audit_user="tester",
        )
        self.assertEqual(updated.amount_eur, 120.0)
        self.assertEqual(updated.description, "Korrigiert")

    def test_delete(self) -> None:
        transfer = create_private_transfer(
            self.conn,
            date="2026-01-15",
            transfer_type="deposit",
            amount_eur=100.0,
            description="Einlage",
            audit_user="tester",
        )
        delete_private_transfer(self.conn, transfer.id, audit_user="tester")
        with self.assertRaises(RecordNotFoundError):
            update_private_transfer(
                self.conn,
                transfer.id,
                description="X",
                audit_user="tester",
            )

    def test_private_paid_expenses_from_persisted_flag(self) -> None:
        create_expense(
            self.conn,
            date="2026-01-10",
            vendor="Adobe",
            amount_eur=-20.0,
            category_name="Laufende EDV-Kosten",
            account="privat",
            private_accounts=["privat"],
            tax_mode="small_business",
            audit_user="tester",
        )
        rows = get_private_paid_expenses(self.conn, year=2026)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].is_private_paid)

    def test_nutzungseinlage_category_sets_private_paid(self) -> None:
        expense = create_expense(
            self.conn,
            date="2026-01-10",
            vendor="PKW",
            amount_eur=-30.0,
            category_name="Fahrtkosten (Nutzungseinlage)",
            tax_mode="small_business",
            audit_user="tester",
        )
        self.assertTrue(expense.is_private_paid)
        self.assertEqual(expense.private_classification, "category_rule")

    def test_summary_calculation(self) -> None:
        create_expense(
            self.conn,
            date="2026-01-10",
            vendor="Adobe",
            amount_eur=-20.0,
            category_name="Laufende EDV-Kosten",
            account="privat",
            private_accounts=["privat"],
            tax_mode="small_business",
            audit_user="tester",
        )
        create_private_transfer(
            self.conn,
            date="2026-01-15",
            transfer_type="deposit",
            amount_eur=100.0,
            description="Einlage",
            audit_user="tester",
        )
        create_private_transfer(
            self.conn,
            date="2026-01-20",
            transfer_type="withdrawal",
            amount_eur=50.0,
            description="Entnahme",
            audit_user="tester",
        )
        summary = get_private_summary(self.conn, year=2026)
        self.assertEqual(summary["deposits_direct"], 100.0)
        self.assertEqual(summary["deposits_private_paid"], 20.0)
        self.assertEqual(summary["deposits_total"], 120.0)
        self.assertEqual(summary["withdrawals_total"], 50.0)

    def test_summary_stable_after_config_change(self) -> None:
        create_expense(
            self.conn,
            date="2026-01-10",
            vendor="Adobe",
            amount_eur=-40.0,
            category_name="Laufende EDV-Kosten",
            account="privat",
            private_accounts=["privat"],
            tax_mode="small_business",
            audit_user="tester",
        )
        summary = get_private_summary(self.conn, year=2026)
        self.assertEqual(summary["deposits_private_paid"], 40.0)


if __name__ == "__main__":
    unittest.main()
