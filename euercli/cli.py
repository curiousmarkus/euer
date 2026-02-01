import argparse

from .commands import (
    cmd_add_expense,
    cmd_add_income,
    cmd_audit,
    cmd_config_show,
    cmd_delete_expense,
    cmd_delete_income,
    cmd_export,
    cmd_import,
    cmd_incomplete_list,
    cmd_init,
    cmd_list_categories,
    cmd_list_expenses,
    cmd_list_income,
    cmd_receipt_check,
    cmd_receipt_open,
    cmd_setup,
    cmd_summary,
    cmd_update_expense,
    cmd_update_income,
)
from .constants import DEFAULT_DB_PATH, DEFAULT_EXPORT_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EÜR - Einnahmenüberschussrechnung CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"Pfad zur Datenbank (default: {DEFAULT_DB_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- init ---
    init_parser = subparsers.add_parser("init", help="Initialisiert die Datenbank")
    init_parser.set_defaults(func=cmd_init)

    # --- setup ---
    setup_parser = subparsers.add_parser("setup", help="Interaktive Ersteinrichtung")
    setup_parser.set_defaults(func=cmd_setup)

    # --- import ---
    import_parser = subparsers.add_parser("import", help="Bulk-Import von Transaktionen")
    import_parser.add_argument(
        "--file",
        required=True,
        help="Pfad zur Importdatei (csv|jsonl), '-' für stdin",
    )
    import_parser.add_argument(
        "--format", choices=["csv", "jsonl"], required=True, help="Importformat"
    )
    import_parser.add_argument(
        "--dry-run", action="store_true", help="Nur prüfen, nichts speichern"
    )
    import_parser.set_defaults(func=cmd_import)

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Fügt Transaktion hinzu")
    add_subparsers = add_parser.add_subparsers(dest="type", required=True)

    # add expense
    add_expense_parser = add_subparsers.add_parser("expense", help="Ausgabe hinzufügen")
    add_expense_parser.add_argument("--date", required=True, help="Datum (YYYY-MM-DD)")
    add_expense_parser.add_argument("--vendor", required=True, help="Lieferant/Zweck")
    add_expense_parser.add_argument("--category", required=True, help="Kategorie")
    add_expense_parser.add_argument(
        "--amount", required=True, type=float, help="Betrag in EUR"
    )
    add_expense_parser.add_argument("--account", help="Bankkonto")
    add_expense_parser.add_argument("--foreign", help="Fremdwährungsbetrag")
    add_expense_parser.add_argument("--receipt", help="Belegname")
    add_expense_parser.add_argument("--notes", help="Bemerkung")
    add_expense_parser.add_argument("--vat", type=float, help="USt-VA Betrag (manuell)")
    add_expense_parser.add_argument(
        "--rc",
        action="store_true",
        help="Reverse-Charge: berechnet 19%% USt automatisch",
    )
    add_expense_parser.set_defaults(func=cmd_add_expense)

    # add income
    add_income_parser = add_subparsers.add_parser("income", help="Einnahme hinzufügen")
    add_income_parser.add_argument("--date", required=True, help="Datum (YYYY-MM-DD)")
    add_income_parser.add_argument("--source", required=True, help="Quelle/Zweck")
    add_income_parser.add_argument("--category", required=True, help="Kategorie")
    add_income_parser.add_argument(
        "--amount", required=True, type=float, help="Betrag in EUR"
    )
    add_income_parser.add_argument("--foreign", help="Fremdwährungsbetrag")
    add_income_parser.add_argument("--receipt", help="Belegname")
    add_income_parser.add_argument("--notes", help="Bemerkung")
    add_income_parser.add_argument(
        "--vat", type=float, help="Umsatzsteuer-Betrag (für Regelb.)"
    )
    add_income_parser.set_defaults(func=cmd_add_income)

    # --- list ---
    list_parser = subparsers.add_parser("list", help="Listet Daten")
    list_subparsers = list_parser.add_subparsers(dest="type", required=True)

    # list expenses
    list_exp_parser = list_subparsers.add_parser("expenses", help="Ausgaben anzeigen")
    list_exp_parser.add_argument("--year", type=int, help="Jahr filtern")
    list_exp_parser.add_argument("--month", type=int, help="Monat filtern (1-12)")
    list_exp_parser.add_argument("--category", help="Kategorie filtern")
    list_exp_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_exp_parser.set_defaults(func=cmd_list_expenses)

    # list income
    list_inc_parser = list_subparsers.add_parser("income", help="Einnahmen anzeigen")
    list_inc_parser.add_argument("--year", type=int, help="Jahr filtern")
    list_inc_parser.add_argument("--month", type=int, help="Monat filtern (1-12)")
    list_inc_parser.add_argument("--category", help="Kategorie filtern")
    list_inc_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_inc_parser.set_defaults(func=cmd_list_income)

    # list categories
    list_cat_parser = list_subparsers.add_parser("categories", help="Kategorien anzeigen")
    list_cat_parser.add_argument(
        "--type", choices=["expense", "income"], help="Typ filtern"
    )
    list_cat_parser.set_defaults(func=cmd_list_categories)

    # --- update ---
    update_parser = subparsers.add_parser("update", help="Aktualisiert Transaktion")
    update_subparsers = update_parser.add_subparsers(dest="type", required=True)

    # update expense
    upd_exp_parser = update_subparsers.add_parser("expense", help="Ausgabe aktualisieren")
    upd_exp_parser.add_argument("id", type=int, help="ID der Ausgabe")
    upd_exp_parser.add_argument("--date", help="Neues Datum")
    upd_exp_parser.add_argument("--vendor", help="Neuer Lieferant")
    upd_exp_parser.add_argument("--category", help="Neue Kategorie")
    upd_exp_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_exp_parser.add_argument("--account", help="Neues Konto")
    upd_exp_parser.add_argument("--foreign", help="Neuer Fremdwährungsbetrag")
    upd_exp_parser.add_argument("--receipt", help="Neuer Belegname")
    upd_exp_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_exp_parser.add_argument("--vat", type=float, help="Neuer USt-VA Betrag")
    upd_exp_parser.add_argument(
        "--rc",
        action="store_true",
        help="Reverse-Charge: setzt Flag und berechnet ggf. 19%% USt",
    )
    upd_exp_parser.set_defaults(func=cmd_update_expense)

    # update income
    upd_inc_parser = update_subparsers.add_parser("income", help="Einnahme aktualisieren")
    upd_inc_parser.add_argument("id", type=int, help="ID der Einnahme")
    upd_inc_parser.add_argument("--date", help="Neues Datum")
    upd_inc_parser.add_argument("--source", help="Neue Quelle")
    upd_inc_parser.add_argument("--category", help="Neue Kategorie")
    upd_inc_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_inc_parser.add_argument("--foreign", help="Neuer Fremdwährungsbetrag")
    upd_inc_parser.add_argument("--receipt", help="Neuer Belegname")
    upd_inc_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_inc_parser.set_defaults(func=cmd_update_income)

    # --- delete ---
    delete_parser = subparsers.add_parser("delete", help="Löscht Transaktion")
    delete_subparsers = delete_parser.add_subparsers(dest="type", required=True)

    # delete expense
    del_exp_parser = delete_subparsers.add_parser("expense", help="Ausgabe löschen")
    del_exp_parser.add_argument("id", type=int, help="ID der Ausgabe")
    del_exp_parser.add_argument("--force", action="store_true", help="Keine Rückfrage")
    del_exp_parser.set_defaults(func=cmd_delete_expense)

    # delete income
    del_inc_parser = delete_subparsers.add_parser("income", help="Einnahme löschen")
    del_inc_parser.add_argument("id", type=int, help="ID der Einnahme")
    del_inc_parser.add_argument("--force", action="store_true", help="Keine Rückfrage")
    del_inc_parser.set_defaults(func=cmd_delete_income)

    # --- export ---
    export_parser = subparsers.add_parser("export", help="Exportiert Daten")
    export_parser.add_argument("--year", type=int, help="Jahr (default: aktuelles)")
    export_parser.add_argument("--format", choices=["csv", "xlsx"], default="xlsx")
    export_parser.add_argument(
        "--output",
        default=None,
        help=(
            "Ausgabeverzeichnis (default: exports.directory aus Config oder "
            f"{DEFAULT_EXPORT_DIR})"
        ),
    )
    export_parser.set_defaults(func=cmd_export)

    # --- summary ---
    summary_parser = subparsers.add_parser("summary", help="Zeigt Zusammenfassung")
    summary_parser.add_argument("--year", type=int, help="Jahr (default: aktuelles)")
    summary_parser.set_defaults(func=cmd_summary)

    # --- audit ---
    audit_parser = subparsers.add_parser("audit", help="Zeigt Änderungshistorie")
    audit_parser.add_argument("id", type=int, help="Datensatz-ID")
    audit_parser.add_argument(
        "--table",
        choices=["expenses", "income"],
        default="expenses",
        help="Tabelle (default: expenses)",
    )
    audit_parser.set_defaults(func=cmd_audit)

    # --- config ---
    config_parser = subparsers.add_parser("config", help="Konfiguration verwalten")
    config_subparsers = config_parser.add_subparsers(dest="action", required=True)

    # config show
    config_show_parser = config_subparsers.add_parser(
        "show", help="Zeigt aktuelle Konfiguration"
    )
    config_show_parser.set_defaults(func=cmd_config_show)

    # --- receipt ---
    receipt_parser = subparsers.add_parser("receipt", help="Beleg-Verwaltung")
    receipt_subparsers = receipt_parser.add_subparsers(dest="action", required=True)

    # receipt check
    receipt_check_parser = receipt_subparsers.add_parser(
        "check", help="Prüft Transaktionen auf fehlende Belege"
    )
    receipt_check_parser.add_argument(
        "--year", type=int, help="Jahr (default: aktuelles)"
    )
    receipt_check_parser.add_argument(
        "--type", choices=["expense", "income"], help="Nur diesen Typ prüfen"
    )
    receipt_check_parser.set_defaults(func=cmd_receipt_check)

    # receipt open
    receipt_open_parser = receipt_subparsers.add_parser(
        "open", help="Öffnet Beleg einer Transaktion"
    )
    receipt_open_parser.add_argument("id", type=int, help="Transaktions-ID")
    receipt_open_parser.add_argument(
        "--table",
        choices=["expenses", "income"],
        default="expenses",
        help="Tabelle (default: expenses)",
    )
    receipt_open_parser.set_defaults(func=cmd_receipt_open)

    # --- incomplete ---
    incomplete_parser = subparsers.add_parser(
        "incomplete", help="Unvollständige Import-Einträge"
    )
    incomplete_subparsers = incomplete_parser.add_subparsers(dest="action", required=True)
    incomplete_list_parser = incomplete_subparsers.add_parser(
        "list", help="Listet unvollständige Einträge"
    )
    incomplete_list_parser.add_argument(
        "--type", choices=["expense", "income", "unknown"], help="Typ filtern"
    )
    incomplete_list_parser.add_argument("--year", type=int, help="Jahr filtern")
    incomplete_list_parser.add_argument(
        "--format", choices=["table", "csv"], default="table"
    )
    incomplete_list_parser.set_defaults(func=cmd_incomplete_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
