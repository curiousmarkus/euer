from __future__ import annotations

import calendar
from dataclasses import dataclass
from decimal import Decimal
from sqlite3 import Connection, Row

from .errors import ValidationError
from .vat import (
    INPUT_INVOICE,
    OUTPUT_REDUCED_7,
    OUTPUT_STANDARD_19,
    OUTPUT_TAX_FREE_NO_VORSTEUER,
    OUTPUT_ZERO_0,
    RC_VAT_CODE_BY_TYPE,
    REVERSE_CHARGE_EU,
    REVERSE_CHARGE_THIRD_COUNTRY,
    included_vat_from_gross,
    round_basis_eur,
    round_money,
    to_decimal,
    vat_from_net_basis,
)


@dataclass
class VatReportPeriod:
    year: int
    start: str
    end: str
    label: str
    title: str


@dataclass
class VatReportLine:
    section: str
    line_label: str
    kennzahl: str
    description: str
    basis_eur_raw: Decimal | None
    basis_eur_rounded: int | None
    tax_eur_raw: Decimal | None
    tax_eur_rounded: Decimal | None
    status: str = "included"
    notes: str = ""


@dataclass
class VatReportDiagnostic:
    status: str
    booking_type: str
    booking_id: int
    reason: str
    reason_code: str
    amount_eur: Decimal | None = None
    vat_input: Decimal | None = None
    vat_output: Decimal | None = None
    vat_rate: float | None = None
    vat_code: str | None = None


@dataclass
class VatReport:
    period: VatReportPeriod
    tax_mode: str
    lines: list[VatReportLine]
    diagnostics: list[VatReportDiagnostic]

    @property
    def warnings(self) -> list[VatReportDiagnostic]:
        return [
            item
            for item in self.diagnostics
            if item.status in {"warning", "excluded", "unsupported"}
        ]


@dataclass(frozen=True)
class _LineDefinition:
    section: str
    line_label: str
    kennzahl: str
    description: str
    has_basis: bool = True
    has_tax: bool = False
    status: str = "included"
    notes: str = ""


LINE_DEFINITIONS: dict[str, _LineDefinition] = {
    "81": _LineDefinition(
        "Ausgangsumsätze",
        "KZ 81",
        "81",
        "Steuerpflichtige Umsätze 19 %",
        has_tax=True,
    ),
    "86": _LineDefinition(
        "Ausgangsumsätze",
        "KZ 86",
        "86",
        "Steuerpflichtige Umsätze 7 %",
        has_tax=True,
    ),
    "87": _LineDefinition(
        "Ausgangsumsätze",
        "KZ 87",
        "87",
        "Steuerpflichtige Umsätze 0 %",
    ),
    "48": _LineDefinition(
        "Ausgangsumsätze",
        "KZ 48",
        "48",
        "Steuerfreie Umsätze ohne Vorsteuerabzug",
    ),
    "46": _LineDefinition(
        "Reverse Charge",
        "KZ 46",
        "46",
        "EU-Bemessungsgrundlage",
    ),
    "47": _LineDefinition(
        "Reverse Charge",
        "KZ 47",
        "47",
        "EU-Steuer",
        has_basis=False,
        has_tax=True,
    ),
    "84": _LineDefinition(
        "Reverse Charge",
        "KZ 84",
        "84",
        "Drittland-Bemessungsgrundlage",
    ),
    "85": _LineDefinition(
        "Reverse Charge",
        "KZ 85",
        "85",
        "Drittland-Steuer",
        has_basis=False,
        has_tax=True,
    ),
    "66": _LineDefinition(
        "Vorsteuer",
        "KZ 66",
        "66",
        "Vorsteuer aus Rechnungen",
        has_basis=False,
        has_tax=True,
    ),
    "67": _LineDefinition(
        "Vorsteuer",
        "KZ 67",
        "67",
        "Vorsteuer aus Reverse-Charge-Leistungen",
        has_basis=False,
        has_tax=True,
    ),
    "83": _LineDefinition(
        "Ergebnis",
        "KZ 83",
        "83",
        "Verbleibende Umsatzsteuer-Vorauszahlung / Überschuss",
        has_basis=False,
        has_tax=True,
    ),
}

