# Spec 008: Privateinlagen & Privatentnahmen

## Status

Implementiert

## Problem

Für die EÜR-Abgabe über ELSTER müssen **Privateinlagen** und **Privatentnahmen** separat ausgewiesen werden (Anlage EÜR, v. a. Zeilen 121/122). Aktuell gibt es im System keine belastbare Erfassung dieser Vorgänge.

Es fehlen zwei Kernfähigkeiten:
1. Reine Kapitalbewegungen zwischen Privat- und Geschäftsbereich (ohne Gewinnwirkung)
2. Saubere Abbildung von **Sacheinlagen** (betrieblich veranlasste Ausgaben, privat bezahlt)

## Architekturziele

1. **Gewinnneutralität sichern:** Privateinlagen/Privatentnahmen dürfen den EÜR-Gewinn nicht verändern.
2. **Historie stabil halten:** ELSTER-relevante Summen dürfen sich nachträglich nicht durch Config-Änderungen verschieben.
3. **Auditierbarkeit erhöhen:** Ausgleichsbuchungen sollen optional auf die verursachende Ausgabe referenzieren.
4. **CLI-Kompatibilität wahren:** Bestehende Befehle wie `euer summary --year YYYY` bleiben unverändert nutzbar.
5. **Export trennscharf machen:** Rohdaten und abgeleitete Daten dürfen nicht unklar vermischt werden.

---

## Hintergrund

### Steuerliche Definition

**Privateinlagen** sind Zuführungen von privatem Vermögen in das Betriebsvermögen:
- Überweisung vom Privatkonto auf das Geschäftskonto
- Betriebsausgabe, die vom Privatkonto bezahlt wurde (Sacheinlage)
- Nutzungseinlage (z. B. privater PKW für betriebliche Fahrten)

**Privatentnahmen** sind Entnahmen von betrieblichem Vermögen für private Zwecke:
- Überweisung vom Geschäftskonto auf das Privatkonto
- Private Rechnung, die vom Geschäftskonto bezahlt wurde
- Barentnahme aus der Geschäftskasse

### ELSTER-Relevanz

| Zeile | Bezeichnung |
|-------|-------------|
| 121   | Privatentnahmen (einschließlich Sach-, Leistungs- und Nutzungsentnahmen) |
| 122   | Privateinlagen (einschließlich Sach-, Leistungs- und Nutzungseinlagen) |

Diese Werte beeinflussen **nicht** den EÜR-Gewinn, dienen aber der Plausibilitätsprüfung.

### Typische Szenarien

| # | Szenario | Privateinlage | Privatentnahme | EÜR-Wirkung |
|---|----------|---------------|----------------|------------|
| 1 | Betriebsausgabe 100 EUR privat bezahlt | 100 EUR | - | Ausgabe 100 EUR |
| 2 | Überweisung 500 EUR vom Privatkonto aufs Geschäftskonto | 500 EUR | - | Keine |
| 3 | Überweisung 1.000 EUR vom Geschäftskonto aufs Privatkonto | - | 1.000 EUR | Keine |
| 4 | Private Rechnung 800 EUR vom Geschäftskonto bezahlt | - | 800 EUR | Keine |
| 5 | Ausgabe 200 EUR privat bezahlt, später Ausgleich ans Privatkonto | 200 EUR | 200 EUR | Ausgabe 200 EUR |

---

## Vorgeschlagene Lösung

### 1. Neue Tabelle `private_transfers` (direkte Privatvorgänge)

```sql
CREATE TABLE IF NOT EXISTS private_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    date DATE NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('deposit', 'withdrawal')),
    amount_eur REAL NOT NULL CHECK(amount_eur > 0),
    description TEXT NOT NULL,
    notes TEXT,
    related_expense_id INTEGER REFERENCES expenses(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash TEXT UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_private_transfers_date ON private_transfers(date);
CREATE INDEX IF NOT EXISTS idx_private_transfers_type ON private_transfers(type);
CREATE INDEX IF NOT EXISTS idx_private_transfers_related_expense ON private_transfers(related_expense_id);
```

| Spalte | Beschreibung |
|--------|--------------|
| `type` | `deposit` = Privateinlage, `withdrawal` = Privatentnahme |
| `amount_eur` | Immer positiv, Richtung über `type` |
| `related_expense_id` | Optionale Referenz für Ausgleichsbuchungen (Szenario 5) |
| `hash` | Duplikat-Erkennung analog zu `expenses`/`income` |

