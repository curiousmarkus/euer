import sys
import tomllib
from pathlib import Path

from .constants import CONFIG_PATH, DEFAULT_USER
from .services.errors import ValidationError
from .services.models import LedgerAccount

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
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            for item in value:
                lines.append(f"[[{section}]]")
                for key, val in item.items():
                    lines.append(f"{key} = {toml_format_value(val)}")
                lines.append("")
        else:
            lines.append(f"{section} = {toml_format_value(value)}")
    return "\n".join(lines).rstrip() + "\n"


def save_config(config: dict) -> None:
    """Schreibt Config in den plattformabhängigen Config-Pfad."""
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


def prompt_text(label: str, default: str | None) -> str:
    """Fragt interaktiv einen Textwert ab."""
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


def prompt_list(label: str, defaults: list[str] | None) -> list[str]:
    """Fragt interaktiv eine kommaseparierte Liste ab."""
    default_str = ", ".join(defaults) if defaults else ""
    prompt = f"{label}"
    if default_str:
        prompt += f" [{default_str}]"
    prompt += ": "
    try:
        value = input(prompt).strip()
    except EOFError:
        return defaults or []
    if not value:
        return defaults or []
    return [item.strip() for item in value.split(",") if item.strip()]


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


def get_audit_user(config: dict) -> str:
    """Liest Audit-User aus der Config."""
    user = config.get("user", {}).get("name", "")
    if not user:
        return DEFAULT_USER
    return str(user)


def get_private_accounts(config: dict) -> list[str]:
    """Liest private Kontobezeichner aus der Config."""
    accounts = config.get("accounts", {}).get("private")
    if not accounts:
        return ["privat"]
    result: list[str] = []
    for item in accounts:
        text = str(item).strip()
        if text:
            result.append(text)
    return result or ["privat"]


def get_ledger_accounts(config: dict) -> list[LedgerAccount]:
    """Lädt den Kontenrahmen aus der Config."""
    raw_accounts = config.get("ledger_accounts")
    if not raw_accounts:
        return []
    if not isinstance(raw_accounts, list):
        raise ValidationError(
            "Ungültige Config: 'ledger_accounts' muss eine Liste von Tabellen sein.",
            code="invalid_ledger_accounts",
        )

    result: list[LedgerAccount] = []
    seen_keys: dict[str, int] = {}

    for index, entry in enumerate(raw_accounts, start=1):
        if not isinstance(entry, dict):
            raise ValidationError(
                f"Ungültiger Kontenrahmen-Eintrag #{index}: erwartete Tabelle.",
                code="invalid_ledger_account_entry",
                details={"index": index},
            )

        key = str(entry.get("key", "")).strip()
        name = str(entry.get("name", "")).strip()
        category = str(entry.get("category", "")).strip()
        account_number_value = entry.get("account_number")
        account_number = None
        if account_number_value is not None:
            account_number_text = str(account_number_value).strip()
            if account_number_text:
                account_number = account_number_text

        missing_fields = []
        if not key:
            missing_fields.append("key")
        if not name:
            missing_fields.append("name")
        if not category:
            missing_fields.append("category")
        if missing_fields:
            raise ValidationError(
                f"Ungültiger Kontenrahmen-Eintrag #{index}: fehlende Felder "
                f"{', '.join(missing_fields)}.",
                code="ledger_account_missing_fields",
                details={"index": index, "fields": missing_fields},
            )

        normalized_key = key.lower()
        if normalized_key in seen_keys:
            raise ValidationError(
                f"Doppelter Buchungskonto-Schlüssel '{key}' in der Config.",
                code="duplicate_ledger_account_key",
                details={"key": key, "first_index": seen_keys[normalized_key], "index": index},
            )
        seen_keys[normalized_key] = index

        result.append(
            LedgerAccount(
                key=key,
                name=name,
                category=category,
                account_number=account_number,
            )
        )

    return result


def resolve_receipt_path(
    receipt_name: str,
    date: str | None,  # YYYY-MM-DD
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
    year = date[:4] if date else None

    names = [receipt_name]
    if not Path(receipt_name).suffix:
        names.extend(
            [
                f"{receipt_name}.pdf",
                f"{receipt_name}.jpg",
                f"{receipt_name}.jpeg",
                f"{receipt_name}.png",
            ]
        )

    candidates: list[Path] = []
    for name in names:
        if year:
            candidates.append(base_path / year / name)
        candidates.append(base_path / name)

    for path in candidates:
        if path.exists():
            return (path, candidates)

    return (None, candidates)


def warn_missing_receipt(
    receipt_name: str | None,
    date: str | None,
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
