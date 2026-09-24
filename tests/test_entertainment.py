import unittest
from decimal import Decimal

from test_services_expenses import make_connection

from euercli.services.entertainment import calculate_entertainment_breakdown
from euercli.services.errors import ValidationError
from euercli.services.eur import get_eur_field
from euercli.services.expenses import (
    create_expense,
    migrate_legacy_entertainment_statuses,
    update_expense,
)
from euercli.services.income import create_income, update_income


class EntertainmentTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_connection()
        self.addCleanup(self.conn.close)

    def create(self, **kwargs):
        values = dict(
            date="2026-01-15",
            vendor="Restaurant",
            amount_eur=-129,
            category_name="Bewirtungsaufwendungen",
            tax_mode="standard",
            audit_user="test",
        )
        values.update(kwargs)
        return create_expense(self.conn, **values)

    def test_standard_and_small_business_amounts(self):
        for vat, status, deductible, rejected in [
            (19, "deductible", "77.00", "33.00"),
            (0, "no_deduction", "90.30", "38.70"),
        ]:
            with self.subTest(status=status):
                result = calculate_entertainment_breakdown(
                    amount_eur=-129, vat_input=vat, vat_status=status
                )
                self.assertEqual(result.deductible_eur, Decimal(deductible))
                self.assertEqual(result.non_deductible_eur, Decimal(rejected))
                self.assertEqual(result.cost_basis_eur + result.vat_input_eur, result.paid_eur)

    def test_rounding_remainder(self):
        result = calculate_entertainment_breakdown(
            amount_eur=-0.05, vat_input=0, vat_status="no_deduction"
        )
        self.assertEqual(result.deductible_eur, Decimal("0.04"))
        self.assertEqual(result.non_deductible_eur, Decimal("0.01"))

    def test_unknown_vat_is_not_zero(self):
        expense = self.create()
        self.assertEqual(expense.entertainment_vat_status, "needs_review")
        result = calculate_entertainment_breakdown(
            amount_eur=expense.amount_eur,
            vat_input=expense.vat_input,
            vat_status=expense.entertainment_vat_status,
        )
        self.assertIsNone(result.deductible_eur)
        self.assertTrue(result.provisional)

    def test_tip_is_included_and_historical_mode_is_preserved(self):
        expense = self.create(vat=19, entertainment_tip_eur=10)
        updated = update_expense(
            self.conn,
            record_id=expense.id,
            notes="checked",
            tax_mode="small_business",
            audit_user="test",
        )
        self.assertEqual(updated.vat_input, 19)
        self.assertEqual(updated.entertainment_tip_eur, 10)
        self.assertEqual(updated.entertainment_vat_status, "deductible")

    def test_rejects_invalid_tip_and_small_business_vat(self):
        for kwargs in [
            dict(vat=19, entertainment_tip_eur=111),
            dict(vat=19, tax_mode="small_business"),
            dict(amount_eur=129),
            dict(amount_eur=-129.001),
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.create(**kwargs)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0], 0)

    def test_rc_create_and_update_are_rejected_atomically(self):
        with self.assertRaises(ValidationError):
            self.create(rc_type="eu")
        expense = self.create(vat=19)
        with self.assertRaises(ValidationError):
            update_expense(
                self.conn,
                record_id=expense.id,
                rc_type="eu",
                tax_mode="standard",
                audit_user="test",
            )
        row = self.conn.execute("SELECT rc_type, vat_input FROM expenses").fetchone()
        self.assertEqual(tuple(row), ("none", 19))

    def test_legacy_refund_and_rc_have_no_cost_split(self):
        for amount, rc in [(129, "none"), (-129, "eu")]:
            result = calculate_entertainment_breakdown(
                amount_eur=amount, vat_input=19, vat_status="deductible", rc_type=rc
            )
            self.assertIsNone(result.deductible_eur)
            self.assertTrue(result.provisional)

    def test_subset_cannot_acquire_vat_on_update(self):
        income = create_income(
            self.conn,
            date="2026-01-15",
            source="Client",
            amount_eur=119,
            category_name="Nicht steuerbare Umsätze",
            tax_mode="small_business",
            audit_user="test",
        )
        with self.assertRaises(ValidationError):
            update_income(
                self.conn, record_id=income.id, vat_rate=19, tax_mode="standard", audit_user="test"
            )
        updated = update_income(
            self.conn,
            record_id=income.id,
            notes="historical",
            tax_mode="standard",
            audit_user="test",
        )
        self.assertIn(updated.vat_output, (None, 0))

    def test_year_mappings_and_unknown_year(self):
        for year, entertainment, vat, deposits in [(2025, 63, 57, 107), (2026, 64, 58, 108)]:
            self.assertEqual(get_eur_field(year, "entertainment_deductible").line, entertainment)
            self.assertEqual(get_eur_field(year, "input_vat").line, vat)
            self.assertEqual(get_eur_field(year, "private_deposits").line, deposits)
        self.assertEqual(get_eur_field(2026, "input_vat").verification_status, "bmf_verified")
        self.assertIsNone(get_eur_field(2027, "input_vat"))

    def test_migration_preserves_amounts_and_is_idempotent(self):
        expense = self.create(vat=19)
        # Simulate pre-migration storage without a per-booking status.
        self.conn.execute(
            "UPDATE categories SET eur_key='entertainment' WHERE name='Bewirtungsaufwendungen'"
        )
        self.conn.execute("UPDATE expenses SET entertainment_vat_status=NULL")
        self.conn.commit()
        self.assertEqual(migrate_legacy_entertainment_statuses(self.conn), 1)
        self.assertEqual(migrate_legacy_entertainment_statuses(self.conn), 0)
        row = self.conn.execute(
            "SELECT amount_eur, vat_input, entertainment_vat_status FROM expenses WHERE id=?",
            (expense.id,),
        ).fetchone()
        self.assertEqual(tuple(row), (-129, 19, "needs_review"))
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='MIGRATE'").fetchone()[
                0
            ],
            1,
        )

    def test_vat_report_keeps_full_entertainment_vat_after_mode_change(self):
        from euercli.services.vat_report import build_vat_report

        self.conn.execute(
            "UPDATE categories SET eur_key='entertainment' WHERE name='Bewirtungsaufwendungen'"
        )
        self.create(vat=19)
        report = build_vat_report(self.conn, year=2026, tax_mode="small_business")
        line = next(line for line in report.lines if line.kennzahl == "66")
        self.assertEqual(line.tax_eur_raw, Decimal("19.00"))
        self.conn.execute("UPDATE expenses SET amount_eur=129")
        report = build_vat_report(self.conn, year=2026, tax_mode="small_business")
        self.assertTrue(
            any(d.reason_code == "unsupported_entertainment_booking" for d in report.diagnostics)
        )
        self.assertFalse(any(line.kennzahl == "66" and line.tax_eur_raw for line in report.lines))
