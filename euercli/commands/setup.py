import sys
from pathlib import Path

from ..config import (
    get_audit_user,
    get_export_dir,
    get_private_accounts,
    load_config,
    normalize_export_path,
    normalize_receipt_path,
    normalize_tax_mode,
    prompt_list,
    prompt_path,
    prompt_text,
    save_config,
)
from ..constants import CONFIG_PATH, DEFAULT_EXPORT_DIR


def _ordered_config(config: dict) -> dict:
    ordered = {}
    for section in ("receipts", "exports", "tax", "user", "accounts"):
        if section in config:
            ordered[section] = config[section]
    for key, value in config.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _normalize_setup_set_value(key: str, value: str):
    if key == "tax.mode":
        return normalize_tax_mode(value)
    if key in {"receipts.expenses", "receipts.income"}:
        return normalize_receipt_path(value)
    if key == "exports.directory":
        return normalize_export_path(value)
    if key == "accounts.private":
        accounts = [item.strip() for item in value.split(",") if item.strip()]
        if not accounts:
            raise ValueError("accounts.private darf nicht leer sein.")
        return accounts
    return value


def cmd_setup_set(key: str, value: str) -> None:
    """Setzt einen einzelnen Config-Wert ohne interaktiven Prompt."""
    if "." not in key:
        raise ValueError("Ungültiger Key. Verwende das Format section.key (z.B. tax.mode).")

    section, config_key = key.split(".", 1)
    if not section or not config_key:
        raise ValueError("Ungültiger Key. Verwende das Format section.key.")

    config = load_config()
    section_config = dict(config.get(section, {}))
    section_config[config_key] = _normalize_setup_set_value(key, value)
    config[section] = section_config

    save_config(_ordered_config(config))

    print(f"Konfiguration gespeichert: {CONFIG_PATH}")
    print(f"  {key} = {section_config[config_key]}")

    if key in {"receipts.expenses", "receipts.income", "exports.directory"}:
        path_value = section_config[config_key]
        if path_value and not Path(path_value).exists():
            print(f"! Hinweis: Pfad existiert nicht: {path_value}", file=sys.stderr)


def cmd_setup(args):
    """Interaktive Ersteinrichtung oder Setzen einzelner Config-Werte."""
    if args.set:
        key, value = args.set
        try:
            cmd_setup_set(key, value)
        except ValueError as exc:
            print(f"Fehler: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    print("Willkommen! Konfiguriere deine EÜR...")
    print()

    config = load_config()
    receipts_config = dict(config.get("receipts", {}))
    exports_config = dict(config.get("exports", {}))
    tax_config = dict(config.get("tax", {}))
    user_config = dict(config.get("user", {}))
    accounts_config = dict(config.get("accounts", {}))

    expenses_input = prompt_path(
        "Beleg-Pfad für Ausgaben", receipts_config.get("expenses")
    )
    income_input = prompt_path(
        "Beleg-Pfad für Einnahmen", receipts_config.get("income")
    )
    export_input = prompt_path(
        "Export-Verzeichnis",
        get_export_dir(config) or exports_config.get("directory") or str(DEFAULT_EXPORT_DIR),
    )
    try:
        default_tax_mode = normalize_tax_mode(str(tax_config.get("mode", "small_business")))
    except ValueError:
        default_tax_mode = "small_business"

    while True:
        tax_input = prompt_path(
            "Steuermodus (small_business|standard)",
            default_tax_mode,
        )
        try:
            tax_mode = normalize_tax_mode(tax_input, default_tax_mode)
            break
        except ValueError:
            print(
                "Ungültiger Steuermodus. Erlaubt: small_business oder standard.",
                file=sys.stderr,
            )

    audit_user_input = prompt_text(
        "Audit-User (Name für Änderungen)",
        get_audit_user(config),
    )

    existing_private = get_private_accounts(config)
    print()
    print("Private Konten (für Sacheinlagen/Privateinlagen):")
    print("  Ausgaben mit diesen Kontonamen werden automatisch als")
    print("  Privateinlage (Sacheinlage) erfasst.")
    print("  Mehrere Konten kommasepariert angeben.")
    private_accounts_input = prompt_list(
        "Private Konten",
        existing_private,
    )

    expenses_path = normalize_receipt_path(expenses_input)
    income_path = normalize_receipt_path(income_input)
    export_path = normalize_export_path(export_input)

    receipts_config["expenses"] = expenses_path
    receipts_config["income"] = income_path
    exports_config["directory"] = export_path
    tax_config["mode"] = tax_mode
    user_config["name"] = audit_user_input
    accounts_config["private"] = private_accounts_input or ["privat"]
    config["receipts"] = receipts_config
    config["exports"] = exports_config
    config["tax"] = tax_config
    config["user"] = user_config
    config["accounts"] = accounts_config

    save_config(_ordered_config(config))

    print()
    print(f"Konfiguration gespeichert: {CONFIG_PATH}")
    print()
    print("[receipts]")
    print(f"  expenses = {expenses_path or '(nicht gesetzt)'}")
    print(f"  income   = {income_path or '(nicht gesetzt)'}")
    print("[exports]")
    print(f"  directory = {export_path or '(nicht gesetzt)'}")
    print("[tax]")
    print(f"  mode = {tax_mode}")
    print("[user]")
    print(f"  name = {audit_user_input}")
    print("[accounts]")
    print(f"  private = {accounts_config.get('private', ['privat'])}")
    print()
    print("Hinweis: Ausgaben mit diesen Kontonamen (--account) werden")
    print("automatisch als Sacheinlage (Privateinlage) erkannt.")

    for path in (expenses_path, income_path, export_path):
        if path and not Path(path).exists():
            print(f"! Hinweis: Pfad existiert nicht: {path}", file=sys.stderr)
