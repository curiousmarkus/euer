import argparse
import importlib.metadata
import sys

# Copyright (C) 2026 EÜR Contributors
# Licensed under GNU AGPLv3

from .commands import (
    cmd_add_expense,
    cmd_add_income,
    cmd_add_private_deposit,
    cmd_add_private_withdrawal,
    cmd_audit,
    cmd_config_show,
    cmd_delete_expense,
    cmd_delete_income,
    cmd_delete_private_transfer,
    cmd_export,
    cmd_import,
    cmd_incomplete_list,
    cmd_init,
    cmd_list_categories,
    cmd_list_expenses,
    cmd_list_income,
    cmd_list_private_deposits,
    cmd_list_private_transfers,
    cmd_list_private_withdrawals,
    cmd_private_summary,
    cmd_query,
    cmd_reconcile_private,
    cmd_receipt_check,
    cmd_receipt_open,
    cmd_setup,
    cmd_summary,
    cmd_update_expense,
    cmd_update_income,
    cmd_update_private_transfer,
)
from .constants import DEFAULT_DB_PATH, DEFAULT_EXPORT_DIR


def load_plugins(subparsers: argparse._SubParsersAction) -> None:
    # Requires Python 3.11+
    entry_points = importlib.metadata.entry_points(group="euer.commands")

    for entry_point in entry_points:
        try:
            plugin = entry_point.load()
            if callable(plugin):
                plugin(subparsers)
            elif hasattr(plugin, "setup") and callable(plugin.setup):
                plugin.setup(subparsers)
            else:
                raise TypeError("Entry point provides neither callable nor setup()")
        except Exception as exc:
            print(
                f"Warnung: Plugin '{entry_point.name}' konnte nicht geladen werden: {exc}",
                file=sys.stderr,
            )


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
    setup_parser = subparsers.add_parser(
        "setup", help="Ersteinrichtung (interaktiv oder --set KEY VALUE)"
    )
    setup_parser.add_argument(
        "--set",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Setzt einen Config-Wert direkt (z.B. tax.mode small_business)",
    )
    setup_parser.set_defaults(func=cmd_setup)

    # --- import ---
    import_parser = subparsers.add_parser(
        "import",
        help="Bulk-Import von Transaktionen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Tipp: euer import --schema",
    )
    import_parser.add_argument(
        "--file",
        help="Pfad zur Importdatei (csv|jsonl), '-' für stdin",
    )
    import_parser.add_argument(
        "--format", choices=["csv", "jsonl"], help="Importformat"
    )
    import_parser.add_argument(
        "--dry-run", action="store_true", help="Nur prüfen, nichts speichern"
    )
    import_parser.add_argument(
        "--schema",
        action="store_true",
        help="Zeigt Import-Schema, Beispiele und Alias-Keys",
    )
    import_parser.set_defaults(func=cmd_import)

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Fügt Transaktion hinzu")
    add_subparsers = add_parser.add_subparsers(dest="type", required=True)

    # add expense
    add_expense_parser = add_subparsers.add_parser("expense", help="Ausgabe hinzufügen")
    add_expense_parser.add_argument(
        "--payment-date",
        "--date",
        dest="payment_date",
        help="Wertstellungsdatum (YYYY-MM-DD)",
    )
    add_expense_parser.add_argument(
        "--invoice-date",
        help="Rechnungsdatum (YYYY-MM-DD)",
    )
    add_expense_parser.add_argument("--vendor", required=True, help="Lieferant/Zweck")
    add_expense_parser.add_argument("--category", help="Kategorie")
    add_expense_parser.add_argument(
        "--amount", required=True, type=float, help="Betrag in EUR"
    )
    add_expense_parser.add_argument("--account", help="Bankkonto")
    add_expense_parser.add_argument("--foreign", help="Fremdwährungsbetrag")
    add_expense_parser.add_argument("--receipt", help="Belegname")
    add_expense_parser.add_argument("--notes", help="Bemerkung")
    add_expense_parser.add_argument("--vat", type=float, help="USt-VA Betrag (manuell)")
    add_expense_parser.add_argument(
        "--private-paid",
        action="store_true",
        help="Markiert Ausgabe als privat bezahlt (Sacheinlage)",
    )
    add_expense_parser.add_argument(
        "--rc",
        action="store_true",
        help="Reverse-Charge: berechnet 19%% USt automatisch",
    )
    add_expense_parser.set_defaults(func=cmd_add_expense)

    # add income
    add_income_parser = add_subparsers.add_parser("income", help="Einnahme hinzufügen")
    add_income_parser.add_argument(
        "--payment-date",
        "--date",
        dest="payment_date",
        help="Wertstellungsdatum (YYYY-MM-DD)",
    )
    add_income_parser.add_argument(
        "--invoice-date",
        help="Rechnungsdatum (YYYY-MM-DD)",
    )
    add_income_parser.add_argument("--source", required=True, help="Quelle/Zweck")
    add_income_parser.add_argument("--category", help="Kategorie")
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

    # add private-deposit
    add_private_deposit_parser = add_subparsers.add_parser(
        "private-deposit", help="Privateinlage hinzufügen"
    )
    add_private_deposit_parser.add_argument("--date", required=True, help="Datum (YYYY-MM-DD)")
    add_private_deposit_parser.add_argument(
        "--amount", required=True, type=float, help="Betrag in EUR (positiv)"
    )
    add_private_deposit_parser.add_argument(
        "--description", required=True, help="Beschreibung"
    )
    add_private_deposit_parser.add_argument("--notes", help="Bemerkung")
    add_private_deposit_parser.add_argument(
        "--related-expense-id",
        type=int,
        help="Optionale Referenz auf Ausgabe-ID",
    )
    add_private_deposit_parser.set_defaults(func=cmd_add_private_deposit)

    # add private-withdrawal
    add_private_withdrawal_parser = add_subparsers.add_parser(
        "private-withdrawal", help="Privatentnahme hinzufügen"
    )
    add_private_withdrawal_parser.add_argument(
        "--date", required=True, help="Datum (YYYY-MM-DD)"
    )
    add_private_withdrawal_parser.add_argument(
        "--amount", required=True, type=float, help="Betrag in EUR (positiv)"
    )
    add_private_withdrawal_parser.add_argument(
        "--description", required=True, help="Beschreibung"
    )
    add_private_withdrawal_parser.add_argument("--notes", help="Bemerkung")
    add_private_withdrawal_parser.add_argument(
        "--related-expense-id",
        type=int,
        help="Optionale Referenz auf Ausgabe-ID",
    )
    add_private_withdrawal_parser.set_defaults(func=cmd_add_private_withdrawal)

    # --- list ---
    list_parser = subparsers.add_parser("list", help="Listet Daten")
    list_subparsers = list_parser.add_subparsers(dest="type", required=True)

    # list expenses
    list_exp_parser = list_subparsers.add_parser("expenses", help="Ausgaben anzeigen")
    list_exp_parser.add_argument(
        "--year",
        type=int,
        help="Jahr filtern (default: aktuelles)",
    )
    list_exp_parser.add_argument("--month", type=int, help="Monat filtern (1-12)")
    list_exp_parser.add_argument("--category", help="Kategorie filtern")
    list_exp_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_exp_parser.set_defaults(func=cmd_list_expenses)

    # list income
    list_inc_parser = list_subparsers.add_parser("income", help="Einnahmen anzeigen")
    list_inc_parser.add_argument(
        "--year",
        type=int,
        help="Jahr filtern (default: aktuelles)",
    )
    list_inc_parser.add_argument("--month", type=int, help="Monat filtern (1-12)")
    list_inc_parser.add_argument("--category", help="Kategorie filtern")
    list_inc_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_inc_parser.set_defaults(func=cmd_list_income)

    # list categories
    list_cat_parser = list_subparsers.add_parser(
        "categories", help="Kategorien anzeigen"
    )
    list_cat_parser.add_argument(
        "--type", choices=["expense", "income"], help="Typ filtern"
    )
    list_cat_parser.set_defaults(func=cmd_list_categories)

    # list private-deposits
    list_private_dep_parser = list_subparsers.add_parser(
        "private-deposits", help="Privateinlagen anzeigen"
    )
    list_private_dep_parser.add_argument("--year", type=int, help="Jahr filtern")
    list_private_dep_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_private_dep_parser.set_defaults(func=cmd_list_private_deposits)

    # list private-withdrawals
    list_private_wdr_parser = list_subparsers.add_parser(
        "private-withdrawals", help="Privatentnahmen anzeigen"
    )
    list_private_wdr_parser.add_argument("--year", type=int, help="Jahr filtern")
    list_private_wdr_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_private_wdr_parser.set_defaults(func=cmd_list_private_withdrawals)

    # list private-transfers
    list_private_all_parser = list_subparsers.add_parser(
        "private-transfers", help="Privateinlagen und Privatentnahmen anzeigen"
    )
    list_private_all_parser.add_argument("--year", type=int, help="Jahr filtern")
    list_private_all_parser.add_argument("--format", choices=["table", "csv"], default="table")
    list_private_all_parser.set_defaults(func=cmd_list_private_transfers)

    # --- update ---
    update_parser = subparsers.add_parser("update", help="Aktualisiert Transaktion")
    update_subparsers = update_parser.add_subparsers(dest="type", required=True)

    # update expense
    upd_exp_parser = update_subparsers.add_parser(
        "expense", help="Ausgabe aktualisieren"
    )
    upd_exp_parser.add_argument("id", type=int, help="ID der Ausgabe")
    upd_exp_parser.add_argument(
        "--payment-date",
        "--date",
        dest="payment_date",
        help="Neues Wertstellungsdatum",
    )
    upd_exp_parser.add_argument("--invoice-date", help="Neues Rechnungsdatum")
    upd_exp_parser.add_argument("--vendor", help="Neuer Lieferant")
    upd_exp_parser.add_argument("--category", help="Neue Kategorie")
    upd_exp_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_exp_parser.add_argument("--account", help="Neues Konto")
    upd_exp_parser.add_argument("--foreign", help="Neuer Fremdwährungsbetrag")
    upd_exp_parser.add_argument("--receipt", help="Neuer Belegname")
    upd_exp_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_exp_parser.add_argument("--vat", type=float, help="Neuer USt-VA Betrag")
    upd_private_paid_group = upd_exp_parser.add_mutually_exclusive_group()
    upd_private_paid_group.add_argument(
        "--private-paid",
        dest="private_paid",
        action="store_const",
        const=True,
        help="Markiert Ausgabe als privat bezahlt (Sacheinlage)",
    )
    upd_private_paid_group.add_argument(
        "--no-private-paid",
        dest="private_paid",
        action="store_const",
        const=False,
        help="Entfernt Markierung als privat bezahlt",
    )
    upd_exp_parser.set_defaults(private_paid=None)
    upd_exp_parser.add_argument(
        "--rc",
        action="store_true",
        help="Reverse-Charge: setzt Flag und berechnet ggf. 19%% USt",
    )
    upd_exp_parser.set_defaults(func=cmd_update_expense)

    # update income
    upd_inc_parser = update_subparsers.add_parser(
        "income", help="Einnahme aktualisieren"
    )
    upd_inc_parser.add_argument("id", type=int, help="ID der Einnahme")
    upd_inc_parser.add_argument(
        "--payment-date",
        "--date",
        dest="payment_date",
        help="Neues Wertstellungsdatum",
    )
    upd_inc_parser.add_argument("--invoice-date", help="Neues Rechnungsdatum")
    upd_inc_parser.add_argument("--source", help="Neue Quelle")
    upd_inc_parser.add_argument("--category", help="Neue Kategorie")
    upd_inc_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_inc_parser.add_argument("--foreign", help="Neuer Fremdwährungsbetrag")
    upd_inc_parser.add_argument("--receipt", help="Neuer Belegname")
    upd_inc_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_inc_parser.add_argument("--vat", type=float, help="Neue Umsatzsteuer")
    upd_inc_parser.set_defaults(func=cmd_update_income)

    # update private-transfer
    upd_private_parser = update_subparsers.add_parser(
        "private-transfer", help="Privatvorgang aktualisieren"
    )
    upd_private_parser.add_argument("id", type=int, help="ID des Privatvorgangs")
    upd_private_parser.add_argument("--date", help="Neues Datum")
    upd_private_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_private_parser.add_argument("--description", help="Neue Beschreibung")
    upd_private_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_private_related_group = upd_private_parser.add_mutually_exclusive_group()
    upd_private_related_group.add_argument(
        "--related-expense-id",
        type=int,
        help="Optionale Referenz auf Ausgabe-ID",
    )
    upd_private_related_group.add_argument(
        "--clear-related-expense",
        action="store_true",
        help="Entfernt die Referenz auf eine Ausgabe",
    )
    upd_private_parser.set_defaults(clear_related_expense=False)
    upd_private_parser.set_defaults(func=cmd_update_private_transfer)

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

    # delete private-transfer
    del_private_parser = delete_subparsers.add_parser(
        "private-transfer", help="Privatvorgang löschen"
    )
    del_private_parser.add_argument("id", type=int, help="ID des Privatvorgangs")
    del_private_parser.add_argument(
        "--force", action="store_true", help="Keine Rückfrage"
    )
    del_private_parser.set_defaults(func=cmd_delete_private_transfer)

    # --- export ---
    export_parser = subparsers.add_parser("export", help="Exportiert Daten")
    export_parser.add_argument(
        "--year",
        type=int,
        help="Jahr filtern (ohne Angabe: alle Jahre exportieren)",
    )
    export_parser.add_argument("--format", choices=["csv", "xlsx"], default="csv")
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
    summary_parser.add_argument(
        "--include-private",
        action="store_true",
        help="Zeigt zusätzlich Privateinlagen und Privatentnahmen",
    )
    summary_parser.set_defaults(func=cmd_summary)

    # --- private-summary ---
    private_summary_parser = subparsers.add_parser(
        "private-summary", help="Zeigt ELSTER-Summen für Privatvorgänge"
    )
    private_summary_parser.add_argument(
        "--year", type=int, required=True, help="Jahr"
    )
    private_summary_parser.set_defaults(func=cmd_private_summary)

    # --- reconcile ---
    reconcile_parser = subparsers.add_parser(
        "reconcile",
        help="Abgleich/Fix für persistierte Daten",
    )
    reconcile_subparsers = reconcile_parser.add_subparsers(dest="type", required=True)

    reconcile_private_parser = reconcile_subparsers.add_parser(
        "private",
        help="Reklassifiziert Sacheinlagen anhand aktueller Config",
    )
    reconcile_private_parser.add_argument(
        "--year",
        type=int,
        help="Optionales Jahr (ohne Angabe: alle Jahre)",
    )
    reconcile_private_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur geplante Änderungen anzeigen",
    )
    reconcile_private_parser.set_defaults(func=cmd_reconcile_private)

    # --- query ---
    query_parser = subparsers.add_parser(
        "query",
        help="Führt eine SQL-SELECT-Query aus (nur lesend)",
    )
    query_parser.add_argument(
        "sql",
        nargs=argparse.REMAINDER,
        help="SQL-Query (nur SELECT, bitte in Anführungszeichen)",
    )
    query_parser.set_defaults(func=cmd_query)

    # --- audit ---
    audit_parser = subparsers.add_parser("audit", help="Zeigt Änderungshistorie")
    audit_parser.add_argument("id", type=int, help="Datensatz-ID")
    audit_parser.add_argument(
        "--table",
        choices=["expenses", "income", "private_transfers"],
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
        "incomplete", help="Unvollständige Buchungen"
    )
    incomplete_subparsers = incomplete_parser.add_subparsers(
        dest="action", required=True
    )
    incomplete_list_parser = incomplete_subparsers.add_parser(
        "list", help="Listet unvollständige Einträge"
    )
    incomplete_list_parser.add_argument(
        "--type", choices=["expense", "income"], help="Typ filtern"
    )
    incomplete_list_parser.add_argument("--year", type=int, help="Jahr filtern")
    incomplete_list_parser.add_argument(
        "--format", choices=["table", "csv"], default="table"
    )
    incomplete_list_parser.set_defaults(func=cmd_incomplete_list)

    load_plugins(subparsers)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
