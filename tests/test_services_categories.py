import sqlite3
import unittest
import uuid

from euercli.schema import SCHEMA, SEED_CATEGORIES
from euercli.services.categories import get_category_by_name, get_category_list


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


if __name__ == "__main__":
    unittest.main()