### 2. Erweiterung `expenses` für historisch stabile Sacheinlagen

Die reine Laufzeit-Ableitung via aktueller Config ist nicht stabil genug. Daher wird die Klassifikation beim Buchen persistiert.

```sql
ALTER TABLE expenses ADD COLUMN is_private_paid INTEGER NOT NULL DEFAULT 0 CHECK(is_private_paid IN (0, 1));
ALTER TABLE expenses ADD COLUMN private_classification TEXT NOT NULL DEFAULT 'none'
    CHECK(private_classification IN ('none', 'account_rule', 'category_rule', 'manual'));
```

| Feld | Bedeutung |
|------|-----------|
| `is_private_paid` | 1 = Ausgabe gilt als Sacheinlage |
| `private_classification` | Warum als Sacheinlage gewertet wurde |

### 3. Klassifikationsregeln für Sacheinlagen

Eine Ausgabe wird als Sacheinlage (`is_private_paid = 1`) markiert, wenn mindestens eine Bedingung erfüllt ist:
1. `account` matcht case-insensitive einen Eintrag aus `config.toml [accounts].private`
2. Kategorie ist `Fahrtkosten (Nutzungseinlage)`
3. User setzt explizit `--private-paid` beim Buchen/Aktualisieren

Wichtig:
- Klassifikation wird beim Schreiben persistiert.
- Spätere Config-Änderungen verändern alte Jahre **nicht** rückwirkend.
- Bei Update einer Ausgabe wird die Klassifikation neu berechnet (oder explizit per Flag gesetzt) und durch Audit-Log nachvollziehbar.

#### Konfiguration in `config.toml`

```toml
[accounts]
private = ["privat", "private Kreditkarte", "private KK", "Barauslagen"]
```

---

## CLI-Befehle

### 1. Buchen

```bash
# Direkte Einlage
euer add private-deposit \
    --date 2026-01-15 \
    --amount 500 \
    --description "Überweisung vom Privatkonto"

# Direkte Entnahme
euer add private-withdrawal \
    --date 2026-01-20 \
    --amount 1000 \
    --description "Überweisung auf Privatkonto"

# Entnahme als Ausgleich zu einer privat bezahlten Ausgabe
euer add private-withdrawal \
    --date 2026-01-20 \
    --amount 200 \
    --description "Ausgleich Adobe" \
    --related-expense-id 14
```

### 2. Auflisten

```bash
euer list private-deposits [--year YYYY]
euer list private-withdrawals [--year YYYY]
euer list private-transfers [--year YYYY]
```

Beispiel `euer list private-transfers --year 2026`:

```text
Privateinlagen & Privatentnahmen 2026
=====================================

Privateinlagen (Geld/Werte -> Geschäft):
  ID   Datum        Beschreibung                      EUR      Quelle
   1   2026-01-15   Überweisung vom Privatkonto     500,00    Direktbuchung
  --   2026-01-10   Adobe Creative Cloud             22,99    Ausgabe #14 (Sacheinlage)
  --   2026-02-05   Hetzner Server                   15,00    Ausgabe #23 (Sacheinlage)
  ---------------------------------------------------------------
  SUMME                                               537,99 EUR

Privatentnahmen (Geld/Werte <- Geschäft):
  ID   Datum        Beschreibung                      EUR      Quelle
   2   2026-01-20   Überweisung auf Privatkonto    1.000,00   Direktbuchung
   3   2026-01-25   Urlaubsbuchung (privat)          800,00   Direktbuchung
  ---------------------------------------------------------------
  SUMME                                             1.800,00 EUR
```

### 3. Summary (kompatibel)

Bestehendes Verhalten bleibt gültig:

```bash
euer summary --year 2026
```

Erweiterung ohne Breaking Change:

```bash
euer summary --year 2026 --include-private
```

Optionaler dedizierter Kurzbericht:

```bash
euer private-summary --year 2026
```

Beispielausgabe `euer private-summary --year 2026`:

