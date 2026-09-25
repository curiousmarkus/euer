# Mandanten-Dossier: {{NAME}}

Geschäftsform: {{GESCHAEFTSFORM}}  

---

## Umsatzsteuer-Regelung

{{STEUER_REGELUNG}}

**Reverse-Charge-Anbieter (§13b UStG):**  
`--rc eu` oder `--rc third-country` erforderlich bei: {{RC_ANBIETER_LISTE}}

**UStVA-Regeln:**
- Bei Regelbesteuerung Einnahmen mit `--vat-rate 19|7|0` oder `--tax-free` klassifizieren.
- `--amount` ist immer der tatsächliche Brutto-Zahlfluss auf dem Konto.
- UStVA-Arbeitsbericht: `euer vat-report --year YYYY`.

---

## Dateiablage

**Beleg-Root:** {{BELEG_ROOT}}  
**Jahresordner-Format:** {{JAHRESORDNER_FORMAT}}  
**Ausgaben-Unterordner:** {{AUSGABEN_UNTERORDNER}}  
**Einnahmen-Unterordner:** {{EINNAHMEN_UNTERORDNER}}  
**Kontoauszüge:** {{PFAD_KONTOAUSZUEGE}}

**Dateinamen:** {{DATEIFORMAT}} (Datum = Rechnungsdatum)  
**Ordner-Struktur:** Jahr/Typ (`<root>/<Jahr>/<Typ>/<Belegname>`)  
**PDF-Tool:** {{PDF_TOOL}}

---

## Bankkonten & Konto-Kennungen

Alle Konten verwenden das Kennungsformat `<g|p>-<name>` (`g-` = geschäftlich, `p-` = privat).

### Geschäftskonto(en)

{{GESCHAEFTSKONTEN_TABELLE}}

### Private Konten (→ `accounts.private`)

Diese Kennungen sind in der Config als `accounts.private` hinterlegt.
Bei Buchungen mit einer dieser Kennungen wird die Ausgabe automatisch als Sacheinlage erkannt.

{{PRIVATE_KONTEN_TABELLE}}

---

## Kategorie-Zuordnungen wiederkehrender Lieferanten

Nur mandantenspezifische Regeln eintragen, etwa Lieferant, Sitz/Land,
fachliche Kategorie, Reverse-Charge-Typ und Besonderheit. Keine festen
EÜR-Zeilennummern speichern: für das Berichtsjahr
`euer list categories --year YYYY` verwenden.

| Lieferant | Sitz/Land | Fachliche Kategorie | RC (`eu`/`third-country`/nein) | Besonderheit |
|---|---|---|---|---|
| {{LIEFERANT}} | {{SITZ}} | {{KATEGORIE}} | {{RC_TYP}} | {{BEMERKUNG}} |

{{KATEGORIE_MAPPING}}

## Toolchain (optional)

{{INSTALLATIONSQUELLE_UND_UPDATEWEG}}

Beispiel bei Homebrew: „Installiert via Homebrew; Updates mit `brew upgrade euer`.“
Einen festen Binärpfad nur angeben, wenn der PATH im Projekt nicht zuverlässig ist.

---

## Besonderheiten

{{BESONDERHEITEN}}

---

## Abweichungen und besondere Arbeitsregeln dieses Mandanten

{{MANDANTENSPEZIFISCHE_ARBEITSREGELN}}

Allgemeine CLI-Befehle, Datums- und Buchungsregeln stehen im
`euer-buchhaltung`-Skill und werden hier nicht dupliziert.

---
