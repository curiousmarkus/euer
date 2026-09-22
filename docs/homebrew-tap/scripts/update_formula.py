#!/usr/bin/env python3
"""Aktualisiert Formula-URL, SHA256 und die XLSX-Python-Ressourcen aus PyPI."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PYPI_JSON = "https://pypi.org/pypi/{project}/json"
STABLE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
REQUIREMENT_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)")
RESOURCE_START = "  # BEGIN AUTO-GENERATED PYTHON RESOURCES"
RESOURCE_END = "  # END AUTO-GENERATED PYTHON RESOURCES"


def fetch_project(project: str) -> dict:
    """Liest die aktuellen PyPI-Metadaten eines Projekts."""
    with urllib.request.urlopen(PYPI_JSON.format(project=project), timeout=30) as response:
        return json.load(response)


def stable_sdist(project: str, metadata: dict) -> tuple[str, str, str]:
    """Gibt Version, sdist-URL und SHA256 der stabilen PyPI-Version zurück."""
    candidates: list[tuple[tuple[int, int, int], str, dict]] = []
    for version, files in metadata["releases"].items():
        if not STABLE_VERSION_RE.fullmatch(version):
            continue
        sdists = sorted(
            (
                file
                for file in files
                if file["packagetype"] == "sdist" and not file.get("yanked", False)
            ),
            key=lambda file: file["url"],
        )
        if sdists:
            candidates.append((tuple(int(part) for part in version.split(".")), version, sdists[0]))
    if not candidates:
        current_version = metadata["info"].get("version", "unbekannt")
        raise ValueError(f"Keine stabile sdist-Version für {project} gefunden: {current_version}")
    _, version, sdist = max(candidates)
    return version, sdist["url"], sdist["digests"]["sha256"]


def requirement_names(metadata: dict, *, include_xlsx_extra: bool = False) -> set[str]:
    """Ermittelt Paketnamen aus Requires-Dist, inklusive des xlsx-Extras."""
    names: set[str] = set()
    for requirement in metadata["info"].get("requires_dist") or []:
        requirement_name, _, marker = requirement.partition(";")
        marker = marker.lower()
        if "extra" in marker:
            if not include_xlsx_extra or "xlsx" not in marker:
                continue
        match = REQUIREMENT_NAME_RE.match(requirement_name.strip())
        if match:
            names.add(match.group(1).replace("_", "-"))
    return names


def resolve_xlsx_resources(root_metadata: dict) -> list[tuple[str, str, str]]:
    """Löst xlsx- und transitive Abhängigkeiten bis zum Ende rekursiv auf."""
    pending = sorted(requirement_names(root_metadata, include_xlsx_extra=True))
    seen: set[str] = set()
    resources: dict[str, tuple[str, str, str]] = {}

    while pending:
        project = pending.pop(0)
        key = project.lower().replace("-", "_")
        if key in seen:
            continue
        seen.add(key)
        metadata = fetch_project(project)
        _, url, sha256 = stable_sdist(project, metadata)
        resources[key] = (project, url, sha256)
        pending.extend(sorted(requirement_names(metadata)))

    return [resources[key] for key in sorted(resources)]


def resource_block(resources: list[tuple[str, str, str]]) -> str:
    """Erzeugt den deterministischen Homebrew-Ressourcenblock."""
    blocks = [RESOURCE_START]
    for project, url, sha256 in resources:
        blocks.extend(
            [
                "",
                f'  resource "{project}" do',
                f'    url "{url}"',
                f'    sha256 "{sha256}"',
                "  end",
            ]
        )
    blocks.extend(["", RESOURCE_END])
    return "\n".join(blocks)


def update_formula(formula_path: Path) -> str:
    """Aktualisiert eine Formula und gibt die aktuelle euer-Version zurück."""
    formula = formula_path.read_text(encoding="utf-8")
    euer_metadata = fetch_project("euer")
    version, url, sha256 = stable_sdist("euer", euer_metadata)
    formula, url_count = re.subn(
        r'(?m)^  url "(?:__PYPI_SDIST_URL__|https://files\.pythonhosted\.org/[^"\n]+)"',
        f'  url "{url}"',
        formula,
        count=1,
    )
    formula, sha_count = re.subn(
        r'(?m)^  sha256 "(?:__PYPI_SDIST_SHA256__|[0-9a-f]{64})"',
        f'  sha256 "{sha256}"',
        formula,
        count=1,
    )
    if url_count != 1 or sha_count != 1:
        raise ValueError("euer-URL oder euer-SHA256 in der Formula fehlt")

    resources = resource_block(resolve_xlsx_resources(euer_metadata))
    formula, resource_count = re.subn(
        rf"(?ms)^{re.escape(RESOURCE_START)}.*?^{re.escape(RESOURCE_END)}",
        resources,
        formula,
        count=1,
    )
    if resource_count != 1:
        raise ValueError("Automatisierter Python-Ressourcenblock fehlt")
    formula_path.write_text(formula, encoding="utf-8")
    return version


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} Formula/euer.rb", file=sys.stderr)
        return 2
    try:
        version = update_formula(Path(sys.argv[1]))
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print(f"Formula-Update fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    print(f"Formula auf euer {version} aktualisiert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