```text
Privateinlagen & Privatentnahmen für ELSTER 2026
=================================================

Privateinlagen (Zeile 122):
  Sacheinlagen (persistiert in expenses):             37,99 EUR
  Direkte Einlagen (private_transfers):              500,00 EUR
  -----------------------------------------------------------
  GESAMT Privateinlagen:                             537,99 EUR

Privatentnahmen (Zeile 121):
  Direkte Entnahmen (private_transfers):           1.800,00 EUR
  -----------------------------------------------------------
  GESAMT Privatentnahmen:                          1.800,00 EUR
```

### 4. Bearbeiten / Löschen

```bash
euer update private-transfer <ID> --amount 600 --description "Korrektur"
euer delete private-transfer <ID>
```

---

## Integration in `euer summary`

Bei `--include-private` wird die bestehende Ausgabe um eine Sektion ergänzt:

```text
Privatvorgänge (ELSTER Zeilen 121/122):
  Privateinlagen (Zeile 122)                         537,99 EUR
  Privatentnahmen (Zeile 121)                      1.800,00 EUR
```

Die Gewinnberechnung bleibt unverändert.

---

## Export-Integration

Export wird in **Rohdaten** und **abgeleitete Daten** getrennt:

1. `private_transfers_YYYY.csv` / Sheet `PrivateTransfers`
   - Nur direkt gebuchte Einlagen/Entnahmen
   - Re-importfähig

2. `private_contributions_from_expenses_YYYY.csv` / Sheet `Sacheinlagen`
   - Aus `expenses.is_private_paid = 1` abgeleitet
   - Analyse-/Nachweisdaten, nicht als Rohbuchungsimport gedacht

3. Optionaler Gesamtbericht:
   - `private_summary_YYYY.csv` mit aggregierten ELSTER-Summen (Zeile 121/122)

---

## Service Layer

### Datenmodell

```python
@dataclass
class PrivateTransfer:
    id: int | None
    uuid: str
    date: str
    type: str  # "deposit" | "withdrawal"
    amount_eur: float
    description: str
    notes: str | None
    related_expense_id: int | None
    hash: str | None
```

### Service-Funktionen (`euercli/services/private_transfers.py`)

```python
def create_private_transfer(
    conn: Connection,
    *,
    date: str,
    transfer_type: str,
    amount_eur: float,
    description: str,
    notes: str | None = None,
    related_expense_id: int | None = None,
    audit_user: str,
) -> PrivateTransfer: ...


def get_private_transfer_list(
    conn: Connection,
    *,
    transfer_type: str | None = None,
    year: int | None = None,
) -> list[PrivateTransfer]: ...


def classify_expense_private_paid(
    *,
    account: str | None,
    category_name: str | None,
    private_accounts: list[str],
    manual_override: bool = False,
) -> tuple[bool, str]:
    """Returns: (is_private_paid, classification_source)."""
    ...


def get_sacheinlagen(
    conn: Connection,
    *,
    year: int | None = None,
) -> list[Expense]:
    """Liest persistierte Sacheinlagen (expenses.is_private_paid = 1)."""
    ...


def get_private_summary(
    conn: Connection,
    *,
    year: int,
) -> dict:
    """Berechnet ELSTER-Zeilen 121/122 aus privaten Transfers + persistierten Sacheinlagen."""
    ...
```

### Query für Sacheinlagen

```sql
SELECT e.*, c.name AS category_name, c.eur_line AS category_eur_line
FROM expenses e
LEFT JOIN categories c ON e.category_id = c.id
WHERE e.is_private_paid = 1
  AND strftime('%Y', e.date) = ?
ORDER BY e.date;
```

---

## CLI-Parser-Integration (`euercli/cli.py`)

Erweiterungen:
1. `add private-deposit` / `add private-withdrawal`
2. `list private-deposits` / `list private-withdrawals` / `list private-transfers`
3. `update private-transfer` / `delete private-transfer`
4. `summary --include-private` (Flag)
5. Neuer Top-Level-Befehl `private-summary`
6. Bei `add expense` und `update expense`: neues Flag `--private-paid`

---

## Migrationsstrategie

Auch ohne produktive Nutzer muss Schema-Upgrade für bestehende Dev-DBs robust sein:

1. `CREATE TABLE IF NOT EXISTS private_transfers`
2. `PRAGMA table_info(expenses)` prüfen
3. Falls fehlend: `ALTER TABLE expenses ADD COLUMN is_private_paid ...`
4. Falls fehlend: `ALTER TABLE expenses ADD COLUMN private_classification ...`

Optionales Backfill-Kommando für Altbestände:

