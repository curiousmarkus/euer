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
    max_id: int | None = None,
) -> list[int]:
    """Findet exakte Dubletten inklusive suffigierter Hashes.

    Treffer mit dem angegebenen Konto haben Vorrang vor Treffern ohne Konto;
    innerhalb dieser Gruppen entscheidet die ID. max_id begrenzt Importtreffer
    auf den Altbestand und weist mehrdeutige Zuordnungen ohne Zielkonto ab.
    Kontokonflikte bei identischen Belegen/Rechnungen werden auch bei neuen
    Buchungen im laufenden Import geprüft.
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
            max_id,
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

    # Prüfen, ob Tabelle 'account'-Spalte hat
    has_account_col = True
    try:
        col_names = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if "account" not in col_names:
            has_account_col = False
    except Exception:
        has_account_col = False

    account_select = "account" if has_account_col else "NULL AS account"

    # Nur Hash-Prädikate im SQL: Mit deleted_at IS NULL wählt SQLite sonst
    # den wenig selektiven Löschindex und prüft sämtliche aktiven Buchungen.
    # Löschstatus und Eigen-ID erst unter den wenigen Hash-Kandidaten filtern.
    query = f"""
        SELECT id, payment_date, invoice_date, {party_col} AS party,
               amount_eur, receipt_name, invoice_number, {account_select}, deleted_at
        FROM {table_name}
        WHERE ({where_clause})
        ORDER BY id ASC
    """
    rows = conn.execute(query, tuple(params)).fetchall()

    matching_ids: list[int] = []
    matching_accounts: dict[int, str | None] = {}
    for row in rows:
        if row["deleted_at"] is not None or row["id"] == exclude_id:
            continue
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
            if max_id is None or row["id"] <= max_id:
                record_id = int(row["id"])
                matching_ids.append(record_id)
                matching_accounts[record_id] = row_acc

    if (
        max_id is not None
        and norm_target_account is None
        and len(set(matching_accounts.values())) > 1
    ):
        ids = ", ".join(f"#{record_id}" for record_id in matching_ids)
        raise ValidationError(
            f"Mehrdeutige Duplikatzuordnung: Buchungen {ids} haben unterschiedliche "
            "Kontoangaben, dieser Vorgang nennt kein Zahlungskonto. "
            "Bitte Konto und vorhandene Buchungen prüfen und das Zahlungskonto "
            "im Import angeben.",
            code="ambiguous_duplicate_account",
            details={"candidate_ids": matching_ids},
        )

    if norm_target_account is not None:
        matching_ids.sort(
            key=lambda record_id: (matching_accounts[record_id] != norm_target_account, record_id),
        )

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
