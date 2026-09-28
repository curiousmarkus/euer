# Spec 026: Innergemeinschaftlicher Warenerwerb (§ 1a UStG) und erweiterte Steuersachverhalte

## Status

Offen

## Ziel

`euer` soll den **innergemeinschaftlichen Erwerb von Gegenständen (physische Waren, Hardware, Arbeitsmittel aus der EU)** nach § 1a UStG formal, rechnerisch und melderechtlich sauber von grenzüberschreitenden Dienstleistungen (Reverse Charge nach § 13b UStG) trennen.

Zusätzlich definiert dieser Spec die Erweiterbarkeit des Datenmodells für weitere steuerliche Sonderfälle (wie Bauleistungen nach § 13b Abs. 2 Nr. 4 UStG und One-Stop-Shop/OSS-Erlöse).

Dieser Spec ist **vollständig unabhängig von Spec 024 (Regelkatalog)** und bildet die fachliche und technische Grundlage im Kern von `euer`.

---

## Motivation & Rechtliche Grundlagen

### Das Problem der bisherigen Vereinfachung
Bislang kennt `euer` für grenzüberschreitende Ausgaben aus der EU lediglich:
* `rc_type = 'eu'`
* `vat_code = 'reverse_charge_eu'`

In der Umsatzsteuer-Voranmeldung (Spec 012 `vat-report`) fließen diese Buchungen ausnahmslos in:
* **Kennziffer 46:** *„Sonstige Leistungen eines im übrigen Gemeinschaftsgebiet ansässigen Unternehmers (§ 13b Abs. 1 UStG)“*
* **Kennziffer 67:** *„Vorsteuerbeträge aus Leistungen im Sinne des § 13b UStG“*

### Gesetzliche Notwendigkeit der Differenzierung
Wenn ein deutscher Unternehmer oder Freiberufler jedoch **physische Gegenstände** (z. B. einen Monitor, Server-Hardware, Bürostühle, Messtechnik oder Werkzeuge) von einem Händler aus einem anderen EU-Land (z. B. Niederlande, Frankreich, Polen) mit seiner deutschen USt-IdNr. umsatzsteuerfrei einkauft, liegt rechtlich **keine sonstige Leistung nach § 13b UStG** vor, sondern ein **Innergemeinschaftlicher Erwerb nach § 1a UStG**.

Das deutsche Umsatzsteuerrecht schreibt dafür separate Zeilen und Kennziffern im UStVA-Vordruck zwingend vor:

| Steuerfall | Rechtsnorm | UStVA Bemessungsgrundlage | UStVA Steuer | UStVA Vorsteuer | DATEV SKR03 / SKR04 |
|---|---|:---:|:---:|:---:|:---:|
| **B2B-Dienstleistung EU** (Software, Hosting, Lizenzen, Beratung) | § 13b Abs. 1 UStG | **KZ 46** | **KZ 47** | **KZ 67** | Konto `3100` / `5900` (BU `94`) |
| **Innergemeinschaftlicher Warenerwerb** (Hardware, Gegenstände, Waren) | § 1a UStG | **KZ 89** (19 %) / **KZ 95** (7 %) | **KZ 93** (19 %) / **KZ 98** (7 %) | **KZ 61** | Konto `3425` / `5425` (BU `19`) |
| **Bauleistungen** (Handwerker/Bau-Subunternehmer) | § 13b Abs. 2 Nr. 4 UStG | **KZ 84** | **KZ 85** | **KZ 67** | Konto `3120` / `5920` (BU `84`) |

Wird der Wareneinkauf in Kennziffer 46 deklariert, führt dies bei einer Umsatzsteuer-Sonderprüfung oder beim automatisierten Abgleich des Bundeszentralamts für Steuern (VIES/MIAS-Datenabgleich) zu Beanstandungen und Rückfragen des Finanzamts.

---

## Fachliche Spezifikation

### 1. Innergemeinschaftlicher Warenerwerb (§ 1a UStG)

