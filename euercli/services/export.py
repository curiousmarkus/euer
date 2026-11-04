"""Service-Layer für versionierte Exporte mit Manifest (Spec 021)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
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
    ts_str = now.strftime("%Y%m%dT%H%M%S%z")
    return f"export_{year_str}_{ts_str}_v{version}"


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
    except Exception as exc:
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

    for item in files_list:
        if not isinstance(item, dict):
            errors.append(f"Ungültiger Eintrag in Dateiliste: {item!r}")
            continue

        rel_path = item.get("relative_path")
        if not rel_path or not isinstance(rel_path, str):
            errors.append("Dateieintrag ohne relativen Pfad.")
            continue

        file_path = base_dir / rel_path
        if not file_path.exists():
            errors.append(f"Exportdatei fehlt: {rel_path}")
            continue

        content_bytes = file_path.read_bytes()
        expected_size = item.get("size_bytes")
        if expected_size is not None and len(content_bytes) != expected_size:
            errors.append(
                f"Dateigröße weicht ab für {rel_path}: erwartet {expected_size} Bytes, "
                f"gefunden {len(content_bytes)} Bytes"
            )

        expected_hash = item.get("sha256")
        actual_hash = hashlib.sha256(content_bytes).hexdigest()
        if expected_hash and actual_hash != expected_hash:
            errors.append(
                f"SHA-256 Prüfsumme weicht ab für {rel_path}: erwartet {expected_hash}, "
                f"berechnet {actual_hash}"
            )

        expected_lines = item.get("line_count")
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
