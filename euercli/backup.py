"""Automatischer Backup-Service für SQLite-Datenbanken (Spec 016 §1.1, Spec 020 §4)."""

import hashlib
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .constants import get_config_path


def get_backup_dir(config: Optional[dict] = None) -> Path:
    """Ermittelt das Verzeichnis für Datenbank-Backups."""
    if config:
        cfg_dir = config.get("backups", {}).get("directory")
        if cfg_dir:
            p = Path(cfg_dir)
            p.mkdir(parents=True, exist_ok=True)
            return p
    default_dir = get_config_path().parent / "backups"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


def rotate_backups(backup_dir: Path, max_keep: int = 10, prefix: str = "euer") -> list[Path]:
    """Behält die neuesten `max_keep` Backups und löscht ältere."""
    if not backup_dir.exists():
        return []
    pattern = f"{prefix}_*.db"
    backups = [p for p in backup_dir.glob(pattern) if p.is_file()]
    # Sortierung nach Änderungszeit absteigend (neueste zuerst)
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    removed = []
    if len(backups) > max_keep:
        for p in backups[max_keep:]:
            try:
                p.unlink()
                removed.append(p)
            except OSError:
                pass
    return removed


def create_database_backup(
    db_source: Path | sqlite3.Connection,
    backup_dir: Optional[Path] = None,
    prefix: str = "euer",
    max_keep: int = 10,
) -> Path:
    """Erstellt ein konsistentes SQLite-Backup über die Online Backup API (inkl. WAL).

    Args:
        db_source: Pfad zur Quelldatenbank oder bestehende sqlite3.Connection
        backup_dir: Zielordner (default: ~/.config/euer/backups)
        prefix: Dateinamens-Präfix
        max_keep: Maximale Anzahl aufzubewahrender Backups

    Returns:
        Absoluter Pfad der erstellten Sicherungsdatei.
    """
    target_dir = backup_dir if backup_dir is not None else get_backup_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_filename = f"{prefix}_{timestamp}.db"
    backup_path = target_dir / backup_filename

    counter = 1
    while backup_path.exists():
        backup_path = target_dir / f"{prefix}_{timestamp}_{counter}.db"
        counter += 1

    close_source = False
    if isinstance(db_source, (str, Path)):
        src_path = Path(db_source)
        if not src_path.exists():
            raise FileNotFoundError(f"Datenbankdatei nicht gefunden: {src_path}")
        src_conn = sqlite3.connect(src_path)
        close_source = True
    elif isinstance(db_source, sqlite3.Connection):
        src_conn = db_source
    else:
        raise TypeError("db_source muss ein Path oder sqlite3.Connection sein")

    # Keep an incomplete backup hidden until the SQLite backup has completed.
    temporary_path = target_dir / f".{backup_filename}.partial.{uuid.uuid4().hex}"
    try:
        fd = os.open(temporary_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        dest_conn = sqlite3.connect(temporary_path)
        try:
            with dest_conn:
                src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
        while True:
            try:
                os.link(temporary_path, backup_path)
                break
            except FileExistsError:
                backup_path = target_dir / f"{prefix}_{timestamp}_{counter}.db"
                counter += 1
    finally:
        temporary_path.unlink(missing_ok=True)
        if close_source:
            src_conn.close()

    rotate_backups(target_dir, max_keep=max_keep, prefix=prefix)
    return backup_path.resolve()


def ensure_daily_backup(db_path: Path) -> Path | None:
    """Create one pre-mutation snapshot per database and calendar day."""
    if not db_path.is_file():
        return None
    backup_dir = get_backup_dir()
    db_key = hashlib.sha256(str(db_path.resolve()).encode()).hexdigest()[:12]
    prefix = f"euer_daily_{db_key}"
    today = datetime.now().strftime("%Y-%m-%d")
    existing = sorted(backup_dir.glob(f"{prefix}_{today}_*.db"))
    if existing:
        return existing[-1]
    return create_database_backup(db_path, backup_dir=backup_dir, prefix=prefix)