UNSUPPORTED_LINE_DEFINITIONS = [
    _LineDefinition(
        "Nicht unterstützte Bereiche",
        "KZ 39",
        "39",
        "Sondervorauszahlung / Dauerfristverlängerung",
        has_basis=False,
        has_tax=True,
        status="unsupported",
        notes="Nicht modelliert.",
    ),
    _LineDefinition(
        "Nicht unterstützte Bereiche",
        "KZ 62",
        "62",
        "Einfuhrumsatzsteuer",
        has_basis=False,
        has_tax=True,
        status="unsupported",
        notes="Nicht modelliert.",
    ),
    _LineDefinition(
        "Nicht unterstützte Bereiche",
        "KZ 64",
        "64",
        "Vorsteuerberichtigung",
        has_basis=False,
        has_tax=True,
        status="unsupported",
        notes="Nicht modelliert.",
    ),
    _LineDefinition(
        "Nicht unterstützte Bereiche",
        "KZ 89/93/90",
        "89/93/90",
        "Innergemeinschaftliche Erwerbe",
        has_basis=True,
        has_tax=True,
        status="unsupported",
        notes="Nicht modelliert.",
    ),
    _LineDefinition(
        "Nicht unterstützte Bereiche",
        "KZ 35/36",
        "35/36",
        "Andere Steuersätze",
        has_basis=True,
        has_tax=True,
        status="unsupported",
        notes="Nicht modelliert.",
    ),
]


def build_vat_period(
    *,
    year: int,
    quarter: int | None = None,
    month: int | None = None,
) -> VatReportPeriod:
    if quarter is not None and month is not None:
        raise ValidationError(
            "--quarter und --month dürfen nicht gemeinsam verwendet werden.",
            code="period_conflict",
        )
    if quarter is not None and quarter not in {1, 2, 3, 4}:
        raise ValidationError(
            "Ungültiges Quartal. Erlaubt sind 1, 2, 3, 4.",
            code="invalid_quarter",
            details={"quarter": quarter},
        )
    if month is not None and month not in set(range(1, 13)):
        raise ValidationError(
            "Ungültiger Monat. Erlaubt sind 1 bis 12.",
            code="invalid_month",
            details={"month": month},
        )

    if quarter is not None:
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        start = f"{year}-{start_month:02d}-01"
        end = f"{year}-{end_month:02d}-{calendar.monthrange(year, end_month)[1]:02d}"
        return VatReportPeriod(
            year=year,
            start=start,
            end=end,
            label=f"Q{quarter}/{year}",
            title=f"USt-Voranmeldung Q{quarter}/{year}",
        )

    if month is not None:
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
        return VatReportPeriod(
            year=year,
            start=start,
            end=end,
            label=f"{month:02d}/{year}",
            title=f"USt-Voranmeldung {month:02d}/{year}",
        )

    return VatReportPeriod(
        year=year,
        start=f"{year}-01-01",
        end=f"{year}-12-31",
        label=str(year),
        title=f"USt-Voranmeldung {year}",
    )


def _decimal_or_none(value: object | None) -> Decimal | None:
    if value is None:
        return None
    return to_decimal(value)


def _diagnostic_from_row(
    row: Row,
    *,
    status: str,
    booking_type: str,
    reason: str,
    reason_code: str,
) -> VatReportDiagnostic:
    return VatReportDiagnostic(
        status=status,
        booking_type=booking_type,
        booking_id=int(row["id"]),
        reason=reason,
        reason_code=reason_code,
        amount_eur=_decimal_or_none(row["amount_eur"]),
        vat_input=_decimal_or_none(row["vat_input"] if "vat_input" in row.keys() else None),
        vat_output=_decimal_or_none(row["vat_output"] if "vat_output" in row.keys() else None),
        vat_rate=row["vat_rate"] if "vat_rate" in row.keys() else None,
        vat_code=row["vat_code"] if "vat_code" in row.keys() else None,
    )


def _add_amount(
    totals: dict[str, dict[str, Decimal]],
    kennzahl: str,
    *,
    basis: Decimal | None = None,
    tax: Decimal | None = None,
) -> None:
    if basis is not None:
        totals[kennzahl]["basis"] += basis
    if tax is not None:
        totals[kennzahl]["tax"] += tax


def _split_output_income(row: Row, rate: float) -> tuple[Decimal, Decimal]:
    gross = abs(to_decimal(row["amount_eur"]))
    stored_tax = _decimal_or_none(row["vat_output"])
    if stored_tax is None:
        calculated_tax = Decimal(str(included_vat_from_gross(float(gross), rate)))
        basis = gross - calculated_tax
        return round_money(basis), round_money(calculated_tax)
    return round_money(gross - stored_tax), round_money(stored_tax)


