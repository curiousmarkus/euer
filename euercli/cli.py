import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Copyright (C) 2026 EÜR Contributors
# Licensed under GNU AGPLv3
from . import VERSION
from .backup import ensure_daily_backup
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
    cmd_doctor,
    cmd_export,
    cmd_import,
    cmd_incomplete_list,
    cmd_init,
    cmd_list_categories,
    cmd_list_expenses,
    cmd_list_income,
    cmd_list_ledger_accounts,
    cmd_list_private_deposits,
    cmd_list_private_transfers,
    cmd_list_private_withdrawals,
    cmd_private_summary,
    cmd_query,
    cmd_receipt_check,
    cmd_receipt_open,
    cmd_receipt_unbooked,
    cmd_reconcile_private,
    cmd_restore,
    cmd_setup,
    cmd_summary,
    cmd_trash_empty,
    cmd_trash_list,
    cmd_undo,
    cmd_update_expense,
    cmd_update_income,
    cmd_update_private_transfer,
    cmd_vat_report,
)
from .constants import DEFAULT_DB_PATH, DEFAULT_EXPORT_DIR
from .project_config import get_project_db_path, project_config_path
from .skill import skill_status


def _receipt_year(value: str) -> int:
    try:
        year = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Jahr muss eine Zahl zwischen 1 und 9999 sein") from exc
    if not 1 <= year <= 9999:
        raise argparse.ArgumentTypeError("Jahr muss zwischen 1 und 9999 liegen")
    return year


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

    if not any(entry_point.name == "datev" for entry_point in entry_points):
        binary = shutil.which("euer-datev")
        if binary:
            external = subparsers.add_parser(
                "datev", help="DATEV-Export und Kanzlei-Werkzeuge (euer-datev)", add_help=False
            )
            external.set_defaults(external_binary=binary)


def _datev_position(argv: list[str]) -> int | None:
    """Findet den ersten Core-Unterbefehl, ohne Plugin-Optionen zu parsen."""
    index = 0
    while index < len(argv):
        value = argv[index]
        if value in {"--db", "--config"}:
            index += 2
        elif value.startswith(("--db=", "--config=")) or value == "--ignore-skill-version":
            index += 1
        elif value.startswith("-"):
            return None
        else:
            return index if value == "datev" else None
    return None


def _datev_db_option(argv: list[str]) -> str | None:
    """Liest nur die explizite DB-Option des externen DATEV-Befehls."""
    for index, value in enumerate(argv):
        if value == "--db" and index + 1 < len(argv):
            return argv[index + 1]
        if value.startswith("--db="):
            return value.partition("=")[2]
    return None


