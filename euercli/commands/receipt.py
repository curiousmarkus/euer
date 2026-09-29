import csv
import json
import os
import platform
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path

from ..config import get_receipt_config, load_config, resolve_receipt_path
from ..db import get_db_connection
from ..services.errors import ValidationError
from ..services.receipts import ScanError, UnbookedResult, find_unbooked_receipts


def _load_receipt_config(config: dict):
    try:
        receipt_config = get_receipt_config(config)
    except ValidationError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)

    if not receipt_config.root:
        print("Fehler: Kein Beleg-Root konfiguriert.", file=sys.stderr)
        print("Setze z.B.: euer setup --set receipts.root /pfad/zu/Buchhaltung", file=sys.stderr)
        print("Siehe: euer config show", file=sys.stderr)
        sys.exit(1)

    return receipt_config


def _print_checked_paths(paths: list[Path]) -> None:
    for path in paths:
        print(f"      - {path}")


def cmd_receipt_unbooked(args):
    """Zeigt Belegdateien ohne zugeordnete aktive Buchung."""
    try:
        result = find_unbooked_receipts(
            Path(args.db), load_config(), args.year or datetime.now().year, args.type
        )
    except (ValidationError, OSError, tomllib.TOMLDecodeError) as exc:
        result = UnbookedResult(
            year=args.year or datetime.now().year,
            types=[args.type] if args.type else ["expense", "income"],
            errors=[ScanError("invalid_config", str(exc))],
        )
    if args.format == "json":
        print(json.dumps(result.to_dict(), ensure_ascii=False))
    elif args.format == "csv":
        if result.scan_complete:
            writer = csv.writer(sys.stdout, lineterminator="\n")
            writer.writerow(["type", "path", "receipt_name", "size_bytes", "modified_at"])
            for item in result.unbooked_files:
                writer.writerow(
                    [item.type, item.path, item.receipt_name, item.size_bytes, item.modified_at]
                )
        _print_unbooked_diagnostics(result, sys.stderr)
    elif result.scan_complete:
        labels = {"expense": "Ausgaben", "income": "Einnahmen"}
        kinds = ", ".join(labels[kind] for kind in result.types)
        print(f"Belegdateien ohne zugeordnete Buchung {result.year} ({kinds})")
        print("=" * 50)
        for item in result.unbooked_files:
            size_kb = max(1, round(item.size_bytes / 1024)) if item.size_bytes > 0 else 0
            print(f"{item.path:<48} {size_kb:>6} KB")
        print(f"\nBerücksichtigte Belegdateien: {result.total_files}")
        print(f"Davon referenziert:          {result.referenced_files}")
        print(f"Ohne Zuordnung:              {result.unbooked_count}")
        print(f"Übersprungene Einträge:      {result.skipped_count}")
        print("Prüfstatus: vollständig")
        _print_unbooked_diagnostics(result, sys.stdout)
        if result.unbooked_count:
            print("\nPrüfe zuerst bestehende Buchungen und die Ablage im Zahlungsjahr.")
            print("Ordne vorhandenen Buchungen den Beleg mit 'update ... --receipt ...' zu.")
            print("Lege nur für noch nicht erfasste Vorgänge eine neue Buchung an.")
    else:
        print("Prüfstatus: unvollständig", file=sys.stderr)
        _print_unbooked_diagnostics(result, sys.stderr)
    if not result.scan_complete:
        sys.exit(2)
    if result.unbooked_count:
        sys.exit(1)


def _print_unbooked_diagnostics(result, stream):
    for item in result.skipped_entries:
        print(f"Übersprungen ({item.reason}): {item.path}", file=stream)
    for item in result.warnings:
        suffix = f" {item.path}" if item.path else ""
        print(
            f"Warnung ({item.code}, {item.type} #{item.record_id}): {item.message}{suffix}",
            file=stream,
        )
    for item in result.errors:
        suffix = f" {item.path}" if item.path else ""
        print(f"Fehler ({item.code}): {item.message}{suffix}", file=stream)
    if result.scan_complete and stream is sys.stderr:
        print(
            f"Belegdateien: {result.total_files}; referenziert: {result.referenced_files}; "
            f"ohne Zuordnung: {result.unbooked_count}; übersprungen: {result.skipped_count}",
            file=stream,
        )


