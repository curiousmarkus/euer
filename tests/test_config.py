import tomllib
import unittest

from euercli.config import dump_toml, get_ledger_accounts
from euercli.services.errors import ValidationError


class ConfigTestCase(unittest.TestCase):
    def test_nested_datev_tables_round_trip(self) -> None:
        data = {
            "database": {"path": "euer.db"},
            "datev": {"skr": "03", "accounts": {"Bank Privat": "1210", "bank": "1200"}},
        }
        self.assertEqual(tomllib.loads(dump_toml(data)), data)

    def test_get_ledger_accounts_parses_valid_entries(self) -> None:
        accounts = get_ledger_accounts(
            {
                "ledger_accounts": [
                    {
                        "key": "hosting",
                        "name": "Hosting & Cloud-Dienste",
                        "category": "Laufende EDV-Kosten",
                        "account_number": "4940",
                    }
                ]
            }
        )

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].key, "hosting")
        self.assertEqual(accounts[0].account_number, "4940")

    def test_get_ledger_accounts_rejects_duplicate_keys_case_insensitive(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            get_ledger_accounts(
                {
                    "ledger_accounts": [
                        {
                            "key": "Hosting",
                            "name": "Hosting",
                            "category": "Laufende EDV-Kosten",
                        },
                        {
                            "key": "hosting",
                            "name": "Cloud",
                            "category": "Laufende EDV-Kosten",
                        },
                    ]
                }
            )

        self.assertEqual(ctx.exception.code, "duplicate_ledger_account_key")

    def test_get_ledger_accounts_rejects_missing_required_fields(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            get_ledger_accounts(
                {
                    "ledger_accounts": [
                        {
                            "key": "hosting",
                            "category": "Laufende EDV-Kosten",
                        }
                    ]
                }
            )

        self.assertEqual(ctx.exception.code, "ledger_account_missing_fields")

    def test_dump_toml_supports_arrays_of_tables(self) -> None:
        content = dump_toml(
            {
                "tax": {"mode": "small_business"},
                "ledger_accounts": [
                    {
                        "key": "hosting",
                        "name": "Hosting & Cloud-Dienste",
                        "category": "Laufende EDV-Kosten",
                        "account_number": "4940",
                    }
                ],
            }
        )

        parsed = tomllib.loads(content)
        self.assertEqual(parsed["tax"]["mode"], "small_business")
        self.assertEqual(parsed["ledger_accounts"][0]["key"], "hosting")
        self.assertEqual(parsed["ledger_accounts"][0]["account_number"], "4940")

    def test_get_private_accounts_validates_list_of_strings(self) -> None:
        from euercli.config import get_private_accounts

        self.assertEqual(get_private_accounts({}), ["privat"])
        self.assertEqual(
            get_private_accounts({"accounts": {"private": ["p-sparkasse", "privat-giro"]}}),
            ["p-sparkasse", "privat-giro"],
        )

        with self.assertRaises(ValidationError) as ctx1:
            get_private_accounts({"accounts": {"private": "p-sparkasse"}})
        self.assertEqual(ctx1.exception.code, "invalid_private_accounts")

        with self.assertRaises(ValidationError) as ctx2:
            get_private_accounts({"accounts": {"private": [123]}})
        self.assertEqual(ctx2.exception.code, "invalid_private_accounts")

        with self.assertRaises(ValidationError) as ctx3:
            get_private_accounts({"accounts": {"private": []}})
        self.assertEqual(ctx3.exception.code, "invalid_private_accounts")

    def test_get_known_accounts_filters_ledger_accounts(self) -> None:
        from euercli.config import get_known_accounts

        cfg = {
            "accounts": {
                "default": "giro",
                "mapping": {
                    "giro": "1200",
                    "paypal": "1210",
                    "hosting": "4940",
                    "erloese": "8400",
                },
            }
        }
        known = get_known_accounts(cfg)
        self.assertIn("giro", known)
        self.assertIn("paypal", known)
        self.assertNotIn("hosting", known)
        self.assertNotIn("erloese", known)


if __name__ == "__main__":
    unittest.main()
