import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ..config import load_config, resolve_receipt_path
from ..db import get_db_connection


def cmd_receipt_check(args):
    """Prüft alle Transaktionen auf fehlende Belege."""
    config = load_config()
    receipts_config = config.get("receipts", {})

    if not receipts_config.get("expenses") and not receipts_config.get("income"):
        print("Fehler: Keine Beleg-Pfade konfiguriert.", file=sys.stderr)
        print("Siehe: python -m euercli config show", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    year = args.year or datetime.now().year
    print(f"Beleg-Prüfung {year}")
    print("=" * 50)
    print()

    missing_count = {"expenses": 0, "income": 0}
    total_count = {"expenses": 0, "income": 0}

    # Ausgaben prüfen
    if args.type in (None, "expense") and receipts_config.get("expenses"):
        expenses = conn.execute(
            """SELECT e.id, e.date, e.vendor, e.receipt_name
               FROM expenses e
               WHERE strftime('%Y', e.date) = ?
               ORDER BY e.date, e.id""",
            (str(year),),
        ).fetchall()

        missing_expenses = []
        for r in expenses:
            total_count["expenses"] += 1
            if not r["receipt_name"]:
                missing_expenses.append(
                    (r["id"], r["date"], r["vendor"], "(kein Beleg)")
                )
                missing_count["expenses"] += 1
                continue

            path, _ = resolve_receipt_path(
                r["receipt_name"], r["date"], "expenses", config
            )
            if path is None:
                missing_expenses.append(
                    (r["id"], r["date"], r["vendor"], r["receipt_name"])
                )
                missing_count["expenses"] += 1

        if missing_expenses:
            print("Fehlende Belege (Ausgaben)")
            print("-" * 60)
            for r in missing_expenses:
                print(f"  #{r[0]:<4} {r[1]} {r[2]:<20} {r[3]}")
            print()

    # Einnahmen prüfen
    if args.type in (None, "income") and receipts_config.get("income"):
        income = conn.execute(
            """SELECT i.id, i.date, i.source, i.receipt_name
               FROM income i
               WHERE strftime('%Y', i.date) = ?
               ORDER BY i.date, i.id""",
            (str(year),),
        ).fetchall()

        missing_income = []
        for r in income:
            total_count["income"] += 1
            if not r["receipt_name"]:
                missing_income.append(
                    (r["id"], r["date"], r["source"], "(kein Beleg)")
                )
                missing_count["income"] += 1
                continue

            path, _ = resolve_receipt_path(
                r["receipt_name"], r["date"], "income", config
            )
            if path is None:
                missing_income.append(
                    (r["id"], r["date"], r["source"], r["receipt_name"])
                )
                missing_count["income"] += 1

        if missing_income:
            print("Fehlende Belege (Einnahmen)")
            print("-" * 60)
            for r in missing_income:
                print(f"  #{r[0]:<4} {r[1]} {r[2]:<20} {r[3]}")
            print()

    conn.close()

    total_missing = missing_count["expenses"] + missing_count["income"]
    total_checked = total_count["expenses"] + total_count["income"]

    print("Zusammenfassung")
    print("-" * 60)
    print(f"  Ausgaben geprüft: {total_count['expenses']}")
    print(f"  Einnahmen geprüft: {total_count['income']}")
    print(f"  Fehlende Belege:   {total_missing}")

    if total_missing > 0:
        sys.exit(1)


def _open_path(path: Path) -> None:
    if platform.system() == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    elif platform.system() == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def cmd_receipt_open(args):
    """Öffnet Beleg einer Transaktion."""
    config = load_config()
    receipts_config = config.get("receipts", {})

    if not receipts_config.get("expenses") and not receipts_config.get("income"):
        print("Fehler: Keine Beleg-Pfade konfiguriert.", file=sys.stderr)
        print("Siehe: python -m euercli config show", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    table = args.table
    if table == "expenses":
        row = conn.execute(
            "SELECT id, date, receipt_name FROM expenses WHERE id = ?", (args.id,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, date, receipt_name FROM income WHERE id = ?", (args.id,)
        ).fetchone()

    conn.close()

    if not row:
        print(f"Fehler: Datensatz #{args.id} nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    if not row["receipt_name"]:
        print("Fehler: Kein Beleg angegeben.", file=sys.stderr)
        sys.exit(1)

    receipt_type = "expenses" if table == "expenses" else "income"
    found_path, checked_paths = resolve_receipt_path(
        row["receipt_name"], row["date"], receipt_type, config
    )

    if not found_path:
        print(
            f"Fehler: Beleg '{row['receipt_name']}' nicht gefunden.", file=sys.stderr
        )
        for p in checked_paths:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    _open_path(found_path)
