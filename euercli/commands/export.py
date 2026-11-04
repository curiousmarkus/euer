import csv
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .. import VERSION
from ..config import get_export_dir, get_ledger_accounts, load_config
from ..constants import DEFAULT_EXPORT_DIR
from ..db import get_db_connection
from ..services.entertainment import calculate_entertainment_breakdown
from ..services.errors import ValidationError
from ..services.eur import (
    get_category_display_name,
    get_category_eur_line,
    is_entertainment_category,
)
from ..services.export import (
    compute_db_snapshot_hash,
    compute_file_metadata,
    create_manifest,
    format_versioned_dir_name,
    publish_export,
    verify_manifest,
)
from ..utils import format_rc_type

# Optional: openpyxl für XLSX-Export
try:
    import openpyxl

    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def cmd_export(args):
    """Exportiert Daten als CSV oder XLSX."""
    try:
        _cmd_export(args)
    except (OSError, sqlite3.Error, ValueError, ValidationError) as exc:
        print(f"Fehler beim Export: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_export(args):
    """Steuert Export und Manifestprüfung mit aufrufbezogener Fehlerbehandlung."""
    explicit_verify = bool(getattr(args, "verify", None))
    config = {} if explicit_verify else load_config()
    config_export_dir = get_export_dir(config)

    if args.output:
        output_dir = Path(args.output)
    elif config_export_dir:
        output_dir = Path(config_export_dir)
    else:
        output_dir = DEFAULT_EXPORT_DIR

    # Modus: Manifestprüfung (--verify)
    if getattr(args, "verify", None) is not None:
        target_str = args.verify.strip() if isinstance(args.verify, str) else ""
        if not target_str:
            if not output_dir.exists():
                print(
                    f"Fehler: Ausgabeverzeichnis {output_dir} existiert nicht.\n"
                    "Bitte Pfad angeben: euer export --verify PFAD",
                    file=sys.stderr,
                )
                sys.exit(1)
            candidates = [
                p
                for p in output_dir.iterdir()
                if p.name.startswith("export_") and p.is_dir() and (p / "manifest.json").is_file()
            ]
            if not candidates:
                print(
                    f"Fehler: Kein versionierter Exportordner mit manifest.json in {output_dir} gefunden.\n"
                    "Bitte Pfad angeben: euer export --verify PFAD",
                    file=sys.stderr,
                )
                sys.exit(1)
            candidates.sort(key=lambda p: (p / "manifest.json").stat().st_mtime_ns, reverse=True)
            verify_path = candidates[0]
        else:
            verify_path = Path(target_str)

        is_valid, errors, manifest = verify_manifest(verify_path)
        if not is_valid:
            print("Fehler bei der Manifestprüfung:", file=sys.stderr)
            for err in errors:
                print(f"  ❌ {err}", file=sys.stderr)
            print(
                "\nHinweis: Manifest und Exportdateien auf fehlende oder ungültige Angaben prüfen.",
                file=sys.stderr,
            )
            sys.exit(1)

        base_dir = verify_path if verify_path.is_dir() else verify_path.parent
        files_count = len(manifest.get("files", [])) if manifest else 0
        print(
            f"✓ Manifestprüfung erfolgreich: Alle {files_count} Dateien stimmen mit dem Manifest überein."
        )
        print(f"  Ordner: {base_dir}")
        if manifest:
            print(f"  Erzeugungszeit: {manifest.get('created_at', '-')}")
            print(f"  euer-Version: {manifest.get('euer_version', '-')}")
            db_info = manifest.get("database", {})
            if isinstance(db_info, dict) and "snapshot_sha256" in db_info:
                print(f"  DB-Snapshot (SHA-256): {db_info['snapshot_sha256']}")
        sys.exit(0)

    is_versioned = bool(getattr(args, "versioned", False))
    if is_versioned and args.format == "xlsx" and not HAS_OPENPYXL:
        print(
            "Fehler: openpyxl nicht installiert. Bitte 'pip install openpyxl'.",
            file=sys.stderr,
        )
        sys.exit(1)

    year = args.year
    now = datetime.now().astimezone()
    versioned_dir_name = format_versioned_dir_name(year, now, VERSION) if is_versioned else None
    versioned_target_dir = (output_dir / versioned_dir_name) if versioned_dir_name else None

    if is_versioned and versioned_target_dir.exists():
        print(
            f"Fehler: Versionierter Exportordner existiert bereits: {versioned_target_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    exp_suffix = f"_{year}" if year is not None else ""
    if not is_versioned:
        output_dir.mkdir(exist_ok=True)
        if args.format == "csv":
            planned_targets = [
                output_dir / f"EÜR{exp_suffix}_Ausgaben.csv",
                output_dir / f"EÜR{exp_suffix}_Einnahmen.csv",
                output_dir / f"EÜR{exp_suffix}_PrivateTransfers.csv",
                output_dir / f"EÜR{exp_suffix}_Sacheinlagen.csv",
            ]
        else:
            planned_targets = [
                output_dir / f"EÜR{exp_suffix}_Ausgaben.xlsx",
                output_dir / f"EÜR{exp_suffix}_Einnahmen.xlsx",
                output_dir / f"EÜR{exp_suffix}_Privatvorgaenge.xlsx",
            ]

        existing_files = [p for p in planned_targets if p.exists()]
        if existing_files and not getattr(args, "force", False):
            print("Fehler: Zieldatei(en) existieren bereits:", file=sys.stderr)
            for p in existing_files:
                print(f"  - {p}", file=sys.stderr)
            print(
                "Bitte '--force' angeben, um bestehende Exportdateien zu überschreiben.",
                file=sys.stderr,
            )
            sys.exit(1)

    db_path = Path(args.db)

    try:
        ledger_accounts = get_ledger_accounts(config)
    except ValidationError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)
    ledger_account_numbers = {
        account.key.lower(): account.account_number or "" for account in ledger_accounts
    }

    if year is not None:
        year_filter = "WHERE e.deleted_at IS NULL AND strftime('%Y', COALESCE(e.payment_date, e.invoice_date)) = ?"
        year_params = (str(year),)
        income_filter = "WHERE i.deleted_at IS NULL AND strftime('%Y', COALESCE(i.payment_date, i.invoice_date)) = ?"
        income_params = (str(year),)
        private_filter = "WHERE p.deleted_at IS NULL AND strftime('%Y', p.date) = ?"
        private_params = (str(year),)
        sacheinlagen_filter = (
            "WHERE e.deleted_at IS NULL AND e.is_private_paid = 1 "
            "AND strftime('%Y', COALESCE(e.payment_date, e.invoice_date)) = ?"
        )
        sacheinlagen_params = (str(year),)
    else:
        year_filter = "WHERE e.deleted_at IS NULL"
        year_params = ()
        income_filter = "WHERE i.deleted_at IS NULL"
        income_params = ()
        private_filter = "WHERE p.deleted_at IS NULL"
        private_params = ()
        sacheinlagen_filter = "WHERE e.deleted_at IS NULL AND e.is_private_paid = 1"
        sacheinlagen_params = ()

    with closing(get_db_connection(db_path, read_only=True)) as conn:
        # Eine Lesetransaktion bindet alle Abfragen und das Backup an denselben Stand.
        conn.execute("BEGIN")
        has_private_transfers = (
            conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='private_transfers'"
            ).fetchone()
            is not None
        )
        expense_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
        }
        has_private_expense_cols = {
            "is_private_paid",
            "private_classification",
        }.issubset(expense_columns)

        # Ausgaben laden
        expenses = conn.execute(
            f"""SELECT e.receipt_name, e.payment_date, e.invoice_date, e.invoice_number, e.vendor,
                      c.name as category, c.eur_key,
                      e.amount_eur, e.account, e.ledger_account, e.foreign_amount, e.notes,
                      e.rc_type, e.vat_input, e.vat_output, e.vat_rate, e.vat_code,
                      e.entertainment_tip_eur, e.entertainment_vat_status
               FROM expenses e
               LEFT JOIN categories c ON e.category_id = c.id
               {year_filter}
               ORDER BY COALESCE(e.payment_date, e.invoice_date), e.id""",
            year_params,
        ).fetchall()

        # Einnahmen laden
        income = conn.execute(
            f"""SELECT i.receipt_name, i.payment_date, i.invoice_date, i.invoice_number, i.source,
                      c.name as category, c.eur_key,
                      i.amount_eur, i.account, i.ledger_account, i.foreign_amount, i.notes,
                      i.vat_output, i.vat_rate, i.vat_code
               FROM income i
               LEFT JOIN categories c ON i.category_id = c.id
               {income_filter}
               ORDER BY COALESCE(i.payment_date, i.invoice_date), i.id""",
            income_params,
        ).fetchall()

        if has_private_transfers:
            private_transfers = conn.execute(
                f"""SELECT p.id, p.date, p.type, p.amount_eur, p.description,
                          p.notes, p.related_expense_id
                   FROM private_transfers p
                   {private_filter}
                   ORDER BY p.date, p.id""",
                private_params,
            ).fetchall()
        else:
            private_transfers = []

        if has_private_expense_cols:
            sacheinlagen = conn.execute(
                f"""SELECT e.id, e.payment_date, e.invoice_date, e.vendor,
                          c.name as category, e.amount_eur,
                          e.account, e.private_classification
                   FROM expenses e
                   LEFT JOIN categories c ON e.category_id = c.id
                   {sacheinlagen_filter}
                   ORDER BY COALESCE(e.payment_date, e.invoice_date), e.id""",
                sacheinlagen_params,
            ).fetchall()
        else:
            sacheinlagen = []

        db_snapshot_hash = compute_db_snapshot_hash(conn) if is_versioned else ""

    def category_label(name: str | None, category_key: str | None) -> str:
        if not name:
            return "Ohne Kategorie"
        name = get_category_display_name(name, category_key) or name
        line = get_category_eur_line(year, category_key) if year is not None else None
        return f"{name} ({line})" if line is not None else name

    def entertainment_export_values(row) -> tuple[str, str, str, str, str]:
        tip = (
            f"{row['entertainment_tip_eur']:.2f}"
            if row["entertainment_tip_eur"] is not None
            else ""
        )
        status = row["entertainment_vat_status"] or ""
        if not is_entertainment_category(row["eur_key"]):
            return tip, status, "", "", ""
        breakdown = calculate_entertainment_breakdown(
            amount_eur=row["amount_eur"],
            vat_input=row["vat_input"],
            vat_status=row["entertainment_vat_status"],
            rc_type=row["rc_type"],
        )
        return (
            tip,
            status,
            f"{breakdown.cost_basis_eur:.2f}" if breakdown.cost_basis_eur is not None else "",
            f"{breakdown.deductible_eur:.2f}" if breakdown.deductible_eur is not None else "",
            (
                f"{breakdown.non_deductible_eur:.2f}"
                if breakdown.non_deductible_eur is not None
                else ""
            ),
        )

    staging_files: list[tuple[Path, Path]] = []
    tmp_stage_dir: Path | None = None
    if is_versioned:
        output_dir.mkdir(parents=True, exist_ok=True)
        tmp_stage_dir = Path(tempfile.mkdtemp(dir=output_dir, prefix=".versioned_stage_"))

    def make_target_path(filename: str) -> Path:
        if is_versioned:
            assert tmp_stage_dir is not None
            return tmp_stage_dir / filename
        target = output_dir / filename
        tmp = target.with_name(f".{target.name}.tmp.{uuid.uuid4().hex[:8]}")
        staging_files.append((tmp, target))
        return tmp

    try:
        if args.format == "csv":
            # CSV Export
            exp_suffix = f"_{year}" if year is not None else ""
            exp_tmp = make_target_path(f"EÜR{exp_suffix}_Ausgaben.csv")
            with open(exp_tmp, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Belegname",
                        "Wertstellung",
                        "Rechnungsdatum",
                        "Rechnungsnummer",
                        "Lieferant",
                        "Kategorie",
                        "EUR",
                        "Konto",
                        "Buchungskonto",
                        "Kontonummer",
                        "Fremdwährung",
                        "Bemerkung",
                        "RC",
                        "Vorsteuer",
                        "Umsatzsteuer",
                        "Steuersatz",
                        "Steuerklasse",
                        "Trinkgeld",
                        "Bewirtung Vorsteuerstatus",
                        "Bewirtung Kostenbasis",
                        "Bewirtung abziehbar",
                        "Bewirtung nicht abziehbar",
                    ]
                )
                for r in expenses:
                    cat = category_label(r["category"], r["eur_key"])
                    entertainment_values = entertainment_export_values(r)
                    writer.writerow(
                        [
                            r["receipt_name"] or "",
                            r["payment_date"] or "",
                            r["invoice_date"] or "",
                            r["invoice_number"] or "",
                            r["vendor"],
                            cat,
                            f"{r['amount_eur']:.2f}",
                            r["account"] or "",
                            r["ledger_account"] or "",
                            ledger_account_numbers.get((r["ledger_account"] or "").lower(), ""),
                            r["foreign_amount"] or "",
                            r["notes"] or "",
                            format_rc_type(r["rc_type"]),
                            f"{r['vat_input']:.2f}" if r["vat_input"] else "",
                            f"{r['vat_output']:.2f}" if r["vat_output"] else "",
                            f"{r['vat_rate']:g}" if r["vat_rate"] is not None else "",
                            r["vat_code"] or "",
                            *entertainment_values,
                        ]
                    )

            inc_tmp = make_target_path(f"EÜR{exp_suffix}_Einnahmen.csv")
            with open(inc_tmp, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Belegname",
                        "Wertstellung",
                        "Rechnungsdatum",
                        "Rechnungsnummer",
                        "Quelle",
                        "Kategorie",
                        "EUR",
                        "Konto",
                        "Buchungskonto",
                        "Kontonummer",
                        "Fremdwährung",
                        "Bemerkung",
                        "Umsatzsteuer",
                        "Steuersatz",
                        "Steuerklasse",
                    ]
                )
                for r in income:
                    cat = category_label(r["category"], r["eur_key"])
                    writer.writerow(
                        [
                            r["receipt_name"] or "",
                            r["payment_date"] or "",
                            r["invoice_date"] or "",
                            r["invoice_number"] or "",
                            r["source"],
                            cat,
                            f"{r['amount_eur']:.2f}",
                            r["account"] or "",
                            r["ledger_account"] or "",
                            ledger_account_numbers.get((r["ledger_account"] or "").lower(), ""),
                            r["foreign_amount"] or "",
                            r["notes"] or "",
                            f"{r['vat_output']:.2f}" if r["vat_output"] else "",
                            f"{r['vat_rate']:g}" if r["vat_rate"] is not None else "",
                            r["vat_code"] or "",
                        ]
                    )

            private_tmp = make_target_path(f"EÜR{exp_suffix}_PrivateTransfers.csv")
            with open(private_tmp, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "ID",
                        "Datum",
                        "Typ",
                        "EUR",
                        "Beschreibung",
                        "Bemerkung",
                        "related_expense_id",
                    ]
                )
                for r in private_transfers:
                    writer.writerow(
                        [
                            r["id"],
                            r["date"],
                            r["type"],
                            f"{r['amount_eur']:.2f}",
                            r["description"],
                            r["notes"] or "",
                            r["related_expense_id"] or "",
                        ]
                    )

            sache_tmp = make_target_path(f"EÜR{exp_suffix}_Sacheinlagen.csv")
            with open(sache_tmp, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "expense_id",
                        "Wertstellung",
                        "Rechnungsdatum",
                        "Lieferant",
                        "Kategorie",
                        "EUR",
                        "Konto",
                        "Klassifikation",
                    ]
                )
                for r in sacheinlagen:
                    writer.writerow(
                        [
                            r["id"],
                            r["payment_date"] or "",
                            r["invoice_date"] or "",
                            r["vendor"],
                            r["category"] or "",
                            f"{abs(r['amount_eur']):.2f}",
                            r["account"] or "",
                            r["private_classification"] or "",
                        ]
                    )

        else:
            # XLSX Export
            if not HAS_OPENPYXL:
                print(
                    "Fehler: openpyxl nicht installiert. Bitte 'pip install openpyxl'.",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Ausgaben
            exp_suffix = f"_{year}" if year is not None else ""
            exp_tmp = make_target_path(f"EÜR{exp_suffix}_Ausgaben.xlsx")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Ausgaben"
            ws.append(
                [
                    "Belegname",
                    "Wertstellung",
                    "Rechnungsdatum",
                    "Rechnungsnummer",
                    "Lieferant",
                    "Kategorie",
                    "EUR",
                    "Konto",
                    "Buchungskonto",
                    "Kontonummer",
                    "Fremdwährung",
                    "Bemerkung",
                    "RC",
                    "Vorsteuer",
                    "Umsatzsteuer",
                    "Steuersatz",
                    "Steuerklasse",
                    "Trinkgeld",
                    "Bewirtung Vorsteuerstatus",
                    "Bewirtung Kostenbasis",
                    "Bewirtung abziehbar",
                    "Bewirtung nicht abziehbar",
                ]
            )
            for r in expenses:
                cat = category_label(r["category"], r["eur_key"])
                entertainment_values = entertainment_export_values(r)
                ws.append(
                    [
                        r["receipt_name"] or "",
                        r["payment_date"] or "",
                        r["invoice_date"] or "",
                        r["invoice_number"] or "",
                        r["vendor"],
                        cat,
                        r["amount_eur"],
                        r["account"] or "",
                        r["ledger_account"] or "",
                        ledger_account_numbers.get((r["ledger_account"] or "").lower(), ""),
                        r["foreign_amount"] or "",
                        r["notes"] or "",
                        format_rc_type(r["rc_type"]),
                        r["vat_input"] if r["vat_input"] else None,
                        r["vat_output"] if r["vat_output"] else None,
                        r["vat_rate"] if r["vat_rate"] is not None else None,
                        r["vat_code"] or "",
                        *[
                            (value if index == 1 else float(value)) if value else None
                            for index, value in enumerate(entertainment_values)
                        ],
                    ]
                )
            wb.save(exp_tmp)

            # Einnahmen
            inc_tmp = make_target_path(f"EÜR{exp_suffix}_Einnahmen.xlsx")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Einnahmen"
            ws.append(
                [
                    "Belegname",
                    "Wertstellung",
                    "Rechnungsdatum",
                    "Rechnungsnummer",
                    "Quelle",
                    "Kategorie",
                    "EUR",
                    "Konto",
                    "Buchungskonto",
                    "Kontonummer",
                    "Fremdwährung",
                    "Bemerkung",
                    "Umsatzsteuer",
                    "Steuersatz",
                    "Steuerklasse",
                ]
            )
            for r in income:
                cat = category_label(r["category"], r["eur_key"])
                ws.append(
                    [
                        r["receipt_name"] or "",
                        r["payment_date"] or "",
                        r["invoice_date"] or "",
                        r["invoice_number"] or "",
                        r["source"],
                        cat,
                        r["amount_eur"],
                        r["account"] or "",
                        r["ledger_account"] or "",
                        ledger_account_numbers.get((r["ledger_account"] or "").lower(), ""),
                        r["foreign_amount"] or "",
                        r["notes"] or "",
                        r["vat_output"] if r["vat_output"] else None,
                        r["vat_rate"] if r["vat_rate"] is not None else None,
                        r["vat_code"] or "",
                    ]
                )
            wb.save(inc_tmp)

            private_tmp = make_target_path(f"EÜR{exp_suffix}_Privatvorgaenge.xlsx")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "PrivateTransfers"
            ws.append(
                [
                    "ID",
                    "Datum",
                    "Typ",
                    "EUR",
                    "Beschreibung",
                    "Bemerkung",
                    "related_expense_id",
                ]
            )
            for r in private_transfers:
                ws.append(
                    [
                        r["id"],
                        r["date"],
                        r["type"],
                        r["amount_eur"],
                        r["description"],
                        r["notes"] or "",
                        r["related_expense_id"] or None,
                    ]
                )

            ws2 = wb.create_sheet("Sacheinlagen")
            ws2.append(
                [
                    "expense_id",
                    "Wertstellung",
                    "Rechnungsdatum",
                    "Lieferant",
                    "Kategorie",
                    "EUR",
                    "Konto",
                    "Klassifikation",
                ]
            )
            for r in sacheinlagen:
                ws2.append(
                    [
                        r["id"],
                        r["payment_date"] or "",
                        r["invoice_date"] or "",
                        r["vendor"],
                        r["category"] or "",
                        abs(r["amount_eur"]),
                        r["account"] or "",
                        r["private_classification"] or "",
                    ]
                )
            wb.save(private_tmp)

        if is_versioned:
            assert tmp_stage_dir is not None
            assert versioned_target_dir is not None
            generated_files = sorted([p for p in tmp_stage_dir.iterdir() if p.is_file()])
            files_meta = [compute_file_metadata(p) for p in generated_files]
            tax_mode = config.get("tax", {}).get("mode", "small_business")
            manifest_data = create_manifest(
                euer_version=VERSION,
                created_at=now.isoformat(timespec="microseconds"),
                report_year=year,
                tax_mode=tax_mode,
                export_format=args.format,
                db_snapshot_hash=db_snapshot_hash,
                files_metadata=files_meta,
            )
            manifest_file = tmp_stage_dir / "manifest.json"
            manifest_file.write_text(
                json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            if versioned_target_dir.exists():
                raise FileExistsError(
                    f"Versionierter Exportordner existiert bereits: {versioned_target_dir}"
                )
            publish_export(tmp_stage_dir, versioned_target_dir)
            print(f"Versionierter Export erfolgreich erstellt: {versioned_target_dir}")
            print(f"Manifest: {versioned_target_dir / 'manifest.json'}")
            for p in generated_files:
                print(f"  - {p.name}")
        else:
            # Individual renames are atomic; restore earlier files if a later rename fails.
            previous: list[tuple[Path, Path | None]] = []
            try:
                for tmp_path, final_path in staging_files:
                    if final_path.exists() and not getattr(args, "force", False):
                        raise FileExistsError(f"Zieldatei existiert bereits: {final_path}")
                    saved = None
                    if final_path.exists():
                        saved = final_path.with_name(f".{final_path.name}.old.{uuid.uuid4().hex}")
                        os.replace(final_path, saved)
                    previous.append((final_path, saved))
                    os.replace(tmp_path, final_path)
            except Exception:
                for final_path, saved in reversed(previous):
                    if saved is None:
                        final_path.unlink(missing_ok=True)
                    else:
                        os.replace(saved, final_path)
                raise
            for _, saved in previous:
                if saved is not None:
                    saved.unlink()
            for _, final_path in staging_files:
                print(f"Exportiert: {final_path}")

    finally:
        if tmp_stage_dir is not None and tmp_stage_dir.exists():
            shutil.rmtree(tmp_stage_dir, ignore_errors=True)
        for tmp_path, _ in staging_files:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
