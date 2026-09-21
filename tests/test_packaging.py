import tomllib
import unittest
from pathlib import Path

from euercli import VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]


class PackagingTestCase(unittest.TestCase):
    def test_package_versions_match(self) -> None:
        with (REPO_ROOT / "pyproject.toml").open("rb") as file:
            project_version = tomllib.load(file)["project"]["version"]

        self.assertEqual(VERSION, project_version)
