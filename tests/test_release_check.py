import tempfile
import unittest
from pathlib import Path

from scripts.release_check import (
    ReleaseCheckError,
    extract_release_notes,
    validate_main_ancestry,
    validate_tag,
)


class ReleaseCheckTestCase(unittest.TestCase):
    def _notes_file(self, content: str) -> Path:
        self.addCleanup(self._cleanup_tempdir)
        self.tempdir = tempfile.TemporaryDirectory()
        path = Path(self.tempdir.name) / "RELEASE_NOTES.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _cleanup_tempdir(self) -> None:
        self.tempdir.cleanup()

    def test_extracts_exact_version_section_without_heading(self) -> None:
        path = self._notes_file(
            "# Release Notes\n\n## 0.8.0\n\n### Änderungen\n\n"
            "- Neuer Kanal.\n\n## 0.7.1\n\n- Fix.\n"
        )

        self.assertEqual("### Änderungen\n\n- Neuer Kanal.", extract_release_notes(path, "0.8.0"))

    def test_missing_section_fails(self) -> None:
        path = self._notes_file("# Release Notes\n\n## 0.7.1\n\n- Fix.\n")

        with self.assertRaisesRegex(ReleaseCheckError, "fehlen"):
            extract_release_notes(path, "0.8.0")

    def test_duplicate_section_fails(self) -> None:
        path = self._notes_file("## 0.8.0\n\n- Eins.\n\n## 0.8.0\n\n- Zwei.\n")

        with self.assertRaisesRegex(ReleaseCheckError, "doppelt"):
            extract_release_notes(path, "0.8.0")

    def test_empty_section_fails(self) -> None:
        path = self._notes_file("## 0.8.0\n\n## 0.7.1\n\n- Fix.\n")

        with self.assertRaisesRegex(ReleaseCheckError, "leer"):
            extract_release_notes(path, "0.8.0")

    def test_tag_must_match_canonical_version(self) -> None:
        validate_tag("v0.8.0", "0.8.0")

        with self.assertRaisesRegex(ReleaseCheckError, "Ungültiges Release-Tag"):
            validate_tag("v0.8.0-rc1", "0.8.0")
        with self.assertRaisesRegex(ReleaseCheckError, "stimmt nicht"):
            validate_tag("v0.8.1", "0.8.0")

    def test_release_commit_must_use_an_annotated_tag(self) -> None:
        with self.assertRaisesRegex(ReleaseCheckError, "nicht annotiert"):
            validate_main_ancestry("HEAD", "HEAD")
