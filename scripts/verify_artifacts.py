#!/usr/bin/env python3
"""Prüft gebaute euer-Artefakte inklusive Installations-Smoke-Tests."""

from __future__ import annotations

import argparse
import email
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path

from euercli import VERSION


class ArtifactVerificationError(ValueError):
    """Fehler in einem gebauten Paket oder seinem Installations-Smoke-Test."""


def _run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode:
        details = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        raise ArtifactVerificationError(
            f"Befehl fehlgeschlagen ({result.returncode}): {' '.join(command)}\n{details}"
        )
    return result


def _metadata_from_wheel(path: Path):
    with zipfile.ZipFile(path) as archive:
        metadata_files = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise ArtifactVerificationError(f"Wheel enthält nicht genau eine METADATA: {path}")
        return email.message_from_bytes(archive.read(metadata_files[0]))


def _metadata_from_sdist(path: Path):
    with tarfile.open(path, "r:gz") as archive:
        metadata_files = [
            member
            for member in archive.getmembers()
            if member.name.endswith("/PKG-INFO") and member.name.count("/") == 1
        ]
        if len(metadata_files) != 1:
            raise ArtifactVerificationError(f"sdist enthält nicht genau eine PKG-INFO: {path}")
        extracted = archive.extractfile(metadata_files[0])
        if extracted is None:
            raise ArtifactVerificationError(f"PKG-INFO konnte nicht gelesen werden: {path}")
        return email.message_from_bytes(extracted.read())


def _assert_metadata(metadata, *, artifact: Path) -> None:
    if metadata.get("Name") != "euer":
        raise ArtifactVerificationError(
            f"{artifact.name}: Paketname ist nicht euer ({metadata.get('Name')!r})."
        )
    if metadata.get("Version") != VERSION:
        raise ArtifactVerificationError(
            f"{artifact.name}: Version {metadata.get('Version')!r} != {VERSION!r}."
        )
    requirements = metadata.get_all("Requires-Dist", []) or []
    unconditional = [
        requirement
        for requirement in requirements
        if requirement.lower().startswith("openpyxl") and "extra ==" not in requirement
    ]
    if unconditional:
        raise ArtifactVerificationError(
            f"{artifact.name}: openpyxl ist eine Pflichtabhängigkeit: {unconditional}"
        )


def _assert_wheel_entry_point(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        entry_point_files = [
            name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")
        ]
        if len(entry_point_files) != 1:
            raise ArtifactVerificationError(
                f"Wheel enthält nicht genau eine entry_points.txt: {path}"
            )
        entry_points = archive.read(entry_point_files[0]).decode("utf-8")
    if "euer = euercli.cli:main" not in entry_points:
        raise ArtifactVerificationError(f"Entry Point euer fehlt in {path}.")


def validate_artifact_metadata(dist_dir: Path) -> tuple[Path, Path]:
    """Validiert die genau einmal gebauten Wheel- und sdist-Dateien."""
    wheels = sorted(dist_dir.glob("euer-*.whl"))
    sdists = sorted(dist_dir.glob("euer-*.tar.gz"))
    all_files = sorted(path for path in dist_dir.iterdir() if path.is_file())
    expected_files = wheels + sdists
    unexpected_files = [path for path in all_files if path not in expected_files]
    if len(wheels) != 1 or len(sdists) != 1:
        raise ArtifactVerificationError(
            f"Erwartet genau ein euer-Wheel und ein euer-sdist, gefunden: "
            f"{[path.name for path in wheels + sdists]}"
        )
    if unexpected_files:
        raise ArtifactVerificationError(
            f"Unerwartete Dateien im Artefaktverzeichnis: "
            f"{[path.name for path in unexpected_files]}"
        )

    wheel, sdist = wheels[0], sdists[0]
    wheel_metadata = _metadata_from_wheel(wheel)
    sdist_metadata = _metadata_from_sdist(sdist)
    _assert_metadata(wheel_metadata, artifact=wheel)
    _assert_metadata(sdist_metadata, artifact=sdist)
    _assert_wheel_entry_point(wheel)
    return wheel, sdist


def _venv_python(environment: Path) -> Path:
    executable = "python.exe" if os.name == "nt" else "python"
    return environment / ("Scripts" if os.name == "nt" else "bin") / executable


def _create_venv(path: Path) -> Path:
    venv.EnvBuilder(with_pip=True, clear=True).create(path)
    return _venv_python(path)


def _version_smoke_test(python: Path, artifact: Path, *, extras: bool = False) -> None:
    requirement = f"{artifact}[xlsx]" if extras else str(artifact)
    install_args = [str(python), "-m", "pip", "install", "--no-deps", requirement]
    if extras:
        install_args = [str(python), "-m", "pip", "install", requirement]
    _run(install_args)
    executable = python.parent / ("euer.exe" if os.name == "nt" else "euer")
    result = _run([str(executable), "--version"])
    if result.stdout.strip() != VERSION:
        raise ArtifactVerificationError(
            f"Versions-Smoke-Test liefert {result.stdout.strip()!r} statt {VERSION!r}."
        )
    _run(
        [
            str(python),
            "-c",
            "import importlib.metadata; print(importlib.metadata.version('euer'))",
        ]
    )


def run_installation_smoke_tests(wheel: Path, sdist: Path) -> None:
    """Installiert Wheel, sdist und das XLSX-Extra in frischen Umgebungen."""
    with tempfile.TemporaryDirectory(prefix="euer-artifacts-") as temporary:
        root = Path(temporary)
        wheel_python = _create_venv(root / "wheel")
        _version_smoke_test(wheel_python, wheel)

        sdist_python = _create_venv(root / "sdist")
        _version_smoke_test(sdist_python, sdist)

        xlsx_python = _create_venv(root / "xlsx")
        _version_smoke_test(xlsx_python, wheel, extras=True)
        database = root / "xlsx.db"
        output = root / "xlsx-output"
        _run([str(xlsx_python), "-m", "euercli", "--db", str(database), "init"])
        _run(
            [
                str(xlsx_python),
                "-m",
                "euercli",
                "--db",
                str(database),
                "export",
                "--format",
                "xlsx",
                "--output",
                str(output),
            ]
        )
        if not list(output.glob("*.xlsx")):
            raise ArtifactVerificationError("XLSX-Smoke-Test erzeugte keine XLSX-Datei.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path, nargs="?", default=Path("dist"))
    args = parser.parse_args()
    try:
        wheel, sdist = validate_artifact_metadata(args.dist)
        _run([sys.executable, "-m", "twine", "check", str(wheel), str(sdist)])
        run_installation_smoke_tests(wheel, sdist)
    except (ArtifactVerificationError, OSError) as exc:
        print(f"Artefaktprüfung fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    print(f"Artefaktprüfung erfolgreich: {wheel.name}, {sdist.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