def _append_missing_payment_diagnostics(
    conn: Connection,
    period: VatReportPeriod,
    diagnostics: list[VatReportDiagnostic],
) -> None:
    income_rows = conn.execute(
        """SELECT id, invoice_date, amount_eur, vat_output, vat_rate, vat_code
           FROM income
           WHERE payment_date IS NULL
             AND invoice_date BETWEEN ? AND ?
           ORDER BY invoice_date, id""",
        (period.start, period.end),
    ).fetchall()
    for row in income_rows:
        diagnostics.append(
            _diagnostic_from_row(
                row,
                status="excluded",
                booking_type="income",
                reason="Einnahme ohne payment_date nicht eingerechnet.",
                reason_code="missing_payment_date",
            )
        )

    expense_rows = conn.execute(
        """SELECT id, invoice_date, amount_eur, vat_input, vat_output, vat_rate, vat_code
           FROM expenses
           WHERE payment_date IS NULL
             AND invoice_date BETWEEN ? AND ?
           ORDER BY invoice_date, id""",
        (period.start, period.end),
    ).fetchall()
    for row in expense_rows:
        diagnostics.append(
            _diagnostic_from_row(
                row,
                status="excluded",
                booking_type="expense",
                reason="Ausgabe ohne payment_date nicht eingerechnet.",
                reason_code="missing_payment_date",
            )
        )


def _aggregate_income(
    conn: Connection,
    period: VatReportPeriod,
    totals: dict[str, dict[str, Decimal]],
    diagnostics: list[VatReportDiagnostic],
) -> None:
    rows = conn.execute(
        """SELECT id, payment_date, amount_eur, vat_output, vat_rate, vat_code
           FROM income
           WHERE payment_date BETWEEN ? AND ?
           ORDER BY payment_date, id""",
        (period.start, period.end),
    ).fetchall()

    for row in rows:
        code = row["vat_code"]
        if not code:
            diagnostics.append(
                _diagnostic_from_row(
                    row,
                    status="excluded",
                    booking_type="income",
                    reason="Einnahme ohne steuerliche Klassifikation nicht eingerechnet.",
                    reason_code="missing_vat_code",
                )
            )
            continue

        if code == OUTPUT_STANDARD_19:
            basis, tax = _split_output_income(row, 19.0)
            _add_amount(totals, "81", basis=basis, tax=tax)
        elif code == OUTPUT_REDUCED_7:
            basis, tax = _split_output_income(row, 7.0)
            _add_amount(totals, "86", basis=basis, tax=tax)
        elif code == OUTPUT_ZERO_0:
            _add_amount(totals, "87", basis=abs(to_decimal(row["amount_eur"])))
        elif code == OUTPUT_TAX_FREE_NO_VORSTEUER:
            _add_amount(totals, "48", basis=abs(to_decimal(row["amount_eur"])))
        else:
            diagnostics.append(
                _diagnostic_from_row(
                    row,
                    status="unsupported",
                    booking_type="income",
                    reason="Nicht unterstützte Steuerklasse nicht eingerechnet.",
                    reason_code="unsupported_vat_code",
                )
            )


def _aggregate_expenses(
    conn: Connection,
    period: VatReportPeriod,
    tax_mode: str,
    totals: dict[str, dict[str, Decimal]],
    diagnostics: list[VatReportDiagnostic],
) -> None:
    rows = conn.execute(
        """SELECT id, payment_date, amount_eur, rc_type, vat_input, vat_output,
                  vat_rate, vat_code
           FROM expenses
           WHERE payment_date BETWEEN ? AND ?
           ORDER BY payment_date, id""",
        (period.start, period.end),
    ).fetchall()

    for row in rows:
        rc_type = row["rc_type"] or "none"
        code = row["vat_code"]

        if rc_type == "unclassified":
            diagnostics.append(
                _diagnostic_from_row(
                    row,
                    status="excluded",
                    booking_type="expense",
                    reason="Reverse-Charge-Buchung ohne EU-/Drittland-Typ nicht eingerechnet.",
                    reason_code="missing_rc_type",
                )
            )
            continue

        if rc_type in RC_VAT_CODE_BY_TYPE:
            expected_code = RC_VAT_CODE_BY_TYPE[rc_type]
            if code and code != expected_code:
                diagnostics.append(
                    _diagnostic_from_row(
                        row,
                        status="excluded",
                        booking_type="expense",
                        reason="Steuerklasse passt nicht zum Reverse-Charge-Typ.",
                        reason_code="vat_code_rc_type_mismatch",
                    )
                )
                continue

            basis = abs(to_decimal(row["amount_eur"]))
            tax = _decimal_or_none(row["vat_output"])
            if tax is None:
                tax = to_decimal(vat_from_net_basis(float(basis), 19.0))
                diagnostics.append(
                    _diagnostic_from_row(
                        row,
                        status="warning",
                        booking_type="expense",
                        reason="RC-Steuer aus Bemessungsgrundlage mit 19 % berechnet.",
                        reason_code="calculated_missing_rc_vat_output",
                    )
                )
            tax = round_money(tax)

            if rc_type == "eu":
                _add_amount(totals, "46", basis=basis)
                _add_amount(totals, "47", tax=tax)
            else:
                _add_amount(totals, "84", basis=basis)
                _add_amount(totals, "85", tax=tax)

            if tax_mode == "standard":
                vat_input = _decimal_or_none(row["vat_input"])
                if vat_input is None:
                    vat_input = tax
                    diagnostics.append(
                        _diagnostic_from_row(
                            row,
                            status="warning",
                            booking_type="expense",
                            reason="RC-Vorsteuer aus RC-Steuerbetrag übernommen.",
                            reason_code="calculated_missing_rc_vat_input",
                        )
                    )
                _add_amount(totals, "67", tax=round_money(vat_input))
            continue

        if code in {REVERSE_CHARGE_EU, REVERSE_CHARGE_THIRD_COUNTRY}:
            diagnostics.append(
                _diagnostic_from_row(
                    row,
                    status="excluded",
                    booking_type="expense",
                    reason="Reverse-Charge-Steuerklasse ohne RC-Typ nicht eingerechnet.",
                    reason_code="vat_code_requires_rc",
                )
            )
            continue

        vat_input = _decimal_or_none(row["vat_input"])
        if code == INPUT_INVOICE or (code is None and vat_input is not None and vat_input > 0):
            if tax_mode == "standard":
                _add_amount(totals, "66", tax=round_money(vat_input or Decimal("0")))
            else:
                diagnostics.append(
                    _diagnostic_from_row(
                        row,
                        status="excluded",
                        booking_type="expense",
                        reason="Vorsteuer wird im Kleinunternehmermodus nicht eingerechnet.",
                        reason_code="input_vat_in_small_business",
                    )
                )
            continue

        if code:
            diagnostics.append(
                _diagnostic_from_row(
                    row,
                    status="unsupported",
                    booking_type="expense",
                    reason="Nicht unterstützte Steuerklasse nicht eingerechnet.",
                    reason_code="unsupported_vat_code",
                )
            )
        elif tax_mode == "standard" and vat_input is None:
            diagnostics.append(
                _diagnostic_from_row(
                    row,
                    status="warning",
                    booking_type="expense",
                    reason="Ausgabe ohne Vorsteuer-Klassifikation; KZ 66 ggf. unvollständig.",
                    reason_code="missing_vat_code",
                )
            )


