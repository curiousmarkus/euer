import csv
import sys
from decimal import Decimal
from pathlib import Path

from ..config import get_export_dir, load_config
from ..constants import DEFAULT_EXPORT_DIR
from ..db import get_db_connection
from ..importers import get_tax_config
from ..services.errors import ValidationError
from ..services.vat_report import (
    VatReport,
    VatReportDiagnostic,
    VatReportLine,
    build_vat_report,
)
from ..utils import format_amount


REPORT_COLUMNS = [
    "period_label",
    "period_start",
    "period_end",
    "tax_mode",
    "section",
    "line_label",
    "kennzahl",
    "description",
    "basis_eur_raw",
    "basis_eur_rounded",
    "tax_eur_raw",
    "tax_eur_rounded",
    "status",
    "notes",
]

DIAGNOSTIC_COLUMNS = [
    "status",
    "booking_type",
    "booking_id",
    "reason",
    "reason_code",
    "amount_eur",
    "vat_input",
    "vat_output",
    "vat_rate",
    "vat_code",
]


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def _format_whole_eur(value: int | None) -> str:
    if value is None:
        return ""
    return f"{value:,}".replace(",", ".")


def _format_report_amount(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format_amount(float(value))


def _line_to_row(report: VatReport, line: VatReportLine) -> list[object]:
    return [
        report.period.label,
        report.period.start,
        report.period.end,
        report.tax_mode,
        line.section,
        line.line_label,
        line.kennzahl,
        line.description,
        _format_decimal(line.basis_eur_raw),
        line.basis_eur_rounded if line.basis_eur_rounded is not None else "",
        _format_decimal(line.tax_eur_raw),
        _format_decimal(line.tax_eur_rounded),
        line.status,
        line.notes,
    ]


def _diagnostic_to_row(item: VatReportDiagnostic) -> list[object]:
    return [
        item.status,
        item.booking_type,
        item.booking_id,
        item.reason,
        item.reason_code,
        _format_decimal(item.amount_eur),
        _format_decimal(item.vat_input),
        _format_decimal(item.vat_output),
        f"{item.vat_rate:g}" if item.vat_rate is not None else "",
        item.vat_code or "",
    ]


def _print_vat_report(report: VatReport) -> None:
    print(report.period.title)
    print("=" * 50)
    print()
    print("Zeitraum:")
    print(f"  {report.period.start} bis {report.period.end}")
    print()
    print("Steuermodus:")
    print(f"  {report.tax_mode}")
    print()

    current_section = None
    for line in report.lines:
        if line.status == "unsupported":
            continue
        if line.section != current_section:
            current_section = line.section
            print(f"{current_section}:")

        if line.kennzahl == "83":
            print("-" * 50)
            label = "ZAHLLAST / ERSTATTUNG"
            print(
                f"{line.line_label:<6} {label:<44} "
                f"{_format_report_amount(line.tax_eur_rounded):>12} EUR"
            )
            print()
            continue

        if line.basis_eur_rounded is not None:
            print(
                f"  {line.line_label:<6} {line.description:<44} "
                f"{_format_whole_eur(line.basis_eur_rounded):>12} EUR"
            )
        if line.tax_eur_rounded is not None:
            tax_label = "Steuer" if line.section != "Vorsteuer" else line.description
            prefix = " " * 8 if line.basis_eur_rounded is not None else f"  {line.line_label:<6}"
            print(
                f"{prefix} {tax_label:<44} "
                f"{_format_report_amount(line.tax_eur_rounded):>12} EUR"
            )
    unsupported = [line for line in report.lines if line.status == "unsupported"]
    if unsupported:
        print("Nicht unterstützte Bereiche:")
        for line in unsupported:
            print(f"  {line.line_label:<10} {line.description}: nicht unterstützt")
        print()

    if report.warnings:
        print("Warnungen:")
        for item in report.warnings:
            booking = "Einnahme" if item.booking_type == "income" else "Ausgabe"
            print(f"  - {booking} #{item.booking_id}: {item.reason}")


def _resolve_output_dir(args_output: str | None) -> Path:
    if args_output:
        output_dir = Path(args_output)
    else:
        config_export_dir = get_export_dir(load_config())
        output_dir = Path(config_export_dir) if config_export_dir else DEFAULT_EXPORT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _file_stem(report: VatReport) -> str:
    return f"UStVA_{report.period.label.replace('/', '_')}"


def _write_csv(report: VatReport, output_dir: Path) -> tuple[Path, Path]:
    report_path = output_dir / f"{_file_stem(report)}.csv"
    diagnostic_path = output_dir / f"{_file_stem(report)}_diagnose.csv"

    with report_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(REPORT_COLUMNS)
        for line in report.lines:
            writer.writerow(_line_to_row(report, line))

    with diagnostic_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(DIAGNOSTIC_COLUMNS)
        for item in report.diagnostics:
            writer.writerow(_diagnostic_to_row(item))

    return report_path, diagnostic_path


def _write_xlsx(report: VatReport, output_dir: Path) -> Path:
    try:
        import openpyxl
    except ImportError as exc:
        raise ValidationError(
            "openpyxl nicht installiert. Bitte 'pip install openpyxl' ausführen.",
            code="openpyxl_missing",
        ) from exc

    path = output_dir / f"{_file_stem(report)}.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Kennzahlen"
    ws.append(REPORT_COLUMNS)
    for line in report.lines:
        ws.append(_line_to_row(report, line))

    diagnostics = wb.create_sheet("Diagnose")
    diagnostics.append(DIAGNOSTIC_COLUMNS)
    for item in report.diagnostics:
        diagnostics.append(_diagnostic_to_row(item))

    wb.save(path)
    return path


def cmd_vat_report(args) -> None:
    """Erzeugt einen ELSTER-nahen UStVA-Report."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    tax_mode = get_tax_config(config)

    try:
        report = build_vat_report(
            conn,
            year=args.year,
            quarter=args.quarter,
            month=args.month,
            tax_mode=tax_mode,
        )
    except ValidationError as exc:
        conn.close()
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)
    conn.close()

    if args.format == "table":
        _print_vat_report(report)
        return

    output_dir = _resolve_output_dir(args.output)
    try:
        if args.format == "csv":
            report_path, diagnostic_path = _write_csv(report, output_dir)
            print(f"Exportiert: {report_path}")
            print(f"Exportiert: {diagnostic_path}")
        else:
            path = _write_xlsx(report, output_dir)
            print(f"Exportiert: {path}")
    except ValidationError as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        sys.exit(1)
