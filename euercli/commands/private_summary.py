from pathlib import Path

from ..db import get_db_connection
from ..services.eur import get_eur_field
from ..services.private_transfers import get_private_summary


def print_private_summary(conn, year: int) -> None:
    summary = get_private_summary(conn, year=year)

    print(f"Privateinlagen & Privatentnahmen für ELSTER {year}")
    print("=" * 49)
    print()

    deposit_field = get_eur_field(year, "private_deposits")
    withdrawal_field = get_eur_field(year, "private_withdrawals")
    deposit_line = f" (Zeile {deposit_field.line})" if deposit_field else " (Zeile nicht geprüft)"
    withdrawal_line = (
        f" (Zeile {withdrawal_field.line})" if withdrawal_field else " (Zeile nicht geprüft)"
    )

    print(f"Privateinlagen{deposit_line}:")
    print(
        "  "
        f"{'Sacheinlagen (persistiert in expenses):':<46}"
        f"{summary['deposits_private_paid']:>10.2f} EUR"
    )
    print(f"  {'Direkte Einlagen (private_transfers):':<46}{summary['deposits_direct']:>10.2f} EUR")
    print("  " + "-" * 58)
    print(f"  {'GESAMT Privateinlagen:':<46}{summary['deposits_total']:>10.2f} EUR")
    print()

    print(f"Privatentnahmen{withdrawal_line}:")
    print(
        f"  {'Direkte Entnahmen (private_transfers):':<46}{summary['withdrawals_total']:>10.2f} EUR"
    )
    print("  " + "-" * 58)
    print(f"  {'GESAMT Privatentnahmen:':<46}{summary['withdrawals_total']:>10.2f} EUR")
    print()
    print("  " + "=" * 58)
    print(f"  {'SALDO (Einlagen - Entnahmen):':<46}{summary['balance']:>10.2f} EUR")


def cmd_private_summary(args):
    """Zeigt ELSTER-relevante Privatvorgänge für ein Jahr."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    try:
        print_private_summary(conn, args.year)
    finally:
        conn.close()
