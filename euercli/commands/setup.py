import sys
from pathlib import Path

from ..config import (
    get_audit_user,
    get_export_dir,
    get_ledger_accounts,
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
from ..db import get_db_connection
from ..services.categories import get_category_list
from ..services.errors import ValidationError


def _ordered_config(config: dict) -> dict:
    ordered = {}
    for section in ("receipts", "exports", "tax", "user", "accounts", "ledger_accounts"):
        if section in config:
            ordered[section] = config[section]
    for key, value in config.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _prompt_yes_no(label: str, default: bool = False) -> bool:
    suffix = "J/n" if default else "j/N"
    try:
        value = input(f"{label} [{suffix}]: ").strip().lower()
    except EOFError:
        return default
    if not value:
        return default
    return value in {"j", "ja", "y", "yes"}


def _prompt_ledger_accounts(db_path: str) -> list[dict]:
    conn = get_db_connection(Path(db_path))
    categories = get_category_list(conn)
    conn.close()

    result: list[dict] = []
    while True:
        key = prompt_text("Konto-Schlüssel", None).strip()
        if not key:
            print("Schlüssel darf nicht leer sein.", file=sys.stderr)
            continue
        if any(entry["key"].lower() == key.lower() for entry in result):
            print(f"Schlüssel '{key}' ist bereits vergeben.", file=sys.stderr)
            continue

        name = prompt_text("Anzeigename", None).strip()
        if not name:
            print("Name darf nicht leer sein.", file=sys.stderr)
            continue

        print("Kategorie wählen:")
        for index, category in enumerate(categories, start=1):
            type_label = "Ausgabe" if category.type == "expense" else "Einnahme"
            eur_line = str(category.eur_line) if category.eur_line else "-"
            print(f"  {index}. {category.name} (Zeile {eur_line}, {type_label})")

        selected_category = None
        while selected_category is None:
            selection = prompt_text("Kategorie-Nummer", None).strip()
            if not selection.isdigit():
                print("Bitte eine gültige Nummer eingeben.", file=sys.stderr)
                continue
            category_index = int(selection)
            if category_index < 1 or category_index > len(categories):
                print("Bitte eine gültige Nummer eingeben.", file=sys.stderr)
                continue
            selected_category = categories[category_index - 1]

        account_number = prompt_text("SKR-Nummer (optional)", None).strip()
        entry = {
            "key": key,
            "name": name,
            "category": selected_category.name,
        }
        if account_number:
            entry["account_number"] = account_number
        result.append(entry)

        if not _prompt_yes_no("Weiteres Konto?", default=False):
            return result


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
    try:
        existing_ledger_accounts = get_ledger_accounts(config)
    except ValidationError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)
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
    print()

    ledger_accounts_config = config.get("ledger_accounts", [])
    wants_ledger_accounts = _prompt_yes_no(
        "Möchtest du Buchungskonten konfigurieren?",
        default=False,
    )
    if wants_ledger_accounts:
        ledger_accounts_config = _prompt_ledger_accounts(args.db)

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
    if ledger_accounts_config:
        config["ledger_accounts"] = ledger_accounts_config
    elif "ledger_accounts" in config:
        del config["ledger_accounts"]

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
    if ledger_accounts_config:
        print("[ledger_accounts]")
        print(f"  {len(ledger_accounts_config)} Konto/Konten konfiguriert")
    print()
    print("Hinweis: Ausgaben mit diesen Kontonamen (--account) werden")
    print("automatisch als Sacheinlage (Privateinlage) erkannt.")

    for path in (expenses_path, income_path, export_path):
        if path and not Path(path).exists():
            print(f"! Hinweis: Pfad existiert nicht: {path}", file=sys.stderr)
