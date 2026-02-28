import csv
import sys
from datetime import datetime
from pathlib import Path

from ..db import get_db_connection
from ..services.categories import get_category_list
from ..services.expenses import list_expenses
from ..services.income import list_income
from ..services.private_transfers import get_private_transfer_list, get_private_paid_expenses


def infer_booking_status(
    payment_date: str | None,
    invoice_date: str | None,
    receipt_name: str | None,
) -> str:
    has_payment = bool(payment_date)
    has_invoice = bool(invoice_date)
    has_receipt = bool(receipt_name)

    if has_payment and has_invoice and has_receipt:
        return "Vollständig"
    if has_payment and not has_receipt:
        return "Zahlung erfolgt, Beleg fehlt"
    if has_invoice and not has_payment and has_receipt:
        return "Rechnung liegt vor, Zahlung ausstehend"
    if has_invoice and not has_payment and not has_receipt:
        return "Rechnung liegt vor, kein Beleg, Zahlung ausstehend"
    if has_payment and has_receipt and not has_invoice:
        return "Zahlung erfolgt, Rechnungsdatum fehlt"
    if has_payment and has_invoice and not has_receipt:
        return "Zahlung erfolgt, Beleg fehlt"
    return "Unvollständig"


def format_category_label(category_name: str | None, category_eur_line: int | None) -> str:
    if not category_name:
        return "Ohne Kategorie"
    if category_eur_line:
        return f"({category_eur_line}) {category_name}"
    return category_name


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
                "Wertstellung",
                "Rechnung",
                "Lieferant",
                "Kategorie",
                "EUR",
                "Konto",
                "Beleg",
                "Status",
                "Fremdwährung",
                "Bemerkung",
                "RC",
                "Vorsteuer",
                "Umsatzsteuer",
            ]
        )
        for r in rows:
            cat_str = format_category_label(r.category_name, r.category_eur_line)
            writer.writerow(
                [
                    r.id,
                    r.payment_date or "",
                    r.invoice_date or "",
                    r.vendor,
                    cat_str,
                    f"{r.amount_eur:.2f}",
                    r.account or "",
                    r.receipt_name or "",
                    infer_booking_status(r.payment_date, r.invoice_date, r.receipt_name),
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

        full_view = bool(getattr(args, "full", False))
        has_vat = any(
            (r.vat_input and r.vat_input != 0)
            or (r.vat_output and r.vat_output != 0)
            or r.is_rc
            for r in rows
        )

        if full_view and has_vat:
            row_fmt = (
                "{id:<5} {payment:<12} {invoice:<12} {vendor:<18} {category:<20} {amount:>10} "
                "{account:<12} {receipt:<20} {foreign:<14} {notes:<24} {status:<35} "
                "{rc:<3} {vout:>8} {vin:>8}"
            )
            header = row_fmt.format(
                id="ID",
                payment="Wertstellung",
                invoice="Rechnung",
                vendor="Lieferant",
                category="Kategorie",
                amount="EUR",
                account="Konto",
                receipt="Beleg",
                foreign="Fremdw.",
                notes="Notiz",
                status="Status",
                rc="RC",
                vout="USt",
                vin="VorSt",
            )
            print(header)
            print("-" * len(header))
        elif full_view:
            row_fmt = (
                "{id:<5} {payment:<12} {invoice:<12} {vendor:<20} {category:<24} {amount:>10} "
                "{account:<12} {receipt:<20} {foreign:<14} {notes:<24} {status:<35}"
            )
            header = row_fmt.format(
                id="ID",
                payment="Wertstellung",
                invoice="Rechnung",
                vendor="Lieferant",
                category="Kategorie",
                amount="EUR",
                account="Konto",
                receipt="Beleg",
                foreign="Fremdw.",
                notes="Notiz",
                status="Status",
            )
            print(header)
            print("-" * len(header))
        elif has_vat:
            print(
                f"{'ID':<5} {'Wertstellung':<12} {'Rechnung':<12} {'Lieferant':<18} {'Kategorie':<20} {'EUR':>10} {'Status':<35} {'RC':<3} {'USt':>8} {'VorSt':>8}"
            )
            print("-" * 150)
        else:
            print(
                f"{'ID':<5} {'Wertstellung':<12} {'Rechnung':<12} {'Lieferant':<20} {'Kategorie':<24} {'EUR':>10} {'Status':<35} {'Konto':<12}"
            )
            print("-" * 140)

        total = 0.0
        vat_out_total = 0.0
        vat_in_total = 0.0
        for r in rows:
            cat_str = format_category_label(r.category_name, r.category_eur_line)
            status = infer_booking_status(r.payment_date, r.invoice_date, r.receipt_name)
            if full_view and has_vat:
                vout_str = f"{r.vat_output:.2f}" if r.vat_output else ""
                vin_str = f"{r.vat_input:.2f}" if r.vat_input else ""
                rc_str = "X" if r.is_rc else ""
                print(
                    row_fmt.format(
                        id=r.id,
                        payment=r.payment_date or "",
                        invoice=r.invoice_date or "",
                        vendor=r.vendor[:18],
                        category=cat_str[:20],
                        amount=f"{r.amount_eur:.2f}",
                        account=(r.account or "")[:12],
                        receipt=(r.receipt_name or "")[:20],
                        foreign=(r.foreign_amount or "")[:14],
                        notes=(r.notes or "")[:24],
                        status=status[:35],
                        rc=rc_str,
                        vout=vout_str,
                        vin=vin_str,
                    )
                )
                if r.vat_output:
                    vat_out_total += r.vat_output
                if r.vat_input:
                    vat_in_total += r.vat_input
            elif full_view:
                print(
                    row_fmt.format(
                        id=r.id,
                        payment=r.payment_date or "",
                        invoice=r.invoice_date or "",
                        vendor=r.vendor[:20],
                        category=cat_str[:24],
                        amount=f"{r.amount_eur:.2f}",
                        account=(r.account or "")[:12],
                        receipt=(r.receipt_name or "")[:20],
                        foreign=(r.foreign_amount or "")[:14],
                        notes=(r.notes or "")[:24],
                        status=status[:35],
                    )
                )
            elif has_vat:
                vout_str = f"{r.vat_output:.2f}" if r.vat_output else ""
                vin_str = f"{r.vat_input:.2f}" if r.vat_input else ""
                rc_str = "X" if r.is_rc else ""
                print(
                    f"{r.id:<5} {(r.payment_date or ''):<12} {(r.invoice_date or ''):<12} {r.vendor[:18]:<18} {cat_str[:20]:<20} {r.amount_eur:>10.2f} {status[:35]:<35} {rc_str:<3} {vout_str:>8} {vin_str:>8}"
                )
                if r.vat_output:
                    vat_out_total += r.vat_output
                if r.vat_input:
                    vat_in_total += r.vat_input
            else:
                print(
                    f"{r.id:<5} {(r.payment_date or ''):<12} {(r.invoice_date or ''):<12} {r.vendor[:20]:<20} {cat_str[:24]:<24} {r.amount_eur:>10.2f} {status[:35]:<35} {(r.account or ''):<12}"
                )
            total += r.amount_eur
        if full_view:
            print("-" * len(header))
        else:
            print("-" * (150 if has_vat else 140))
        if full_view and has_vat:
            print(
                row_fmt.format(
                    id="GESAMT",
                    payment="",
                    invoice="",
                    vendor="",
                    category="",
                    amount=f"{total:.2f}",
                    account="",
                    receipt="",
                    foreign="",
                    notes="",
                    status="",
                    rc="",
                    vout=f"{vat_out_total:.2f}",
                    vin=f"{vat_in_total:.2f}",
                )
            )
        elif full_view:
            print(
                row_fmt.format(
                    id="GESAMT",
                    payment="",
                    invoice="",
                    vendor="",
                    category="",
                    amount=f"{total:.2f}",
                    account="",
                    receipt="",
                    foreign="",
                    notes="",
                    status="",
                )
            )
        elif has_vat:
            print(
                f"{'GESAMT':<90} {total:>10.2f} {'':<39} {vat_out_total:>8.2f} {vat_in_total:>8.2f}"
            )
        else:
            print(f"{'GESAMT':<76} {total:>10.2f}")


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
                "Wertstellung",
                "Rechnung",
                "Quelle",
                "Kategorie",
                "EUR",
                "Beleg",
                "Status",
                "Fremdwährung",
                "Bemerkung",
                "Umsatzsteuer",
            ]
        )
        for r in rows:
            cat_str = format_category_label(r.category_name, r.category_eur_line)
            writer.writerow(
                [
                    r.id,
                    r.payment_date or "",
                    r.invoice_date or "",
                    r.source,
                    cat_str,
                    f"{r.amount_eur:.2f}",
                    r.receipt_name or "",
                    infer_booking_status(r.payment_date, r.invoice_date, r.receipt_name),
                    r.foreign_amount or "",
                    r.notes or "",
                    f"{r.vat_output:.2f}" if r.vat_output else "",
                ]
            )
    else:
        if not rows:
            print("Keine Einnahmen gefunden.")
            return

        full_view = bool(getattr(args, "full", False))
        if full_view:
            row_fmt = (
                "{id:<5} {payment:<12} {invoice:<12} {source:<20} {category:<26} "
                "{amount:>12} {status:<30} {vat:>8} {notes:<24}"
            )
            header = row_fmt.format(
                id="ID",
                payment="Wertstellung",
                invoice="Rechnung",
                source="Quelle",
                category="Kategorie",
                amount="EUR",
                status="Status",
                vat="USt",
                notes="Notiz",
            )
        else:
            row_fmt = (
                "{id:<5} {payment:<12} {invoice:<12} {source:<20} {category:<26} "
                "{amount:>12} {status:<30} {vat:>8}"
            )
            header = row_fmt.format(
                id="ID",
                payment="Wertstellung",
                invoice="Rechnung",
                source="Quelle",
                category="Kategorie",
                amount="EUR",
                status="Status",
                vat="USt",
            )
        print(header)
        print("-" * len(header))

        total = 0.0
        vat_out_total = 0.0

        for r in rows:
            cat_str = format_category_label(r.category_name, r.category_eur_line)
            status = infer_booking_status(r.payment_date, r.invoice_date, r.receipt_name)
            amount_str = f"{r.amount_eur:.2f}"
            vat_str = f"{r.vat_output:.2f}" if r.vat_output else ""
            if full_view:
                print(
                    row_fmt.format(
                        id=r.id,
                        payment=r.payment_date or "",
                        invoice=r.invoice_date or "",
                        source=r.source[:20],
                        category=cat_str[:26],
                        amount=amount_str,
                        status=status[:30],
                        vat=vat_str,
                        notes=(r.notes or "")[:24],
                    )
                )
            else:
                print(
                    row_fmt.format(
                        id=r.id,
                        payment=r.payment_date or "",
                        invoice=r.invoice_date or "",
                        source=r.source[:20],
                        category=cat_str[:26],
                        amount=amount_str,
                        status=status[:30],
                        vat=vat_str,
                    )
                )
            if r.vat_output:
                vat_out_total += r.vat_output
            total += r.amount_eur
        print("-" * len(header))
        if full_view:
            print(
                row_fmt.format(
                    id="GESAMT",
                    payment="",
                    invoice="",
                    source="",
                    category="",
                    amount=f"{total:.2f}",
                    status="",
                    vat=f"{vat_out_total:.2f}",
                    notes="",
                )
            )
        else:
            print(
                row_fmt.format(
                    id="GESAMT",
                    payment="",
                    invoice="",
                    source="",
                    category="",
                    amount=f"{total:.2f}",
                    status="",
                    vat=f"{vat_out_total:.2f}",
                )
            )


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
    private_paid_expenses = get_private_paid_expenses(conn, year=year)
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
        for row in private_paid_expenses:
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

    if not transfers and not private_paid_expenses:
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

    for row in private_paid_expenses:
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
    private_paid_expenses = get_private_paid_expenses(conn, year=year)
    conn.close()

    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["type", "id", "date", "description", "amount_eur", "source"])
        for row in deposits:
            writer.writerow(["deposit", row.id, row.date, row.description, f"{row.amount_eur:.2f}", "direct"])
        for row in private_paid_expenses:
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
        abs(row.amount_eur) for row in private_paid_expenses
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
    for row in private_paid_expenses:
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
