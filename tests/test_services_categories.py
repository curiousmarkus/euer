import sqlite3
import unittest
import uuid

from euercli.schema import SCHEMA, SEED_CATEGORIES
from euercli.services.categories import (
    get_category_by_name,
    get_category_list,
    get_ledger_accounts_for_category,
    resolve_ledger_account,
)
from euercli.services.errors import ValidationError
from euercli.services.models import LedgerAccount


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


class CategoryServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = make_connection()

    def tearDown(self) -> None:
        self.conn.close()

    def test_get_category_list_filters_type(self) -> None:
        expenses = get_category_list(self.conn, "expense")
        self.assertTrue(expenses)
        self.assertTrue(all(cat.type == "expense" for cat in expenses))

    def test_get_category_by_name(self) -> None:
        category = get_category_by_name(self.conn, "Arbeitsmittel", "expense")
        self.assertIsNotNone(category)
        assert category is not None
        self.assertEqual(category.name, "Arbeitsmittel")
        self.assertEqual(category.type, "expense")
        self.assertTrue(category.uuid)

    def test_get_ledger_accounts_for_category(self) -> None:
        accounts = get_ledger_accounts_for_category(
            "Laufende EDV-Kosten",
            [
                LedgerAccount(
                    key="hosting",
                    name="Hosting",
                    category="Laufende EDV-Kosten",
                ),
                LedgerAccount(
                    key="beratung",
                    name="Beratung",
                    category="Rechts- und Steuerberatung, Buchführung",
                ),
            ],
        )

        self.assertEqual([account.key for account in accounts], ["hosting"])

    def test_resolve_ledger_account_validates_type(self) -> None:
        ledger_account = resolve_ledger_account(
            self.conn,
            "hosting",
            [
                LedgerAccount(
                    key="hosting",
                    name="Hosting",
                    category="Laufende EDV-Kosten",
                )
            ],
            "expense",
        )

        self.assertEqual(ledger_account.category, "Laufende EDV-Kosten")

    def test_resolve_ledger_account_rejects_wrong_type(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            resolve_ledger_account(
                self.conn,
                "erloese-19",
                [
                    LedgerAccount(
                        key="erloese-19",
                        name="Erlöse 19%",
                        category="Umsatzsteuerpflichtige Betriebseinnahmen",
                    )
                ],
                "expense",
            )

        self.assertEqual(ctx.exception.code, "ledger_account_type_mismatch")


if __name__ == "__main__":
    unittest.main()
