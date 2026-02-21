import sys


def warn_unusual_date_order(
    payment_date: str | None,
    invoice_date: str | None,
) -> None:
    """Warnt wenn Wertstellungsdatum vor Rechnungsdatum liegt."""
    if payment_date and invoice_date and payment_date < invoice_date:
        print(
            "Warnung: Wertstellungsdatum liegt vor Rechnungsdatum. Bitte prüfen.",
            file=sys.stderr,
        )
