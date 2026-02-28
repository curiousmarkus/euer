from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Category:
    id: int | None
    uuid: str
    name: str
    eur_line: int | None
    type: str


@dataclass
class LedgerAccount:
    key: str
    name: str
    category: str
    account_number: str | None = None


@dataclass
class Expense:
    id: int | None
    uuid: str
    payment_date: str | None
    invoice_date: str | None
    vendor: str
    amount_eur: float
    category_id: int | None
    category_name: str | None = None
    category_eur_line: int | None = None
    account: str | None = None
    ledger_account: str | None = None
    receipt_name: str | None = None
    foreign_amount: str | None = None
    notes: str | None = None
    is_rc: bool = False
    vat_input: float | None = None
    vat_output: float | None = None
    is_private_paid: bool = False
    private_classification: str = "none"
    hash: str | None = None

    @property
    def date(self) -> str:
        """Kompatibilitätsalias: priorisiert Wertstellungsdatum."""
        return self.payment_date or self.invoice_date or ""


@dataclass
class Income:
    id: int | None
    uuid: str
    payment_date: str | None
    invoice_date: str | None
    source: str
    amount_eur: float
    category_id: int | None
    category_name: str | None = None
    category_eur_line: int | None = None
    ledger_account: str | None = None
    receipt_name: str | None = None
    foreign_amount: str | None = None
    notes: str | None = None
    vat_output: float | None = None
    hash: str | None = None

    @property
    def date(self) -> str:
        """Kompatibilitätsalias: priorisiert Wertstellungsdatum."""
        return self.payment_date or self.invoice_date or ""


@dataclass
class PrivateTransfer:
    id: int | None
    uuid: str
    date: str
    type: str
    amount_eur: float
    description: str
    notes: str | None = None
    related_expense_id: int | None = None
    hash: str | None = None
