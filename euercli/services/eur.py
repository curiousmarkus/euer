"""Versionierte Zuordnung fachlicher EÜR-Felder zu Formularjahren."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EurField:
    year: int
    key: str
    line: int
    label: str
    source: str
    verification_status: str
    elster_source: str | None = None


BMF_2025 = (
    "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
    "Steuerarten/Einkommensteuer/2025-08-29-anlage-EUER-2025.pdf?__blob=publicationFile&v=2"
)
BMF_2026 = (
    "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
    "Steuerarten/Einkommensteuer/2026-09-01-anlage-EUER-2026.pdf?__blob=publicationFile&v=4"
)
ELSTER_HELP_2025 = "https://www.elster.de/eportal/helpGlobal?themaGlobal=help_euer_ufa_77_2025"


def _fields(
    year: int,
    source: str,
    status: str,
    lines: dict[str, tuple[int, str]],
    *,
    elster_verified_keys: set[str] | None = None,
) -> dict[str, EurField]:
    elster_verified_keys = elster_verified_keys or set()
    return {
        key: EurField(
            year,
            key,
            line,
            label,
            source,
            "elster_verified" if key in elster_verified_keys else status,
            ELSTER_HELP_2025 if key in elster_verified_keys else None,
        )
        for key, (line, label) in lines.items()
    }


FORM_FIELDS: dict[int, dict[str, EurField]] = {
    2025: _fields(
        2025,
        BMF_2025,
        "bmf_verified",
        {
            "goods_materials": (27, "Waren, Rohstoffe und Hilfsstoffe"),
            "external_services": (29, "Bezogene Fremdleistungen"),
            "low_value_assets": (36, "Geringwertige Wirtschaftsgüter"),
            "telecommunications": (43, "Telekommunikation"),
            "travel_accommodation": (44, "Übernachtungs- und Reisenebenkosten"),
            "training": (45, "Fortbildungskosten"),
            "tax_advice": (46, "Rechts- und Steuerberatung, Buchführung"),
            "insurance_fees": (49, "Beiträge, Gebühren, Abgaben und Versicherungen"),
            "computer_costs": (50, "Laufende EDV-Kosten"),
            "work_equipment": (51, "Arbeitsmittel"),
            "advertising": (54, "Werbekosten"),
            "input_vat": (57, "Abziehbare Vorsteuer"),
            "vat_paid": (58, "Gezahlte Umsatzsteuer"),
            "other_operating_expenses": (60, "Übrige Betriebsausgaben"),
            "entertainment_deductible": (63, "Bewirtungsaufwendungen, abziehbar"),
            "entertainment_non_deductible": (
                63,
                "Bewirtungsaufwendungen, nicht abziehbar",
            ),
            "meal_allowance": (64, "Verpflegungsmehraufwendungen"),
            "vehicle_use_contribution": (71, "Fahrtkosten (Nutzungseinlage)"),
            "small_business_income": (12, "Betriebseinnahmen als Kleinunternehmer"),
            "small_business_non_taxable_subset": (
                13,
                "Davon nicht steuerbare Umsätze nach § 19 Abs. 2 UStG",
            ),
            "taxable_business_income": (15, "Umsatzsteuerpflichtige Betriebseinnahmen"),
            "tax_free_income": (16, "Umsatzsteuerfreie/nicht umsatzsteuerbare Einnahmen"),
            "vat_collected": (17, "Vereinnahmte Umsatzsteuer"),
            "vat_refund": (18, "Vom Finanzamt erstattete Umsatzsteuer"),
            "asset_disposal": (19, "Veräußerung oder Entnahme von Anlagevermögen"),
            "private_vehicle_use": (20, "Private Kfz-Nutzung"),
            "other_private_withdrawals": (21, "Sonstige Sach-, Nutzungs- und Leistungsentnahmen"),
            "private_withdrawals": (106, "Privatentnahmen"),
            "private_deposits": (107, "Privateinlagen"),
        },
        elster_verified_keys={
            "input_vat",
            "entertainment_deductible",
            "entertainment_non_deductible",
        },
    ),
    2026: _fields(
        2026,
        BMF_2026,
        "bmf_verified",
        {
            "goods_materials": (29, "Waren, Rohstoffe und Hilfsstoffe"),
            "external_services": (30, "Bezogene Fremdleistungen"),
            "low_value_assets": (37, "Geringwertige Wirtschaftsgüter"),
            "telecommunications": (44, "Telekommunikation"),
            "travel_accommodation": (45, "Übernachtungs- und Reisenebenkosten"),
            "training": (46, "Fortbildungskosten"),
            "tax_advice": (47, "Rechts- und Steuerberatung, Buchführung"),
            "insurance_fees": (50, "Beiträge, Gebühren, Abgaben und Versicherungen"),
            "computer_costs": (51, "Laufende EDV-Kosten"),
            "work_equipment": (52, "Arbeitsmittel"),
            "advertising": (55, "Werbekosten"),
            "input_vat": (58, "Abziehbare Vorsteuer"),
            "vat_paid": (59, "Gezahlte Umsatzsteuer"),
            "other_operating_expenses": (61, "Übrige Betriebsausgaben"),
            "entertainment_deductible": (64, "Bewirtungsaufwendungen, abziehbar"),
            "entertainment_non_deductible": (
                64,
                "Bewirtungsaufwendungen, nicht abziehbar",
            ),
            "meal_allowance": (65, "Verpflegungsmehraufwendungen"),
            "vehicle_use_contribution": (72, "Fahrtkosten (Nutzungseinlage)"),
            "small_business_income": (12, "Betriebseinnahmen als Kleinunternehmer"),
            "small_business_non_taxable_subset": (
                13,
                "Davon nicht steuerbare Umsätze nach § 19 Abs. 2 UStG",
            ),
            "taxable_business_income": (15, "Umsatzsteuerpflichtige Betriebseinnahmen"),
            "tax_free_income": (16, "Umsatzsteuerfreie/nicht umsatzsteuerbare Einnahmen"),
            "vat_collected": (17, "Vereinnahmte Umsatzsteuer"),
            "vat_refund": (18, "Vom Finanzamt erstattete Umsatzsteuer"),
            "asset_disposal": (19, "Veräußerung oder Entnahme von Anlagevermögen"),
            "private_vehicle_use": (20, "Private Kfz-Nutzung"),
            "other_private_withdrawals": (21, "Sonstige Sach-, Nutzungs- und Leistungsentnahmen"),
            "private_withdrawals": (107, "Privatentnahmen"),
            "private_deposits": (108, "Privateinlagen"),
        },
    ),
}


# Stabile Schlüssel werden an Seed-Kategorien gespeichert. Die Namen und IDs der
# bereits verwendeten Kategorien bleiben dabei unverändert.
CATEGORY_EUR_KEYS: dict[tuple[str, str], str] = {
    ("Waren, Rohstoffe und Hilfsstoffe", "expense"): "goods_materials",
    ("Bezogene Fremdleistungen", "expense"): "external_services",
    ("Aufwendungen für geringwertige Wirtschaftsgüter (GWG)", "expense"): "low_value_assets",
    ("Telekommunikation", "expense"): "telecommunications",
    ("Übernachtungs- und Reisenebenkosten", "expense"): "travel_accommodation",
    ("Fortbildungskosten", "expense"): "training",
    ("Rechts- und Steuerberatung, Buchführung", "expense"): "tax_advice",
    ("Beiträge, Gebühren, Abgaben und Versicherungen", "expense"): "insurance_fees",
    ("Laufende EDV-Kosten", "expense"): "computer_costs",
    ("Arbeitsmittel", "expense"): "work_equipment",
    ("Werbekosten", "expense"): "advertising",
    ("Gezahlte USt", "expense"): "vat_paid",
    ("Übrige Betriebsausgaben", "expense"): "other_operating_expenses",
    ("Bewirtungsaufwendungen", "expense"): "entertainment",
    ("Verpflegungsmehraufwendungen", "expense"): "meal_allowance",
    ("Fahrtkosten (Nutzungseinlage)", "expense"): "vehicle_use_contribution",
    ("Betriebseinnahmen als Kleinunternehmer", "income"): "small_business_income",
    ("Nicht steuerbare Umsätze", "income"): "small_business_non_taxable_subset",
    ("Umsatzsteuerpflichtige Betriebseinnahmen", "income"): "taxable_business_income",
    (
        "Umsatzsteuerfreie, nicht umsatzsteuerbare Betriebseinnahmen",
        "income",
    ): "tax_free_income",
    ("Vereinnahmte Umsatzsteuer", "income"): "vat_collected",
    ("Vom Finanzamt erstattete Umsatzsteuer", "income"): "vat_refund",
    ("Veräußerung oder Entnahme von Anlagevermögen", "income"): "asset_disposal",
    ("Private Kfz-Nutzung", "income"): "private_vehicle_use",
    ("Sonstige Sach-, Nutzungs- und Leistungsentnahmen", "income"): "other_private_withdrawals",
}


CATEGORY_FIELD_KEYS: dict[str, str] = {
    "goods_materials": "goods_materials",
    "external_services": "external_services",
    "low_value_assets": "low_value_assets",
    "telecommunications": "telecommunications",
    "travel_accommodation": "travel_accommodation",
    "training": "training",
    "tax_advice": "tax_advice",
    "insurance_fees": "insurance_fees",
    "computer_costs": "computer_costs",
    "work_equipment": "work_equipment",
    "advertising": "advertising",
    "vat_paid": "vat_paid",
    "other_operating_expenses": "other_operating_expenses",
    "entertainment": "entertainment_deductible",
    "meal_allowance": "meal_allowance",
    "vehicle_use_contribution": "vehicle_use_contribution",
    "small_business_income": "small_business_income",
    "small_business_non_taxable_subset": "small_business_non_taxable_subset",
    "taxable_business_income": "taxable_business_income",
    "tax_free_income": "tax_free_income",
    "vat_collected": "vat_collected",
    "vat_refund": "vat_refund",
    "asset_disposal": "asset_disposal",
    "private_vehicle_use": "private_vehicle_use",
    "other_private_withdrawals": "other_private_withdrawals",
}


def category_key_for_name(name: str, category_type: str) -> str | None:
    """Löst Seed-Namen auf stabile fachliche EÜR-Schlüssel auf."""
    return CATEGORY_EUR_KEYS.get((name, category_type))


def get_eur_field(year: int, key: str) -> EurField | None:
    """Gibt nur für lokal geprüfte Formularjahre ein Feld zurück."""
    return FORM_FIELDS.get(year, {}).get(key)


def get_category_eur_field(year: int, category_key: str | None) -> EurField | None:
    if category_key is None:
        return None
    field_key = CATEGORY_FIELD_KEYS.get(category_key)
    if field_key is None:
        return None
    return get_eur_field(year, field_key)


def get_category_eur_line(year: int, category_key: str | None) -> int | None:
    field = get_category_eur_field(year, category_key)
    return field.line if field is not None else None


def get_category_display_name(name: str | None, category_key: str | None) -> str | None:
    if category_key == "small_business_non_taxable_subset":
        return "Davon nicht steuerbare Kleinunternehmerumsätze (§ 19 Abs. 2 UStG)"
    return name


def is_entertainment_category(category_key: str | None) -> bool:
    return category_key == "entertainment"


def is_small_business_subset(category_key: str | None) -> bool:
    return category_key == "small_business_non_taxable_subset"


def is_paid_vat_category(category_key: str | None) -> bool:
    return category_key == "vat_paid"
