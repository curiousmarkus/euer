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


def normalize_category_name(value: object) -> str | None:
    """Normalisiert Kategorienamen (entfernt optionale EÜR-Zeilennummern)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(")") and " (" in text:
        base, _, tail = text.rpartition(" (")
        if tail[:-1].isdigit():
            return base
    return text


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
    raw_type = get_row_value(row, "type", "kind", "direction", "Typ")
    amount_value = get_row_value(
        row, "amount_eur", "amount", "EUR", "Betrag", "Betrag in EUR"
    )
    amount = parse_amount(amount_value)

    row_type = parse_import_type(raw_type)
    if not row_type and amount is not None:
        if amount < 0:
            row_type = "expense"
        elif amount > 0:
            row_type = "income"

    category_value = get_row_value(row, "category", "category_name", "Kategorie")

    return {
        "type": row_type,
        "date": get_row_value(row, "date", "Datum"),
        "party": get_row_value(
            row,
            "party",
            "vendor",
            "source",
            "counterparty",
            "Lieferant",
            "Quelle",
            "Partei",
        ),
        "category": normalize_category_name(category_value),
        "amount_eur": amount,
        "account": get_row_value(row, "account", "Konto"),
        "foreign_amount": get_row_value(
            row, "foreign_amount", "foreign", "Fremdwährung", "Fremdwaehrung"
        ),
        "receipt_name": get_row_value(
            row, "receipt_name", "receipt", "Belegname", "Beleg"
        ),
        "notes": get_row_value(row, "notes", "Bemerkung", "Notiz"),
        "rc": parse_bool(get_row_value(row, "rc", "is_rc", "RC")),
        "private_paid": parse_bool(
            get_row_value(row, "private_paid", "Privat bezahlt")
        ),
        "vat_input": parse_amount(
            get_row_value(row, "vat_input", "Vorsteuer", "USt-VA")
        ),
        "vat_output": parse_amount(get_row_value(row, "vat_output", "Umsatzsteuer")),
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
