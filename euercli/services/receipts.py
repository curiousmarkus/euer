"""Lesender Abgleich von Belegdateien mit aktiven Buchungen."""

import os
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..config import get_receipt_config, resolve_receipt_path
from ..db import get_db_connection
from .errors import ValidationError

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"})
BOOKING_TYPES = {"expense": "expenses", "income": "income"}


@dataclass(frozen=True)
class ReceiptFile:
    type: str
    path: str
    receipt_name: str
    size_bytes: int
    modified_at: str


@dataclass(frozen=True)
class SkippedEntry:
    type: str
    path: str
    reason: str


@dataclass(frozen=True)
class ScanWarning:
    code: str
    message: str
    type: str
    record_id: int
    path: str | None


@dataclass(frozen=True)
class ScanError:
    code: str
    message: str
    type: str | None = None
    path: str | None = None


@dataclass
class UnbookedResult:
    year: int
    types: list[str]
    root: str | None = None
    scan_complete: bool = False
    total_files: int | None = None
    referenced_files: int | None = None
    unbooked_count: int | None = None
    skipped_count: int = 0
    unbooked_files: list[ReceiptFile] = field(default_factory=list)
    skipped_entries: list[SkippedEntry] = field(default_factory=list)
    warnings: list[ScanWarning] = field(default_factory=list)
    errors: list[ScanError] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Gibt den stabilen JSON-Vertrag zurück."""
        return asdict(self)


def _ignored(name: str) -> bool:
    lower = name.lower()
    return (
        name.startswith(".")
        or name.startswith("~$")
        or lower in {"thumbs.db", "desktop.ini"}
        or lower.endswith(".tmp")
    )


def _scan_directory(
    directory: Path,
    root: Path,
    type_dir: Path,
    booking_type: str,
    files: dict[Path, ReceiptFile],
    result: UnbookedResult,
) -> None:
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                try:
                    if entry.is_symlink():
                        reason = "symlink"
                    elif _ignored(entry.name):
                        reason = "ignored_name"
                    elif entry.is_dir(follow_symlinks=False):
                        _scan_directory(path, root, type_dir, booking_type, files, result)
                        continue
                    elif not entry.is_file(follow_symlinks=False):
                        reason = "non_regular_file"
                    elif path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                        reason = "unsupported_extension"
                    else:
                        stat = entry.stat(follow_symlinks=False)
                        files[path] = ReceiptFile(
                            type=booking_type,
                            path=relative,
                            receipt_name=path.relative_to(type_dir).as_posix(),
                            size_bytes=stat.st_size,
                            modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                            .isoformat(timespec="seconds")
                            .replace("+00:00", "Z"),
                        )
                        continue
                    result.skipped_entries.append(SkippedEntry(booking_type, relative, reason))
                except OSError as exc:
                    result.errors.append(
                        ScanError("scan_io_error", str(exc), booking_type, relative)
                    )
    except OSError as exc:
        result.errors.append(
            ScanError(
                "scan_io_error", str(exc), booking_type, directory.relative_to(root).as_posix()
            )
        )


def find_unbooked_receipts(
    db_path: Path, config: dict, year: int, booking_type: str | None = None
) -> UnbookedResult:
    """Scannt das Zahlungsjahr und gleicht aufgelöste Pfade mit aktiven Buchungen ab."""
    if not 1 <= year <= 9999:
        raise ValidationError("Das Jahr muss zwischen 1 und 9999 liegen.")
    if booking_type is not None and booking_type not in BOOKING_TYPES:
        raise ValidationError("Ungültiger Belegtyp.")
    types = [booking_type] if booking_type else list(BOOKING_TYPES)
    result = UnbookedResult(year=year, types=types)
    try:
        receipt_config = get_receipt_config(config)
        if not receipt_config.root:
            raise ValidationError("Kein Beleg-Root konfiguriert.")
        root = Path(receipt_config.root).expanduser().resolve()
        result.root = str(root)
        if not root.is_dir():
            code = "directory_missing" if not root.exists() else "not_a_directory"
            result.errors.append(
                ScanError(code, f"Beleg-Root nicht als Ordner verfügbar: {root}", path=str(root))
            )
            _sort_diagnostics(result)
            result.skipped_count = len(result.skipped_entries)
            return result
        year_dir = root / receipt_config.year_dir.format(year=year)
        directories = {}
        for kind in types:
            name = receipt_config.expenses_dir if kind == "expense" else receipt_config.income_dir
            directory = year_dir / name
            # Die Konfiguration darf den Scan nicht aus dem Root herausführen.
            if not directory.absolute().is_relative_to(root) or any(
                part == ".." for part in Path(receipt_config.year_dir.format(year=year), name).parts
            ):
                raise ValidationError("Belegordner liegt außerhalb des Beleg-Root.")
            directories[kind] = directory
    except (ValidationError, OSError, ValueError, TypeError, AttributeError) as exc:
        result.errors.append(ScanError("invalid_config", str(exc)))
        _sort_diagnostics(result)
        result.skipped_count = len(result.skipped_entries)
        return result

    files: dict[str, dict[Path, ReceiptFile]] = {kind: {} for kind in types}
    for kind, directory in directories.items():
        relative = directory.relative_to(root).as_posix()
        if any(
            part.is_symlink()
            for part in (directory, *directory.parents)
            if part != root and part.is_relative_to(root)
        ):
            result.errors.append(
                ScanError("not_a_directory", "Typordner ist ein Symlink.", kind, relative)
            )
        elif not directory.exists():
            result.errors.append(
                ScanError("directory_missing", "Belegordner fehlt.", kind, relative)
            )
        elif not directory.is_dir():
            result.errors.append(
                ScanError("not_a_directory", "Belegpfad ist kein Ordner.", kind, relative)
            )
        else:
            _scan_directory(directory, root, directory, kind, files[kind], result)

    if result.errors:
        _sort_diagnostics(result)
        result.skipped_count = len(result.skipped_entries)
        return result

    if not db_path.is_file():
        result.errors.append(ScanError("database_error", f"Datenbank fehlt: {db_path}"))
        _sort_diagnostics(result)
        result.skipped_count = len(result.skipped_entries)
        return result

    case_map: dict[str, dict[str, list[Path]]] = {kind: {} for kind in types}
    for kind in types:
        for p in files[kind]:
            rel_lower = p.relative_to(root).as_posix().lower()
            case_map[kind].setdefault(rel_lower, []).append(p)

    referenced: dict[str, set[Path]] = {kind: set() for kind in types}
    try:
        with closing(get_db_connection(db_path, read_only=True)) as conn:
            for kind in types:
                table = BOOKING_TYPES[kind]
                rows = conn.execute(
                    f"SELECT id, payment_date, receipt_name FROM {table} "
                    "WHERE deleted_at IS NULL AND receipt_name IS NOT NULL "
                    "AND TRIM(receipt_name) <> '' "
                    "AND (payment_date IS NULL OR payment_date = '' OR "
                    "SUBSTR(payment_date, 1, 4) = ?)",
                    (f"{year:04d}",),
                ).fetchall()
                for row in rows:
                    name = row["receipt_name"]
                    parts = Path(name).parts
                    invalid = (
                        Path(name).is_absolute()
                        or name.startswith(("/", "\\"))
                        or (len(name) > 1 and name[1] == ":")
                        or ".." in parts
                        or "\\" in name
                    )
                    if invalid:
                        result.warnings.append(
                            ScanWarning(
                                "invalid_receipt_reference",
                                "Unsichere Belegreferenz.",
                                kind,
                                row["id"],
                                name,
                            )
                        )
                        continue
                    found, _ = resolve_receipt_path(
                        name,
                        row["payment_date"],
                        table,
                        config,
                        fallback_year=year,
                    )
                    if found is None:
                        continue
                    # Ein Symlink im Pfad darf auch bei einer gültigen Referenz
                    # nicht nachträglich eine Scan-Datei zuordnen.
                    if any(
                        part.is_symlink()
                        for part in (found, *found.parents)
                        if part != Path(receipt_config.root)
                        and part.is_relative_to(Path(receipt_config.root))
                    ):
                        result.warnings.append(
                            ScanWarning(
                                "invalid_receipt_reference",
                                "Belegreferenz führt über einen Symlink.",
                                kind,
                                row["id"],
                                name,
                            )
                        )
                        continue
                    normalized_found = found.resolve()
                    target_path: Path | None = None
                    if normalized_found in files[kind]:
                        target_path = normalized_found
                    else:
                        try:
                            rel_lower = normalized_found.relative_to(root).as_posix().lower()
                            for cand in case_map[kind].get(rel_lower, []):
                                if cand.samefile(normalized_found):
                                    target_path = cand
                                    break
                        except (ValueError, OSError):
                            pass

                    if target_path is not None:
                        referenced[kind].add(target_path)
                        if not row["payment_date"]:
                            result.warnings.append(
                                ScanWarning(
                                    "missing_payment_date",
                                    "Zahlungsjahr vorläufig: Wertstellungsdatum fehlt.",
                                    kind,
                                    row["id"],
                                    files[kind][target_path].path,
                                )
                            )
    except (sqlite3.Error, OSError, ValidationError) as exc:
        result.errors.append(ScanError("database_error", str(exc)))
        _sort_diagnostics(result)
        result.skipped_count = len(result.skipped_entries)
        return result

    result.total_files = sum(len(items) for items in files.values())
    result.referenced_files = sum(len(items) for items in referenced.values())
    result.unbooked_files = sorted(
        (
            item
            for kind in types
            for path, item in files[kind].items()
            if path not in referenced[kind]
        ),
        key=lambda item: (item.type, item.path),
    )
    result.unbooked_count = len(result.unbooked_files)
    result.scan_complete = True
    result.skipped_count = len(result.skipped_entries)
    _sort_diagnostics(result)
    return result


def _sort_diagnostics(result: UnbookedResult) -> None:
    result.skipped_entries.sort(key=lambda item: (item.type, item.path, item.reason))
    result.warnings.sort(key=lambda item: (item.type, item.path or "", item.record_id, item.code))
    result.errors.sort(key=lambda item: (item.type or "", item.path or "", item.code))