def _run_external_datev(binary: str, arguments: list[str]) -> None:
    if sys.platform == "win32":
        raise SystemExit(subprocess.call([binary, *arguments]))
    os.execv(binary, [binary, *arguments])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EÜR - Einnahmenüberschussrechnung CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=VERSION,
        help="Zeigt die installierte Version an",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=f"Pfad zur Datenbank (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument("--config", default=None, help="Alternative Config für DATEV-Befehle")
    parser.add_argument(
        "--ignore-skill-version",
        action="store_true",
        help="Umgeht die Skill-Versionssperre für diesen Aufruf",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- init ---
    init_parser = subparsers.add_parser(
        "init", help="Initialisiert oder aktualisiert die Datenbank"
    )
    init_parser.add_argument(
        "--create",
        action="store_true",
        help="Erlaubt die Neuanlage einer Datenbank an einem explizit angegebenen Pfad",
    )
    init_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Führt Migrationen nur zur Probe aus und zeigt den Plan an, ohne Daten zu verändern",
    )
    init_parser.add_argument(
        "--json",
        action="store_true",
        help="Gibt den Migrationsbericht oder Dry-Run als JSON aus",
    )
    init_parser.add_argument(
        "--save-db-path",
        action="store_true",
        help="Speichert den mit --db gewählten Pfad dauerhaft in der Projekt-Config",
    )
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
    import_parser.add_argument("--format", choices=["csv", "jsonl"], help="Importformat")
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
        "--ledger-account",
        help="Buchungskonto aus dem Kontenrahmen (setzt Kategorie automatisch)",
    )
    add_expense_parser.add_argument("--amount", required=True, type=float, help="Betrag in EUR")
    add_expense_parser.add_argument("--account", help="Bankkonto")
    add_expense_parser.add_argument("--foreign", help="Fremdwährungsbetrag")
    add_expense_parser.add_argument("--receipt", help="Belegname")
    add_expense_parser.add_argument("--invoice-number", help="Rechnungsnummer")
    add_expense_parser.add_argument("--notes", help="Bemerkung")
    add_expense_parser.add_argument(
        "--vat",
        type=float,
        help="Belegter abziehbarer Vorsteuerbetrag in EUR (bei Bewirtung ausdrücklich geprüft)",
    )
    add_expense_parser.add_argument(
        "--vat-rate",
        type=float,
        choices=[0.0, 7.0, 19.0],
        help="Vorsteuer-Steuersatz (0, 7, 19)",
    )
    add_expense_parser.add_argument(
        "--tip",
        dest="entertainment_tip_eur",
        type=float,
        help="Im Zahlbetrag enthaltenes freiwilliges Trinkgeld (nur Bewirtung)",
    )
    add_expense_parser.add_argument(
        "--entertainment-vat-status",
        choices=["deductible", "no_deduction", "needs_review"],
        help="Vorsteuerstatus bzw. Prüfbedarf der Bewirtung",
    )
    add_expense_parser.add_argument(
        "--private-paid",
        action="store_true",
        help="Markiert Ausgabe als privat bezahlt (Sacheinlage)",
    )
    add_expense_parser.add_argument(
        "--rc",
        choices=["eu", "third-country"],
        metavar="{eu,third-country}",
        help="Reverse-Charge mit Jurisdiktion: eu oder third-country",
    )
    add_expense_parser.add_argument(
        "--force",
        action="store_true",
        help="Erzwingt Buchung trotz Schwellenwert-Überschreitung oder möglicher Duplikate",
    )
    add_expense_parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Erlaubt mögliches Duplikat trotz Ähnlichkeit",
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
        "--ledger-account",
        help="Buchungskonto aus dem Kontenrahmen (setzt Kategorie automatisch)",
    )
    add_income_parser.add_argument("--amount", required=True, type=float, help="Betrag in EUR")
    add_income_parser.add_argument("--foreign", help="Fremdwährungsbetrag")
    add_income_parser.add_argument("--receipt", help="Belegname")
    add_income_parser.add_argument("--invoice-number", help="Rechnungsnummer")
    add_income_parser.add_argument("--notes", help="Bemerkung")
    add_income_parser.add_argument("--vat", type=float, help="Umsatzsteuer-Betrag (für Regelb.)")
    add_income_parser.add_argument(
        "--vat-rate",
        type=float,
        choices=[0.0, 7.0, 19.0],
        help="USt-Satz für Ausgangsumsätze (0, 7, 19)",
    )
    add_income_parser.add_argument(
        "--tax-free",
        action="store_true",
        help="Steuerfreie Einnahme ohne Vorsteuerabzug (§19/steuerfrei)",
    )
    add_income_parser.add_argument(
        "--force",
        action="store_true",
        help="Erzwingt Buchung trotz Schwellenwert-Überschreitung oder möglicher Duplikate",
    )
    add_income_parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Erlaubt mögliches Duplikat trotz Ähnlichkeit",
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
    add_private_deposit_parser.add_argument("--description", required=True, help="Beschreibung")
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
    add_private_withdrawal_parser.add_argument("--date", required=True, help="Datum (YYYY-MM-DD)")
    add_private_withdrawal_parser.add_argument(
        "--amount", required=True, type=float, help="Betrag in EUR (positiv)"
    )
    add_private_withdrawal_parser.add_argument("--description", required=True, help="Beschreibung")
    add_private_withdrawal_parser.add_argument("--notes", help="Bemerkung")
    add_private_withdrawal_parser.add_argument(
        "--related-expense-id",
        type=int,
        help="Optionale Referenz auf Ausgabe-ID",
    )
    add_private_withdrawal_parser.set_defaults(func=cmd_add_private_withdrawal)

    # --- list ---
    list_parser = subparsers.add_parser("list", help="Listet Daten")
    list_parser.add_argument(
        "--trash", action="store_true", help="Gelöschte Einträge (Papierkorb) anzeigen"
    )
    list_subparsers = list_parser.add_subparsers(dest="type", required=False)
    list_parser.set_defaults(
        func=lambda args: (
            cmd_trash_list(args)
            if getattr(args, "trash", False)
            else (list_parser.print_help(), sys.exit(1))
        )
    )

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
    list_exp_parser.add_argument(
        "--full",
        action="store_true",
        help="Tabellenansicht mit zusätzlichen Spalten (Konto, Beleg, Fremdwährung, Notiz)",
    )
    list_exp_parser.add_argument(
        "--trash",
        action="store_true",
        help="Nur gelöschte Ausgaben anzeigen",
    )
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
    list_inc_parser.add_argument(
        "--full",
        action="store_true",
        help="Tabellenansicht mit zusätzlicher Spalte (Notiz)",
    )
    list_inc_parser.add_argument(
        "--trash",
        action="store_true",
        help="Nur gelöschte Einnahmen anzeigen",
    )
    list_inc_parser.set_defaults(func=cmd_list_income)

    # list categories
    list_cat_parser = list_subparsers.add_parser("categories", help="Kategorien anzeigen")
    list_cat_parser.add_argument("--type", choices=["expense", "income"], help="Typ filtern")
    list_cat_parser.add_argument("--year", type=int, help="Geprüftes Formularjahr anzeigen")
    list_cat_parser.set_defaults(func=cmd_list_categories)

    list_ledger_parser = list_subparsers.add_parser("ledger-accounts", help="Kontenrahmen anzeigen")
    list_ledger_parser.add_argument("--category", help="Kategorie filtern")
    list_ledger_parser.set_defaults(func=cmd_list_ledger_accounts)

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
    upd_exp_parser = update_subparsers.add_parser("expense", help="Ausgabe aktualisieren")
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
    upd_exp_parser.add_argument(
        "--ledger-account",
        help="Neues Buchungskonto aus dem Kontenrahmen",
    )
    upd_exp_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_exp_parser.add_argument("--account", help="Neues Konto")
    upd_exp_parser.add_argument("--foreign", help="Neuer Fremdwährungsbetrag")
    upd_exp_parser.add_argument("--receipt", help="Neuer Belegname")
    upd_exp_parser.add_argument(
        "--invoice-number", help="Neue Rechnungsnummer (leer zum Entfernen)"
    )
    upd_exp_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_exp_parser.add_argument(
        "--vat",
        type=float,
        help="Belegter abziehbarer Vorsteuerbetrag in EUR",
    )
    upd_exp_parser.add_argument(
        "--vat-rate",
        type=float,
        choices=[0.0, 7.0, 19.0],
        help="Neuer Vorsteuer-Steuersatz (0, 7, 19)",
    )
    upd_exp_parser.add_argument(
        "--tip",
        dest="entertainment_tip_eur",
        type=float,
        help="Im Zahlbetrag enthaltenes Trinkgeld (nur Bewirtung)",
    )
    upd_exp_parser.add_argument(
        "--entertainment-vat-status",
        choices=["deductible", "no_deduction", "needs_review"],
        help="Vorsteuerstatus bzw. Prüfbedarf der Bewirtung nachpflegen",
    )
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
    upd_rc_group = upd_exp_parser.add_mutually_exclusive_group()
    upd_rc_group.add_argument(
        "--rc",
        choices=["eu", "third-country"],
        metavar="{eu,third-country}",
        help="Setzt Reverse-Charge mit Jurisdiktion: eu oder third-country",
    )
    upd_rc_group.add_argument(
        "--no-rc",
        action="store_true",
        help="Entfernt Reverse-Charge und Jurisdiktion",
    )
    upd_exp_parser.add_argument(
        "--force",
        action="store_true",
        help="Erzwingt Änderung trotz Schwellenwert-Überschreitung oder möglicher Duplikate",
    )
    upd_exp_parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Erlaubt mögliches Duplikat trotz Ähnlichkeit",
    )
    upd_exp_parser.set_defaults(func=cmd_update_expense)

    # update income
    upd_inc_parser = update_subparsers.add_parser("income", help="Einnahme aktualisieren")
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
    upd_inc_parser.add_argument(
        "--ledger-account",
        help="Neues Buchungskonto aus dem Kontenrahmen",
    )
    upd_inc_parser.add_argument("--amount", type=float, help="Neuer Betrag")
    upd_inc_parser.add_argument("--foreign", help="Neuer Fremdwährungsbetrag")
    upd_inc_parser.add_argument("--receipt", help="Neuer Belegname")
    upd_inc_parser.add_argument(
        "--invoice-number", help="Neue Rechnungsnummer (leer zum Entfernen)"
    )
    upd_inc_parser.add_argument("--notes", help="Neue Bemerkung")
    upd_inc_parser.add_argument("--vat", type=float, help="Neue Umsatzsteuer")
    upd_inc_parser.add_argument(
        "--vat-rate",
        type=float,
        choices=[0.0, 7.0, 19.0],
        help="Neuer USt-Satz für Ausgangsumsätze (0, 7, 19)",
    )
    upd_inc_parser.add_argument(
        "--tax-free",
        action="store_true",
        help="Setzt die Einnahme auf steuerfrei ohne Vorsteuerabzug",
    )
    upd_inc_parser.add_argument(
        "--force",
        action="store_true",
        help="Erzwingt Änderung trotz Schwellenwert-Überschreitung oder möglicher Duplikate",
    )
    upd_inc_parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Erlaubt mögliches Duplikat trotz Ähnlichkeit",
    )
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
    del_exp_parser.add_argument(
        "--purge", action="store_true", help="Endgültig löschen (Purge statt Papierkorb)"
    )
    del_exp_parser.set_defaults(func=cmd_delete_expense)

    # delete income
    del_inc_parser = delete_subparsers.add_parser("income", help="Einnahme löschen")
    del_inc_parser.add_argument("id", type=int, help="ID der Einnahme")
    del_inc_parser.add_argument("--force", action="store_true", help="Keine Rückfrage")
    del_inc_parser.add_argument(
        "--purge", action="store_true", help="Endgültig löschen (Purge statt Papierkorb)"
    )
    del_inc_parser.set_defaults(func=cmd_delete_income)

    # delete private-transfer
    del_private_parser = delete_subparsers.add_parser(
        "private-transfer", help="Privatvorgang löschen"
    )
    del_private_parser.add_argument("id", type=int, help="ID des Privatvorgangs")
    del_private_parser.add_argument("--force", action="store_true", help="Keine Rückfrage")
    del_private_parser.add_argument(
        "--purge", action="store_true", help="Endgültig löschen (Purge statt Papierkorb)"
    )
    del_private_parser.set_defaults(func=cmd_delete_private_transfer)

    # --- restore ---
    restore_parser = subparsers.add_parser("restore", help="Stellt gelöschten Datensatz wieder her")
    restore_parser.add_argument("id", type=int, help="ID des wiederherzustellenden Eintrags")
    restore_parser.add_argument(
        "--table",
        choices=["expenses", "income", "private_transfers"],
        help="Tabelle des Eintrags (optional, wird sonst automatisch ermittelt)",
    )
    restore_parser.set_defaults(func=cmd_restore)

    # --- undo ---
    undo_parser = subparsers.add_parser("undo", help="Macht eine Änderung rückgängig")
    undo_parser.add_argument("--id", type=int, help="Spezifische Audit-Log-ID rückgängig machen")
    undo_parser.add_argument(
        "--force",
        action="store_true",
        help="Keine interaktive Bestätigung anfordern",
    )
    undo_parser.set_defaults(func=cmd_undo)

    # --- trash ---
    trash_parser = subparsers.add_parser("trash", help="Verwaltet den Papierkorb")
    trash_subparsers = trash_parser.add_subparsers(dest="action", required=False)
    trash_list_parser = trash_subparsers.add_parser("list", help="Gelöschte Einträge anzeigen")
    trash_list_parser.set_defaults(func=cmd_trash_list)
    trash_empty_parser = trash_subparsers.add_parser("empty", help="Papierkorb endgültig leeren")
    trash_empty_parser.add_argument("--force", action="store_true", help="Keine Rückfrage")
    trash_empty_parser.set_defaults(func=cmd_trash_empty)
    trash_parser.set_defaults(
        func=lambda args: cmd_trash_list(args) if getattr(args, "action", None) is None else None
    )

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
            f"Ausgabeverzeichnis (default: exports.directory aus Config oder {DEFAULT_EXPORT_DIR})"
        ),
    )
    export_parser.add_argument(
        "--force",
        action="store_true",
        help="Bestehende Exportdateien überschreiben",
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

    # --- vat-report ---
    vat_report_parser = subparsers.add_parser(
        "vat-report",
        help="Erzeugt einen ELSTER-nahen USt-Voranmeldungs-Report",
    )
    vat_report_parser.add_argument("--year", type=int, required=True, help="Jahr")
    vat_period_group = vat_report_parser.add_mutually_exclusive_group()
    vat_period_group.add_argument("--quarter", type=int, choices=[1, 2, 3, 4], help="Quartal")
    vat_period_group.add_argument("--month", type=int, choices=range(1, 13), help="Monat")
    vat_report_parser.add_argument(
        "--format",
        choices=["table", "csv", "xlsx"],
        default="table",
        help="Ausgabeformat",
    )
    vat_report_parser.add_argument(
        "--output",
        default=None,
        help=(
            "Ausgabeverzeichnis für csv/xlsx (default: exports.directory aus Config oder "
            f"{DEFAULT_EXPORT_DIR})"
        ),
    )
    vat_report_parser.set_defaults(func=cmd_vat_report)

    # --- private-summary ---
    private_summary_parser = subparsers.add_parser(
        "private-summary", help="Zeigt ELSTER-Summen für Privatvorgänge"
    )
    private_summary_parser.add_argument("--year", type=int, required=True, help="Jahr")
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
    config_show_parser = config_subparsers.add_parser("show", help="Zeigt aktuelle Konfiguration")
    config_show_parser.set_defaults(func=cmd_config_show)

    # --- receipt ---
    receipt_parser = subparsers.add_parser("receipt", help="Beleg-Verwaltung")
    receipt_subparsers = receipt_parser.add_subparsers(dest="action", required=True)

    # receipt check
    receipt_check_parser = receipt_subparsers.add_parser(
        "check", help="Prüft Transaktionen auf fehlende Belege"
    )
    receipt_check_parser.add_argument("--year", type=int, help="Jahr (default: aktuelles)")
    receipt_check_parser.add_argument(
        "--type", choices=["expense", "income"], help="Nur diesen Typ prüfen"
    )
    receipt_check_parser.set_defaults(func=cmd_receipt_check)

    receipt_unbooked_parser = receipt_subparsers.add_parser(
        "unbooked", help="Findet Belegdateien ohne zugeordnete Buchung"
    )
    receipt_unbooked_parser.add_argument(
        "--year", type=_receipt_year, default=None, help="Ablagejahr (default: aktuelles Jahr)"
    )
    receipt_unbooked_parser.add_argument(
        "--type", choices=["expense", "income"], help="Nur diesen Typ prüfen"
    )
    receipt_unbooked_parser.add_argument(
        "--format", choices=["table", "csv", "json"], default="table", help="Ausgabeformat"
    )
    receipt_unbooked_parser.set_defaults(func=cmd_receipt_unbooked)

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
    incomplete_parser = subparsers.add_parser("incomplete", help="Unvollständige Buchungen")
    incomplete_subparsers = incomplete_parser.add_subparsers(dest="action", required=True)
    incomplete_list_parser = incomplete_subparsers.add_parser(
        "list", help="Listet unvollständige Einträge"
    )
    incomplete_list_parser.add_argument("--type", choices=["expense", "income"], help="Typ filtern")
    incomplete_list_parser.add_argument("--year", type=int, help="Jahr filtern")
    incomplete_list_parser.add_argument("--format", choices=["table", "csv"], default="table")
    incomplete_list_parser.set_defaults(func=cmd_incomplete_list)

    # --- doctor ---
    doctor_parser = subparsers.add_parser("doctor", help="Umgebungs- und Pre-Flight-Diagnose")
    doctor_parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    doctor_parser.set_defaults(func=cmd_doctor)

    load_plugins(subparsers)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    # Das globale Notfall-Flag darf auch hinter dem letzten Unterbefehl stehen.
    ignored = "--ignore-skill-version" in argv
    argv = [item for item in argv if item != "--ignore-skill-version"]
    datev_position = _datev_position(argv)
    external_args: list[str] | None = None
    if datev_position is not None:
        external_args = argv[datev_position + 1 :]
    datev_entry_point_exists = any(
        entry_point.name == "datev"
        for entry_point in importlib.metadata.entry_points(group="euer.commands")
    )
    external_binary = None if datev_entry_point_exists else shutil.which("euer-datev")
    if datev_position is not None and not datev_entry_point_exists and not external_binary:
        parser.exit(
            2,
            "Fehler: 'datev' ist nicht installiert. Installiere euer-datev mit "
            "'brew install curiousmarkus/euer/euer-datev' oder 'pipx install euer-datev'.\n",
        )
    external = datev_position is not None and external_binary is not None
    args = parser.parse_args(argv[: datev_position + 1] if external else argv)
    if external:
        args.datev_command = external_args[0] if external_args else None
        datev_db = _datev_db_option(external_args or [])
        if datev_db is not None:
            args.db = datev_db
    args.ignore_skill_version = ignored
    datev_info_only = args.command == "datev" and (
        getattr(args, "datev_command", None) not in {"export", "validate"}
        or (
            external
            and any(option in (external_args or []) for option in {"-h", "--help", "--version"})
        )
    )
    exempt = (
        args.command in {"doctor", "config"}
        or (args.command == "setup" and args.set is not None and args.set[0] == "skill.version")
        or datev_info_only
    )
    if not exempt:
        skill = skill_status()
        if skill["status"] == "error":
            parser.exit(1, f"Fehler: {skill.get('error', 'Skill oder Config nicht lesbar')}\n")
        if skill["status"] != "current" and not args.ignore_skill_version:
            confirmed = skill["confirmed_version"] or "(nicht bestätigt)"
            expected = skill["expected_version"]
            message = (
                "[✗] FEHLER: Deine bestätigte Skill-Version weicht von der erwarteten Version ab.\n"
                f"Bestätigt: {confirmed}; erwartet: {expected}\n"
                f"Skill-Bundle: {skill['bundle_path']}\n"
                "Ersetze deinen Skill vollständig durch den mitgelieferten Stand über den "
                "Installationsweg deines Agentensystems. Lies die aktualisierten Anweisungen.\n"
                "Bestätige anschließend die verwendete Version mit: "
                f'euer setup --set skill.version "{expected}"\n'
                "Falls du das Update aufgrund fehlender Rechte nicht durchführen kannst, "
                "hänge --ignore-skill-version an deinen Befehl an, um die Blockade zu umgehen."
            )
            if getattr(args, "json", False):
                print(
                    json.dumps(
                        {
                            "status": "error",
                            "error_code": "outdated_skill",
                            "message": message,
                            "confirmed_version": skill["confirmed_version"],
                            "expected_version": expected,
                            "bundle_path": skill["bundle_path"],
                            "remediation": f'euer setup --set skill.version "{expected}"',
                        },
                        ensure_ascii=False,
                    ),
                    file=sys.stderr,
                )
                parser.exit(1)
            parser.exit(1, message + "\n")
    if datev_info_only:
        if external:
            forwarded = list(external_args or [])
            if (
                args.config is not None
                and "--config" not in forwarded
                and not any(value.startswith("--config=") for value in forwarded)
            ):
                forwarded[1:1] = ["--config", args.config]
            _run_external_datev(args.external_binary, forwarded)
        else:
            result = args.func(args)
            if isinstance(result, int):
                raise SystemExit(result)
        return
    args.is_explicit_db = args.db is not None
    args.project_root = Path.cwd()
    if getattr(args, "save_db_path", False) and not args.is_explicit_db:
        parser.error("--save-db-path erfordert --db PFAD")
    if not args.is_explicit_db:
        try:
            project_db = get_project_db_path(args.project_root)
        except (ValueError, OSError) as exc:
            if args.command == "doctor":
                # doctor soll den Fehler selbst diagnostizieren und alle anderen
                # Prüfungen einschließlich Skill-Auskunft trotzdem ausgeben.
                project_db = None
            else:
                message = (
                    f"Ungültige Projekt-Config {project_config_path(args.project_root)}: {exc}"
                )
                if args.command == "init" and getattr(args, "json", False):
                    print(json.dumps({"status": "error", "error": message}, ensure_ascii=False))
                    parser.exit(1)
                parser.exit(1, f"Fehler: {message}\n")
        args.db = str(project_db or args.project_root / "euer.db")
        args.db_from_project_config = project_db is not None
    else:
        args.db_from_project_config = False
    db_independent = (
        args.command in {"init", "config", "doctor", "datev"}
        or (args.command == "setup" and args.set is not None)
        or (args.command == "import" and args.schema)
        or datev_info_only
    )
    if (
        not db_independent
        and not Path(args.db).is_file()
        and not (args.command == "receipt" and args.action == "unbooked")
    ):
        parser.exit(
            1,
            f"Fehler: Datenbank nicht gefunden: {Path(args.db).resolve()}. "
            "Vorhandene DB mit 'euer --db PFAD init --save-db-path' verbinden "
            "oder mit 'euer init --create' eine neue DB anlegen.\n",
        )
    mutating_commands = {"add", "update", "delete", "restore", "undo", "import", "reconcile"}
    needs_backup = args.command in mutating_commands or (
        args.command == "trash" and args.action == "empty"
    )
    if needs_backup and not getattr(args, "dry_run", False) and not getattr(args, "schema", False):
        try:
            ensure_daily_backup(Path(args.db))
        except Exception as exc:
            parser.exit(1, f"Fehler: Sicherheits-Backup fehlgeschlagen: {exc}\n")
    if external:
        forwarded = list(external_args or [])
        if (
            args.config is not None
            and "--config" not in forwarded
            and not any(value.startswith("--config=") for value in forwarded)
        ):
            forwarded[1:1] = ["--config", args.config]
        if args.datev_command in {"export", "validate"} and _datev_db_option(forwarded) is None:
            forwarded.insert(1, "--db")
            forwarded.insert(2, args.db)
        _run_external_datev(args.external_binary, forwarded)
    else:
        result = args.func(args)
        if isinstance(result, int):
            raise SystemExit(result)


if __name__ == "__main__":
    main()
