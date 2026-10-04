from __future__ import annotations

import hashlib
import sqlite3
from enum import Enum

from ..utils import compute_hash
from .utils import hash_date


class DuplicateAction(str, Enum):
    """Steuert das Verhalten bei erkanntem Duplikat."""

    RAISE = "raise"
    SKIP = "skip"


def find_all_exact_duplicates(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    payment_date: str | None,
    invoice_date: str | None,
    party: str,
    amount_eur: float,
    receipt_name: str | None,
    invoice_number: str | None,
) -> list[int]:
    """Findet alle exakten Dubletten geordnet nach ID, inklusive suffigierter Hashes."""
    date = hash_date(payment_date, invoice_date)
    base = f"{date}|{party}|{amount_eur:.2f}|{receipt_name or ''}"
    hashes = {
        compute_hash(date, party, amount_eur, receipt_name or "", invoice_number),
        compute_hash(date, party, amount_eur, receipt_name or ""),
    }
    if invoice_number:
        hashes.add(hashlib.sha256(f"{base}|{invoice_number}".encode("utf-8")).hexdigest())
    party_col = "vendor" if table_name == "expenses" else "source"
    where_parts: list[str] = []
    params: list[object] = []
    for h in sorted(hashes):
        where_parts.append("(hash = ? OR hash LIKE ?)")
        params.extend([h, f"{h}#%"])
    where_clause = " OR ".join(where_parts)
    rows = conn.execute(
        f"""SELECT id, payment_date, invoice_date, {party_col} AS party,
                   amount_eur, receipt_name, invoice_number
            FROM {table_name} WHERE ({where_clause}) AND deleted_at IS NULL
            ORDER BY id ASC""",
        tuple(params),
    )
    matching_ids: list[int] = []
    for row in rows:
        if (
            hash_date(row["payment_date"], row["invoice_date"]) == date
            and row["party"] == party
            and f"{row['amount_eur']:.2f}" == f"{amount_eur:.2f}"
            and (row["receipt_name"] or "") == (receipt_name or "")
            and (row["invoice_number"] == invoice_number or row["invoice_number"] is None)
        ):
            matching_ids.append(int(row["id"]))
    return matching_ids


def find_exact_duplicate(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    payment_date: str | None,
    invoice_date: str | None,
    party: str,
    amount_eur: float,
    receipt_name: str | None,
    invoice_number: str | None,
) -> int | None:
    """Findet die erste exakte Dublette auch mit dem früheren Rechnungsnummer-Hash."""
    matches = find_all_exact_duplicates(
        conn,
        table_name=table_name,
        payment_date=payment_date,
        invoice_date=invoice_date,
        party=party,
        amount_eur=amount_eur,
        receipt_name=receipt_name,
        invoice_number=invoice_number,
    )
    return matches[0] if matches else None
