from __future__ import annotations

import hashlib
import sqlite3
from enum import Enum

from ..utils import compute_hash
from .errors import ValidationError
from .utils import hash_date, normalize_account_name


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
    account: str | None = None,
    exclude_id: int | None = None,
    cache: dict[tuple, list[int]] | None = None,
) -> list[int]:
    """Findet alle exakten Dubletten geordnet nach ID, inklusive suffigierter Hashes.

    Berücksichtigt das Zahlungskonto und meldet Prüfbedarf bei widersprüchlichen
    Kontoangaben auf identischen Beleg-/Rechnungsvorgängen.
    """
    date = hash_date(payment_date, invoice_date)
    norm_target_account = normalize_account_name(account)
    norm_receipt = receipt_name or ""
    norm_inv_num = invoice_number.strip() if invoice_number else None

    cache_key: tuple | None = None
    if cache is not None:
        cache_key = (
            table_name,
            date,
            party,
            f"{amount_eur:.2f}",
            norm_receipt,
            norm_inv_num or "",
            norm_target_account or "",
            exclude_id,
        )
        if cache_key in cache:
            return list(cache[cache_key])

    base = f"{date}|{party}|{amount_eur:.2f}|{norm_receipt}"
    hashes = {
        compute_hash(date, party, amount_eur, norm_receipt, norm_inv_num),
        compute_hash(date, party, amount_eur, norm_receipt),
    }
    if norm_inv_num:
        hashes.add(hashlib.sha256(f"{base}|{norm_inv_num}".encode("utf-8")).hexdigest())

    party_col = "vendor" if table_name == "expenses" else "source"
    where_parts: list[str] = []
    params: list[object] = []
    # Index-freundliche Abfrage: Basishash = ? OR Suffixbereich [h#, h#~]
    for h in sorted(hashes):
        where_parts.append("(hash = ? OR (hash >= ? AND hash <= ?))")
        params.extend([h, f"{h}#", f"{h}#~"])
    where_clause = " OR ".join(where_parts)

    extra_clauses = ["deleted_at IS NULL"]
    if exclude_id is not None:
        extra_clauses.append("id != ?")
        params.append(exclude_id)

    # Prüfen, ob Tabelle 'account'-Spalte hat
    has_account_col = True
    try:
        col_names = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if "account" not in col_names:
            has_account_col = False
    except Exception:
        has_account_col = False

    account_select = "account" if has_account_col else "NULL AS account"

    query = f"""
        SELECT id, payment_date, invoice_date, {party_col} AS party,
               amount_eur, receipt_name, invoice_number, {account_select}
        FROM {table_name}
        WHERE ({where_clause}) AND {" AND ".join(extra_clauses)}
        ORDER BY id ASC
    """
    rows = conn.execute(query, tuple(params)).fetchall()

    matching_ids: list[int] = []
    for row in rows:
        if (
            hash_date(row["payment_date"], row["invoice_date"]) == date
            and row["party"] == party
            and f"{row['amount_eur']:.2f}" == f"{amount_eur:.2f}"
            and (row["receipt_name"] or "") == norm_receipt
            and (row["invoice_number"] == norm_inv_num or row["invoice_number"] is None)
        ):
            row_acc = normalize_account_name(row["account"]) if has_account_col else None
            # Kontoabgleich:
            # 1. Beide Konten bekannt und unterschiedlich:
            if (
                norm_target_account is not None
                and row_acc is not None
                and norm_target_account != row_acc
            ):
                # Widersprüchliche Kontoangaben bei expliziter Beleg- oder Rechnungsnummer
                if (norm_inv_num and row["invoice_number"] == norm_inv_num) or (
                    norm_receipt and (row["receipt_name"] or "") == norm_receipt
                ):
                    raise ValidationError(
                        f"Widersprüchliche Angaben: Buchung #{row['id']} ist auf Konto '{row_acc}' "
                        f"erfasst, dieser Vorgang nennt '{norm_target_account}'. Prüfbedarf!",
                        code="account_conflict",
                        details={
                            "existing_id": int(row["id"]),
                            "existing_account": row_acc,
                            "account": norm_target_account,
                        },
                    )
                # Ansonsten: zwei getrennte Buchungen auf unterschiedlichen Konten (keine Dublette)
                continue

            # 2. Gleiche Konten ODER fehlendes vs. bekanntes Konto -> Dublette
            matching_ids.append(int(row["id"]))

    if cache is not None and cache_key is not None:
        cache[cache_key] = list(matching_ids)

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
    account: str | None = None,
    exclude_id: int | None = None,
    cache: dict[tuple, list[int]] | None = None,
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
        account=account,
        exclude_id=exclude_id,
        cache=cache,
    )
    return matches[0] if matches else None
