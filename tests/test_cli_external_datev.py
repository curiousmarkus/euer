"""Integration des separat installierten DATEV-Kommandos."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from euercli import cli


class TestExternalDatev(unittest.TestCase):
    def setUp(self):
        self.entry_points = mock.patch.object(
            cli.importlib.metadata, "entry_points", return_value=[]
        )
        self.which = mock.patch.object(cli.shutil, "which", return_value="/bin/euer-datev")
        self.dispatch = mock.patch.object(cli, "_run_external_datev")
        self.skill = mock.patch.object(cli, "skill_status", return_value={"status": "current"})
        for patcher in (self.entry_points, self.which, self.dispatch, self.skill):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_help_and_setup_do_not_require_database_or_project_config(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(cli.Path, "cwd", return_value=Path(directory)):
                (Path(directory) / ".euer").mkdir()
                (Path(directory) / ".euer" / "config.toml").write_text("invalid = [")
                cli.main(["datev", "--help"])
                cli.main(["datev", "export", "--help"])
                cli.main(["datev", "init-skr", "--skr", "03"])
        self.assertEqual(cli._run_external_datev.call_count, 3)
        cli.skill_status.assert_not_called()

    def test_project_db_is_passed_to_data_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "books.db"
            database.touch()
            (root / ".euer").mkdir()
            (root / ".euer" / "config.toml").write_text(
                '[database]\npath = "books.db"\n', encoding="utf-8"
            )
            with mock.patch.object(cli.Path, "cwd", return_value=root):
                cli.main(["datev", "validate", "--year", "2026"])
            cli._run_external_datev.assert_called_with(
                "/bin/euer-datev", ["validate", "--db", str(database.resolve()), "--year", "2026"]
            )

    def test_datev_db_overrides_global_db(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "local.db"
            local.touch()
            with mock.patch.object(cli.Path, "cwd", return_value=root):
                cli.main(["--db", "missing.db", "datev", "export", "--db", str(local)])
            cli._run_external_datev.assert_called_with(
                "/bin/euer-datev", ["export", "--db", str(local)]
            )

    def test_root_config_is_forwarded_to_external_datev(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(cli.Path, "cwd", return_value=Path(directory)):
                cli.main(["--config", "file with spaces.toml", "datev", "doctor"])
            cli._run_external_datev.assert_called_with(
                "/bin/euer-datev", ["doctor", "--config", "file with spaces.toml"]
            )

    def test_root_db_is_forwarded_to_external_doctor(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "mandant.db")
            with mock.patch.object(cli.Path, "cwd", return_value=Path(directory)):
                cli.main(["--db", db, "datev", "doctor"])
            cli._run_external_datev.assert_called_with("/bin/euer-datev", ["doctor", "--db", db])

    def test_root_db_is_not_forwarded_to_init_skr(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "mandant.db")
            with mock.patch.object(cli.Path, "cwd", return_value=Path(directory)):
                cli.main(["--db", db, "datev", "init-skr", "--skr", "03"])
            cli._run_external_datev.assert_called_with(
                "/bin/euer-datev", ["init-skr", "--skr", "03"]
            )

    def test_missing_datev_has_installation_hint(self):
        cli.shutil.which.return_value = None
        with self.assertRaises(SystemExit) as result:
            cli.main(["datev", "--help"])
        self.assertEqual(result.exception.code, 2)
