import sqlite3
import unittest
import uuid
from decimal import Decimal

from euercli.schema import SCHEMA, SEED_CATEGORIES
from euercli.services.expenses import create_expense
from euercli.services.income import create_income
from euercli.services.vat import round_basis_eur
from euercli.services.vat_report import build_vat_period, build_vat_report


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


def line_by_kz(report, kennzahl: str):
    return next(line for line in report.lines if line.kennzahl == kennzahl)


class VatReportServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = make_connection()

    def tearDown(self) -> None:
        self.conn.close()

    def test_period_labels(self) -> None:
        self.assertEqual(build_vat_period(year=2026).start, "2026-01-01")
        q2 = build_vat_period(year=2026, quarter=2)
        self.assertEqual(q2.start, "2026-04-01")
        self.assertEqual(q2.end, "2026-06-30")
        self.assertEqual(q2.label, "Q2/2026")
        march = build_vat_period(year=2026, month=3)
        self.assertEqual(march.start, "2026-03-01")
        self.assertEqual(march.end, "2026-03-31")

    def test_standard_report_maps_core_kennzahlen(self) -> None:
        create_income(
            self.conn,
            date="2026-01-20",
            source="Standard",
            amount_eur=1190.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            vat_rate=19.0,
            tax_mode="standard",
            audit_user="tester",
        )
        create_income(
            self.conn,
            date="2026-02-20",
            source="Reduced",
            amount_eur=107.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            vat_rate=7.0,
            tax_mode="standard",
            audit_user="tester",
        )
        create_income(
            self.conn,
            date="2026-02-22",
            source="Zero",
            amount_eur=50.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            vat_rate=0.0,
            tax_mode="standard",
            audit_user="tester",
        )
        create_income(
            self.conn,
            date="2026-03-01",
            source="TaxFree",
            amount_eur=40.0,
            category_name="Umsatzsteuerfreie, nicht umsatzsteuerbare Betriebseinnahmen",
            tax_free=True,
            tax_mode="standard",
            audit_user="tester",
        )
        create_expense(
            self.conn,
            date="2026-01-15",
            vendor="EU SaaS",
            amount_eur=-100.0,
            category_name="Laufende EDV-Kosten",
            rc_type="eu",
            tax_mode="standard",
            audit_user="tester",
        )
        create_expense(
            self.conn,
            date="2026-01-16",
            vendor="Drittland SaaS",
            amount_eur=-50.0,
            category_name="Laufende EDV-Kosten",
            rc_type="third_country",
            tax_mode="standard",
            audit_user="tester",
        )
        create_expense(
            self.conn,
            date="2026-01-18",
            vendor="Office",
            amount_eur=-119.0,
            category_name="Arbeitsmittel",
            vat=20.0,
            tax_mode="standard",
            audit_user="tester",
        )

        report = build_vat_report(self.conn, year=2026, quarter=1, tax_mode="standard")

        self.assertEqual(line_by_kz(report, "81").basis_eur_raw, Decimal("1000.00"))
        self.assertEqual(line_by_kz(report, "81").tax_eur_rounded, Decimal("190.00"))
        self.assertEqual(line_by_kz(report, "86").basis_eur_raw, Decimal("100.00"))
        self.assertEqual(line_by_kz(report, "86").tax_eur_rounded, Decimal("7.00"))
        self.assertEqual(line_by_kz(report, "87").basis_eur_raw, Decimal("50.00"))
        self.assertEqual(line_by_kz(report, "48").basis_eur_raw, Decimal("40.00"))
        self.assertEqual(line_by_kz(report, "46").basis_eur_raw, Decimal("100.00"))
        self.assertEqual(line_by_kz(report, "47").tax_eur_rounded, Decimal("19.00"))
        self.assertEqual(line_by_kz(report, "84").basis_eur_raw, Decimal("50.00"))
        self.assertEqual(line_by_kz(report, "85").tax_eur_rounded, Decimal("9.50"))
        self.assertEqual(line_by_kz(report, "66").tax_eur_rounded, Decimal("20.00"))
        self.assertEqual(line_by_kz(report, "67").tax_eur_rounded, Decimal("28.50"))
        self.assertEqual(line_by_kz(report, "83").tax_eur_rounded, Decimal("177.00"))

    def test_missing_payment_date_and_unclassified_rc_are_diagnostics(self) -> None:
        create_income(
            self.conn,
            invoice_date="2026-01-20",
            source="InvoiceOnly",
            amount_eur=119.0,
            category_name="Umsatzsteuerpflichtige Betriebseinnahmen",
            vat_rate=19.0,
            tax_mode="standard",
            audit_user="tester",
        )
        self.conn.execute(
            """INSERT INTO expenses
               (uuid, payment_date, vendor, amount_eur, rc_type, vat_input, vat_output,
                hash)
               VALUES (?, ?, ?, ?, 'unclassified', 0.0, 19.0, ?)""",
            ("legacy-rc", "2026-01-15", "Legacy SaaS", -100.0, "legacy-rc-hash"),
        )
        self.conn.commit()

        report = build_vat_report(self.conn, year=2026, tax_mode="standard")
        reason_codes = {item.reason_code for item in report.diagnostics}

        self.assertIn("missing_payment_date", reason_codes)
        self.assertIn("missing_rc_type", reason_codes)

    def test_small_business_rc_does_not_create_kz67(self) -> None:
        create_expense(
            self.conn,
            date="2026-01-15",
            vendor="EU SaaS",
            amount_eur=-100.0,
            category_name="Laufende EDV-Kosten",
            rc_type="eu",
            tax_mode="small_business",
            audit_user="tester",
        )

        report = build_vat_report(self.conn, year=2026, tax_mode="small_business")

        self.assertEqual(line_by_kz(report, "47").tax_eur_rounded, Decimal("19.00"))
        self.assertEqual(line_by_kz(report, "67").tax_eur_rounded, Decimal("0.00"))

    def test_round_basis_helper(self) -> None:
        self.assertEqual(round_basis_eur(Decimal("1.49")), 1)
        self.assertEqual(round_basis_eur(Decimal("1.50")), 2)
        self.assertEqual(round_basis_eur(Decimal("-1.50")), -2)


if __name__ == "__main__":
    unittest.main()
