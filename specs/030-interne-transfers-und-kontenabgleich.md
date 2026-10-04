# Spec 030: Interne Transfers, Provider-Auszahlungen und Kontenabgleich (Geldtransit)

## Status

Entwurf / Geplant (v0.16.0)

## Motivation und Ziel

In der EÜR nach § 4 Abs. 3 EStG ermittelt sich der Gewinn ausschließlich aus der Differenz zwischen Betriebseinnahmen und Betriebsausgaben (§ 11 EStG Zufluss-/Abflussprinzip). Geldbewegungen zwischen betrieblichen Eigenkonten (z. B. Überweisung vom Geschäftskonto auf ein Tagesgeldkonto, Auskehrung von Stripe-/PayPal-Guthaben auf das Girokonto) sind **erfolgsneutral** und dürfen das steuerliche Ergebnis weder erhöhen noch senken.

In der bisherigen Architektur (bis Spec 029) fehlen interne Transfers als eigenständiges Datenmodell:
1. **Lückenhafter Kontoauszug-Import:** Bei Bank- oder Zahlungsdienstleister-Importen müssen Transfer-Zeilen bisher manuell gefiltert oder abgewiesen werden (`type="transfer"`).
2. **Unmöglicher Saldenabgleich (Reconciliation):** Ein lückenloser Kontenabgleich (Anfangssaldo + Bewegungen = Endsaldo) kann nicht durchgeführt werden, weil legitime interne Transaktionen im System fehlen.
3. **Provider-Auszahlungen mit Gebührenabzug:** Zahlungsdienstleister wie Stripe oder PayPal behalten Transaktionsgebühren ein und zahlen den Nettobetrag aus (z. B. Brutto-Umsatz 1.000,00 € abzüglich 29,00 € Gebühr = 971,00 € Auszahlung). Bisher existiert kein einheitlicher Vertrag, um diese Auszahlung mit den Erlösen und Gebühren abzustimmen.
4. **DATEV-Geldtransit (SKR03: 1360 / SKR04: 1460):** In der Buchhaltung müssen solche Vorgänge über Geldtransit-Gegenkonten erfasst werden. Ohne interne Transfers entstehen offene Posten oder unklare Kanzleirückfragen.

Ziel dieser Spec ist ein schlanker, robuster Standard für **interne Transfers**, **erfolgsneutrale Umbuchungen** und den **Kontensalden-Abgleich**.

---

## Fachliches Modell

### 1. Datenstruktur `internal_transfers`

Tabelle in SQLite:

```sql
CREATE TABLE IF NOT EXISTS internal_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    source_account TEXT NOT NULL,
    target_account TEXT NOT NULL,
    source_date TEXT NOT NULL,
    target_date TEXT,
    amount_eur REAL NOT NULL CHECK(amount_eur > 0),
    fee_eur REAL CHECK(fee_eur >= 0),
    fee_expense_id INTEGER REFERENCES expenses(id) ON DELETE SET NULL,
    reference TEXT,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_internal_transfers_source ON internal_transfers(source_account, source_date);
CREATE INDEX IF NOT EXISTS idx_internal_transfers_target ON internal_transfers(target_account, target_date);
CREATE INDEX IF NOT EXISTS idx_internal_transfers_deleted ON internal_transfers(deleted_at);
```

### 2. Fachliche Regeln

* **Erfolgsneutralität:** Interne Transfers fließen **weder** in den EÜR-Gewinn noch in die UStVA (`vat-report`) ein.
* **Betrag:** `amount_eur` ist immer positiv.
* **Zwei Datumsangaben:** 
  * `source_date`: Wertstellung der Abbuchung auf dem Quellkonto.
  * `target_date`: Wertstellung der Gutschrift auf dem Zielkonto (oft 1–3 Tage später wegen Banklaufzeiten; falls taggleich, identisch mit `source_date`).
* **Gebührenverknüpfung (`fee_eur` / `fee_expense_id`):** 
  * Wenn ein Provider (z. B. Stripe) 1.000 € Umsatz hat, 29 € Gebühr abzieht und 971 € überweist:
  * Einnahme: 1.000,00 € auf Konto `stripe`.
  * Ausgabe (Kosten des Geldverkehrs): -29,00 € auf Konto `stripe` (optional verknüpft via `fee_expense_id`).
  * Interner Transfer: 971,00 € von `stripe` nach `giro`.
  * Saldo auf `stripe`: 1.000 - 29 - 971 = 0,00 € (perfekt ausgeglichen).
  * Saldo auf `giro`: +971,00 € (stimmt exakt mit dem Bankkontoauszug überein).

---

## CLI-Schnittstelle

### Neuer Befehl `euer add transfer`

```bash
euer add transfer \
  --from stripe \
  --to giro \
  --amount 971.00 \
  --date 2026-03-01 \
  [--target-date 2026-03-03] \
  [--fee 29.00] \
  [--reference "Payout po_12345"] \
  [--notes "Monatsauszahlung Stripe"]
```

### Abfragebefehle

* `euer list transfers [--year JJJJ] [--account KONTO] [--format csv]`
* `euer update transfer <ID> ...`
* `euer delete transfer <ID> [--purge]`

### Kontenabgleich `euer reconcile account`

Ermöglicht den Soll-Ist-Abgleich für ein bestimmtes Zahlungskonto:

```bash
euer reconcile account giro --year 2026 --month 3
```

**Berechnung:**
$$\Delta\text{Saldo} = \sum \text{Einnahmen} - \sum \text{Ausgaben} + \sum \text{Transfers (In)} - \sum \text{Transfers (Out)} + \sum \text{Einlagen} - \sum \text{Entnahmen}$$

Ausgabe zeigt eine transparente Übersicht über alle Kontobewegungen zur Prüfung gegen den Kontoauszug der Bank.

---

## Import-Unterstützung

Im CSV- und JSONL-Import (`euer import`):
* `type = "transfer"` / `direction = "transfer"` / `Typ = "Umbuchung"`.
* Pflichtfelder bei Transfers: `amount_eur`, `date`, `account` (Quellkonto), `target_account` (Zielkonto).
* Werden automatisch als `internal_transfers` angelegt.

---

## DATEV-Export (EXTF 700)

Für jeden internen Transfer werden zwei Buchungssätze erzeugt:
1. **Abgang Quellkonto:**
   * Soll: Geldtransit (SKR03: `1360`, SKR04: `1460`)
   * Haben: Quell-Finanzkonto (z. B. `1220` Stripe)
   * Datum: `source_date`
2. **Zugang Zielkonto:**
   * Soll: Ziel-Finanzkonto (z. B. `1200` Girokonto)
   * Haben: Geldtransit (SKR03: `1360`, SKR04: `1460`)
   * Datum: `target_date` oder `source_date`

Beide Buchungen heben sich auf dem DATEV-Geldtransitkonto saldenneutral auf.
