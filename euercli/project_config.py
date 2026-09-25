"""Projektbezogene Bindung an eine SQLite-Datenbank."""

import os
import tomllib
import uuid
from pathlib import Path

from .config import dump_toml

PROJECT_CONFIG_RELATIVE_PATH = Path(".euer") / "config.toml"


def project_config_path(project_root: Path) -> Path:
    return project_root / PROJECT_CONFIG_RELATIVE_PATH


def _read_project_config(project_root: Path) -> dict:
    path = project_config_path(project_root)
    if not path.exists():
        return {}
    with path.open("rb") as file:
        data = tomllib.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Ungültige Projekt-Config: {path}")
    return data


def get_project_db_path(project_root: Path) -> Path | None:
    """Liest den DB-Pfad; relative Pfade beziehen sich auf den Projektordner."""
    data = _read_project_config(project_root)
    if not data:
        return None
    database = data.get("database")
    if not isinstance(database, dict):
        raise ValueError(
            f"Ungültige Projekt-Config: [database] fehlt in {project_config_path(project_root)}"
        )
    value = database.get("path")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Ungültige Projekt-Config: database.path fehlt in {project_config_path(project_root)}"
        )
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def save_project_db_path(project_root: Path, db_path: Path) -> Path:
    """Speichert die Bindung atomar, ohne andere Projekt-Config-Werte zu entfernen."""
    data = _read_project_config(project_root)
    database = data.get("database", {})
    if not isinstance(database, dict):
        raise ValueError("Ungültige Projekt-Config: [database] muss ein Abschnitt sein.")
    resolved_root = project_root.resolve()
    resolved_db = db_path.resolve()
    try:
        stored_path = str(resolved_db.relative_to(resolved_root))
    except ValueError:
        stored_path = str(resolved_db)
    database["path"] = stored_path
    data["database"] = database

    config_path = project_config_path(project_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = config_path.with_name(f".{config_path.name}.tmp.{uuid.uuid4().hex}")
    try:
        fd = os.open(temporary_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(dump_toml(data))
        os.replace(temporary_path, config_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return config_path
