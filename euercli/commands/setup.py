import sys
from pathlib import Path

from ..config import (
    get_audit_user,
    get_export_dir,
    load_config,
    normalize_export_path,
    normalize_receipt_path,
    normalize_tax_mode,
    prompt_path,
    prompt_text,
    save_config,
)
from ..constants import CONFIG_PATH, DEFAULT_EXPORT_DIR


def cmd_setup(args):
    """Interaktive Ersteinrichtung."""
    print("Willkommen! Konfiguriere deine EÜR...")
    print()

    config = load_config()
    receipts_config = dict(config.get("receipts", {}))
    exports_config = dict(config.get("exports", {}))
    tax_config = dict(config.get("tax", {}))
    user_config = dict(config.get("user", {}))

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
    audit_user_input = prompt_text(
        "Audit-User (Name für Änderungen)",
        get_audit_user(config),
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

    expenses_path = normalize_receipt_path(expenses_input)
    income_path = normalize_receipt_path(income_input)
    export_path = normalize_export_path(export_input)

    receipts_config["expenses"] = expenses_path
    receipts_config["income"] = income_path
    exports_config["directory"] = export_path
    tax_config["mode"] = tax_mode
    user_config["name"] = audit_user_input
    config["receipts"] = receipts_config
    config["exports"] = exports_config
    config["tax"] = tax_config
    config["user"] = user_config

    ordered_config = {
        "receipts": receipts_config,
        "exports": exports_config,
        "tax": tax_config,
        "user": user_config,
    }
    for key, value in config.items():
        if key not in ("receipts", "exports", "tax", "user"):
            ordered_config[key] = value

    save_config(ordered_config)

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

    for path in (expenses_path, income_path, export_path):
        if path and not Path(path).exists():
            print(f"! Hinweis: Pfad existiert nicht: {path}", file=sys.stderr)
