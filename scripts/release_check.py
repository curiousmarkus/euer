#!/usr/bin/env python3
"""Prüft Release-Tag, Versionsquelle, main-Ancestry und Release Notes."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from euercli import VERSION

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
RELEASE_HEADING_RE = re.compile(r"^## (\d+\.\d+\.\d+)\s*$", re.MULTILINE)


class ReleaseCheckError(ValueError):
    """Fehler bei einer nicht veröffentlichbaren Version."""


def extract_release_notes(notes_path: Path, version: str) -> str:
    """Extrahiert genau den nicht leeren Release-Notes-Abschnitt einer Version."""
    text = notes_path.read_text(encoding="utf-8")
    headings = list(RELEASE_HEADING_RE.finditer(text))
    matching = [heading for heading in headings if heading.group(1) == version]
    if not matching:
        raise ReleaseCheckError(f"Release Notes für Version {version} fehlen in {notes_path}.")
    if len(matching) > 1:
        raise ReleaseCheckError(
            f"Release Notes für Version {version} sind in {notes_path} doppelt vorhanden."
        )

    heading = matching[0]
    next_heading = next(
        (candidate for candidate in headings if candidate.start() > heading.start()),
        None,
    )
    section_end = next_heading.start() if next_heading else len(text)
    section = text[heading.end() : section_end].strip()
    if not section:
        raise ReleaseCheckError(f"Release-Notes-Abschnitt {version} ist leer.")
    return section


def validate_tag(tag: str, version: str = VERSION) -> None:
    """Prüft das Produktions-Tag und seinen Abgleich mit der Paketversion."""
    tag_match = TAG_RE.fullmatch(tag)
    if not tag_match:
        raise ReleaseCheckError(
            f"Ungültiges Release-Tag {tag!r}; erwartet wird vMAJOR.MINOR.PATCH."
        )
    if not SEMVER_RE.fullmatch(version):
        raise ReleaseCheckError(f"Ungültige kanonische Version {version!r}.")
    tag_version = ".".join(tag_match.groups())
    if tag_version != version:
        raise ReleaseCheckError(
            f"Tag-Version {tag_version} stimmt nicht mit euercli.VERSION {version} überein."
        )


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def validate_main_ancestry(tag: str, main_ref: str) -> None:
    """Stellt sicher, dass der Release-Commit Bestandteil des Main-Zweigs ist."""
    tag_type = _git("cat-file", "-t", tag)
    if tag_type.returncode != 0:
        raise ReleaseCheckError(f"Tag {tag} ist im Checkout nicht vorhanden.")
    if tag_type.stdout.strip() != "tag":
        raise ReleaseCheckError(f"Tag {tag} ist nicht annotiert.")

    resolved_tag = _git("rev-parse", "--verify", f"{tag}^{{commit}}")
    if resolved_tag.returncode != 0:
        raise ReleaseCheckError(f"Tag {tag} ist im Checkout nicht vorhanden.")

    resolved_main = _git("rev-parse", "--verify", f"{main_ref}^{{commit}}")
    if resolved_main.returncode != 0:
        details = resolved_main.stderr.strip() or "unbekannter Git-Fehler"
        raise ReleaseCheckError(f"Main-Referenz {main_ref!r} ist nicht verfügbar: {details}")

    ancestry = _git("merge-base", "--is-ancestor", tag, main_ref)
    if ancestry.returncode != 0:
        raise ReleaseCheckError(f"Der Commit von {tag} ist kein Bestandteil von {main_ref}.")


def check_release(
    *,
    tag: str,
    notes_path: Path,
    main_ref: str,
    version: str = VERSION,
) -> str:
    """Führt alle lokalen Release-Metadatenprüfungen aus und gibt die Notes zurück."""
    validate_tag(tag, version)
    validate_main_ancestry(tag, main_ref)
    return extract_release_notes(notes_path, version)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Release-Tag, z. B. v0.8.0")
    parser.add_argument(
        "--notes",
        type=Path,
        default=Path("docs/RELEASE_NOTES.md"),
        help="Kanonische Release-Notes-Datei",
    )
    parser.add_argument(
        "--main-ref",
        default="origin/main",
        help="Git-Referenz für die Ancestry-Prüfung (default: origin/main)",
    )
    parser.add_argument(
        "--notes-output",
        type=Path,
        help="Optionaler Ausgabepfad für den extrahierten Notes-Abschnitt",
    )
    args = parser.parse_args()

    try:
        notes = check_release(
            tag=args.tag,
            notes_path=args.notes,
            main_ref=args.main_ref,
        )
        if args.notes_output:
            args.notes_output.write_text(notes + "\n", encoding="utf-8")
        print(f"Release-Check erfolgreich: {args.tag} / {VERSION}")
    except (OSError, ReleaseCheckError) as exc:
        print(f"Release-Check fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
