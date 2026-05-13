from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .errors import ValidationError

VALID_VAT_RATES = {0.0, 7.0, 19.0}

OUTPUT_STANDARD_19 = "output_standard_19"
OUTPUT_REDUCED_7 = "output_reduced_7"
OUTPUT_ZERO_0 = "output_zero_0"
OUTPUT_TAX_FREE_NO_VORSTEUER = "output_tax_free_no_vorsteuer"
INPUT_INVOICE = "input_invoice"
REVERSE_CHARGE_EU = "reverse_charge_eu"
REVERSE_CHARGE_THIRD_COUNTRY = "reverse_charge_third_country"

INCOME_VAT_CODES = {
    OUTPUT_STANDARD_19,
    OUTPUT_REDUCED_7,
    OUTPUT_ZERO_0,
    OUTPUT_TAX_FREE_NO_VORSTEUER,
}
EXPENSE_VAT_CODES = {
    INPUT_INVOICE,
    REVERSE_CHARGE_EU,
    REVERSE_CHARGE_THIRD_COUNTRY,
}

INCOME_CODE_BY_RATE = {
    19.0: OUTPUT_STANDARD_19,
    7.0: OUTPUT_REDUCED_7,
    0.0: OUTPUT_ZERO_0,
}
INCOME_RATE_BY_CODE = {code: rate for rate, code in INCOME_CODE_BY_RATE.items()}
INCOME_RATE_BY_CODE[OUTPUT_TAX_FREE_NO_VORSTEUER] = 0.0

RC_VAT_CODE_BY_TYPE = {
    "eu": REVERSE_CHARGE_EU,
    "third_country": REVERSE_CHARGE_THIRD_COUNTRY,
}


def validate_vat_rate(value: float | None) -> float | None:
    """Validiert persistierte USt-Sätze."""
    if value is None:
        return None
    rate = float(value)
    if rate not in VALID_VAT_RATES:
        raise ValidationError(
            "Ungültiger Steuersatz. Erlaubt sind: 0, 7, 19.",
            code="invalid_vat_rate",
            details={"vat_rate": value},
        )
    return rate


def validate_vat_code(value: str | None, allowed_codes: set[str]) -> str | None:
    """Validiert persistierte USt-Codes gegen den erwarteten Tabellenkontext."""
    if value is None:
        return None
    if value not in allowed_codes:
        raise ValidationError(
            f"Ungültige Steuerklasse: {value}",
            code="invalid_vat_code",
            details={"vat_code": value},
        )
    return value


def to_decimal(value: float | int | str | Decimal | None) -> Decimal:
    """Konvertiert Geldwerte ohne binäre Float-Artefakte."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_money(value: float | int | str | Decimal | None) -> Decimal:
    """Rundet Steuerbeträge auf Cent."""
    return to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round_basis_eur(value: float | int | str | Decimal | None) -> int:
    """Rundet Bemessungsgrundlagen formularnah auf volle Euro."""
    return int(to_decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def included_vat_from_gross(amount_eur: float, vat_rate: float) -> float:
    """Berechnet enthaltene USt aus einem Brutto-Zahlfluss."""
    rate = validate_vat_rate(vat_rate)
    if not rate:
        return 0.0
    gross = abs(to_decimal(amount_eur))
    tax = gross * to_decimal(rate) / (Decimal("100") + to_decimal(rate))
    return float(round_money(tax))


def vat_from_net_basis(amount_eur: float, vat_rate: float) -> float:
    """Berechnet USt aus einer Netto-Bemessungsgrundlage."""
    rate = validate_vat_rate(vat_rate)
    if not rate:
        return 0.0
    tax = abs(to_decimal(amount_eur)) * to_decimal(rate) / Decimal("100")
    return float(round_money(tax))
