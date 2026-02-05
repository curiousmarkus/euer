# Agent.md – Persönliche Buchhaltungskonfiguration

> Diese Datei enthält deine persönlichen Daten für den EÜR-Buchhalter-Agent.
> Erstelle sie mit dem Onboarding-Interview (`onboarding-prompt.md`) oder fülle sie manuell aus.
> Stelle sie deinem KI-Buchhalter als Kontext zur Verfügung.

---

## 1. Persönliche Daten

| Feld | Wert |
|------|------|
| **Name** | `{{NAME}}` |
| **Geschäftsform** | `{{GESCHAEFTSFORM}}` |

---

## 2. Steuerlicher Status

### Umsatzsteuer-Regelung

- [ ] **Kleinunternehmerregelung (§19 UStG)**
  - Kein Vorsteuerabzug möglich
  - Alle Ausgaben werden mit Bruttobetrag gebucht
  - Voraussetzung: Umsatz im Vorjahr max. 25.000€ UND voraussichtlich max. 100.000€ im laufenden Jahr
  - Reverse-Charge-Pflicht bei Leistungen von im Ausland ansässigen Unternehmern (§13b UStG)

- [ ] **Regelbesteuerung**
  - Vorsteuerabzug möglich
  - USt-Voranmeldung erforderlich
  - Bei Reverse Charge: USt und VorSt gleichen sich aus

### Reverse-Charge-Anbieter (§13b UStG)

Diese Anbieter sind NICHT in Deutschland ansässig und erfordern das `--rc` Flag:
- `{{RC_ANBIETER_1}}`
- `{{RC_ANBIETER_2}}`

**Typische Beispiele:** Adobe, AWS, Google Cloud, GitHub, Notion, Figma, Zoom, Slack, OpenAI, Anthropic, Vercel, Render, DigitalOcean, Stripe (Gebühren), Microsoft 365

---

## 3. Verzeichnisse & Dateipfade

### Beleg-Ordner

| Typ | Pfad |
|-----|------|
| **Ausgaben-Belege** | `{{PFAD_AUSGABEN}}` |
| **Einnahmen-Belege** | `{{PFAD_EINNAHMEN}}` |
| **Kontoauszüge** | `{{PFAD_KONTOAUSZUEGE}}` |

### Dateinamen-Format für Belege

Format: `{{DATEIFORMAT}}`

- **Datum**: Rechnungsdatum (nicht Download-Datum oder Wertstellungsdatum!)
- **Anbieter**: Kurzname des Lieferanten/Dienstleisters

### Ordner-Hierarchie

`{{ORDNERSTRUKTUR}}`

**Mögliche Strukturen:**

**Option A: Typ/Jahr**
```
{{PFAD_AUSGABEN}}/
├── 2025/
│   ├── 2025-01-15_Adobe.pdf
│   └── 2025-01-20_BueroMaterial.pdf
└── 2026/
    └── ...
```

**Option B: Jahr/Typ**
```
2025/
├── Ausgaben/
│   ├── 2025-01-15_Adobe.pdf
│   └── 2025-01-20_BueroMaterial.pdf
└── Einnahmen/
    └── ...
```

**Option C: Jahr/Monat** (Einnahmen/Ausgaben gemischt)
```
2025/
├── 01/
│   ├── 2025-01-15_Adobe.pdf (Ausgabe)
│   └── 2025-01-18_Kunde_A.pdf (Einnahme)
└── 02/
    └── ...
```

**Option D: Flach** (keine Unterordner)
```
{{PFAD_AUSGABEN}}/
├── 2025-01-15_Adobe.pdf
├── 2025-01-20_BueroMaterial.pdf
├── 2025-02-01_Server.pdf
└── ...
```

### PDF-Tool

Tool zum Extrahieren von Text aus PDFs: `{{PDF_TOOL}}`

> Empfohlen: `markitdown` – Nutzung: `markitdown "pfad/zur/datei.pdf"`

---

## 4. Bankkonten

| Konto-Name | Bank | IBAN (letzte 4) | Verwendung |
|------------|------|-----------------|------------|
| `{{KONTO_1_NAME}}` | `{{KONTO_1_BANK}}` | ...`{{KONTO_1_IBAN4}}` | Geschäftskonto |
| `{{KONTO_2_NAME}}` | `{{KONTO_2_BANK}}` | ...`{{KONTO_2_IBAN4}}` | `{{KONTO_2_VERWENDUNG}}` |

---

## 5. Wiederkehrende Buchungen & Kategorie-Mapping

Diese Zuordnungen helfen dem Agent, automatisch die richtige Kategorie zu wählen.

| Lieferant | Kategorie | RC? | Anmerkungen |
|-----------|-----------|-----|-------------|
| `{{LIEFERANT_1}}` | `{{KAT_NAME_1}}` | `{{RC_1}}` | `{{ANMERKUNG_1}}` |
| `{{LIEFERANT_2}}` | `{{KAT_NAME_2}}` | `{{RC_2}}` | `{{ANMERKUNG_2}}` |

**Verfügbare Kategorien:**

Ausgaben:
- Waren, Rohstoffe und Hilfsstoffe (27)
- Bezogene Fremdleistungen (29)
- Aufwendungen für GWG (36)
- Telekommunikation (43)
- Übernachtungs-/Reisenebenkosten (44)
- Fortbildungskosten (45)
- Rechts-/Steuerberatung, Buchführung (46)
- Beiträge, Gebühren, Versicherungen (49)
- Laufende EDV-Kosten (50)
- Arbeitsmittel (51)
- Werbekosten (54)
- Gezahlte USt (57)
- Übrige Betriebsausgaben (60)
- Bewirtungsaufwendungen (63)
- Verpflegungsmehraufwendungen (64)
- Fahrtkosten/Nutzungseinlage (71)

Einnahmen:
- Umsatzsteuerpflichtige Betriebseinnahmen (14)
- Sonstige betriebsfremde Einnahme

---

## 6. Besonderheiten

> Hier Sonderfälle dokumentieren (z.B. anteilige Nutzung, Home-Office-Pauschale)

- `{{BESONDERHEIT_1}}`
- `{{BESONDERHEIT_2}}`

---

## Wichtige Regeln

### Buchungsdatum
In der EÜR gilt das **Zufluss-/Abflussprinzip**: Das Buchungsdatum ist das **Wertstellungsdatum** aus dem Kontoauszug (wann das Geld tatsächlich floss), NICHT das Rechnungsdatum.

### Matching
- **Betrag muss exakt übereinstimmen** (EUR-Betrag aus Kontoauszug)
- Bei Fremdwährung: EUR-Abbuchungsbetrag ist maßgeblich, Originalbetrag in `--foreign` dokumentieren
- Bei Unklarheit: IMMER beim User nachfragen!

### Beleg-Benennung
Für den Dateinamen des Belegs wird das **Rechnungsdatum** verwendet (nicht Wertstellung).

### CLI-Konfiguration
Führe `euer setup` aus, um Beleg-Pfade und Steuermodus auch im CLI zu konfigurieren.
Prüfe mit `euer config show` die aktuelle Konfiguration.

---

## Changelog

| Datum | Änderung |
|-------|----------|
| `{{DATUM_ERSTELLT}}` | Initiale Erstellung |
