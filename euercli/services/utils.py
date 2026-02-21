from __future__ import annotations

import sqlite3

from .errors import ValidationError


def get_optional(row: sqlite3.Row, key: str):
    return row[key] if key in row.keys() else None


def resolve_dates(
    *,
    payment_date: str | None,
    invoice_date: str | None,
    legacy_date: str | None = None,
) -> tuple[str | None, str | None]:
    """Löst payment_date/invoice_date auf und validiert, dass mindestens eines gesetzt ist."""
    resolved_payment_date = payment_date if payment_date is not None else legacy_date
    resolved_invoice_date = invoice_date
    if not resolved_payment_date and not resolved_invoice_date:
        raise ValidationError(
            "Mindestens eines der Felder payment_date oder invoice_date muss gesetzt sein.",
            code="missing_dates",
        )
    return resolved_payment_date, resolved_invoice_date


def hash_date(payment_date: str | None, invoice_date: str | None) -> str:
    """Gibt das für die Hash-Berechnung relevante Datum zurück (payment > invoice)."""
    return payment_date or invoice_date or ""
