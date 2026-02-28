# Spec 010: Kontenrahmen (Buchungskonten je Kategorie)

## Status

Offen

## Motivation

Die EÜR kennt aktuell nur ELSTER-Kategorien (z.B. „Laufende EDV-Kosten", Zeile 50).
In der Praxis nutzen Buchhalter:innen und Steuerberater:innen jedoch einen
**Kontenrahmen** (SKR 03 / SKR 04), in dem jede ELSTER-Gruppe mehrere
Buchungskonten enthält — z.B.:

| ELSTER-Kategorie (Zeile 50) | Buchungskonto |
|------------------------------|---------------|
| Laufende EDV-Kosten          | saas – Software/SaaS |
| Laufende EDV-Kosten          | hosting – Hosting/Cloud |
| Laufende EDV-Kosten          | it-support – IT-Support |

Ein solcher Kontenrahmen bietet:

1. **Feinere Auswertung** — „Wie viel gebe ich für SaaS vs. Hosting aus?"
2. **Weniger Fehler bei der Buchung** — Konto impliziert die Kategorie; die
   Kategorie muss nicht separat angegeben werden.
3. **Steuerberater-Kompatibilität** — Kontoeinträge können optionale
   SKR-Nummern enthalten, die der Steuerberater direkt zuordnen kann.
4. **KI-Agent-Unterstützung** — Buchungsagenten können einem Benutzer passende
   Konten vorschlagen und so die Buchungsqualität verbessern.

### Abgrenzung

- Die Konten sind **rein informativ / organisatorisch** und haben keine
  steuerrechtliche Wirkung innerhalb der EÜR-Berechnung.
- Es wird **kein vollständiger SKR** abgebildet, sondern ein frei
  konfigurierbarer, vom Nutzer definierter Kontenrahmen.
- Die Funktion ist **vollständig optional**; bestehende Workflows (Buchung
  nur mit Kategorie) bleiben unverändert.

### Begriffe & Abgrenzung `account` vs. `konto`

| Konzept | DB-Feld | CLI-Flag | Bedeutung |
|---------|---------|----------|-----------|
| **Zahlungskonto** (Bankkonto) | `account` (besteht) | `--account` | Über welches Bankkonto wurde bezahlt? (z.B. `g-n26`, `p-sparkasse`) |
| **Buchungskonto** (Kontenrahmen) | `ledger_account` (neu) | `--konto` | Was wurde gekauft/eingenommen? (z.B. `hosting`, `saas`) |

Die beiden Konzepte sind **vollständig unabhängig**. `--account` (Zahlungskonto)
wird weiterhin für die Private-Classification-Logik verwendet. `--konto`
(Buchungskonto) steuert die automatische Kategoriezuordnung.

---

## Designentscheidungen

1. **Kontenrahmen in Config, nicht in DB.** Der Kontenrahmen ist ein
   Konfigurationsartefakt (Zuordnungsregel), kein transaktionaler Datensatz.
   Die DB speichert nur den gewählten `key` pro Buchung als `ledger_account`.
2. **`key` statt Kontonummer als Pflichtfeld.** Der frei wählbare Schlüssel
   (z.B. `hosting`, `saas`) ist selbstdokumentierend. Die SKR-Kontonummer
   ist optional — nur relevant für Steuerberater-Export.
3. **Neues DB-Feld `ledger_account`.** Wird in `expenses` und `income`
   ergänzt (Schema-Migration). Speichert den `key` des Buchungskontos.
4. **Backend English, Output Deutsch.** Code, DB-Felder und Dataclasses
   sind Englisch. CLI-Ausgaben, TOML-Config-Schlüssel und Hilfe-Texte
   sind Deutsch (konsistent mit dem bestehenden Projekt).
5. **Config-Schlüssel `[[ledger_accounts]]`.** Englisch, konsistent mit den
   bestehenden Sections `[receipts]`, `[exports]`, `[tax]`, `[accounts]`.

---

## Anforderungen

### A1: Kontenrahmen-Konfiguration in `config.toml`

Der Kontenrahmen wird in der bestehenden Konfigurationsdatei
(`~/.config/euer/config.toml`) definiert. Jeder Eintrag ordnet ein
Buchungskonto einer ELSTER-Kategorie zu.

**TOML-Struktur:**

```toml
# Kontenrahmen — ordnet Buchungskonten den ELSTER-Kategorien zu.
# key:      Kurzbezeichner (frei wählbar, muss eindeutig sein)
# name:     Anzeigename / Beschreibung
# category: ELSTER-Kategorie (exakter Match auf categories.name)
# account_number: (optional) SKR-03/04-Kontonummer für Steuerberater-Export

[[ledger_accounts]]
key = "saas"
name = "Software / SaaS-Abos"
category = "Laufende EDV-Kosten"
account_number = "4930"

[[ledger_accounts]]
key = "hosting"
name = "Hosting & Cloud-Dienste"
category = "Laufende EDV-Kosten"
account_number = "4940"

[[ledger_accounts]]
key = "it-support"
name = "IT-Support & Wartung"
category = "Laufende EDV-Kosten"
account_number = "4950"

[[ledger_accounts]]
key = "bueromaterial"
name = "Büromaterial"
category = "Arbeitsmittel"

[[ledger_accounts]]
key = "sonstige"
name = "Sonstige betriebliche Aufwendungen"
category = "Übrige Betriebsausgaben"
account_number = "6300"

[[ledger_accounts]]
key = "beratung"
name = "Rechts- und Beratungskosten"
category = "Rechts- und Steuerberatung, Buchführung"
account_number = "4400"

[[ledger_accounts]]
key = "erloese-19"
name = "Erlöse 19% USt"
category = "Umsatzsteuerpflichtige Betriebseinnahmen"
account_number = "8400"
```

**Felder:**

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `key` | String | Ja | Kurzbezeichner (frei wählbar, z.B. `hosting`, `saas`). Lookup-Key für `--konto`. |
| `name` | String | Ja | Anzeigename / Beschreibung des Kontos |
| `category` | String | Ja | Name der ELSTER-Kategorie (exakter Match auf `categories.name`) |
| `account_number` | String | Nein | SKR-03/04-Kontonummer (für Export/Steuerberater) |

**Regeln:**

- `key` muss innerhalb der Config eindeutig sein.
  Duplikate → Fehler beim Laden.
- `key`-Lookup ist **case-insensitive** (konsistent mit Kategorie-Lookup).
- `category` muss einer existierenden Kategorie in der Datenbank
  entsprechen. Validierung erfolgt bei Nutzung (nicht beim Config-Laden,
  da keine DB-Verbindung vorliegt). Ungültige Kategorie → Fehler bei
  `resolve_ledger_account()`.
- Ein Konto erbt den `type` (expense/income) automatisch von der
  zugeordneten Kategorie.

### A2: Config-Ladefunktion `get_ledger_accounts()`

Neue Funktion in `euercli/config.py`:

```python
def get_ledger_accounts(config: dict) -> list[LedgerAccount]:
    """Lädt den Kontenrahmen aus der Config.
    
    Führt strukturelle Validierung durch (Pflichtfelder, Eindeutigkeit).
    Kategorie-Existenz wird NICHT geprüft (braucht DB-Verbindung).
    
    Returns:
        Liste aller konfigurierten Konten. Leere Liste wenn kein 
        Kontenrahmen konfiguriert ist.
        
    Raises:
        ValidationError: Bei fehlenden Pflichtfeldern oder doppeltem key.
    """
```

**Validierungsstufen:**

| Stufe | Wann | Was | Wo |
|-------|------|-----|-----|
| Strukturell (ohne DB) | Beim Config-Laden | Pflichtfelder, key-Eindeutigkeit | `get_ledger_accounts()` |
| Semantisch (mit DB) | Bei Nutzung | Kategorie-Existenz, Typ-Konsistenz | `resolve_ledger_account()` |

### A3: Service-Funktion `get_ledger_accounts_for_category()`

Neue Funktion in `euercli/services/categories.py`:

```python
def get_ledger_accounts_for_category(
    category_name: str,
    ledger_accounts: list[LedgerAccount],
) -> list[LedgerAccount]:
    """Gibt alle konfigurierten Buchungskonten für eine Kategorie zurück.
    
    Args:
        category_name: Name der ELSTER-Kategorie
        ledger_accounts: Geladener Kontenrahmen
        
    Returns:
        Liste der zugeordneten Konten. Leere Liste wenn keine Konten
        konfiguriert sind oder die Kategorie nicht gefunden wird.
    """
```

### A4: Service-Funktion `resolve_ledger_account()`

Neue Funktion in `euercli/services/categories.py`:

```python
def resolve_ledger_account(
    conn: sqlite3.Connection,
    key: str,
    ledger_accounts: list[LedgerAccount],
    expected_type: str,  # "expense" oder "income"
) -> LedgerAccount:
    """Löst einen Konto-Schlüssel auf und validiert gegen die DB.
    
    Args:
        conn: DB-Verbindung (zur Kategorie-Validierung)
        key: Konto-Schlüssel (z.B. "hosting"), case-insensitive
        ledger_accounts: Geladener Kontenrahmen
        expected_type: Erwarteter Typ ("expense" oder "income")
        
    Returns:
        Das aufgelöste LedgerAccount.
        
    Raises:
        ValidationError (code="ledger_account_not_found"):
            Wenn der key nicht im Kontenrahmen existiert.
        ValidationError (code="category_not_found"):
            Wenn die zugeordnete Kategorie nicht in der DB existiert.
        ValidationError (code="ledger_account_type_mismatch"):
            Wenn das Konto zu einer Kategorie mit falschem Typ gehört
            (z.B. Income-Konto bei Expense-Buchung).
    """
```

### A5: Implizite Kategorie bei Buchung über Konto

Wenn bei `euer add expense` oder `euer add income` ein `--konto`-Wert
angegeben wird, der einem konfigurierten Buchungskonto entspricht, soll:

1. Die zugehörige Kategorie **automatisch** gesetzt werden.
2. Eine explizit angegebene `--category` wird **nicht** überschrieben, sondern
   gegen die Konto-Kategorie validiert. Bei Widerspruch → Fehler.
3. Wenn kein Kontenrahmen konfiguriert ist oder `--konto` nicht verwendet
   wird, bleibt das Verhalten wie bisher.

**Speicherung:** Der `key` wird im neuen DB-Feld `ledger_account` gespeichert
(z.B. `"hosting"`). Der key ist stabil — bei Config-Änderung des Namens
oder der SKR-Nummer bleiben bestehende Buchungen konsistent.

**Konkretes Verhalten in `create_expense()` / `create_income()`:**

```
Eingabe: --konto hosting --category (leer)
→ Key "hosting" erkannt → Kategorie "Laufende EDV-Kosten" automatisch gesetzt.
→ DB: ledger_account = "hosting"

Eingabe: --konto hosting --category "Laufende EDV-Kosten"
→ OK, Kategorie stimmt mit Konto überein.

Eingabe: --konto hosting --category "Arbeitsmittel"
→ Fehler: Buchungskonto "hosting" gehört zur Kategorie "Laufende EDV-Kosten",
  nicht zu "Arbeitsmittel".

Eingabe: --category "Laufende EDV-Kosten" (ohne --konto)
→ Bisheriges Verhalten, Kategorie wird normal verwendet, ledger_account = NULL.
```

**Update-Verhalten:** `euer update expense --konto hosting` löst die
Kategorie ebenfalls automatisch auf und aktualisiert `category_id` +
`ledger_account` gemeinsam.

### A6: Schema-Migration

Neue Spalte `ledger_account TEXT` in `expenses` und `income`:

```sql
ALTER TABLE expenses ADD COLUMN ledger_account TEXT;
ALTER TABLE income ADD COLUMN ledger_account TEXT;
```

Die Migration wird in `ensure_ledger_account_column(conn)` in
`euercli/commands/init.py` implementiert (analog zu
`ensure_expenses_private_columns`). Bestehende Buchungen erhalten
`ledger_account = NULL` — kein automatisches Mapping alter `account`-Werte.

### A7: CLI-Befehl `euer list konten`

Neuer Befehl zum Anzeigen der konfigurierten Konten:

```
$ euer list konten

Kontenrahmen (7 Konten konfiguriert):

Laufende EDV-Kosten (Zeile 50, Ausgabe):
  saas         Software / SaaS-Abos                [4930]
  hosting      Hosting & Cloud-Dienste              [4940]
  it-support   IT-Support & Wartung                  [4950]

Arbeitsmittel (Zeile 51, Ausgabe):
  bueromaterial  Büromaterial

Rechts- und Steuerberatung, Buchführung (Zeile 46, Ausgabe):
  beratung     Rechts- und Beratungskosten           [4400]

Übrige Betriebsausgaben (Zeile 60, Ausgabe):
  sonstige     Sonstige betriebliche Aufwendungen    [6300]

Umsatzsteuerpflichtige Betriebseinnahmen (Zeile 15, Einnahme):
  erloese-19   Erlöse 19% USt                        [8400]
```

Die SKR-Nummer wird nur angezeigt, wenn `account_number` konfiguriert ist
(in eckigen Klammern).

Optional mit Filter:

```
$ euer list konten --category "Laufende EDV-Kosten"

Laufende EDV-Kosten (Zeile 50, Ausgabe):
  saas         Software / SaaS-Abos                [4930]
  hosting      Hosting & Cloud-Dienste              [4940]
  it-support   IT-Support & Wartung                  [4950]
```

Dieser Befehl braucht eine initialisierte DB (für Zeilen-Nummern und
Typ-Information aus der `categories`-Tabelle).

### A8: Kontenrahmen-Validierung

**Strukturelle Validierung** (in `get_ledger_accounts()`, ohne DB):

1. **Pflichtfelder** — Jeder Eintrag muss `key`, `name` und `category`
   enthalten. Fehlende Felder → Fehler mit Hinweis auf den betroffenen Eintrag.
2. **Eindeutigkeit** — `key` muss innerhalb des Kontenrahmens eindeutig sein
   (case-insensitive). Duplikate → Fehler.

**Semantische Validierung** (in `resolve_ledger_account()`, mit DB):

3. **Kategorie-Existenz** — Die angegebene `category` muss in der DB
   existieren. Ungültige Kategorie → `ValidationError`.
4. **Typ-Konsistenz** — Expense-Buchung kann nur Konten mit Expense-Kategorie
   verwenden und umgekehrt. Wird durch den bestehenden
   `get_category_by_name(conn, name, cat_type)`-Aufruf sichergestellt.

### A9: Kontenrahmen im Import

Der bestehende Import-Befehl (`euer import`) soll Konto-Schlüssel im
neuen Feld `ledger_account` (bzw. Alias `konto`) erkennen und die Kategorie
automatisch auflösen, analog zur manuellen Buchung (A5). Der Import-Flow
nutzt bereits den Service Layer (Spec 009), so dass die Konten-Auflösung
zentral in `create_expense()` / `create_income()` greift.

Import-CSV/JSONL-Spalte: `konto` (oder `ledger_account`).

### A10: Kontenrahmen-Hilfe bei Fehlern

Wenn eine Buchung ohne Kategorie und ohne `--konto` ausgeführt wird und
ein Kontenrahmen konfiguriert ist, soll die Fehlermeldung einen Hinweis geben:

```
Fehler: Kategorie erforderlich.
Verfügbare Kategorien:
  - Laufende EDV-Kosten (Konten: saas, hosting, it-support)
  - Arbeitsmittel (Konten: bueromaterial)
  - ...
Tipp: Verwende --konto <Schlüssel>, um die Kategorie automatisch zu setzen.
```

Wenn kein Kontenrahmen konfiguriert ist, wird der Tipp weggelassen und
die Fehlermeldung bleibt wie bisher.

### A11: Kontenrahmen im Setup

`euer setup` wird um eine interaktive Kontenrahmen-Konfiguration erweitert:

1. Frage: "Möchtest du Buchungskonten konfigurieren? (j/N)"
2. Bei Ja → Iterativ Konten anlegen:
   - Schlüssel eingeben (z.B. `hosting`)
   - Name eingeben (z.B. `Hosting & Cloud-Dienste`)
   - Kategorie aus Liste wählen (nummerierte Liste der verfügbaren Kategorien)
   - SKR-Nummer optional eingeben
   - "Weiteres Konto? (j/N)"
3. Ergebnis wird als `[[ledger_accounts]]` in `config.toml` geschrieben.

Dafür muss `dump_toml()` um Unterstützung für Arrays-of-Tables
(`[[section]]`) erweitert werden.

### A12: Kontenrahmen im Export

`euer export` erhält zwei zusätzliche Spalten:

| Spalte | Inhalt | Beispiel |
|--------|--------|----------|
| `Buchungskonto` | `key` aus dem Kontenrahmen | `hosting` |
| `Kontonummer` | `account_number` (wenn vorhanden) | `4940` |

Buchungen ohne `ledger_account` erhalten leere Zellen.

---

## Service-Layer-Signatur

Die Services erhalten **nicht** das gesamte `config`-Dict, sondern die
bereits aufgelöste Konten-Liste. So bleibt der Service Layer unabhängig
von der Config-Struktur und einfach testbar.

```python
# create_expense() / create_income() — neuer optionaler Parameter:
def create_expense(
    conn,
    *,
    # ... bestehende Parameter ...
    ledger_account_key: str | None = None,
    ledger_accounts: list[LedgerAccount] | None = None,
) -> Expense | None:

# update_expense() / update_income() — analog:
def update_expense(
    conn,
    expense_id: int,
    *,
    # ... bestehende Parameter ...
    ledger_account_key: str | None = None,
    ledger_accounts: list[LedgerAccount] | None = None,
) -> Expense:
```

Die Commands in `euercli/commands/` laden die Config, rufen
`get_ledger_accounts(config)` auf und reichen das Ergebnis an den
Service weiter.

---

## Implementierungsplan

### Phase 1: Config & Datenhaltung

1. **Dataclass `LedgerAccount`** in `euercli/services/models.py` anlegen.
2. **`get_ledger_accounts(config)`** in `euercli/config.py` implementieren
   (inkl. struktureller Validierung).
3. **`dump_toml()` erweitern** — Unterstützung für Arrays-of-Tables
   (`[[section]]`), damit `save_config()` den Kontenrahmen schreiben kann.
4. **Schema-Migration** — `ensure_ledger_account_column(conn)` in
   `euercli/commands/init.py`, `ledger_account TEXT` in `euercli/schema.py`.
5. **Unit-Tests** für Config-Parsing (leerer Kontenrahmen, gültige Einträge,
   fehlende Felder, Duplikate, case-insensitive Keys).

### Phase 2: Service Layer

6. **`get_ledger_accounts_for_category()`** in
   `euercli/services/categories.py` implementieren.
7. **`resolve_ledger_account()`** in `euercli/services/categories.py`
   implementieren.
8. **`create_expense()` / `create_income()` erweitern** — neuer optionaler
   Parameter `ledger_account_key` + `ledger_accounts` für Konten-Auflösung:
   - Kategorie automatisch setzen
   - Kategorie-Konflikt prüfen
   - `ledger_account` in DB schreiben
9. **`update_expense()` / `update_income()` erweitern** — analog,
   Kategorie wird bei `--konto`-Änderung automatisch aktualisiert.
10. **Unit-Tests** für alle Service-Funktionen.

### Phase 3: CLI

11. **`--konto`-Flag** in `cli.py` für `add expense`, `add income`,
    `update expense`, `update income` registrieren.
12. **`euer list konten`** implementieren (Command + Parser).
13. **`cmd_add_expense` / `cmd_add_income`** — Config laden, Konten-Liste
    an Service-Funktionen durchreichen.
14. **Fehlermeldungen verbessern** (A10) — Kontenliste in Kategorie-Fehlern
    einblenden (nur wenn Kontenrahmen konfiguriert).
15. **`euer setup`** — Interaktive Kontenrahmen-Konfiguration ergänzen.

### Phase 4: Import & Export

16. **Import** — `konto`/`ledger_account` als optionale Spalte erkennen
    und an `create_expense()`/`create_income()` weiterreichen.
17. **Export** — Spalten `Buchungskonto` und `Kontonummer` ergänzen.

### Phase 5: Dokumentation

18. **`docs/USER_GUIDE.md`** — Abschnitt „Kontenrahmen" ergänzen mit
    Konfigurationsbeispiel und Workflow.
19. **`docs/skills/euer-buchhaltung/SKILL.md`** — Konten-Auflösung als
    Buchungsregel dokumentieren.
20. **`docs/templates/onboarding-prompt.md`** — Neuen Abschnitt im
    Interview ergänzen: Buchungskonten vorschlagen und konfigurieren.
    Setup-Befehle-Block am Ende entsprechend erweitern.
21. **`DEVELOPMENT.md`** — Spec-Tabelle aktualisieren.

---

## Nicht-Ziele (bewusst ausgeklammert)

- **DB-Tabelle für Kontenrahmen-Definition:** Der Kontenrahmen lebt
  ausschließlich in der Config. Die DB speichert nur den gewählten `key`
  pro Buchung (Feld `ledger_account`).
- **Automatische SKR-03/04-Vorlagen:** Es wird kein Standard-Kontenrahmen
  ausgeliefert. Falls gewünscht, kann dies als späteres Feature (z.B.
  `euer setup kontenrahmen --template skr03`) ergänzt werden.
- **Kontensalden / Kontoblätter:** Keine Saldenberechnung je Konto.
  Auswertungen pro Konto können als separates Feature (z.B. `euer summary
  --by-konto`) in einer späteren Spec ergänzt werden.
- **Migration bestehender Buchungen:** Bestehende Buchungen erhalten
  `ledger_account = NULL`. Kein automatisches Mapping.

---

## Beispiel: Vollständiger Workflow

```bash
# 1. Kontenrahmen konfigurieren (in ~/.config/euer/config.toml)
#    → siehe Beispiel oben unter A1

# 2. Konten anzeigen
$ euer list konten
Kontenrahmen (7 Konten konfiguriert):

Laufende EDV-Kosten (Zeile 50, Ausgabe):
  saas         Software / SaaS-Abos                [4930]
  hosting      Hosting & Cloud-Dienste              [4940]
  it-support   IT-Support & Wartung                  [4950]
...

# 3. Buchung mit Konto (Kategorie wird automatisch aufgelöst)
$ euer add expense --payment-date 2026-02-15 --vendor "Hetzner" \
    --amount 49.90 --konto hosting
Ausgabe #42 hinzugefügt: Hetzner 49,90 EUR
  → Buchungskonto: hosting (Hosting & Cloud-Dienste)
  → Kategorie: Laufende EDV-Kosten (Zeile 50)

# 4. Buchung mit Konto + expliziter Kategorie (konsistent → OK)
$ euer add expense --payment-date 2026-02-15 --vendor "GitHub" \
    --amount 3.67 --konto saas --category "Laufende EDV-Kosten"
Ausgabe #43 hinzugefügt: GitHub 3,67 EUR

# 5. Buchung mit widersprüchlicher Kategorie → Fehler
$ euer add expense --payment-date 2026-02-15 --vendor "GitHub" \
    --amount 3.67 --konto hosting --category "Arbeitsmittel"
Fehler: Buchungskonto "hosting" gehört zur Kategorie "Laufende EDV-Kosten",
  nicht zu "Arbeitsmittel".

# 6. Buchung ohne Konto → bisheriges Verhalten
$ euer add expense --payment-date 2026-02-15 --vendor "Büro GmbH" \
    --amount 120.00 --category "Arbeitsmittel"
Ausgabe #44 hinzugefügt: Büro GmbH 120,00 EUR

# 7. Buchung mit Konto + Zahlungskonto (beides unabhängig)
$ euer add expense --payment-date 2026-02-15 --vendor "Hetzner" \
    --amount 49.90 --konto hosting --account p-sparkasse
Ausgabe #45 hinzugefügt: Hetzner 49,90 EUR
  → Buchungskonto: hosting (Hosting & Cloud-Dienste)
  → Kategorie: Laufende EDV-Kosten (Zeile 50)
  → Privateinlage erkannt (Konto: p-sparkasse)

# 8. Update mit Konto-Änderung → Kategorie wird automatisch aktualisiert
$ euer update expense 42 --konto saas
Ausgabe #42 aktualisiert.
  → Buchungskonto: saas (Software / SaaS-Abos)
  → Kategorie: Laufende EDV-Kosten (Zeile 50)

# 9. Konten einer Kategorie abfragen
$ euer list konten --category "Laufende EDV-Kosten"
Laufende EDV-Kosten (Zeile 50, Ausgabe):
  saas         Software / SaaS-Abos                [4930]
  hosting      Hosting & Cloud-Dienste              [4940]
  it-support   IT-Support & Wartung                  [4950]
```
