# Spezifikation: Erweiterte Steuerlogik (Kleinunternehmer vs. Regelbesteuerung)

## 1. Ausgangslage

Aktuell ist das System implizit auf **Kleinunternehmer (§19 UStG)** ausgelegt:
- Einnahmen werden ohne USt erfasst.
- Ausgaben werden brutto als Kosten erfasst.
- **Reverse Charge (RC)** wird als Sonderfall behandelt: Es entsteht eine Steuerschuld (`vat_amount`), die an das Finanzamt abgeführt werden muss.

## 2. Problemstellung

Der Nutzer möchte konfigurieren können, ob die **Kleinunternehmerregelung** oder **Regelbesteuerung** gilt. Dies ändert die Interpretation der Umsatzsteuer fundament:

1.  **Kleinunternehmer (Status Quo):**
    *   Normale Ausgabe: Brutto = Kosten. Keine Vorsteuer.
    *   RC Ausgabe: Netto = Kosten. USt (19%) = Verbindlichkeit (muss gezahlt werden).
    *   Einnahmen: Keine USt.

2.  **Regelbesteuerung (Neu):**
    *   Normale Ausgabe: Netto = Kosten. USt = **Forderung** (Vorsteuer, Geld zurück).
    *   RC Ausgabe: Netto = Kosten. USt = Verbindlichkeit UND Forderung (Nullsummenspiel, aber meldepflichtig).
    *   Einnahmen: Netto = Erlös. USt = **Verbindlichkeit** (muss abgeführt werden).

Aktuell speichert `vat_amount` nur die RC-Schuld. Wir benötigen eine präzisere Unterscheidung zwischen **Verbindlichkeit** (Umsatzsteuer) und **Forderung** (Vorsteuer).

## 3. Lösungsvorschlag

### 3.1 Konfiguration (`config.toml`)

Wir führen eine Sektion `[tax]` ein.

```toml
[tax]
# "small_business" (Kleinunternehmer) oder "standard" (Regelbesteuerung)
mode = "small_business" 
```

### 3.2 Datenbank-Schema

Wir ersetzen (oder ergänzen) die Spalte `vat_amount` durch zwei explizite Spalten in `expenses` und `income` (bzw. nur `expenses` für Vorsteuer), um die Bilanz gegenüber dem Finanzamt sauber abzubilden.

**Vorschlag für Tabelle `expenses`:**

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `vat_input` | REAL | **Vorsteuer (Forderung).** Betrag, den wir vom FA zurückbekommen. |
| `vat_output` | REAL | **Umsatzsteuer (Verbindlichkeit).** Betrag, den wir dem FA schulden (z.B. bei RC). |

**Vorschlag für Tabelle `income`:**

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `vat_output` | REAL | **Umsatzsteuer (Verbindlichkeit).** Betrag, den wir auf Einnahmen erhoben haben und abführen müssen. |

### 3.3 Logik-Matrix

Wie sich die Spalten je nach Konfiguration füllen:

#### Szenario A: Ausgabe 100€ (Netto)

| Modus | Typ | Brutto-Zahlung | `vat_input` (Forderung) | `vat_output` (Verbindlichkeit) | EÜR-Kosten | USt-Zahllast Effekt |
|-------|-----|----------------|-------------------------|--------------------------------|------------|---------------------|
| **KU** | Normal | 119 € | 0 € | 0 € | 119 € | 0 € |
| **KU** | RC | 100 € | 0 € | 19 € | 100 € | -19 € (Zahlen) |
| **RB** | Normal | 119 € | 19 € | 0 € | 100 € | +19 € (Erstattung) |
| **RB** | RC | 100 € | 19 € | 19 € | 100 € | 0 € (Neutral) |

*Abkürzungen: KU = Kleinunternehmer, RB = Regelbesteuerung, RC = Reverse Charge*

#### Szenario B: Einnahme 100€ (Netto)

| Modus | Brutto-Eingang | `vat_output` (Verbindlichkeit) | EÜR-Erlös | USt-Zahllast Effekt |
|-------|----------------|--------------------------------|-----------|---------------------|
| **KU** | 100 € | 0 € | 100 € | 0 € |
| **RB** | 119 € | 19 € | 100 € | -19 € (Zahlen) |

## 4. Umsetzungsschritte

1.  **Migration:**
    *   Bestehende `vat_amount` (aus RC) in neue Spalte `vat_output` migrieren.
    *   Neue Spalte `vat_input` mit 0 initialisieren.
2.  **CLI Anpassung:**
    *   `add expense` und `add income`: Logik basierend auf `config.toml` anpassen.
    *   Bei `add expense --vat X` in RB-Modus: Interpretiere X als Vorsteuer (`vat_input`).
    *   Bei `add expense --rc` in RB-Modus: Setze `vat_input` UND `vat_output`.
3.  **Reporting:**
    *   `summary`: Muss nun "Umsatzsteuer-Zahllast" berechnen als: `SUM(vat_output) - SUM(vat_input)`.
    *   (Positives Ergebnis = Schuld, Negatives Ergebnis = Erstattung).

## 5. Offene Fragen zur Diskussion

1.  Sollen wir `vat_amount` behalten und nur umbenennen oder migrieren? -> *Empfehlung: Neue explizite Spalten für Klarheit.*
2.  Brauchen wir für Regelbesteuerte auch Steuersätze (7% vs 19%)? -> *Vorerst vermutlich fester Satz oder manuell via `--vat`.*
3.  Wie gehen wir mit historischen Daten um, wenn der User den Modus wechselt (z.B. Wechsel von KU zu RB zum 01.01.2027)?
    *   *Lösung:* Die Config gilt für *neue* Einträge. Die DB speichert die absoluten Werte.
