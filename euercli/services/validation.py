"""Validierungs- und Plausibilitätsprüfungen (Spec 016 §2)."""

from __future__ import annotations

import datetime
import difflib
import re
import sqlite3
from decimal import Decimal

from .errors import ValidationError
from .vat import to_decimal

DEFAULT_AMOUNT_THRESHOLD = 5000.0


def validate_vat_math(
    *,
    amount_eur: float,
    vat_rate: float | None,
    vat_amount: float | None,
) -> None:
    """Prüft die mathematische Konsistenz von Brutto/Netto und USt-Satz (Spec 016 §2.1).

    Weicht die explizit übergebene Steuer um mehr als 0,02 € von der rechnerischen Steuer ab,
    wird ein ValidationError('vat_mismatch') geworfen.
    """
    if vat_rate is None or vat_rate not in (7.0, 19.0) or vat_amount is None:
        return

    gross = abs(to_decimal(amount_eur))
    rate_dec = to_decimal(vat_rate)
    # Rechnerische Steuer: amount * rate / (100 + rate)
    expected_vat = gross * rate_dec / (Decimal("100") + rate_dec)
    actual_vat = abs(to_decimal(vat_amount))

    diff = abs(actual_vat - expected_vat)
    if diff > Decimal("0.02"):
        raise ValidationError(
            f"Umsatzsteuer-Betrag ({float(actual_vat):.2f} €) weicht um mehr als 0,02 € "
            f"von rechnerischer USt ({float(expected_vat):.2f} € bei {vat_rate:g}%) ab.",
            code="vat_mismatch",
            details={
                "expected_vat": float(expected_vat),
                "provided_vat": float(actual_vat),
                "diff": float(diff),
                "vat_rate": vat_rate,
            },
        )


def _parse_date(val: str | datetime.date | None) -> datetime.date | None:
    if val is None:
        return None
    if isinstance(val, datetime.date):
        return val
    try:
        return datetime.date.fromisoformat(str(val))
    except ValueError:
        return None


def validate_date_plausibility(
    *,
    payment_date: str | datetime.date | None,
    invoice_date: str | datetime.date | None,
    today: datetime.date | None = None,
) -> list[str]:
    """Prüft Datumsplausibilität auf Zukunftsdaten und alte Daten (Spec 016 §2.2).

    Returns:
        Liste von Warnmeldungen (z. B. wenn Datum > 2 Jahre zurückliegt).
    Raises:
        ValidationError('future_date') bei unzulässigen Zukunftsdaten.
    """
    if today is None:
        today = datetime.date.today()

    p_date = _parse_date(payment_date)
    i_date = _parse_date(invoice_date)
    warnings: list[str] = []

    # Zukunftsdaten:
    # 1. Zahlungsdaten in der Zukunft sind bei EÜR unzulässig
    if p_date is not None and p_date > today:
        raise ValidationError(
            f"Zahlungsdatum {p_date} liegt in der Zukunft. Zukunftsdaten sind bei EÜR unzulässig.",
            code="future_date",
            details={"payment_date": str(p_date), "today": str(today)},
        )

    # 2. Rechnungsdatum in der Zukunft ist nur zulässig, wenn Zahlungsdatum noch offen ist
    if i_date is not None and i_date > today:
        if p_date is not None:
            raise ValidationError(
                f"Rechnungsdatum {i_date} liegt in der Zukunft bei bereits bezahlter Buchung.",
                code="future_date",
                details={"invoice_date": str(i_date), "payment_date": str(p_date)},
            )

    # Vergangene Daten (> 2 Jahre = 730 Tage)
    two_years_ago = today - datetime.timedelta(days=730)
    if p_date is not None and p_date < two_years_ago:
        warnings.append(f"Zahlungsdatum {p_date} liegt mehr als 2 Jahre in der Vergangenheit.")
    elif i_date is not None and i_date < two_years_ago and p_date is None:
        warnings.append(f"Rechnungsdatum {i_date} liegt mehr als 2 Jahre in der Vergangenheit.")

    return warnings


def validate_amount_threshold(
    *,
    amount_eur: float,
    threshold: float = DEFAULT_AMOUNT_THRESHOLD,
    force: bool = False,
) -> None:
    """Prüft, ob der Betrag den Schwellenwert überschreitet (Spec 016 §2.2)."""
    if force:
        return
    abs_amt = abs(float(amount_eur))
    if abs_amt > threshold:
        raise ValidationError(
            f"Betrag ({abs_amt:.2f} €) überschreitet den Schwellenwert von {threshold:.2f} €. "
            "Bitte mit --force bestätigen.",
            code="amount_threshold_exceeded",
            details={"amount": abs_amt, "threshold": threshold},
        )


def _normalize_name(name: str) -> str:
    """Normalisiert Kreditor-/Debitor-Namen für Fuzzy-Matching."""
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    return " ".join(cleaned.split())


