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
class Expense:
    id: int | None
    uuid: str
    date: str
    vendor: str
    amount_eur: float
    category_id: int | None
    category_name: str | None = None
    category_eur_line: int | None = None
    account: str | None = None
    receipt_name: str | None = None
    foreign_amount: str | None = None
    notes: str | None = None
    is_rc: bool = False
    vat_input: float | None = None
    vat_output: float | None = None
    is_private_paid: bool = False
    private_classification: str = "none"
    hash: str | None = None


@dataclass
class Income:
    id: int | None
    uuid: str
    date: str
    source: str
    amount_eur: float
    category_id: int | None
    category_name: str | None = None
    category_eur_line: int | None = None
    receipt_name: str | None = None
    foreign_amount: str | None = None
    notes: str | None = None
    vat_output: float | None = None
    hash: str | None = None


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
