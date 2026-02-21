from pathlib import Path

from ..config import get_audit_user, get_private_accounts, load_config
from ..db import get_db_connection, log_audit, row_to_dict
from ..services.private_classification import classify_expense_private_paid


def _reconcile_private_expenses(
    conn,
    *,
    private_accounts: list[str],
    audit_user: str,
    year: int | None,
    dry_run: bool,
) -> tuple[int, int, int, list[tuple[int, bool, str, bool, str]]]:
    query = "SELECT * FROM expenses WHERE 1=1"
    params: list[object] = []
    if year is not None:
        query += " AND strftime('%Y', COALESCE(payment_date, invoice_date)) = ?"
        params.append(str(year))
    query += " ORDER BY COALESCE(payment_date, invoice_date) ASC, id ASC"

    category_rows = conn.execute(
        "SELECT id, name FROM categories WHERE type = 'expense'"
    ).fetchall()
    category_lookup = {row["id"]: row["name"] for row in category_rows}

    checked = 0
    changed = 0
    skipped_manual = 0
    changes: list[tuple[int, bool, str, bool, str]] = []

    rows = conn.execute(query, params).fetchall()
    for row in rows:
        checked += 1
        old_is_private_paid = bool(row["is_private_paid"])
        old_classification = row["private_classification"] or "none"

        if old_classification == "manual":
            skipped_manual += 1
            continue

        category_name = category_lookup.get(row["category_id"])
        new_is_private_paid, new_classification = classify_expense_private_paid(
            account=row["account"],
            category_name=category_name,
            private_accounts=private_accounts,
        )

        if (
            new_is_private_paid == old_is_private_paid
            and new_classification == old_classification
        ):
            continue

        changed += 1
        changes.append(
            (
                row["id"],
                old_is_private_paid,
                old_classification,
                new_is_private_paid,
                new_classification,
            )
        )

        if dry_run:
            continue

        old_data = row_to_dict(row)
        new_data = dict(old_data)
        new_data["is_private_paid"] = 1 if new_is_private_paid else 0
        new_data["private_classification"] = new_classification

        conn.execute(
            """UPDATE expenses
               SET is_private_paid = ?, private_classification = ?
               WHERE id = ?""",
            (1 if new_is_private_paid else 0, new_classification, row["id"]),
        )
        log_audit(
            conn,
            "expenses",
            row["id"],
            "MIGRATE",
            record_uuid=row["uuid"],
            old_data=old_data,
            new_data=new_data,
            user=audit_user,
        )

    if not dry_run:
        conn.commit()

    return checked, changed, skipped_manual, changes


def cmd_reconcile_private(args):
    """Reklassifiziert persistierte Sacheinlagen auf Basis der aktuellen Config."""
    db_path = Path(args.db)
    conn = get_db_connection(db_path)
    config = load_config()
    audit_user = get_audit_user(config)
    private_accounts = get_private_accounts(config)

    try:
        checked, changed, skipped_manual, changes = _reconcile_private_expenses(
            conn,
            private_accounts=private_accounts,
            audit_user=audit_user,
            year=args.year,
            dry_run=bool(args.dry_run),
        )
    finally:
        conn.close()

    suffix = " (Dry-Run)" if args.dry_run else ""
    print(f"Reconcile private abgeschlossen{suffix}.")
    print(f"  Geprüft: {checked}")
    print(f"  Geändert: {changed}")
    print(f"  Übersprungen (manuell): {skipped_manual}")

    if not changes:
        return

    print("  Geplante Änderungen:" if args.dry_run else "  Änderungen:")
    for record_id, old_paid, old_cls, new_paid, new_cls in changes[:25]:
        old_label = f"{'1' if old_paid else '0'}/{old_cls}"
        new_label = f"{'1' if new_paid else '0'}/{new_cls}"
        print(f"    Ausgabe #{record_id}: {old_label} -> {new_label}")
    if len(changes) > 25:
        print(f"    ... {len(changes) - 25} weitere Änderung(en)")
