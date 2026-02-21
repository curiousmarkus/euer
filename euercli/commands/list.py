import csv
import sys
from datetime import datetime
from pathlib import Path

from ..db import get_db_connection
from ..services.categories import get_category_list
from ..services.expenses import list_expenses
from ..services.income import list_income
from ..services.private_transfers import get_private_transfer_list, get_sacheinlagen


def cmd_list_expenses(args):
    """Listet Ausgaben."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    year = args.year or datetime.now().year

    rows = list_expenses(
        conn,
        year=year,
        month=args.month,
        category_name=args.category,
    )
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Datum",
                "Lieferant",
                "Kategorie",
                "EUR",
                "Konto",
                "Beleg",
                "Fremdwährung",
                "Bemerkung",
                "RC",
                "Vorsteuer",
                "Umsatzsteuer",
            ]
        )
        for r in rows:
            if r.category_name:
                cat_str = (
                    f"{r.category_name} ({r.category_eur_line})"
                    if r.category_eur_line
                    else r.category_name
                )
            else:
                cat_str = "Ohne Kategorie"
            writer.writerow(
                [
                    r.id,
                    r.date,
                    r.vendor,
                    cat_str,
                    f"{r.amount_eur:.2f}",
                    r.account or "",
                    r.receipt_name or "",
                    r.foreign_amount or "",
                    r.notes or "",
                    "X" if r.is_rc else "",
                    f"{r.vat_input:.2f}" if r.vat_input else "",
                    f"{r.vat_output:.2f}" if r.vat_output else "",
                ]
            )
    else:
        if not rows:
            print("Keine Ausgaben gefunden.")
            return

        has_vat = any(
            (r.vat_input and r.vat_input != 0)
            or (r.vat_output and r.vat_output != 0)
            or r.is_rc
            for r in rows
        )

        if has_vat:
            print(
                f"{'ID':<5} {'Datum':<12} {'Lieferant':<20} {'Kategorie':<25} {'EUR':>10} {'RC':<3} {'USt':>8} {'VorSt':>8} {'Konto':<10}"
            )
            print("-" * 110)
        else:
            print(
                f"{'ID':<5} {'Datum':<12} {'Lieferant':<20} {'Kategorie':<30} {'EUR':>10} {'Konto':<12}"
            )
            print("-" * 95)

        total = 0.0
        vat_out_total = 0.0
        vat_in_total = 0.0
        for r in rows:
            if r.category_name:
                cat_str = (
                    f"{r.category_name} ({r.category_eur_line})"
                    if r.category_eur_line
                    else r.category_name
                )
            else:
                cat_str = "Ohne Kategorie"
            if has_vat:
                vout_str = f"{r.vat_output:.2f}" if r.vat_output else ""
                vin_str = f"{r.vat_input:.2f}" if r.vat_input else ""
                rc_str = "X" if r.is_rc else ""
                print(
                    f"{r.id:<5} {r.date:<12} {r.vendor[:20]:<20} {cat_str[:25]:<25} {r.amount_eur:>10.2f} {rc_str:<3} {vout_str:>8} {vin_str:>8} {(r.account or ''):<10}"
                )
                if r.vat_output:
                    vat_out_total += r.vat_output
                if r.vat_input:
                    vat_in_total += r.vat_input
            else:
                print(
                    f"{r.id:<5} {r.date:<12} {r.vendor[:20]:<20} {cat_str[:30]:<30} {r.amount_eur:>10.2f} {(r.account or ''):<12}"
                )
            total += r.amount_eur
        print("-" * (110 if has_vat else 95))
        if has_vat:
            print(
                f"{'GESAMT':<68} {total:>10.2f}     {vat_out_total:>8.2f} {vat_in_total:>8.2f}"
            )
        else:
            print(f"{'GESAMT':<69} {total:>10.2f}")


def cmd_list_income(args):
    """Listet Einnahmen."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    year = args.year or datetime.now().year

    rows = list_income(
        conn,
        year=year,
        month=args.month,
        category_name=args.category,
    )
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Datum",
                "Quelle",
                "Kategorie",
                "EUR",
                "Beleg",
                "Fremdwährung",
                "Bemerkung",
                "Umsatzsteuer",
            ]
        )
        for r in rows:
            if r.category_name:
                cat_str = (
                    f"{r.category_name} ({r.category_eur_line})"
                    if r.category_eur_line
                    else r.category_name
                )
            else:
                cat_str = "Ohne Kategorie"
            writer.writerow(
                [
                    r.id,
                    r.date,
                    r.source,
                    cat_str,
                    f"{r.amount_eur:.2f}",
                    r.receipt_name or "",
                    r.foreign_amount or "",
                    r.notes or "",
                    f"{r.vat_output:.2f}" if r.vat_output else "",
                ]
            )
    else:
        if not rows:
            print("Keine Einnahmen gefunden.")
            return

        has_vat = any(r.vat_output and r.vat_output != 0 for r in rows)

        if has_vat:
            print(
                f"{'ID':<5} {'Datum':<12} {'Quelle':<25} {'Kategorie':<35} {'EUR':>12} {'USt':>8}"
            )
            print("-" * 105)
        else:
            print(f"{'ID':<5} {'Datum':<12} {'Quelle':<25} {'Kategorie':<35} {'EUR':>12}")
            print("-" * 95)

        total = 0.0
        vat_out_total = 0.0

        for r in rows:
            if r.category_name:
                cat_str = (
                    f"{r.category_name} ({r.category_eur_line})"
                    if r.category_eur_line
                    else r.category_name
                )
            else:
                cat_str = "Ohne Kategorie"
            amount_str = f"{r.amount_eur:>12.2f}"
            if has_vat:
                vat_str = f"{r.vat_output:.2f}" if r.vat_output else ""
                print(
                    f"{r.id:<5} {r.date:<12} {r.source[:25]:<25} {cat_str[:35]:<35} {amount_str} {vat_str:>8}"
                )
                if r.vat_output:
                    vat_out_total += r.vat_output
            else:
                print(
                    f"{r.id:<5} {r.date:<12} {r.source[:25]:<25} {cat_str[:35]:<35} {amount_str}"
                )
            total += r.amount_eur
        print("-" * (105 if has_vat else 95))
        if has_vat:
            print(f"{'GESAMT':<79} {total:>12.2f} {vat_out_total:>8.2f}")
        else:
            print(f"{'GESAMT':<79} {total:>12.2f}")


