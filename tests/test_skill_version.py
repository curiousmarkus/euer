import argparse
import json
import re
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from euercli.cli import build_parser
from euercli.skill import expected_version, skill_status
from tests.cli_test_base import REPO_ROOT, BaseCLITestCase


class SkillVersionCLITestCase(BaseCLITestCase):
    def raw_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "euercli", "--db", str(self.db_path), *args],
            cwd=REPO_ROOT,
            env=self.env,
            text=True,
            capture_output=True,
        )

    def test_missing_invalid_older_and_newer_confirmation(self) -> None:
        for content, status in [
            ("", "unconfirmed"),
            ('[skill]\nversion = "x"\n', "invalid"),
            ('[skill]\nversion = "0.1.0"\n', "mismatch"),
            ('[skill]\nversion = "99.0.0"\n', "mismatch"),
        ]:
            with self.subTest(status=status, content=content):
                self.write_config(content)
                result = self.raw_cli("list", "categories")
                self.assertEqual(1, result.returncode)
                self.assertIn("--ignore-skill-version", result.stderr)
                self.assertIn(expected_version(), result.stderr)
                report = json.loads(self.raw_cli("doctor", "--json").stdout)
                self.assertEqual(status, report["skill"]["status"])

    def test_confirmation_preserves_config_and_unlocks_commands(self) -> None:
        self.write_config('[tax]\nmode = "standard"\n')
        result = self.raw_cli("setup", "--set", "skill.version", expected_version())
        self.assertEqual(0, result.returncode, result.stderr)
        config = tomllib.loads(self.expected_config_path().read_text())
        self.assertEqual("standard", config["tax"]["mode"])
        self.assertEqual(expected_version(), config["skill"]["version"])
        self.assertEqual(0, self.raw_cli("list", "categories").returncode)
        self.assertEqual(
            "current", json.loads(self.raw_cli("doctor", "--json").stdout)["skill"]["status"]
        )
        invalid = self.raw_cli("setup", "--set", "skill.version", "1.2")
        self.assertEqual(1, invalid.returncode)
        self.assertEqual(config, tomllib.loads(self.expected_config_path().read_text()))

    def test_confirmation_works_before_database_creation(self) -> None:
        self.db_path.unlink()
        result = self.raw_cli("setup", "--set", "skill.version", expected_version())
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            expected_version(),
            tomllib.loads(self.expected_config_path().read_text())["skill"]["version"],
        )

    def test_escape_hatch_at_end_and_json_error(self) -> None:
        self.write_config("")
        self.assertEqual(0, self.raw_cli("list", "categories", "--ignore-skill-version").returncode)
        report = self.raw_cli("init", "--json")
        self.assertEqual(1, report.returncode)
        data = json.loads(report.stderr)
        self.assertEqual("outdated_skill", data["error_code"])
        self.assertIn("bundle_path", data)

    def test_doctor_reports_skill_without_database(self) -> None:
        self.db_path.unlink()
        report = json.loads(self.raw_cli("doctor", "--json").stdout)
        self.assertEqual("unconfirmed", report["skill"]["status"])
        self.assertTrue(Path(report["skill"]["bundle_path"]).is_absolute())
        self.assertEqual(expected_version(), report["skill"]["expected_version"])

    def test_broken_config_is_file_error_even_with_escape_hatch(self) -> None:
        self.write_config("invalid [toml")
        result = self.raw_cli("list", "categories", "--ignore-skill-version")
        self.assertEqual(1, result.returncode)
        self.assertIn("Fehler:", result.stderr)
        self.assertNotIn("Skill-Version weicht", result.stderr)

    def test_missing_bundle_is_diagnostic_error(self) -> None:
        with patch("euercli.skill.bundle_path", return_value=self.root / "missing-skill"):
            status = skill_status()
        self.assertEqual("error", status["status"])
        self.assertIsNone(status["expected_version"])

    def test_doctor_keeps_skill_diagnosis_with_invalid_project_config(self) -> None:
        project_config = self.root / ".euer" / "config.toml"
        project_config.parent.mkdir()
        project_config.write_text("broken [toml")
        result = subprocess.run(
            [sys.executable, "-m", "euercli", "doctor", "--json"],
            cwd=self.root,
            env={**self.env, "PYTHONPATH": str(REPO_ROOT)},
            text=True,
            capture_output=True,
        )
        self.assertEqual(1, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual("unconfirmed", report["skill"]["status"])
        self.assertFalse(report["config"]["project_config"]["valid"])


class SkillReferenceTestCase(unittest.TestCase):
    def test_current_setup_examples_use_bundled_skill_version(self) -> None:
        for relative_path in (
            "docs/skills/euer-buchhaltung/SKILL.md",
            "docs/skills/euer-buchhaltung/references/cli_reference.md",
            "docs/templates/onboarding-prompt.md",
        ):
            with self.subTest(document=relative_path):
                document = (REPO_ROOT / relative_path).read_text()
                versions = re.findall(
                    r'euer setup --set skill\.version "(\d+\.\d+\.\d+)"', document
                )
                self.assertTrue(versions, relative_path)
                self.assertEqual({expected_version()}, set(versions))

    def test_skill_links_resolve_inside_bundle(self) -> None:
        bundle = REPO_ROOT / "docs/skills/euer-buchhaltung"
        for document in bundle.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
                path = target.split("#", 1)[0]
                if not path or "://" in path:
                    continue
                resolved = (document.parent / path).resolve()
                self.assertTrue(resolved.is_relative_to(bundle.resolve()), (document, target))
                self.assertTrue(resolved.is_file(), (document, target))

    def test_every_core_parser_argument_is_in_its_own_section(self) -> None:
        reference = (
            REPO_ROOT / "docs/skills/euer-buchhaltung/references/cli_reference.md"
        ).read_text()
        root, *blocks = reference.split("\n### euer ")
        sections = {block.split("\n", 1)[0]: block.split("\n", 1)[1] for block in blocks}

        def check(parser: argparse.ArgumentParser, path: tuple[str, ...] = ()) -> None:
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    for name, child in action.choices.items():
                        child_path = (*path, name)
                        section = sections.get(" ".join(child_path))
                        self.assertIsNotNone(section, f"Fehlender Abschnitt: {child_path}")
                        for argument in child._actions:
                            if argument.dest == "help" or isinstance(
                                argument, argparse._SubParsersAction
                            ):
                                continue
                            tokens = argument.option_strings or [argument.dest]
                            for token in tokens:
                                self.assertIn(
                                    f"`{token}`",
                                    section.split("**Beispiel:**", 1)[0].split(
                                        "| Argument | Bedeutung |", 1
                                    )[-1],
                                    (child_path, token),
                                )
                        check(child, child_path)

        with patch("euercli.cli.load_plugins"):
            parser = build_parser()
        check(parser)
        global_options = root.split("## Globale Optionen", 1)[1]
        for action in parser._actions:
            if action.dest == "help" or isinstance(action, argparse._SubParsersAction):
                continue
            for option in action.option_strings:
                self.assertIn(f"`{option}`", global_options, option)


if __name__ == "__main__":
    unittest.main()
