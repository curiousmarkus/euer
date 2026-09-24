from datetime import datetime
from decimal import Decimal
from pathlib import Path

from ..config import load_config
from ..db import get_db_connection
from ..importers import get_tax_config
from ..services.entertainment import calculate_entertainment_breakdown
from ..services.eur import (
    get_category_display_name,
    get_category_eur_line,
    get_eur_field,
    is_entertainment_category,
    is_small_business_subset,
)
from ..services.private_transfers import get_private_summary

ENTERTAINMENT_CATEGORY = "Bewirtungsaufwendungen"


def _eur_label(name: str | None, key: str | None, year: int) -> str:
    if not name:
        return "Ohne Kategorie"
    name = get_category_display_name(name, key) or name
    line = get_category_eur_line(year, key)
    return f"{name} (Zeile {line})" if line is not None else name


def _field_label(year: int, key: str, fallback: str) -> str:
    field = get_eur_field(year, key)
    if field is None:
        return fallback
    return f"{field.label} (Zeile {field.line})"


def cmd_summary(args):
    """Zeigt Kategorie-Zusammenfassung und die EÜR-Felder des Berichtsjahrs."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    tax_mode = get_tax_config(config)

    year = args.year or datetime.now().year

    print(f"EÜR-Zusammenfassung {year}")
    print("=" * 50)
    print()
    if get_eur_field(year, "input_vat") is None:
        print(
            f"Hinweis: Für {year} ist keine geprüfte Formularzuordnung mitgeliefert. "
            "Beträge erscheinen ohne ELSTER-Zeilennummern."
        )
        print()

    skipped_expenses = conn.execute(
        """SELECT COUNT(*) as cnt FROM expenses
           WHERE payment_date IS NULL
             AND invoice_date IS NOT NULL
             AND strftime('%Y', invoice_date) = ?""",
        (str(year),),
    ).fetchone()["cnt"]
    skipped_income = conn.execute(
        """SELECT COUNT(*) as cnt FROM income
           WHERE payment_date IS NULL
             AND invoice_date IS NOT NULL
             AND strftime('%Y', invoice_date) = ?""",
        (str(year),),
    ).fetchone()["cnt"]
    skipped_total = skipped_expenses + skipped_income
    if skipped_total > 0:
        print(
            f"Hinweis: {skipped_total} Buchung(en) ohne Wertstellungsdatum ausgelassen "
            f"({skipped_expenses} Ausgaben, {skipped_income} Einnahmen)."
        )
        print(
            "  → Wertstellungsdatum per `euer update expense|income <ID> --payment-date` ergänzen."
        )
        print()

    legacy_rc_count = conn.execute(
        """SELECT COUNT(*) as cnt FROM expenses
           WHERE rc_type = 'unclassified'
             AND payment_date IS NOT NULL
             AND strftime('%Y', payment_date) = ?""",
        (str(year),),
    ).fetchone()["cnt"]
    if legacy_rc_count > 0:
        print(f"Hinweis: {legacy_rc_count} Reverse-Charge-Buchung(en) ohne EU-/Drittland-Typ.")
        print(
            "  → Für die spätere USt-Voranmeldung bitte per "
            "`euer update expense <ID> --rc eu|third-country` nachpflegen."
        )
        print()

    entertainment_rows = conn.execute(
        """SELECT e.id, e.amount_eur, e.vat_input, e.entertainment_vat_status, e.rc_type
           FROM expenses e
           JOIN categories c ON e.category_id = c.id
           WHERE c.eur_key = 'entertainment'
             AND e.payment_date IS NOT NULL
             AND strftime('%Y', e.payment_date) = ?
           ORDER BY e.id""",
        (str(year),),
    ).fetchall()
    entertainment_breakdowns = {
        row["id"]: calculate_entertainment_breakdown(
            amount_eur=row["amount_eur"],
            vat_input=row["vat_input"],
            vat_status=row["entertainment_vat_status"],
            rc_type=row["rc_type"],
        )
        for row in entertainment_rows
    }
    open_entertainment = [
        row for row in entertainment_rows if entertainment_breakdowns[row["id"]].provisional
    ]
    finalized_entertainment_deductible = Decimal("0.00")
    finalized_entertainment_non_deductible = Decimal("0.00")
    provisional_entertainment_deductible = Decimal("0.00")
    provisional_entertainment_non_deductible = Decimal("0.00")
    for row in entertainment_rows:
        breakdown = entertainment_breakdowns[row["id"]]
        if breakdown.deductible_eur is None:
            continue
        if breakdown.provisional:
            provisional_entertainment_deductible += breakdown.deductible_eur
            provisional_entertainment_non_deductible += breakdown.non_deductible_eur or Decimal(
                "0.00"
            )
        else:
            finalized_entertainment_deductible += breakdown.deductible_eur
            finalized_entertainment_non_deductible += breakdown.non_deductible_eur or Decimal(
                "0.00"
            )

    expense_rows = conn.execute(
        """SELECT c.name, c.eur_key, SUM(e.amount_eur) as total,
                  SUM(CASE WHEN COALESCE(e.rc_type, 'none') = 'none'
                           THEN COALESCE(e.vat_input, 0) ELSE 0 END) as vat_input_total
           FROM expenses e
           LEFT JOIN categories c ON e.category_id = c.id
           WHERE e.payment_date IS NOT NULL
             AND strftime('%Y', e.payment_date) = ?
           GROUP BY c.id
           ORDER BY c.name""",
        (str(year),),
    ).fetchall()

    print("Ausgaben nach Kategorie:")
    expense_total = Decimal("0.00")
    total_input_vat = Decimal("0.00")
    for row in expense_rows:
        vat_total = Decimal(str(row["vat_input_total"] or 0)).quantize(Decimal("0.01"))
        total_input_vat += vat_total
        if is_entertainment_category(row["eur_key"]):
            if finalized_entertainment_deductible:
                amount = -finalized_entertainment_deductible
                label = _eur_label(ENTERTAINMENT_CATEGORY, row["eur_key"], year)
                print(f"  {label + ' – abziehbar':<56} {amount:>12.2f} EUR")
                expense_total += amount
            if finalized_entertainment_non_deductible:
                label = _eur_label(ENTERTAINMENT_CATEGORY, row["eur_key"], year)
                print(
                    f"  {label + ' – nicht abziehbar':<56} "
                    f"{finalized_entertainment_non_deductible:>12.2f} EUR"
                )
            if provisional_entertainment_deductible:
                label = _eur_label(ENTERTAINMENT_CATEGORY, row["eur_key"], year)
                print(
                    f"  {label + ' – vorläufig abziehbar':<56} "
                    f"{-provisional_entertainment_deductible:>12.2f} EUR"
                )
            if provisional_entertainment_non_deductible:
                print(
                    f"  {'Bewirtung – vorläufig nicht abziehbar':<56} "
                    f"{provisional_entertainment_non_deductible:>12.2f} EUR"
                )
            continue

        raw_amount = Decimal(str(row["total"] or 0))
        # amount_eur enthält den Zahlbetrag. Die abziehbare Vorsteuer wird als
        # eigener EÜR-Bestandteil ausgewiesen; hier bleibt der Nettobetrag.
        amount = raw_amount + vat_total
        label = _eur_label(row["name"], row["eur_key"], year)
        print(f"  {label:<56} {amount:>12.2f} EUR")
        expense_total += amount

    provisional_entertainment_vat = sum(
        Decimal(str(row["vat_input"] or 0)).quantize(Decimal("0.01"))
        for row in entertainment_rows
        if entertainment_breakdowns[row["id"]].provisional and row["rc_type"] == "none"
    )
    known_input_vat = total_input_vat - provisional_entertainment_vat
    if known_input_vat:
        input_vat_label = _field_label(year, "input_vat", "Abziehbare Vorsteuer")
        input_vat_expense = -known_input_vat
        print(f"  {input_vat_label:<56} {input_vat_expense:>12.2f} EUR")
        expense_total += input_vat_expense
    if provisional_entertainment_vat:
        input_vat_label = _field_label(year, "input_vat", "Vorsteuer, Bewirtung – vorläufig")
        print(
            f"  {(input_vat_label + ' – Prüfung offen'):<56} "
            f"{-provisional_entertainment_vat:>12.2f} EUR"
        )

    print("  " + "-" * 70)
    print(f"  {'GESAMT Ausgaben (bekannte, geprüfte Werte)':<56} {expense_total:>12.2f} EUR")
    print()

    if entertainment_rows:
        final_payment = sum(
            Decimal(str(abs(row["amount_eur"]))).quantize(Decimal("0.01"))
            for row in entertainment_rows
            if not entertainment_breakdowns[row["id"]].provisional
        )
        print("Bewirtungsaufwendungen:")
        print(f"  {'Geprüfte Zahlungsvorgänge (100%)':<56} {final_payment:>12.2f} EUR")
        print(
            f"  {_field_label(year, 'entertainment_deductible', 'Abziehbar (70%)'):<56} "
            f"{-finalized_entertainment_deductible:>12.2f} EUR"
        )
        print(
            f"  {_field_label(year, 'entertainment_non_deductible', 'Nicht abziehbar (30%)'):<56} "
            f"{finalized_entertainment_non_deductible:>12.2f} EUR"
        )
        if open_entertainment:
            ids = ", ".join(f"#{row['id']}" for row in open_entertainment)
            print(
                f"  Prüfung offen: {len(open_entertainment)} Buchung(en) {ids}. "
                "Vorläufige Teilbeträge stehen oben; EÜR und Gewinn sind unvollständig."
            )
        print()

    # USt-Summen bleiben an vat_input gebunden; die 70/30-Kürzung ändert den
    # belegten Vorsteuerbetrag nicht.
    vat_stats_expenses = conn.execute(
        """SELECT SUM(vat_input) as sum_input, SUM(vat_output) as sum_output
           FROM expenses
           WHERE payment_date IS NOT NULL
             AND strftime('%Y', payment_date) = ?""",
        (str(year),),
    ).fetchone()
    exp_vat_input = vat_stats_expenses["sum_input"] or 0.0
    exp_vat_output = vat_stats_expenses["sum_output"] or 0.0
    vat_stats_income = conn.execute(
        """SELECT SUM(vat_output) as sum_output
           FROM income
           WHERE payment_date IS NOT NULL
             AND strftime('%Y', payment_date) = ?""",
        (str(year),),
    ).fetchone()
    inc_vat_output = vat_stats_income["sum_output"] or 0.0
    total_vat_input = exp_vat_input
    total_vat_output = exp_vat_output + inc_vat_output
    vat_payment = total_vat_output - total_vat_input

    if tax_mode == "small_business":
        if total_vat_output != 0:
            vat_title = "Umsatzsteuer (Kleinunternehmer)"
            if open_entertainment:
                vat_title += " – Teilwerte, Bewirtungsprüfung offen"
            print(f"{vat_title}:")
            print(f"  {'USt aus Reverse-Charge (Schuld)':<40} {total_vat_output:>12.2f} EUR")
            print()
    else:
        vat_title = "Umsatzsteuer-Voranmeldung (Berechnung)"
        if open_entertainment:
            vat_title = "Umsatzsteuer-Voranmeldung (Teilwerte, Bewirtungsprüfung offen)"
        print(f"{vat_title}:")
        print(f"  {'Umsatzsteuer (aus Einnahmen + RC)':<40} {total_vat_output:>12.2f} EUR")
        print(f"  {'Abziehbare Vorsteuer (aus Ausgaben)':<40} {-total_vat_input:>12.2f} EUR")
        print("  " + "-" * 54)
        label = "ZAHLLAST" if vat_payment >= 0 else "ERSTATTUNG"
        print(f"  {label:<40} {vat_payment:>12.2f} EUR")
        print()

    income_rows = conn.execute(
        """SELECT c.name, c.eur_key, SUM(i.amount_eur) as total
           FROM income i
           LEFT JOIN categories c ON i.category_id = c.id
           WHERE i.payment_date IS NOT NULL
             AND strftime('%Y', i.payment_date) = ?
           GROUP BY c.id
           ORDER BY c.name""",
        (str(year),),
    ).fetchall()
    subset_total = sum(
        Decimal(str(row["total"] or 0))
        for row in income_rows
        if is_small_business_subset(row["eur_key"])
    )
    ku_total = (
        sum(
            Decimal(str(row["total"] or 0))
            for row in income_rows
            if row["eur_key"] == "small_business_income"
        )
        + subset_total
    )

    print("Einnahmen nach Kategorie:")
    income_total = Decimal("0.00")
    has_ku_income = any(row["eur_key"] == "small_business_income" for row in income_rows)
    for row in income_rows:
        key = row["eur_key"]
        if is_small_business_subset(key) or key == "small_business_income":
            continue
        amount = Decimal(str(row["total"] or 0))
        label = _eur_label(row["name"], key, year)
        print(f"  {label:<56} {amount:>12.2f} EUR")
        income_total += amount
    if has_ku_income or subset_total:
        ku_label = _eur_label(
            "Betriebseinnahmen als Kleinunternehmer",
            "small_business_income",
            year,
        )
        print(f"  {ku_label:<56} {ku_total:>12.2f} EUR")
        income_total += ku_total
    if subset_total:
        field = get_eur_field(year, "small_business_non_taxable_subset")
        line_text = f" (Zeile {field.line})" if field is not None else ""
        print(
            f"  {'davon: Nicht steuerbare Kleinunternehmerumsätze' + line_text:<56} "
            f"{subset_total:>12.2f} EUR"
        )
    print("  " + "-" * 70)
    print(f"  {'GESAMT Einnahmen':<56} {income_total:>12.2f} EUR")
    print()

    result = income_total + expense_total
    if open_entertainment:
        print(
            f"Vorläufiger Zwischensaldo ohne ungeprüfte Bewirtungen: {result:.2f} EUR "
            "(unvollständig)"
        )
    else:
        print("  " + "=" * 70)
        label = "GEWINN" if result >= 0 else "VERLUST"
        print(f"  {label:<56} {result:>12.2f} EUR")

    if args.include_private:
        summary = get_private_summary(conn, year=year)
        deposits = get_eur_field(year, "private_deposits")
        withdrawals = get_eur_field(year, "private_withdrawals")
        deposit_label = (
            f"Privateinlagen (Zeile {deposits.line})"
            if deposits
            else "Privateinlagen (Zeile ungeprüft)"
        )
        withdrawal_label = (
            f"Privatentnahmen (Zeile {withdrawals.line})"
            if withdrawals
            else "Privatentnahmen (Zeile ungeprüft)"
        )
        print()
        print("Privatvorgänge:")
        print(f"  {deposit_label:<56} {summary['deposits_total']:>12.2f} EUR")
        print(f"  {withdrawal_label:<56} {summary['withdrawals_total']:>12.2f} EUR")

    conn.close()