def cmd_list_categories(args):
    """Listet alle Kategorien."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    rows = get_category_list(conn, args.type)
    conn.close()

    print(f"{'ID':<4} {'Typ':<8} {'EÜR':<5} {'Name':<40}")
    print("-" * 60)
    for r in rows:
        eur = str(r.eur_line) if r.eur_line else "-"
        print(f"{r.id:<4} {r.type:<8} {eur:<5} {r.name:<40}")


def cmd_list_private_deposits(args):
    """Listet Privateinlagen (direkt + Sacheinlagen)."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    year = args.year or datetime.now().year

    transfers = get_private_transfer_list(conn, transfer_type="deposit", year=year)
    # Sacheinlagen kommen aus persistierten Flags in expenses, nicht aus aktueller Config.
    sacheinlagen = get_sacheinlagen(conn, year=year)
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["ID", "Datum", "Beschreibung", "EUR", "Quelle", "Klassifikation"])
        for row in transfers:
            writer.writerow(
                [
                    row.id,
                    row.date,
                    row.description,
                    f"{row.amount_eur:.2f}",
                    "Direktbuchung",
                    "direct",
                ]
            )
        for row in sacheinlagen:
            writer.writerow(
                [
                    "",
                    row.date,
                    row.vendor,
                    f"{abs(row.amount_eur):.2f}",
                    f"Ausgabe #{row.id} (Sacheinlage)",
                    row.private_classification,
                ]
            )
        return

    if not transfers and not sacheinlagen:
        print("Keine Privateinlagen gefunden.")
        return

    print(f"Privateinlagen {year}")
    print("=" * 60)
    print(
        f"{'ID':<5} {'Datum':<12} {'Beschreibung':<30} {'EUR':>10} "
        f"{'Quelle':<20} {'Klass.':<12}"
    )
    print("-" * 98)

    total = 0.0
    for row in transfers:
        print(
            f"{row.id:<5} {row.date:<12} {row.description[:30]:<30} {row.amount_eur:>10.2f} "
            f"{'Direktbuchung':<20} {'direct':<12}"
        )
        total += row.amount_eur

    for row in sacheinlagen:
        amount = abs(row.amount_eur)
        source = f"Ausgabe #{row.id}"
        print(
            f"{'--':<5} {row.date:<12} {row.vendor[:30]:<30} {amount:>10.2f} "
            f"{source:<20} {row.private_classification:<12}"
        )
        total += amount

    print("-" * 98)
    print(f"{'GESAMT':<62} {total:>10.2f}")


