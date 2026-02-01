import sys
import tomllib
from pathlib import Path

from .constants import CONFIG_PATH

VALID_TAX_MODES = {"small_business", "standard"}


def load_config() -> dict:
    """Lädt Config, gibt leeres Dict zurück wenn nicht vorhanden."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def toml_escape(value: str) -> str:
    """Escaped String für TOML."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def toml_format_value(value: object) -> str:
    """Formatiert einfache TOML-Werte."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value}"
    if isinstance(value, str):
        return f"\"{toml_escape(value)}\""
    if isinstance(value, list):
        inner = ", ".join(toml_format_value(v) for v in value)
        return f"[{inner}]"
    return f"\"{toml_escape(str(value))}\""


def dump_toml(config: dict) -> str:
    """Erzeugt TOML aus einer flachen Config-Struktur."""
    lines = []
    for section, value in config.items():
        if isinstance(value, dict):
            lines.append(f"[{section}]")
            for key, val in value.items():
                lines.append(f"{key} = {toml_format_value(val)}")
            lines.append("")
        else:
            lines.append(f"{section} = {toml_format_value(value)}")
    return "\n".join(lines).rstrip() + "\n"


def save_config(config: dict) -> None:
    """Schreibt Config nach ~/.config/euer/config.toml."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(dump_toml(config))


def prompt_path(label: str, default: str | None) -> str:
    """Fragt interaktiv einen Pfad ab."""
    prompt = f"{label}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    try:
        value = input(prompt).strip()
    except EOFError:
        if default is not None:
            return default
        return ""
    if not value and default is not None:
        return default
    return value


def normalize_receipt_path(value: str) -> str:
    """Normalisiert Pfad-Eingaben."""
    if not value:
        return ""
    cleaned = value
    if (
        (cleaned.startswith('"') and cleaned.endswith('"'))
        or (cleaned.startswith("'") and cleaned.endswith("'"))
    ):
        cleaned = cleaned[1:-1]
    return str(Path(cleaned).expanduser())


def normalize_export_path(value: str) -> str:
    """Normalisiert Export-Pfad-Eingaben."""
    return normalize_receipt_path(value)


def normalize_tax_mode(value: str, default: str = "small_business") -> str:
    """Normalisiert den Steuermodus für die Config."""
    cleaned = value.strip().lower()
    if not cleaned:
        return default

    aliases = {
        "small-business": "small_business",
        "kleinunternehmer": "small_business",
        "kleinunternehmerregelung": "small_business",
        "regelbesteuerung": "standard",
    }
    normalized = aliases.get(cleaned, cleaned)
    if normalized in VALID_TAX_MODES:
        return normalized

    raise ValueError(f"Ungültiger Steuermodus: {value}")


def get_export_dir(config: dict) -> str:
    """Liest Export-Verzeichnis aus der Config."""
    return config.get("exports", {}).get("directory", "")


def resolve_receipt_path(
    receipt_name: str,
    date: str,  # YYYY-MM-DD
    receipt_type: str,  # 'expenses' oder 'income'
    config: dict,
) -> tuple[Path | None, list[Path]]:
    """
    Sucht Beleg-Datei.

    Returns:
        (found_path, checked_paths)
        found_path ist None wenn nicht gefunden
    """
    base = config.get("receipts", {}).get(receipt_type, "")
    if not base:
        return (None, [])

    base_path = Path(base)
    year = date[:4]  # "2026" aus "2026-01-15"

    # Reihenfolge: Erst Jahres-Ordner, dann Basis
    candidates = [
        base_path / year / receipt_name,
        base_path / receipt_name,
    ]

    for path in candidates:
        if path.exists():
            return (path, candidates)

    return (None, candidates)


def warn_missing_receipt(
    receipt_name: str | None,
    date: str,
    receipt_type: str,  # 'expenses' oder 'income'
    config: dict,
) -> None:
    """Gibt Warnung aus wenn Beleg nicht gefunden wird."""
    if not receipt_name:
        return

    found_path, checked_paths = resolve_receipt_path(
        receipt_name, date, receipt_type, config
    )

    if found_path is None and checked_paths:
        print(f"! Beleg '{receipt_name}' nicht gefunden:", file=sys.stderr)
        for p in checked_paths:
            print(f"  - {p}", file=sys.stderr)