def _build_line(definition: _LineDefinition, basis: Decimal, tax: Decimal) -> VatReportLine:
    basis_raw = round_money(basis) if definition.has_basis else None
    tax_raw = round_money(tax) if definition.has_tax else None
    return VatReportLine(
        section=definition.section,
        line_label=definition.line_label,
        kennzahl=definition.kennzahl,
        description=definition.description,
        basis_eur_raw=basis_raw,
        basis_eur_rounded=round_basis_eur(basis_raw) if basis_raw is not None else None,
        tax_eur_raw=tax_raw,
        tax_eur_rounded=round_money(tax_raw) if tax_raw is not None else None,
        status=definition.status,
        notes=definition.notes,
    )


def build_vat_report(
    conn: Connection,
    *,
    year: int,
    tax_mode: str,
    quarter: int | None = None,
    month: int | None = None,
) -> VatReport:
    if tax_mode not in {"small_business", "standard"}:
        raise ValidationError(
            f"Unbekannter Steuermodus: {tax_mode}",
            code="invalid_tax_mode",
            details={"tax_mode": tax_mode},
        )

    period = build_vat_period(year=year, quarter=quarter, month=month)
    totals = {
        kennzahl: {"basis": Decimal("0"), "tax": Decimal("0")}
        for kennzahl in LINE_DEFINITIONS
    }
    diagnostics: list[VatReportDiagnostic] = []

    _append_missing_payment_diagnostics(conn, period, diagnostics)
    _aggregate_income(conn, period, totals, diagnostics)
    _aggregate_expenses(conn, period, tax_mode, totals, diagnostics)

    output_tax = (
        totals["81"]["tax"]
        + totals["86"]["tax"]
        + totals["47"]["tax"]
        + totals["85"]["tax"]
    )
    input_tax = totals["66"]["tax"] + totals["67"]["tax"]
    totals["83"]["tax"] = output_tax - input_tax

    lines = [
        _build_line(definition, totals[key]["basis"], totals[key]["tax"])
        for key, definition in LINE_DEFINITIONS.items()
    ]
    lines.extend(
        VatReportLine(
            section=definition.section,
            line_label=definition.line_label,
            kennzahl=definition.kennzahl,
            description=definition.description,
            basis_eur_raw=None,
            basis_eur_rounded=None,
            tax_eur_raw=None,
            tax_eur_rounded=None,
            status=definition.status,
            notes=definition.notes,
        )
        for definition in UNSUPPORTED_LINE_DEFINITIONS
    )

    return VatReport(period=period, tax_mode=tax_mode, lines=lines, diagnostics=diagnostics)
