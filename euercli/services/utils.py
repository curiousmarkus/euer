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


RESERVED_PRIVATE_ACCOUNTS = {"privat", "privateinlage", "privatentnahme"}


def normalize_account_name(account: str | None) -> str | None:
    """Normalisiert Kontonamen: trimmt Leerzeichen und wandelt in Kleinbuchstaben."""
    if account is None:
        return None
    val = str(account).strip().lower()
    return val if val else None


def validate_income_account(
    account: str | None, private_accounts: list[str] | None = None
) -> None:
    """Weist private Konten für Einnahmen mit 'unsupported_private_income_account' ab."""
    if not account:
        return
    norm = str(account).strip().lower()
    all_private = set(RESERVED_PRIVATE_ACCOUNTS)
    if private_accounts:
        all_private.update(p.strip().lower() for p in private_accounts if p)
    if norm in all_private:
        raise ValidationError(
            f"Einnahmen auf Privatkonten ('{account}') werden nicht unterstützt. "
            "Bitte betriebliches Zahlungskonto verwenden oder Sachverhalt klären.",
            code="unsupported_private_income_account",
            details={"account": account},
        )
