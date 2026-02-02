from ..config import get_audit_user, get_export_dir, load_config
from ..constants import CONFIG_PATH


def cmd_config_show(args):
    """Zeigt aktuelle Konfiguration."""
    print("EÜR Konfiguration")
    print("=================")
    print()
    print(f"Config-Datei: {CONFIG_PATH}", end="")

    if not CONFIG_PATH.exists():
        print(" (nicht vorhanden)")
        print()
        print("Erstelle Config mit:")
        print()
        print("  euer setup")
        print("  # oder")
        print("  python -m euercli setup")
        print()
        print("Oder manuell:")
        print()
        print("  mkdir -p ~/.config/euer")
        print("  cat > ~/.config/euer/config.toml << 'EOF'")
        print("  [receipts]")
        print('  expenses = "/pfad/zu/ausgaben-belege"')
        print('  income = "/pfad/zu/einnahmen-belege"')
        print("  [exports]")
        print('  directory = "/pfad/zu/exports"')
        print("  [user]")
        print('  name = "Dein Name"')
        print("  [tax]")
        print('  mode = "small_business"')
        print("  EOF")
        return

    print()
    print()

    config = load_config()
    receipts = config.get("receipts", {})

    print("[receipts]")
    expenses_path = receipts.get("expenses", "")
    income_path = receipts.get("income", "")
    print(f"  expenses = {expenses_path or '(nicht gesetzt)'}")
    print(f"  income   = {income_path or '(nicht gesetzt)'}")

    export_dir = get_export_dir(config)
    print("[exports]")
    print(f"  directory = {export_dir or '(nicht gesetzt)'}")
    tax_mode = config.get("tax", {}).get("mode", "small_business")
    print("[tax]")
    print(f"  mode = {tax_mode}")
    audit_user = get_audit_user(config)
    print("[user]")
    print(f"  name = {audit_user}")
