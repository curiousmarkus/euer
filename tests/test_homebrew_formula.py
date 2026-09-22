import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "docs" / "homebrew-tap" / "scripts" / "update_formula.py"


def load_formula_updater():
    spec = importlib.util.spec_from_file_location("homebrew_formula_updater", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Homebrew-Updater konnte nicht geladen werden")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HomebrewFormulaTestCase(unittest.TestCase):
    def test_stable_sdist_ignores_newer_prerelease(self) -> None:
        updater = load_formula_updater()
        metadata = {
            "info": {"version": "0.9.0rc1"},
            "releases": {
                "0.9.0rc1": [
                    {
                        "packagetype": "sdist",
                        "url": "https://example.test/euer-0.9.0rc1.tar.gz",
                        "digests": {"sha256": "a" * 64},
                    }
                ],
                "0.8.0": [
                    {
                        "packagetype": "sdist",
                        "url": "https://example.test/euer-0.8.0.tar.gz",
                        "digests": {"sha256": "b" * 64},
                    }
                ],
            },
        }

        self.assertEqual(
            (
                "0.8.0",
                "https://example.test/euer-0.8.0.tar.gz",
                "b" * 64,
            ),
            updater.stable_sdist("euer", metadata),
        )

    def test_update_workflow_runs_commit_job_commands_separately(self) -> None:
        workflow = (
            REPO_ROOT / "docs" / "homebrew-tap" / ".github" / "workflows" / "update-formula.yml"
        ).read_text(encoding="utf-8")

        self.assertIn(
            """      - name: Formula erneut aktualisieren
        run: |
          python3 scripts/update_formula.py Formula/euer.rb
          brew style Formula/euer.rb
          brew audit --tap="$GITHUB_REPOSITORY" --formula""",
            workflow,
        )

    def test_update_formula_resolves_xlsx_resources(self) -> None:
        updater = load_formula_updater()
        formula_template = (
            REPO_ROOT / "docs" / "homebrew-tap" / "Formula" / "euer.rb.template"
        ).read_text(encoding="utf-8")
        projects = {
            "euer": {
                "info": {
                    "version": "0.8.0",
                    "requires_dist": ['openpyxl>=3.1.0; extra == "xlsx"'],
                },
                "releases": {
                    "0.8.0": [
                        {
                            "packagetype": "sdist",
                            "url": "https://files.pythonhosted.org/euer-0.8.0.tar.gz",
                            "digests": {"sha256": "a" * 64},
                        }
                    ]
                },
            },
            "openpyxl": {
                "info": {
                    "version": "3.1.5",
                    "requires_dist": ["et_xmlfile"],
                },
                "releases": {
                    "3.1.5": [
                        {
                            "packagetype": "sdist",
                            "url": "https://files.pythonhosted.org/openpyxl-3.1.5.tar.gz",
                            "digests": {"sha256": "b" * 64},
                        }
                    ]
                },
            },
            "et-xmlfile": {
                "info": {"version": "2.0.0", "requires_dist": None},
                "releases": {
                    "2.0.0": [
                        {
                            "packagetype": "sdist",
                            "url": "https://files.pythonhosted.org/et-xmlfile-2.0.0.tar.gz",
                            "digests": {"sha256": "c" * 64},
                        }
                    ]
                },
            },
        }

        with tempfile.TemporaryDirectory() as temporary:
            formula_path = Path(temporary) / "euer.rb"
            formula_path.write_text(formula_template, encoding="utf-8")
            with patch.object(updater, "fetch_project", side_effect=projects.__getitem__):
                version = updater.update_formula(formula_path)

            formula = formula_path.read_text(encoding="utf-8")

        self.assertEqual("0.8.0", version)
        self.assertIn('url "https://files.pythonhosted.org/euer-0.8.0.tar.gz"', formula)
        self.assertIn('resource "et-xmlfile"', formula)
        self.assertIn('resource "openpyxl"', formula)
        self.assertIn('sha256 "' + "b" * 64 + '"', formula)