```bash
euer reconcile private [--year YYYY] [--dry-run]
```

Zweck: bestehende `expenses` einmalig anhand aktueller Regeln klassifizieren und persistieren.

---

## Audit-Logging

Alle INSERT/UPDATE/DELETE auf `private_transfers` werden geloggt.

Zusätzlich wird bei Änderungen an `expenses.is_private_paid` oder `expenses.private_classification` immer ein UPDATE-Audit geschrieben.

---

## Validierungsregeln

1. `amount_eur > 0` (DB-Constraint + Applikationsvalidierung)
2. `type IN ('deposit', 'withdrawal')` (DB-Constraint)
3. `date` im Format `YYYY-MM-DD`
4. `description` nicht leer
5. `related_expense_id` muss existieren, falls gesetzt
6. Duplikat-Erkennung via `hash = compute_hash(date, description, amount_eur)`

---

## Testplan

### Unit-Tests (`tests/test_services_private_transfers.py`)

- `test_create_deposit`
- `test_create_withdrawal`
- `test_amount_must_be_positive`
- `test_related_expense_reference_valid`
- `test_list_by_type`
- `test_list_by_year`
- `test_duplicate_detection`
- `test_update`
- `test_delete`
- `test_sacheinlagen_from_persisted_flag`
- `test_nutzungseinlage_category_sets_private_paid`
- `test_summary_calculation`
- `test_summary_stable_after_config_change`

### CLI-Tests (`tests/test_cli.py`, Erweiterung)

- `test_add_private_deposit`
- `test_add_private_withdrawal`
- `test_add_private_withdrawal_with_related_expense`
- `test_list_private_transfers`
- `test_summary_include_private_flag`
- `test_private_summary_command`
- `test_expense_private_paid_flag_persisted`
- `test_private_totals_unchanged_after_config_edit`

---

## Abgrenzung / Nicht im Scope

- Keine automatische Erkennung von Privatentnahmen aus normalen Ausgaben/Einnahmen (außer explizit über `private_transfers`)
- Keine automatische USt-Sonderlogik auf Privatentnahmen
- Keine komplexe Entnahmebewertung für Anlagenvermögen über diesen Scope hinaus

---

## Getroffene Entscheidungen (nicht mehr offen)

1. **Nutzungseinlage Fahrtkosten:** Wird automatisch als Privateinlage behandelt (auch ohne privates Konto).
2. **Default-Config:** `accounts.private` enthält standardmäßig `"privat"`.
3. **Historie:** Sacheinlagen werden persistiert (`expenses.is_private_paid`) statt nur dynamisch aus aktueller Config abgeleitet.

---

## Akzeptanzkriterien (Definition of Done)

1. `private_transfers` ist mit positiver Betragsvalidierung implementiert.
2. `expenses` speichert private Klassifikation persistent.
3. Änderung von `config.toml [accounts].private` ändert alte Jahres-Summen nicht rückwirkend.
4. `euer summary --year YYYY` bleibt kompatibel; `--include-private` erweitert nur die Ausgabe.
5. `euer private-summary --year YYYY` liefert ELSTER-relevante Zeilen 121/122.
6. Export trennt Rohdaten und abgeleitete Sacheinlagen.
7. Tests für Stabilität, Verknüpfung und Summenlogik sind grün.

---

## Zusammenfassung der Dateiänderungen

| Datei | Änderung |
|-------|----------|
| `euercli/schema.py` | Tabelle `private_transfers`, neue Spalten in `expenses` |
| `euercli/services/private_transfers.py` | Neu: CRUD + Summary + Sacheinlagen-Abfragen |
| `euercli/services/models.py` | `PrivateTransfer` erweitert um `related_expense_id` |
| `euercli/services/expenses.py` | Persistente Klassifikation `is_private_paid` / `private_classification` |
| `euercli/commands/add.py` | `cmd_add_private_deposit`, `cmd_add_private_withdrawal`, `--private-paid` für Ausgaben |
| `euercli/commands/list.py` | Private-Listenbefehle |
| `euercli/commands/delete.py` | `delete private-transfer` |
| `euercli/commands/update.py` | `update private-transfer` + optional Re-Klassifikation Ausgabe |
| `euercli/commands/summary.py` | `--include-private` + Ausgabe-Sektion |
| `euercli/commands/private_summary.py` | Neu: dedizierter ELSTER-Privatbericht |
| `euercli/commands/export.py` | Getrennte Exporte für Roh-/abgeleitete Privatdaten |
| `euercli/config.py` | Lesen von `[accounts].private` |
| `euercli/cli.py` | Parser-Registrierung neuer Befehle/Flags |
| `tests/test_services_private_transfers.py` | Neu: Service-Tests |
| `tests/test_cli.py` | Erweiterte CLI-Tests |