#### A. Voraussetzungen
1. Physische Beförderung oder Versendung eines Gegenstands aus einem EU-Mitgliedstaat nach Deutschland.
2. Der liefernde Unternehmer tritt mit ausländischer EU-USt-IdNr. auf.
3. Der Leistungsempfänger tritt mit deutscher USt-IdNr. auf (Rechnung weist 0 % USt mit Hinweis auf steuerfreie innergemeinschaftliche Lieferung / Intra-Community Supply aus).

#### B. Steuerliche Wirkung
* **Steuersatz:** In der Regel 19 % (bzw. ermäßigt 7 % bei Büchern/Druckerzeugnissen) bezogen auf den Rechnungsbetrag.
* **Modus `standard` (Regelbesteuerung):**  
  Der Erwerber schuldet die Steuer (Erwerbsteuer 19 % in KZ 93) und zieht gleichzeitig denselben Betrag als Vorsteuer nach § 15 Abs. 1 Satz 1 Nr. 3 UStG in **KZ 61** ab. Die Zahllast ist per Saldo 0 EUR.
* **Modus `small_business` (Kleinunternehmer):**  
  Sofern die Erwerbsschwelle von 12.500 EUR (§ 1a Abs. 3 Nr. 2 UStG) überschritten wird oder der Kleinunternehmer zur USt-IdNr. optiert hat, entsteht die Erwerbsteuer in KZ 93. Es besteht **kein** Vorsteuerabzug (KZ 61 bleibt 0 EUR).

---

## Technische Anforderungen

### A1: Datenmodell (`schema.py`)

Die Spalten `rc_type` und `vat_code` in der Tabelle `expenses` werden erweitert:

```sql
-- In expenses:
rc_type TEXT NOT NULL DEFAULT 'none'
    CHECK(rc_type IN (
        'none', 
        'eu', 
        'third_country', 
        'eu_goods',          -- NEU: Innergemeinschaftlicher Warenerwerb § 1a UStG
        'construction',      -- NEU: Bauleistungen § 13b Abs. 2 Nr. 4 UStG
        'unclassified'
    ))

vat_code TEXT CHECK(vat_code IS NULL OR vat_code IN (
    'input_invoice',
    'reverse_charge_eu',
    'reverse_charge_third_country',
    'intra_community_goods_19',      -- NEU: Warenerwerb 19%
    'intra_community_goods_7',       -- NEU: Warenerwerb 7%
    'reverse_charge_construction'    -- NEU: Bauleistungen 19%
))
```

### A2: Service Layer & Modelle (`euercli/services/`)

1. **`euercli/services/models.py`:**  
   `Expense` Dataclass unterstützt `rc_type = "eu_goods"`.
2. **`euercli/services/expenses.py`:**  
   * Wenn `rc_type == "eu_goods"`:
     * Bei `vat_rate == 7.0`: `vat_code = "intra_community_goods_7"`
     * Sonst (Default 19.0): `vat_code = "intra_community_goods_19"`
     * Berechnung von `vat_output` (19 % bzw. 7 % des Bruttobetrags).
     * Im Modus `standard`: `vat_input = vat_output`.
     * Im Modus `small_business`: `vat_input = 0.0`.

### A3: CLI-Schnittstelle (`euercli/commands/`)

Die Erfassung erfolgt über ein intuitives Flag bei `add expense` und `update expense`:

```bash
# Explizite Angabe als Warenerwerb:
euer add expense --vendor "Hardware Direct NL" --amount 850.00 --rc eu-goods --category "Arbeitsmittel"

# ODER als semantische Kombination (--rc eu mit --goods):
euer add expense --vendor "Hardware Direct NL" --amount 850.00 --rc eu --goods --category "Arbeitsmittel"
```

