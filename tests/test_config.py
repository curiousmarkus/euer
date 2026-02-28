import tomllib
import unittest

from euercli.config import dump_toml, get_ledger_accounts
from euercli.services.errors import ValidationError


class ConfigTestCase(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
