import csv
import json
import sys

from .utils import parse_amount, parse_bool


def get_row_value(row: dict, *keys: str) -> object | None:
    """Liest den ersten nicht-leeren Wert aus einem Dict."""
    for key in keys:
        if key in row:
            value = row[key]
        else:
            bom_key = f"\ufeff{key}"
            if bom_key not in row:
                continue
            value = row[bom_key]
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                continue
        return value
    return None


def parse_import_type(value: object) -> str | None:
    """Normalisiert Typ-Angaben auf 'expense' oder 'income'."""
    if value is None:
        return None
    text = str(value).strip().lower()
    mapping = {
        "expense": "expense",
        "expenses": "expense",
        "ausgabe": "expense",
        "ausgaben": "expense",
        "debit": "expense",
        "outflow": "expense",
        "outgoing": "expense",
        "income": "income",
        "einnahme": "income",
        "einnahmen": "income",
        "credit": "income",
        "inflow": "income",
        "incoming": "income",
    }
    return mapping.get(text)


def get_tax_config(config: dict) -> str:
    """Gibt den Steuermodus ('small_business' oder 'standard') zurück."""
    return config.get("tax", {}).get("mode", "small_business")


def normalize_import_row(row: dict) -> dict:
    """Normalisiert Importzeile auf kanonische Keys."""
    raw_type = get_row_value(row, "type", "kind", "direction")
    amount_value = get_row_value(row, "amount_eur", "amount")
    amount = parse_amount(amount_value)

    row_type = parse_import_type(raw_type)
    if not row_type and amount is not None:
        if amount < 0:
            row_type = "expense"
        elif amount > 0:
            row_type = "income"

    return {
        "type": row_type,
        "date": get_row_value(row, "date"),
        "party": get_row_value(row, "party", "vendor", "source", "counterparty"),
        "category": get_row_value(row, "category", "category_name"),
        "amount_eur": amount,
        "account": get_row_value(row, "account"),
        "foreign_amount": get_row_value(row, "foreign_amount", "foreign"),
        "receipt_name": get_row_value(row, "receipt_name", "receipt"),
        "notes": get_row_value(row, "notes"),
        "rc": parse_bool(get_row_value(row, "rc")),
        "vat_input": parse_amount(get_row_value(row, "vat_input")),
        "vat_output": parse_amount(get_row_value(row, "vat_output")),
        "raw_data": row,
    }


def iter_import_rows(path: str, fmt: str) -> list[dict]:
    """Lädt Importdaten aus Datei oder stdin."""
    rows: list[dict] = []
    if path == "-":
        stream = sys.stdin
        if fmt == "csv":
            reader = csv.DictReader(stream)
            rows.extend(reader)
        else:
            for line in stream:
                if not line.strip():
                    continue
                rows.append(json.loads(line))
        return rows

    encoding = "utf-8-sig" if fmt == "csv" else "utf-8"
    with open(path, "r", encoding=encoding) as f:
        if fmt == "csv":
            reader = csv.DictReader(f)
            rows.extend(reader)
        else:
            for line in f:
                if not line.strip():
                    continue
                rows.append(json.loads(line))
    return rows