def cmd_list_private_withdrawals(args):
    """Listet Privatentnahmen."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    year = args.year or datetime.now().year
    transfers = get_private_transfer_list(conn, transfer_type="withdrawal", year=year)
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["ID", "Datum", "Beschreibung", "EUR", "Quelle"])
        for row in transfers:
            writer.writerow([row.id, row.date, row.description, f"{row.amount_eur:.2f}", "Direktbuchung"])
        return

    if not transfers:
        print("Keine Privatentnahmen gefunden.")
        return

    print(f"Privatentnahmen {year}")
    print("=" * 60)
    print(f"{'ID':<5} {'Datum':<12} {'Beschreibung':<40} {'EUR':>10}")
    print("-" * 72)
    total = 0.0
    for row in transfers:
        print(f"{row.id:<5} {row.date:<12} {row.description[:40]:<40} {row.amount_eur:>10.2f}")
        total += row.amount_eur
    print("-" * 72)
    print(f"{'GESAMT':<59} {total:>10.2f}")


def cmd_list_private_transfers(args):
    """Listet Privateinlagen und Privatentnahmen."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    year = args.year or datetime.now().year
    deposits = get_private_transfer_list(conn, transfer_type="deposit", year=year)
    withdrawals = get_private_transfer_list(conn, transfer_type="withdrawal", year=year)
    sacheinlagen = get_sacheinlagen(conn, year=year)
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["type", "id", "date", "description", "amount_eur", "source"])
        for row in deposits:
            writer.writerow(["deposit", row.id, row.date, row.description, f"{row.amount_eur:.2f}", "direct"])
        for row in sacheinlagen:
            writer.writerow(
                [
                    "deposit",
                    "",
                    row.date,
                    row.vendor,
                    f"{abs(row.amount_eur):.2f}",
                    f"expense:{row.id}",
                ]
            )
        for row in withdrawals:
            writer.writerow(
                [
                    "withdrawal",
                    row.id,
                    row.date,
                    row.description,
                    f"{row.amount_eur:.2f}",
                    "direct",
                ]
            )
        return

    deposits_total = sum(row.amount_eur for row in deposits) + sum(
        abs(row.amount_eur) for row in sacheinlagen
    )
    withdrawals_total = sum(row.amount_eur for row in withdrawals)

    print(f"Privateinlagen & Privatentnahmen {year}")
    print("=" * 50)
    print()

    print("Privateinlagen (Geld/Werte -> Geschäft):")
    print(f"{'ID':<5} {'Datum':<12} {'Beschreibung':<30} {'EUR':>10} {'Quelle':<20}")
    print("-" * 85)
    for row in deposits:
        print(
            f"{row.id:<5} {row.date:<12} {row.description[:30]:<30} {row.amount_eur:>10.2f} {'Direktbuchung':<20}"
        )
    for row in sacheinlagen:
        print(
            f"{'--':<5} {row.date:<12} {row.vendor[:30]:<30} {abs(row.amount_eur):>10.2f} {f'Ausgabe #{row.id}':<20}"
        )
    print("-" * 85)
    print(f"{'SUMME':<49} {deposits_total:>10.2f} EUR")
    print()

    print("Privatentnahmen (Geld/Werte <- Geschäft):")
    print(f"{'ID':<5} {'Datum':<12} {'Beschreibung':<30} {'EUR':>10} {'Quelle':<20}")
    print("-" * 85)
    for row in withdrawals:
        print(
            f"{row.id:<5} {row.date:<12} {row.description[:30]:<30} {row.amount_eur:>10.2f} {'Direktbuchung':<20}"
        )
    print("-" * 85)
    print(f"{'SUMME':<49} {withdrawals_total:>10.2f} EUR")