def cmd_receipt_check(args):
    """Prüft alle Transaktionen auf fehlende Belege."""
    config = load_config()
    _load_receipt_config(config)

    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    year = args.year or datetime.now().year
    print(f"Beleg-Prüfung {year}")
    print("=" * 50)
    print()

    missing_count = {"expenses": 0, "income": 0}
    total_count = {"expenses": 0, "income": 0}

    # Ausgaben prüfen
    if args.type in (None, "expense"):
        expenses = conn.execute(
            """SELECT e.id, e.payment_date, e.invoice_date, e.vendor, e.receipt_name
               FROM expenses e
               WHERE strftime('%Y', COALESCE(e.payment_date, e.invoice_date)) = ?
                 AND e.deleted_at IS NULL
               ORDER BY COALESCE(e.payment_date, e.invoice_date), e.id""",
            (str(year),),
        ).fetchall()

        missing_expenses = []
        for r in expenses:
            receipt_date = r["payment_date"]
            display_date = r["payment_date"] or r["invoice_date"] or ""
            total_count["expenses"] += 1
            if not r["receipt_name"]:
                missing_expenses.append((r["id"], display_date, r["vendor"], "(kein Beleg)", []))
                missing_count["expenses"] += 1
                continue

            path, checked_paths = resolve_receipt_path(
                r["receipt_name"],
                receipt_date,
                "expenses",
                config,
                fallback_year=year,
            )
            if path is None:
                missing_expenses.append(
                    (r["id"], display_date, r["vendor"], r["receipt_name"], checked_paths)
                )
                missing_count["expenses"] += 1

        if missing_expenses:
            print("Fehlende Belege (Ausgaben)")
            print("-" * 60)
            for r in missing_expenses:
                print(f"  #{r[0]:<4} {r[1]} {r[2]:<20} {r[3]}")
                _print_checked_paths(r[4])
            print()

    # Einnahmen prüfen
    if args.type in (None, "income"):
        income = conn.execute(
            """SELECT i.id, i.payment_date, i.invoice_date, i.source, i.receipt_name
               FROM income i
               WHERE strftime('%Y', COALESCE(i.payment_date, i.invoice_date)) = ?
                 AND i.deleted_at IS NULL
               ORDER BY COALESCE(i.payment_date, i.invoice_date), i.id""",
            (str(year),),
        ).fetchall()

        missing_income = []
        for r in income:
            receipt_date = r["payment_date"]
            display_date = r["payment_date"] or r["invoice_date"] or ""
            total_count["income"] += 1
            if not r["receipt_name"]:
                missing_income.append((r["id"], display_date, r["source"], "(kein Beleg)", []))
                missing_count["income"] += 1
                continue

            path, checked_paths = resolve_receipt_path(
                r["receipt_name"],
                receipt_date,
                "income",
                config,
                fallback_year=year,
            )
            if path is None:
                missing_income.append(
                    (r["id"], display_date, r["source"], r["receipt_name"], checked_paths)
                )
                missing_count["income"] += 1

        if missing_income:
            print("Fehlende Belege (Einnahmen)")
            print("-" * 60)
            for r in missing_income:
                print(f"  #{r[0]:<4} {r[1]} {r[2]:<20} {r[3]}")
                _print_checked_paths(r[4])
            print()

    conn.close()

    total_missing = missing_count["expenses"] + missing_count["income"]
    total_checked = total_count["expenses"] + total_count["income"]

    print("Zusammenfassung")
    print("-" * 60)
    print(f"  Ausgaben geprüft: {total_count['expenses']}")
    print(f"  Einnahmen geprüft: {total_count['income']}")
    print(f"  Gesamt geprüft:    {total_checked}")
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
    _load_receipt_config(config)

    db_path = Path(args.db)
    conn = get_db_connection(db_path)

    table = args.table
    if table == "expenses":
        row = conn.execute(
            "SELECT id, payment_date, invoice_date, receipt_name FROM expenses WHERE id = ? AND deleted_at IS NULL",
            (args.id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, payment_date, invoice_date, receipt_name FROM income WHERE id = ? AND deleted_at IS NULL",
            (args.id,),
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
        row["receipt_name"], row["payment_date"], receipt_type, config
    )

    if not found_path:
        print(f"Fehler: Beleg '{row['receipt_name']}' nicht gefunden.", file=sys.stderr)
        if not row["payment_date"]:
            print(
                "Hinweis: Ohne Wertstellungsdatum kann kein jahresbezogener "
                "Belegpfad abgeleitet werden.",
                file=sys.stderr,
            )
            print(
                f"Setze zuerst: euer update {'expense' if table == 'expenses' else 'income'} "
                f"{args.id} --payment-date YYYY-MM-DD",
                file=sys.stderr,
            )
        for p in checked_paths:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    _open_path(found_path)
