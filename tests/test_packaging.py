import tomllib
import unittest
from pathlib import Path

from euercli import VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]


class PackagingTestCase(unittest.TestCase):
    def test_package_uses_canonical_dynamic_version(self) -> None:
        with (REPO_ROOT / "pyproject.toml").open("rb") as file:
            metadata = tomllib.load(file)

        self.assertEqual(["version"], metadata["project"]["dynamic"])
        self.assertEqual(
            {"attr": "euercli.VERSION"},
            metadata["tool"]["setuptools"]["dynamic"]["version"],
        )
        self.assertEqual("euer", metadata["project"]["name"])
        self.assertEqual("euer", metadata["project"]["urls"]["Repository"].rsplit("/", 1)[-1])
        self.assertRegex(VERSION, r"^\d+\.\d+\.\d+$")
