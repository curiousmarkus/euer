"""Bewirtungskosten: Cent-genaue, von der CLI unabhängige Fachlogik."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .errors import ValidationError

ENTERTAINMENT_VAT_STATUSES = {"deductible", "no_deduction", "needs_review"}
CENT = Decimal("0.01")


@dataclass(frozen=True)
class EntertainmentBreakdown:
    paid_eur: Decimal
    vat_input_eur: Decimal | None
    cost_basis_eur: Decimal | None
    deductible_eur: Decimal | None
    non_deductible_eur: Decimal | None
    status: str
    provisional: bool


def _to_decimal(value: float | int | Decimal | None, name: str) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        number = Decimal("NaN")
    if not number.is_finite():
        raise ValidationError(
            f"{name} muss ein gültiger Geldbetrag sein.",
            code="invalid_entertainment_amount",
            details={name: value},
        )
    if number.quantize(CENT, rounding=ROUND_HALF_UP) != number:
        raise ValidationError(
            f"{name} darf höchstens zwei Nachkommastellen haben.",
            code="invalid_entertainment_cents",
            details={name: value},
        )
    return number


def _invalid(message: str, code: str, **details: object) -> ValidationError:
    return ValidationError(message, code=code, details=details)


def resolve_entertainment_fields(
    *,
    amount_eur: float,
    vat_input: float | None,
    tip_eur: float | None,
    vat_status: str | None,
    tax_mode: str,
    vat_was_provided: bool,
    allow_historical_vat: bool = False,
) -> tuple[float | None, float | None, str]:
    """Validiert Bewirtungswerte und bestimmt den pro Buchung gespeicherten Status."""
    amount = _to_decimal(amount_eur, "amount_eur")
    vat = _to_decimal(vat_input, "vat_input")
    tip = _to_decimal(tip_eur, "entertainment_tip_eur")
    assert amount is not None
    paid = abs(amount)

    if amount >= 0:
        raise _invalid(
            "Bewirtungsaufwendungen benötigen einen negativen Zahlbetrag.",
            "invalid_entertainment_sign",
            amount_eur=amount_eur,
        )
    if vat is not None and (vat < 0 or vat > paid):
        raise _invalid(
            "Vorsteuer muss zwischen 0,00 € und dem Zahlbetrag liegen.",
            "invalid_entertainment_vat",
            vat_input=vat_input,
            paid=amount_eur,
        )
    if tip is not None and (tip < 0 or tip > paid - (vat or Decimal("0"))):
        raise _invalid(
            "Trinkgeld muss zwischen 0,00 € und Zahlbetrag abzüglich Vorsteuer liegen.",
            "invalid_entertainment_tip",
            entertainment_tip_eur=tip_eur,
        )
    if tax_mode not in {"small_business", "standard"}:
        raise _invalid(
            f"Unbekannter Steuermodus: {tax_mode}",
            "invalid_tax_mode",
            tax_mode=tax_mode,
        )
    if vat_status is not None and vat_status not in ENTERTAINMENT_VAT_STATUSES:
        raise _invalid(
            "Ungültiger Bewirtungs-Vorsteuerstatus. Erlaubt sind deductible, "
            "no_deduction und needs_review.",
            "invalid_entertainment_vat_status",
            entertainment_vat_status=vat_status,
        )

    if (
        tax_mode == "small_business"
        and vat_was_provided
        and vat is not None
        and vat > 0
        and not allow_historical_vat
    ):
        raise _invalid(
            "Im Kleinunternehmermodus ist bei Bewirtung kein Vorsteuerabzug zulässig.",
            "entertainment_vat_conflicts_with_tax_mode",
            vat_input=vat_input,
        )

    if vat_status is None:
        if tax_mode == "small_business":
            vat = Decimal("0.00") if vat is None else vat
            status = "no_deduction"
        elif vat_was_provided:
            status = "deductible" if vat is not None and vat > 0 else "no_deduction"
        else:
            status = "needs_review"
    else:
        status = vat_status

    if status == "deductible" and (vat is None or vat <= 0):
        raise _invalid(
            "Status deductible erfordert einen positiven belegten Vorsteuerbetrag.",
            "entertainment_status_amount_conflict",
            entertainment_vat_status=status,
            vat_input=vat_input,
        )
    if status == "no_deduction" and vat is None:
        vat = Decimal("0.00")
    if status == "no_deduction" and vat not in {Decimal("0"), Decimal("0.00")}:
        raise _invalid(
            "Status no_deduction erfordert 0,00 € Vorsteuer.",
            "entertainment_status_amount_conflict",
            entertainment_vat_status=status,
            vat_input=vat_input,
        )
    if vat is not None:
        vat = vat.quantize(CENT, rounding=ROUND_HALF_UP)
    if tip is not None:
        tip = tip.quantize(CENT, rounding=ROUND_HALF_UP)
    resolved_vat = float(vat) if vat is not None else None
    resolved_tip = float(tip) if tip is not None else None
    return resolved_vat, resolved_tip, status


def calculate_entertainment_breakdown(
    *,
    amount_eur: float,
    vat_input: float | None,
    vat_status: str | None,
) -> EntertainmentBreakdown:
    """Berechnet die 70/30-Aufteilung; Altwerte bleiben klar vorläufig."""
    amount = _to_decimal(amount_eur, "amount_eur")
    vat = _to_decimal(vat_input, "vat_input")
    assert amount is not None
    paid = abs(amount).quantize(CENT, rounding=ROUND_HALF_UP)
    status = vat_status or "needs_review"
    provisional = status == "needs_review"

    can_calculate = status in {"deductible", "no_deduction"} or (
        provisional and vat is not None and vat > 0
    )
    if not can_calculate or vat is None:
        return EntertainmentBreakdown(paid, vat, None, None, None, status, provisional)

    if vat < 0 or vat > paid:
        raise _invalid(
            "Gespeicherte Vorsteuer liegt außerhalb des Zahlbetrags.",
            "invalid_entertainment_vat",
            vat_input=vat_input,
            paid=float(paid),
        )
    cost_basis = (paid - vat).quantize(CENT, rounding=ROUND_HALF_UP)
    deductible = (cost_basis * Decimal("0.70")).quantize(CENT, rounding=ROUND_HALF_UP)
    non_deductible = (cost_basis - deductible).quantize(CENT, rounding=ROUND_HALF_UP)
    return EntertainmentBreakdown(
        paid,
        vat,
        cost_basis,
        deductible,
        non_deductible,
        status,
        provisional,
    )
