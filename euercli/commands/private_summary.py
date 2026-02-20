from pathlib import Path

from ..db import get_db_connection
from ..services.private_transfers import get_private_summary


def print_private_summary(conn, year: int) -> None:
    summary = get_private_summary(conn, year=year)

    print(f"Privateinlagen & Privatentnahmen für ELSTER {year}")
    print("=" * 49)
    print()

    print("Privateinlagen (Zeile 122):")
    print(
        "  "
        f"{'Sacheinlagen (persistiert in expenses):':<46}"
        f"{summary['deposits_sacheinlagen']:>10.2f} EUR"
    )
    print(
        "  "
        f"{'Direkte Einlagen (private_transfers):':<46}"
        f"{summary['deposits_direct']:>10.2f} EUR"
    )
    print("  " + "-" * 58)
    print(
        "  "
        f"{'GESAMT Privateinlagen:':<46}"
        f"{summary['deposits_total']:>10.2f} EUR"
    )
    print()

    print("Privatentnahmen (Zeile 121):")
    print(
        "  "
        f"{'Direkte Entnahmen (private_transfers):':<46}"
        f"{summary['withdrawals_total']:>10.2f} EUR"
    )
    print("  " + "-" * 58)
    print(
        "  "
        f"{'GESAMT Privatentnahmen:':<46}"
        f"{summary['withdrawals_total']:>10.2f} EUR"
    )


def cmd_private_summary(args):
    """Zeigt ELSTER-relevante Privatvorgänge für ein Jahr."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    try:
        print_private_summary(conn, args.year)
    finally:
        conn.close()
