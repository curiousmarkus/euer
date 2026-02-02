import hashlib
import json


def compute_hash(
    date: str, vendor_or_source: str, amount_eur: float, receipt_name: str = ""
) -> str:
    """Erzeugt einen eindeutigen Hash für eine Transaktion."""
    data = f"{date}|{vendor_or_source}|{amount_eur:.2f}|{receipt_name or ''}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def format_amount(amount: float) -> str:
    """Formatiert einen Betrag mit deutschem Zahlenformat."""
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_bool(value: object) -> bool:
    """Parst verschiedene Wahrheitswerte."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "ja", "j", "x"}


def parse_amount(value: object) -> float | None:
    """Parst Betrag (unterstützt deutsches und internationales Format)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None

    text = text.replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def format_missing_fields(value: str | None) -> str:
    """Formatiert fehlende Felder für die Anzeige."""
    if not value:
        return ""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, list):
        return ", ".join(str(item) for item in parsed)
    return str(parsed)
