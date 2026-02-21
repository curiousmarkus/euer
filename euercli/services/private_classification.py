USAGE_CONTRIBUTION_CATEGORY = "Fahrtkosten (Nutzungseinlage)"


def classify_expense_private_paid(
    *,
    account: str | None,
    category_name: str | None,
    private_accounts: list[str],
    manual_override: bool = False,
) -> tuple[bool, str]:
    """Klassifiziert eine Ausgabe als private Sacheinlage."""
    if manual_override:
        return (True, "manual")

    if category_name and category_name == USAGE_CONTRIBUTION_CATEGORY:
        return (True, "category_rule")

    if account:
        normalized = account.strip().lower()
        for item in private_accounts:
            if normalized == item.strip().lower():
                return (True, "account_rule")

    return (False, "none")