def check_fuzzy_duplicate(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    name: str,
    amount_eur: float,
    date_val: str | datetime.date | None,
    invoice_number: str | None = None,
    invoice_date: str | None = None,
    receipt_name: str | None = None,
    allow_duplicate: bool = False,
    force: bool = False,
    exclude_id: int | None = None,
    invoice_only: bool = False,
) -> None:
    """Prüft ähnliche Buchungen und vorhandene Rechnungsnummern auf Duplikate."""
    if force or allow_duplicate:
        return

    target_abs = abs(round(float(amount_eur), 2))
    clean_target_name = _normalize_name(name)
    name_col = "vendor" if table_name == "expenses" else "source"

    # Gleiche Rechnungsnummern sind bei gleichem Aussteller und Betrag verdächtig;
    # Teilzahlungen mit anderem Betrag bleiben möglich.
    if invoice_number and clean_target_name:
        query = f"""
            SELECT id, {name_col} AS entity_name, amount_eur
            FROM {table_name}
            WHERE deleted_at IS NULL AND invoice_number = ?
        """
        params: list[object] = [invoice_number]
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)
        for row in conn.execute(query, params):
            if (
                _normalize_name(str(row["entity_name"] or "")) == clean_target_name
                and abs(round(float(row["amount_eur"]), 2)) == target_abs
            ):
                raise ValidationError(
                    f"Mögliches Duplikat: Rechnungsnummer {invoice_number} bei {name} "
                    f"und {target_abs:.2f} € gehört bereits zu Buchung #{row['id']}. "
                    "Mit --allow-duplicate oder --force bestätigen.",
                    code="suspicious_duplicate",
                    details={
                        "existing_id": row["id"],
                        "invoice_number": invoice_number,
                        "existing_name": row["entity_name"],
                        "amount": target_abs,
                    },
                )

    # Wenn nur eine Buchung eine Nummer hat, kann der gemeinsame Beleg dennoch
    # über Rechnungsdatum oder Dateiname erkannt werden, auch bei späterer Zahlung.
    if (invoice_date or receipt_name) and clean_target_name:
        matches = []
        params = []
        if invoice_date:
            matches.append("invoice_date = ?")
            params.append(invoice_date)
        if receipt_name:
            matches.append("receipt_name = ?")
            params.append(receipt_name)
        number_clause = "invoice_number IS NULL" if invoice_number else "invoice_number IS NOT NULL"
        query = f"""
            SELECT id, {name_col} AS entity_name, amount_eur
            FROM {table_name}
            WHERE deleted_at IS NULL AND {number_clause} AND ({" OR ".join(matches)})
        """
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)
        for row in conn.execute(query, params):
            if (
                _normalize_name(str(row["entity_name"] or "")) == clean_target_name
                and abs(round(float(row["amount_eur"]), 2)) == target_abs
            ):
                raise ValidationError(
                    f"Mögliches Duplikat: Buchung #{row['id']} von {name} über "
                    f"{target_abs:.2f} € hat dasselbe Rechnungsdatum oder denselben Beleg; "
                    "nur eine Buchung enthält eine Rechnungsnummer. "
                    "Mit --allow-duplicate oder --force bestätigen.",
                    code="suspicious_duplicate",
                    details={"existing_id": row["id"], "amount": target_abs},
                )

    if invoice_only:
        return

    parsed_date = _parse_date(date_val)
    if parsed_date is None or not name:
        return

    d_min = str(parsed_date - datetime.timedelta(days=2))
    d_max = str(parsed_date + datetime.timedelta(days=2))
    query = f"""
        SELECT id, payment_date, invoice_date, {name_col} as entity_name, amount_eur
        FROM {table_name}
        WHERE deleted_at IS NULL
          AND (
            (payment_date IS NOT NULL AND payment_date BETWEEN ? AND ?)
            OR (invoice_date IS NOT NULL AND invoice_date BETWEEN ? AND ?)
          )
    """
    params: list[object] = [d_min, d_max, d_min, d_max]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)

    rows = conn.execute(query, params).fetchall()

    for r in rows:
        row_amount = abs(round(float(r["amount_eur"]), 2))
        if row_amount != target_abs:
            continue

        existing_name = str(r["entity_name"] or "")
        clean_existing_name = _normalize_name(existing_name)

        # Ähnlichkeitsprüfung:
        # a) Exakter Match
        # b) Substring-Match bei mind. 3 Zeichen
        # c) Levenshtein / SequenceMatcher ratio >= 0.75
        is_match = False
        if clean_target_name == clean_existing_name:
            is_match = True
        elif len(clean_target_name) >= 3 and len(clean_existing_name) >= 3:
            if clean_target_name in clean_existing_name or clean_existing_name in clean_target_name:
                is_match = True
            elif (
                difflib.SequenceMatcher(None, clean_target_name, clean_existing_name).ratio()
                >= 0.75
            ):
                is_match = True

        if is_match:
            rec_id = r["id"]
            existing_date = r["payment_date"] or r["invoice_date"] or "-"
            raise ValidationError(
                f"Mögliches Duplikat: Buchung #{rec_id} vom {existing_date} über {target_abs:.2f} € "
                f"({existing_name}) existiert bereits. Mit --allow-duplicate oder --force bestätigen.",
                code="suspicious_duplicate",
                details={
                    "existing_id": rec_id,
                    "existing_date": existing_date,
                    "existing_name": existing_name,
                    "amount": target_abs,
                },
            )
