"""Service-Layer für versionierte Exporte mit Manifest (Spec 021)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

MANIFEST_VERSION = "1.0"


def compute_db_snapshot_hash(conn: sqlite3.Connection) -> str:
    """Erstellt ein konsistentes SQLite-Backup und liefert dessen SHA-256-Prüfsumme.

    Dadurch wird auch bei aktivem WAL-Journal der exakte, transaktionale DB-Snapshot
    erfasst, anstatt nur die unvollständige Hauptdatei auf dem Dateisystem zu hashen.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
    try:
        dest_conn = sqlite3.connect(tmp_path)
        try:
            conn.backup(dest_conn)
        finally:
            dest_conn.close()
        return hashlib.sha256(tmp_path.read_bytes()).hexdigest()
    finally:
        tmp_path.unlink(missing_ok=True)


def compute_file_metadata(file_path: Path) -> dict[str, Any]:
    """Ermittelt Bytegröße, SHA-256 und ggf. Zeilenzahl einer Exportdatei."""
    content_bytes = file_path.read_bytes()
    meta: dict[str, Any] = {
        "relative_path": file_path.name,
        "size_bytes": len(content_bytes),
        "sha256": hashlib.sha256(content_bytes).hexdigest(),
    }
    # Zeilenzahl nur angeben, wenn sie eindeutig definiert ist (CSV-Textdateien)
    if file_path.suffix.lower() == ".csv":
        text = content_bytes.decode("utf-8-sig", errors="replace")
        meta["line_count"] = len(text.splitlines())
    return meta


def create_manifest(
    *,
    euer_version: str,
    created_at: str,
    report_year: int | None,
    tax_mode: str,
    export_format: str,
    db_snapshot_hash: str,
    files_metadata: list[dict[str, Any]],
) -> dict[str, Any]:
    """Baut die Manifest-Struktur für einen versionierten Exportlauf auf."""
    return {
        "manifest_version": MANIFEST_VERSION,
        "program": "euer",
        "euer_version": euer_version,
        "created_at": created_at,
        "report_year": report_year,
        "tax_mode": tax_mode,
        "parameters": {
            "format": export_format,
            "year": report_year,
            "versioned": True,
        },
        "database": {
            "snapshot_sha256": db_snapshot_hash,
        },
        "files": files_metadata,
    }


def format_versioned_dir_name(year: int | None, now: datetime, version: str) -> str:
    """Erzeugt einen eindeutigen, dateisystem-kompatiblen Ordnernamen."""
    year_str = str(year) if year is not None else "all"
    ts_str = now.strftime("%Y%m%dT%H%M%S%f%z")
    return f"export_{year_str}_{ts_str}_v{version}"


def publish_export(staging_dir: Path, target_dir: Path) -> None:
    """Verschiebt den Lauf atomar, ohne auch ein leeres Ziel zu ersetzen.

    Fehlt die Dateisystem-Unterstützung, wird sicher abgebrochen.
    """
    if sys.platform == "win32":
        os.rename(staging_dir, target_dir)  # Windows ersetzt bestehende Ziele niemals.
        return

    import ctypes
    import errno

    libc = ctypes.CDLL(None, use_errno=True)
    source, target = os.fsencode(staging_dir), os.fsencode(target_dir)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        rename = libc.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        arguments = (source, target, 0x00000004)  # RENAME_EXCL
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        rename = libc.renameat2
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        arguments = (-100, source, -100, target, 1)  # AT_FDCWD, RENAME_NOREPLACE
    else:
        raise OSError(errno.ENOTSUP, "Atomarer Export ohne Überschreiben nicht unterstützt")
    rename.restype = ctypes.c_int
    if rename(*arguments) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(target_dir))


def verify_manifest(target_path: Path) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Prüft einen versionierten Exportlauf anhand seines Manifests.

    Liefert (is_valid, errors, manifest_data).
    """
    if target_path.is_dir():
        manifest_path = target_path / "manifest.json"
    else:
        manifest_path = target_path

    if not manifest_path.exists():
        return False, [f"Manifestdatei nicht gefunden: {manifest_path}"], None

    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(manifest_text)
    except (OSError, UnicodeError, ValueError) as exc:
        return False, [f"Manifest konnte nicht gelesen werden: {exc}"], None

    if not isinstance(manifest, dict):
        return False, ["Ungültiges Manifest-Format: JSON-Objekt erwartet."], None

    version = manifest.get("manifest_version")
    if str(version) != MANIFEST_VERSION:
        return (
            False,
            [f"Nicht unterstützte Manifest-Version: {version!r} (erwartet {MANIFEST_VERSION!r})"],
            manifest,
        )

    files_list = manifest.get("files")
    if not isinstance(files_list, list) or not files_list:
        return False, ["Manifest enthält keine gültige Dateiliste."], manifest

    base_dir = manifest_path.parent
    errors: list[str] = []
    seen_paths: set[str] = set()

    for item in files_list:
        if not isinstance(item, dict):
            errors.append(f"Ungültiger Eintrag in Dateiliste: {item!r}")
            continue

        rel_path = item.get("relative_path")
        if not rel_path or not isinstance(rel_path, str):
            errors.append("Dateieintrag ohne relativen Pfad.")
            continue

        relative = Path(rel_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in rel_path:
            errors.append(f"Ungültiger relativer Dateipfad: {rel_path}")
            continue
        if rel_path in seen_paths:
            errors.append(f"Doppelter Dateieintrag: {rel_path}")
            continue
        seen_paths.add(rel_path)

        expected_size = item.get("size_bytes")
        expected_hash = item.get("sha256")
        if type(expected_size) is not int or expected_size < 0:
            errors.append(f"Ungültige oder fehlende Bytegröße für {rel_path}")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            errors.append(f"Ungültige oder fehlende SHA-256-Prüfsumme für {rel_path}")
        expected_lines = item.get("line_count")
        if "line_count" in item and (
            relative.suffix.lower() != ".csv"
            or type(expected_lines) is not int
            or expected_lines < 0
        ):
            errors.append(f"Ungültige Zeilenzahl für {rel_path}")

        file_path = base_dir / relative
        try:
            if not file_path.resolve().is_relative_to(base_dir.resolve()):
                errors.append(f"Dateipfad außerhalb des Exportordners: {rel_path}")
                continue
            content_bytes = file_path.read_bytes()
        except FileNotFoundError:
            errors.append(f"Exportdatei fehlt: {rel_path}")
            continue
        except (OSError, ValueError, RuntimeError) as exc:
            errors.append(f"Exportdatei nicht lesbar: {rel_path}: {exc}")
            continue

        if expected_size is not None and len(content_bytes) != expected_size:
            errors.append(
                f"Dateigröße weicht ab für {rel_path}: erwartet {expected_size} Bytes, "
                f"gefunden {len(content_bytes)} Bytes"
            )

        actual_hash = hashlib.sha256(content_bytes).hexdigest()
        if expected_hash and actual_hash != expected_hash:
            errors.append(
                f"SHA-256 Prüfsumme weicht ab für {rel_path}: erwartet {expected_hash}, "
                f"berechnet {actual_hash}"
            )

        if expected_lines is not None:
            text = content_bytes.decode("utf-8-sig", errors="replace")
            actual_lines = len(text.splitlines())
            if actual_lines != expected_lines:
                errors.append(
                    f"Zeilenzahl weicht ab für {rel_path}: erwartet {expected_lines}, "
                    f"gefunden {actual_lines}"
                )

    is_valid = len(errors) == 0
    return is_valid, errors, manifest
