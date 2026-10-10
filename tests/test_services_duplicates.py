import hashlib
import tempfile
import unittest
from pathlib import Path

from euercli.db import get_db_connection
from euercli.schema import SCHEMA
from euercli.services.duplicates import find_all_exact_duplicates
from euercli.services.errors import ValidationError
from euercli.utils import compute_hash


class DuplicateLookupTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.conn = get_db_connection(Path(self.temp_dir.name) / "test.db")
        self.conn.executescript(SCHEMA)

    def tearDown(self) -> None:
        self.conn.close()
        self.temp_dir.cleanup()

    def lookup(self, table: str, *, account: str | None = "bank", **kwargs) -> list[int]:
        return find_all_exact_duplicates(
            self.conn,
            table_name=table,
            payment_date="2026-03-01",
            invoice_date=None,
            party="Test",
            amount_eur=100.0,
            receipt_name="beleg.pdf",
            invoice_number="R1",
            account=account,
            **kwargs,
        )

    def insert_candidate(self, table: str, tx_hash: str, *, deleted: bool = False) -> int:
        party_col = "vendor" if table == "expenses" else "source"
        cursor = self.conn.execute(
            f"""INSERT INTO {table}
                (uuid, {party_col}, amount_eur, payment_date, receipt_name,
                 invoice_number, account, hash, deleted_at)
                VALUES (?, 'Test', 100, '2026-03-01', 'beleg.pdf', 'R1', 'bank', ?, ?)""",
            (f"{table}-{tx_hash}", tx_hash, "2026-03-02" if deleted else None),
        )
        return cursor.lastrowid

    def test_hash_variants_keep_order_and_exclude_deleted_and_self(self) -> None:
        base = compute_hash("2026-03-01", "Test", 100.0, "beleg.pdf", "R1")
        legacy = hashlib.sha256(b"2026-03-01|Test|100.00|beleg.pdf|R1").hexdigest()
        numberless = compute_hash("2026-03-01", "Test", 100.0, "beleg.pdf")
        for table in ("expenses", "income"):
            with self.subTest(table=table):
                first = self.insert_candidate(table, base)
                excluded = self.insert_candidate(table, f"{base}#2")
                old = self.insert_candidate(table, legacy)
                without_number = self.insert_candidate(table, numberless)
                self.conn.execute(
                    f"UPDATE {table} SET invoice_number = NULL WHERE id = ?", (without_number,)
                )
                self.insert_candidate(table, f"{base}#3", deleted=True)
                self.assertEqual(
                    self.lookup(table, exclude_id=excluded), [first, old, without_number]
                )

    def test_import_snapshot_account_ambiguity_is_not_hidden_by_cache(self) -> None:
        for table in ("expenses", "income"):
            with self.subTest(table=table):
                base = compute_hash("2026-03-01", "Test", 100.0, "beleg.pdf", "R1")
                first = self.insert_candidate(table, base)
                second = self.insert_candidate(table, f"{base}#2")
                self.conn.execute(f"UPDATE {table} SET account = 'paypal' WHERE id = ?", (second,))
                cache = {}
                self.assertEqual(self.lookup(table, account=None, cache=cache), [first, second])
                self.assertEqual(
                    self.lookup(table, account=None, cache=cache, max_id=first),
                    [first],
                )
                with self.assertRaises(ValidationError) as ctx:
                    self.lookup(table, account=None, cache=cache, max_id=second)
                self.assertEqual(ctx.exception.code, "ambiguous_duplicate_account")
                self.assertEqual(ctx.exception.details["candidate_ids"], [first, second])

    def test_known_account_precedes_older_candidate_without_account(self) -> None:
        for table in ("expenses", "income"):
            with self.subTest(table=table):
                base = compute_hash("2026-03-01", "Test", 100.0, "beleg.pdf", "R1")
                first = self.insert_candidate(table, base)
                second = self.insert_candidate(table, f"{base}#2")
                self.conn.execute(f"UPDATE {table} SET account = NULL WHERE id = ?", (first,))
                cache = {}
                for _ in range(2):
                    self.assertEqual(
                        self.lookup(table, cache=cache, max_id=second),
                        [second, first],
                    )

    def test_lookup_work_does_not_scale_with_unrelated_active_rows(self) -> None:
        # Echtes Schema einschließlich konkurrierendem deleted_at-Index.
        # SQLite-VM-Schritte messen statt instabiler Laufzeiten oder Indexnamen.
        for table in ("expenses", "income"):
            with self.subTest(table=table):
                base = compute_hash("2026-03-01", "Test", 100.0, "beleg.pdf", "R1")
                target = self.insert_candidate(table, base)
                party_col = "vendor" if table == "expenses" else "source"
                self.conn.executemany(
                    f"""INSERT INTO {table} (uuid, {party_col}, amount_eur, payment_date, hash)
                        VALUES (?, 'Andere', 1, '2026-03-01', ?)""",
                    [
                        (f"{table}-other-{i}", hashlib.sha256(str(i).encode()).hexdigest())
                        for i in range(10_000)
                    ],
                )
                self.conn.commit()
                callbacks = 0

                def count_steps() -> int:
                    nonlocal callbacks
                    callbacks += 1
                    return 0

                self.conn.set_progress_handler(count_steps, 100)
                try:
                    self.assertEqual(self.lookup(table), [target])
                    self.assertEqual(self.lookup(table, exclude_id=target), [])
                finally:
                    self.conn.set_progress_handler(None, 0)
                self.assertLess(callbacks, 50, "Duplikatsuche prüft zu viele unbeteiligte Zeilen")
