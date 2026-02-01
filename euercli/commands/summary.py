from datetime import datetime
from pathlib import Path

from ..config import load_config
from ..db import get_db_connection
from ..importers import get_tax_config


def cmd_summary(args):
    """Zeigt Kategorie-Zusammenfassung."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    tax_mode = get_tax_config(config)

    year = args.year or datetime.now().year

    print(f"EÜR-Zusammenfassung {year}")
    print("=" * 50)
    print()

    # Ausgaben nach Kategorie
    expenses = conn.execute(
        """SELECT c.name, c.eur_line, SUM(e.amount_eur) as total
           FROM expenses e
           JOIN categories c ON e.category_id = c.id
           WHERE strftime('%Y', e.date) = ?
           GROUP BY c.id
           ORDER BY c.eur_line, c.name""",
        (str(year),),
    ).fetchall()

    print("Ausgaben nach Kategorie:")
    expense_total = 0.0
    for r in expenses:
        cat = f"{r['name']} ({r['eur_line']})" if r["eur_line"] else r["name"]
        print(f"  {cat:<40} {r['total']:>12.2f} EUR")
        expense_total += r["total"]
    print("  " + "-" * 54)
    print(f"  {'GESAMT Ausgaben':<40} {expense_total:>12.2f} EUR")
    print()

    # Steuerberechnung (USt-Zahllast)

    # Ausgaben: Vorsteuer (Input) und RC USt (Output)
    # Beachte: vat_output ist nun der korrekte Spaltenname (alt: vat_amount)
    vat_stats_expenses = conn.execute(
        """SELECT SUM(vat_input) as sum_input, SUM(vat_output) as sum_output
           FROM expenses
           WHERE strftime('%Y', date) = ?""",
        (str(year),),
    ).fetchone()

    exp_vat_input = vat_stats_expenses["sum_input"] or 0.0
    exp_vat_output = vat_stats_expenses["sum_output"] or 0.0

    # Einnahmen: USt (Output)
    # income hat nun auch vat_output
    vat_stats_income = conn.execute(
        """SELECT SUM(vat_output) as sum_output
           FROM income
           WHERE strftime('%Y', date) = ?""",
        (str(year),),
    ).fetchone()

    inc_vat_output = vat_stats_income["sum_output"] or 0.0

    total_vat_input = exp_vat_input
    total_vat_output = exp_vat_output + inc_vat_output
    vat_payment = total_vat_output - total_vat_input

    if tax_mode == "small_business":
        if total_vat_output != 0:
            print("Umsatzsteuer (Kleinunternehmer):")
            print(
                f"  {'USt aus Reverse-Charge (Schuld)':<40} {total_vat_output:>12.2f} EUR"
            )
            print()
    else:
        # Regelbesteuerung
        print("Umsatzsteuer-Voranmeldung (Berechnung):")
        print(
            f"  {'Umsatzsteuer (aus Einnahmen + RC)':<40} {total_vat_output:>12.2f} EUR"
        )
        print(
            f"  {'Abziehbare Vorsteuer (aus Ausgaben)':<40} {-total_vat_input:>12.2f} EUR"
        )
        print("  " + "-" * 54)
        label = "ZAHLLAST" if vat_payment >= 0 else "ERSTATTUNG"
        print(f"  {label:<40} {vat_payment:>12.2f} EUR")
        print()

    # Einnahmen nach Kategorie
    income = conn.execute(
        """SELECT c.name, c.eur_line, SUM(i.amount_eur) as total
           FROM income i
           JOIN categories c ON i.category_id = c.id
           WHERE strftime('%Y', i.date) = ?
           GROUP BY c.id
           ORDER BY c.eur_line, c.name""",
        (str(year),),
    ).fetchall()

    print("Einnahmen nach Kategorie:")
    income_total = 0.0
    for r in income:
        cat = f"{r['name']} ({r['eur_line']})" if r["eur_line"] else r["name"]
        print(f"  {cat:<40} {r['total']:>12.2f} EUR")
        income_total += r["total"]
    print("  " + "-" * 54)
    print(f"  {'GESAMT Einnahmen':<40} {income_total:>12.2f} EUR")
    print()

    print("  " + "=" * 54)
    result = income_total + expense_total  # expense_total ist negativ
    label = "GEWINN" if result >= 0 else "VERLUST"
    print(f"  {label:<40} {result:>12.2f} EUR")

    conn.close()
