"""Version und Bestätigung des mit dem Paket ausgelieferten Buchhaltungs-Skills."""

import re
import tomllib
from pathlib import Path

from .config import load_config

VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def bundle_path() -> Path:
    """Liefert den Skill der aktiven Installation (im Checkout die kanonische Quelle)."""
    package_bundle = Path(__file__).resolve().parent / "assets" / "skill"
    if package_bundle.is_dir():
        return package_bundle.resolve()
    source_bundle = Path(__file__).resolve().parent.parent / "docs" / "skills" / "euer-buchhaltung"
    if source_bundle.is_dir():
        return source_bundle.resolve()
    return package_bundle.resolve()


def expected_version() -> str:
    """Liest die einzige Versionsquelle aus dem YAML-Header ohne YAML-Abhängigkeit."""
    path = bundle_path() / "SKILL.md"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Skill-Bundle nicht lesbar: {path}: {exc}") from exc
    header = content.split("---", 2)
    if len(header) < 3 or header[0].strip():
        raise ValueError(f"Ungültiger Skill-Header: {path}")
    match = re.search(
        r'^metadata:\s*\n(?:[ \t]+[^\n]*\n)*?[ \t]+version:\s*["\']([^"\']+)["\']\s*$',
        header[1],
        re.M,
    )
    if not match or not VERSION_PATTERN.fullmatch(match.group(1)):
        raise ValueError(f"Ungültige Skill-Version im Bundle: {path}")
    return match.group(1)


def skill_status() -> dict[str, str | None]:
    """Prüft Bundle und Selbstauskunft; Dateifehler bleiben als Fehler erkennbar."""
    result: dict[str, str | None] = {
        "confirmed_version": None,
        "expected_version": None,
        "bundle_path": str(bundle_path()),
        "status": None,
    }
    try:
        result["expected_version"] = expected_version()
        config = load_config()
        section = config.get("skill", {})
        if not isinstance(section, dict):
            result["status"] = "invalid"
            return result
        confirmed = section.get("version")
        if confirmed is None:
            result["status"] = "unconfirmed"
        elif not isinstance(confirmed, str) or not VERSION_PATTERN.fullmatch(confirmed):
            result["confirmed_version"] = str(confirmed)
            result["status"] = "invalid"
        else:
            result["confirmed_version"] = confirmed
            result["status"] = "current" if confirmed == result["expected_version"] else "mismatch"
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        result["status"] = "error"
        result["error"] = str(exc)
    return result
