# Spec 006: Rechnungs- und Wertstellungsdatum erfassen

## Problem

Aktuell wird in der Datenbank nur **ein** Datum pro Buchung gespeichert (das Feld `date` - eigentlich Wertstellungsdatum im Sinne der EÜR). Es ist aber für den User verwirrend und führt zu mehreren Problemen:

1. **Zufluss-/Abflussprinzip nicht sauber abbildbar**: Für die EÜR ist das Wertstellungsdatum maßgeblich, aber wenn nur eine Rechnung vorliegt, kann dieses Datum nicht gesetzt werden.
2. **Kein Tracking des Zahlungsstatus**: Man kann nicht erkennen, ob eine Rechnung bereits bezahlt wurde oder ob für eine Zahlung schon der Beleg ausgelesen wurde (abseits der Zuordnung des Belegnamens).
3. **Belegname-Konvention nicht umsetzbar**: Belege sollen nach Rechnungsdatum benannt werden, teilweise wurde dies aber verwechselt.

## Hintergrund

Bei der Buchhaltung gibt es zwei verschiedene Zeitpunkte:

- **Rechnungsdatum** (`invoice_date`): Datum auf der Rechnung/dem Beleg
  - Wird zur Benennung des Belegdateinamens verwendet
  - Kommt immer aus der Rechnung selbst
  
- **Wertstellungsdatum** (`payment_date`): Wann das Geld tatsächlich geflossen ist
  - Maßgeblich für EÜR (Zufluss-/Abflussprinzip)
  - Kommt immer aus dem Kontoauszug
  - (aktuell im Feld `date` gespeichert)

Diese beiden Daten können mehrere Tage oder Wochen auseinander liegen.

### Typische Workflows

**Workflow A: Vom Kontoauszug ausgehend**
1. Kontoauszug zeigt Transaktion → `payment_date` ist bekannt
2. Beleg wird gesucht/zugeordnet → `invoice_date` wird ergänzt

**Workflow B: Von der Rechnung ausgehend**
1. Rechnung liegt vor → `invoice_date` ist bekannt
2. Kontoauszug kommt später → `payment_date` wird ergänzt

→ Beim Erfassen einer Buchung muss **mindestens eines** der beiden Daten vorhanden sein, das jeweils andere kann unbekannt sein und später ergänzt werden.

## Vorgeschlagene Lösung

### Neue Felder im Schema

**Für `expenses` und `income` Tabellen:**

```sql
-- Bestehende date Spalte umbenennen zu payment_date
ALTER TABLE expenses RENAME COLUMN date TO payment_date;
ALTER TABLE income RENAME COLUMN date TO payment_date;

-- Neues Feld für Rechnungsdatum
ALTER TABLE expenses ADD COLUMN invoice_date DATE;
ALTER TABLE income ADD COLUMN invoice_date DATE;

-- CHECK Constraint: Mindestens eines muss gesetzt sein
ALTER TABLE expenses ADD CONSTRAINT check_dates_expenses 
    CHECK (invoice_date IS NOT NULL OR payment_date IS NOT NULL);
ALTER TABLE income ADD CONSTRAINT check_dates_income 
    CHECK (invoice_date IS NOT NULL OR payment_date IS NOT NULL);

-- Soft-Warnung bei unüblicher Reihenfolge
ALTER TABLE expenses ADD CONSTRAINT check_date_order_expenses 
    CHECK (payment_date IS NULL OR invoice_date IS NULL OR payment_date >= invoice_date);
ALTER TABLE income ADD CONSTRAINT check_date_order_income 
    CHECK (payment_date IS NULL OR invoice_date IS NULL OR payment_date >= invoice_date);
```

**Hinweis:** Das bestehende `date` Feld wird zu `payment_date` umbenannt. Keine Abwärtskompatibilität nötig, da noch nicht produktiv im Einsatz.

### Impliziter Status durch Datumskombination

Der Status ergibt sich automatisch aus den vorhandenen Daten:

| `invoice_date` | `payment_date` | `receipt_name` | Impliziter Status |
|----------------|----------------|----------------|-------------------|
| ✅ | ✅ | ✅ | Vollständig |
| ✅ | ❌ | ✅ | Rechnung liegt vor, Zahlung ausstehend |
| ❌ | ✅ | ❌ | Zahlung erfolgt, Beleg fehlt |
| ✅ | ❌ | ❌ | Rechnung liegt vor, kein Beleg, Zahlung ausstehend |

### CLI-Erweiterungen

```bash
# Ausgabe mit beiden Daten hinzufügen
euer add expense \
    --invoice-date 2026-01-15 \
    --payment-date 2026-01-17 \
    --vendor "Adobe" \
    --amount -22.99

# Nur Rechnungsdatum (Zahlung noch ausstehend)
euer add expense \
    --invoice-date 2026-01-15 \
    --vendor "Adobe" \
    --amount -22.99

# Nur Wertstellungsdatum (Beleg fehlt noch)
euer add expense \
    --payment-date 2026-01-17 \
    --vendor "Adobe" \
    --amount -22.99

# Zahlung ergänzen
euer update expense 42 --payment-date 2026-01-17

# Rechnung ergänzen
euer update expense 42 --invoice-date 2026-01-15

# Liste zeigt payment_date (maßgeblich für EÜR) + invoice_date
euer list expenses --year 2026
# Spalten: ID | Payment | Invoice | Vendor | Amount | Receipt | Status

# Unvollständige Buchungen (fehlendes Datum oder Beleg)
euer incomplete list
# Zeigt Einträge mit fehlendem invoice_date, payment_date oder receipt_name
```

### Migration bestehender Daten

Da noch nicht produktiv im Einsatz:
- Bestehende Daten mit `date` → werden automatisch zu `payment_date` (via RENAME)
- `invoice_date` bleibt zunächst NULL und kann manuell nachgepflegt werden

## Alternativen

### Alternative A: Explizites `status` Feld
- ❌ Redundant zu den Datumsinformationen
- ❌ Muss manuell gepflegt werden
- ❌ Kann inkonsistent werden

### Alternative B: Nur ein Datumsfeld + `is_paid` Boolean
- ❌ Verliert Information (wann war Rechnung, wann Zahlung?)
- ❌ Nicht ausreichend für komplexe Fälle

### Alternative C: Aktueller Zustand beibehalten
- ❌ Kein sauberes Tracking möglich
- ❌ Verwechslungsgefahr (welches Datum ist gespeichert?)

## Vorteile der Lösung

✅ **Faktisch, nicht interpretiert**: Speichert reale Daten statt abgeleiteten Status  
✅ **Flexible Workflows**: Unterstützt beide Einstiegspunkte (Rechnung zuerst oder Kontoauszug zuerst)  
✅ **EÜR-konform**: `payment_date` ist das maßgebliche Buchungsdatum  
✅ **Beleg-Verwaltung**: `invoice_date` für korrekte Dateinamen-Konvention  
✅ **Automatisches Status-Tracking**: Status ergibt sich aus Datumskombination  

## Entscheidungen

1. **Migration**: `date` wird zu `payment_date` umbenannt (RENAME COLUMN)
2. **Validierung**: Soft-Warnung via CHECK Constraint wenn `payment_date < invoice_date`
3. **Display**: `payment_date` primär (maßgeblich für EÜR), `invoice_date` als zusätzliche Spalte
4. **Abwärtskompatibilität**: Nicht nötig (noch nicht produktiv)