---

## Change Requests (Post-Review)

Folgende Nachbesserungen wurden nach dem ersten Review und einem realen Praxistest identifiziert.

### CR-1: `euer reconcile private` implementieren (HOCH)

**Problem:** Im Praxistest wurden Expenses per `euer import` importiert, ohne dass `euer setup` vorher gelaufen war. Die privaten Kontonamen waren daher nicht konfiguriert, und alle Ausgaben wurden mit `is_private_paid = 0` persistiert. Es gibt aktuell keine Möglichkeit, bestehende Expenses nachträglich anhand der (inzwischen korrekten) Config zu re-klassifizieren.

**Lösung:** Das in der Spec bereits vorgesehene Backfill-Kommando implementieren:

```bash
euer reconcile private [--year YYYY] [--dry-run]
```

**Verhalten:**
- Liest alle `expenses` (optional gefiltert nach `--year`)
- Wendet `classify_expense_private_paid()` mit der aktuellen Config auf jede Ausgabe an
- Vergleicht mit persistiertem `is_private_paid` / `private_classification`
- Aktualisiert nur abweichende Datensätze
- Schreibt Audit-Log für jede Änderung (`action = 'MIGRATE'`)
- `--dry-run` zeigt geplante Änderungen ohne zu schreiben
- Ausgabe: Anzahl geprüft / geändert / übersprungen (manuell klassifizierte nicht überschreiben)

**Wichtig:** `private_classification = 'manual'` darf NICHT überschrieben werden (User hat bewusst `--private-paid` gesetzt). Nur `none`, `account_rule`, `category_rule` werden re-evaluiert.

**Dateien:**
| Datei | Änderung |
|-------|----------|
| `euercli/commands/reconcile.py` | Neu: `cmd_reconcile_private()` |
| `euercli/cli.py` | Parser `reconcile private` registrieren |
| `tests/test_cli.py` | Test: reconcile ändert Klassifikation, dry-run ändert nichts, manual bleibt |

---

### CR-2: Onboarding → `euer setup`-Brücke (HOCH)

**Problem:** Das Onboarding (Interview in separatem LLM-Chat) sammelt alle relevanten Daten inkl. privater Kontonamen und erzeugt eine `Agents.md`. Aber die dort gesammelten Werte müssen danach nochmals manuell in `euer setup` eingegeben werden. Im Praxistest wurde `euer setup` einfach übersprungen — die privaten Konten waren dann nicht in der `config.toml`, und Sacheinlagen wurden nicht erkannt.

**Lösung (mehrstufig):**

**a) `euer setup` um nicht-interaktiven Modus erweitern:**

```bash
# Einzelne Config-Werte direkt setzen (kein interaktiver Prompt)
euer setup --set accounts.private "privat, Sparkasse Giro, Sparkasse Kreditkarte"
euer setup --set tax.mode "small_business"
euer setup --set receipts.expenses "/pfad/zu/belegen/ausgaben"
euer setup --set user.name "Markus"
```

**b) Onboarding-Prompt: Am Ende copy-paste-fertige Setup-Befehle ausgeben:**

Der Onboarding-Assistent soll nach der `Agents.md` zusätzlich folgende Sektion ausgeben:

```
## Setup-Befehle (copy & paste in dein Terminal)

euer init
euer setup --set tax.mode "small_business"
euer setup --set receipts.expenses "/Users/markus/.../Belege/Ausgaben"
euer setup --set receipts.income "/Users/markus/.../Belege/Einnahmen"
euer setup --set exports.directory "/Users/markus/.../exports"
euer setup --set user.name "Markus"
euer setup --set accounts.private "privat, Sparkasse Kreditkarte"
```

**Dateien:**
| Datei | Änderung |
|-------|----------|
| `euercli/commands/setup.py` | `--set KEY VALUE`-Modus ergänzen |
| `euercli/cli.py` | Parser für `setup --set` erweitern |
| `docs/templates/onboarding-prompt.md` | Schlusswort um Setup-Befehle ergänzen |
| `tests/test_cli.py` | Test: `euer setup --set accounts.private "..."` |