#### Validierungsregeln der CLI:
* `--goods` darf nur angegeben werden, wenn `--rc eu` gesetzt ist. Bei Inlandsausgaben oder Drittland (Import unterliegt der Einfuhrumsatzsteuer) bricht die CLI mit einem Validierungsfehler ab.
* Standard-Steuersatz bei `eu-goods` ist `19 %`, außer `--vat-rate 7` wird explizit angegeben.

### A4: USt-Voranmeldungs-Report (`euer vat-report`)

Im Report (Spec 012) werden die amtlichen UStVA-Kennziffern für das Wirtschaftsjahr 2026 ergänzt:

#### 1. Ausgangs-Umsatzsteuer / Erwerbsteuer:
* **Kennziffer 89 (Zeile 33):**  
  *Bezeichnung:* Steuerpflichtige innergemeinschaftliche Erwerbe zum Steuersatz von 19 % (Bemessungsgrundlage / Netto)  
  *Datenquelle:* Summe `amount_eur` aller Ausgaben mit `vat_code = 'intra_community_goods_19'`.
* **Kennziffer 93:**  
  *Bezeichnung:* Steuerbetrag zu Kennziffer 89 (19 %).
* **Kennziffer 95 (Zeile 34):**  
  *Bezeichnung:* Steuerpflichtige innergemeinschaftliche Erwerbe zum Steuersatz von 7 % (Bemessungsgrundlage).
* **Kennziffer 98:**  
  *Bezeichnung:* Steuerbetrag zu Kennziffer 95 (7 %).

#### 2. Vorsteuer:
* **Kennziffer 61 (Zeile 40):**  
  *Bezeichnung:* Abziehbare Vorsteuerbeträge aus dem innergemeinschaftlichen Erwerb von Gegenständen (§ 15 Abs. 1 Satz 1 Nr. 3 UStG)  
  *Datenquelle:* Summe `vat_input` aller Ausgaben mit `vat_code` in (`intra_community_goods_19`, `intra_community_goods_7`) im Modus `standard`.

---

### A5: DATEV-Export & Kanzlei-Schnittstelle (`euer-datev`)

Beim Export im DATEV EXTF-700 Format (Spec 07) wird der Buchungssatz automatisch auf die offiziellen DATEV-Standardkonten für den Warenerwerb geleitet:

| Kontenrahmen | Konto (Aufwand/Warenerwerb) | Gegenkonto | BU-Schlüssel | Bedeutung |
|---|:---:|:---:|:---:|---|
| **SKR 03** | `3425` | `1200` (Bank) | `19` | Innergemeinschaftlicher Erwerb 19 % Vorsteuer und 19 % USt |
| **SKR 03 (7 %)** | `3420` | `1200` (Bank) | `18` | Innergemeinschaftlicher Erwerb 7 % Vorsteuer und 7 % USt |
| **SKR 04** | `5425` | `1800` (Bank) | `19` | Innergemeinschaftlicher Erwerb 19 % Vorsteuer und 19 % USt |
| **SKR 04 (7 %)** | `5420` | `1800` (Bank) | `18` | Innergemeinschaftlicher Erwerb 7 % Vorsteuer und 7 % USt |

---

## DB-Migration (Migration 010)

Bestehende SQLite-Datenbanken erhalten ein Schema-Upgrade:
1. `expenses`-Tabelle mit neuem `CHECK`-Constraint neu aufbauen (`rc_type` und `vat_code`).
2. Bestehende Daten (`rc_type = 'eu'`, etc.) 1:1 beibehalten.
3. Schema-Version in `schema_migrations` auf 10 erhöhen.

---

## Ausblick: Anbindung an den Regelkatalog (Spec 024)

Sobald Spec 024 (Regelkatalog) implementiert wird, erhält der Katalog eine entsprechende Regeldefinition:
* **Regel-ID:** `EUER-R-ACQUISITION-EU-GOODS-01`
* **Voraussetzungen:** `supplier_region == "eu"` AND `transaction_nature == "goods"` AND `invoice_has_zero_vat == true`.
* **Ergebnis:** `rc_type = "eu_goods"`, `vat_code = "intra_community_goods_19"`.
