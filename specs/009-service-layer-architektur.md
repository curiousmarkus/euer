# Spec 009: Service-Layer-Architektur (Import-Refactoring)

## Status

Offen

## Problem

Der Import-Befehl (`euercli/commands/import_data.py`) umgeht den Service Layer und führt rohe SQL-INSERTs aus. Dadurch muss jede neue Geschäftslogik (Validierung, Klassifikation, Berechnung) manuell im Import-Code dupliziert werden. Dies hat bereits zu einer Lücke geführt: Die Private-Klassifikation musste separat in den Import eingebaut werden, statt automatisch über `create_expense()` / `create_income()` zu laufen.

### Ist-Zustand

```
CLI Command (add expense)  →  Service Layer (create_expense)  →  DB
CLI Command (import)       →  ────── direkt SQL INSERT ──────→  DB
```

Die Service-Funktionen `create_expense()` und `create_income()` enthalten:
- Hash-Berechnung (Duplikat-Erkennung)
- Kategorie-Auflösung
- VAT-Berechnung (RC, Standard, Kleinunternehmer)
- Private Klassifikation (`classify_expense_private_paid`)
- Audit-Logging
- Validierung

Der Import dupliziert **all diese Logik** inline (~200 Zeilen).

### Konkreter Fehlerfall

Im Praxistest (Feb 2026) wurde nach `euer init` + `euer import` festgestellt:
- Sacheinlagen wurden nicht erkannt → Private Klassifikation war zwar im Import eingebaut, aber der Agent hatte die Kontonamen transformiert. Wäre die Logik zentral im Service Layer, hätte es eine einzige Stelle zum Debuggen gegeben.
- Zukünftige Features (z.B. automatische Kategorie-Vorschläge, Plausibilitätsprüfungen) müssten in `import_data.py` separat nachgebaut werden.

## Architekturziel

```
CLI Command (add expense)  →  Service Layer (create_expense)  →  DB
CLI Command (import)       →  Service Layer (create_expense)  →  DB
```

**Ein Pfad, eine Wahrheit:** Alle Schreiboperationen laufen über den Service Layer.

---

## Vorgeschlagene Lösung

### 1. Service-Funktionen erweitern

`create_expense()` und `create_income()` müssen die folgenden Parameter akzeptieren, die aktuell nur im Import-Code behandelt werden:

```python
def create_expense(
    conn: Connection,
    *,
    date: str,
    vendor: str,
    category_name: str | None = None,
    amount_eur: float,
    account: str | None = None,
    foreign_amount: str | None = None,
    receipt_name: str | None = None,
    notes: str | None = None,
    rc: bool = False,
    vat_input: float | None = None,   # Überschreibt Auto-Berechnung
    vat_output: float | None = None,  # Überschreibt Auto-Berechnung
    private_paid: bool = False,
    private_accounts: list[str] | None = None,
    audit_user: str = "default",
    tax_mode: str | None = None,      # NEU: für Auto-VAT
    skip_vat_auto: bool = False,      # NEU: VAT explizit übergeben, nicht berechnen
) -> Expense:
```

**Wichtig:** Die VAT-Auto-Berechnung (RC bei Kleinunternehmer etc.) liegt aktuell nur im Import. Sie muss in den Service Layer verschoben oder als optionale Logik eingebaut werden, ohne bestehende `add expense`-Aufrufe zu brechen.

### 2. Import vereinfachen

Nach dem Refactoring reduziert sich der Import-Code auf:

```python
for row_type, normalized in iter_import_rows(path, format_type):
    if row_type == "expense":
        create_expense(
            conn,
            date=normalized["date"],
            vendor=normalized["party"],
            category_name=normalized.get("category"),
            amount_eur=normalized["amount_eur"],
            account=normalized.get("account"),
            foreign_amount=normalized.get("foreign_amount"),
            receipt_name=normalized.get("receipt_name"),
            notes=normalized.get("notes"),
            rc=normalized.get("rc", False),
            vat_input=normalized.get("vat_input"),
            vat_output=normalized.get("vat_output"),
            private_paid=normalized.get("private_paid", False),
            private_accounts=private_accounts,
            audit_user=audit_user,
            tax_mode=tax_mode,
        )
    elif row_type == "income":
        create_income(conn, ...)
```

Duplikat-Erkennung, Hash-Berechnung, Audit-Logging — alles kommt aus dem Service.

### 3. Duplikat-Handling im Service

Aktuell macht der Import die Duplikat-Prüfung selbst (hash-Check + Skip). Der Service Layer sollte diese Option anbieten:

```python
class DuplicateAction(Enum):
    RAISE = "raise"    # ValidationError werfen (Default, wie jetzt bei `add`)
    SKIP = "skip"      # Silently skippen, Zähler zurückgeben

def create_expense(..., on_duplicate: DuplicateAction = DuplicateAction.RAISE) -> Expense | None:
```

### 4. Batch-Performance

Der Import läuft innerhalb einer Transaktion. Das muss auch nach dem Refactoring so bleiben. Die Service-Funktionen dürfen intern kein `conn.commit()` aufrufen — der Caller (Import-Command) steuert die Transaktion.

**Prüfen:** Aktuell ruft `create_expense()` intern `conn.commit()` auf. Für Batch-Nutzung muss das optional sein (z.B. `auto_commit=True` als Default, `auto_commit=False` für Import).

---

## Migrationsstrategie

1. Service-Funktionen erweitern (rückwärtskompatibel durch Defaults)
2. Import-Code schrittweise auf Service-Aufrufe umstellen
3. Inline-SQL aus `import_data.py` entfernen
4. Tests: Bestehende Import-Tests müssen weiterhin grün sein

---

## Betroffene Dateien

| Datei | Änderung |
|-------|----------|
| `euercli/services/expenses.py` | `create_expense()` erweitern: `tax_mode`, `skip_vat_auto`, `on_duplicate` |
| `euercli/services/income.py` | `create_income()` erweitern: `on_duplicate` |
| `euercli/commands/import_data.py` | Inline-SQL durch Service-Aufrufe ersetzen |
| `euercli/commands/add.py` | Ggf. anpassen falls Signatur sich ändert |
| `tests/test_services_expenses.py` | Tests für neue Parameter |
| `tests/test_cli.py` | Import-Tests validieren |

---

## Abgrenzung

- Keine Änderung am Import-Dateiformat (CSV/JSONL bleibt gleich)
- Keine neuen CLI-Befehle
- Kein Refactoring anderer Commands (nur Import)
- Performance-Regression vermeiden (Batch-Commit beibehalten)

---

## Akzeptanzkriterien

1. `euer import` ruft `create_expense()` / `create_income()` aus dem Service Layer auf
2. Kein direktes SQL-INSERT in `import_data.py`
3. Alle bestehenden Import-Tests bleiben grün
4. Duplikat-Handling (Skip) funktioniert wie bisher
5. VAT-Auto-Berechnung (RC, Steuermodus) liefert identische Ergebnisse
6. Private Klassifikation läuft über denselben Code-Pfad wie `add expense`
7. Performance: Import von 100 Zeilen < 2 Sekunden