---

### CR-3: `private_paid`-Feld im Import-Schema (MITTEL)

**Problem:** Das Import-Format (`euer import --schema`) kennt kein `private_paid`-Feld. Bei Bulk-Imports kann eine Ausgabe nicht manuell als privat bezahlt markiert werden — es greift nur die automatische Erkennung über Kontoname/Kategorie.

**Lösung:** `private_paid` als optionalen Import-Key ergänzen.

**Umsetzung:**
- Alias-Key in `normalize_import_row()`: `private_paid` / `Privat bezahlt`
- Akzeptierte Werte: `true`, `1`, `yes`, `X` (case-insensitive)
- Wenn gesetzt: `classify_expense_private_paid(manual_override=True)`
- Schema-Ausgabe (`--schema`) um Feld ergänzen

**Dateien:**
| Datei | Änderung |
|-------|----------|
| `euercli/commands/import_data.py` | `private_paid`-Key in Schema + Normalisierung |
| `tests/test_cli.py` | Test: Import mit `private_paid: true` erzeugt Sacheinlage |

---

### CR-4: Fehlende CLI-Tests ergänzen (MITTEL)

**Problem:** Der Spec-Testplan definiert 8 CLI-Tests, davon wurden nur 4 implementiert. Besonders fehlen Standalone-Tests für die Basisfunktionen.

**Fehlende Tests:**

| Test | Beschreibung |
|------|-------------|
| `test_add_private_deposit` | Deposit anlegen, Output und DB-Wert prüfen |
| `test_add_private_withdrawal` | Withdrawal anlegen, Output prüfen |
| `test_add_private_withdrawal_with_related_expense` | Withdrawal mit `--related-expense-id`, Referenz prüfen |
| `test_list_private_transfers` | Kombinierte Ansicht, Sacheinlagen enthalten |
| `test_expense_private_paid_flag_persisted` | Expense mit `--private-paid` anlegen, per Query `is_private_paid = 1` verifizieren |
| `test_import_with_private_classification` | Import einer JSONL mit privatem Konto, Sacheinlage prüfen |

**Dateien:**
| Datei | Änderung |
|-------|----------|
| `tests/test_cli.py` | 6 neue Testfälle |

---

### CR-5: `_get_optional()` Helper deduplizieren (NIEDRIG)

**Problem:** Identische Helper-Funktion `_get_optional()` existiert in `euercli/services/expenses.py` und `euercli/services/private_transfers.py`.

**Lösung:** In gemeinsames Modul extrahieren (z.B. `euercli/services/utils.py` oder `euercli/utils.py`).

**Dateien:**
| Datei | Änderung |
|-------|----------|
| `euercli/utils.py` (oder `euercli/services/utils.py`) | `_get_optional()` dorthin verschieben |
| `euercli/services/expenses.py` | Import statt lokaler Definition |
| `euercli/services/private_transfers.py` | Import statt lokaler Definition |

---

### CR-6: `private_classification` in List-Output anzeigen (NIEDRIG)

**Problem:** In `euer list expenses` und `euer list private-deposits` ist nicht ersichtlich, *warum* eine Ausgabe als Sacheinlage klassifiziert wurde. Debugging erfordert aktuell rohe SQL-Queries.

**Lösung:** Optional `private_classification` in der Ausgabe anzeigen — z.B. über ein `--verbose`-Flag oder als zusätzliche Spalte bei `list private-deposits`.

---

### CR-7: `private-summary` um Saldo ergänzen (NIEDRIG)

**Problem:** `euer private-summary` zeigt Einlagen und Entnahmen getrennt, aber keinen Nettosaldo.

**Lösung:** Am Ende eine Zeile ergänzen:

```text
  ======================================================
  SALDO (Einlagen - Entnahmen)                    -1.262,01 EUR
```

---

### Abgrenzung: Import-Architektur → Spec 009

Das Problem, dass `euercli/commands/import_data.py` den Service Layer umgeht und rohe SQL-INSERTs ausführt, ist kein 008-spezifisches Issue, sondern ein grundsätzliches Architekturthema. Es wird in **Spec 009 (Service-Layer-Architektur)** behandelt.
