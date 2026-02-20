# Mandanten-Dossier: {{NAME}}

Geschäftsform: {{GESCHAEFTSFORM}}  

---

## Umsatzsteuer-Regelung

{{STEUER_REGELUNG}}

**Reverse-Charge-Anbieter (§13b UStG):**  
Flag `--rc` erforderlich bei: {{RC_ANBIETER_LISTE}}

---

## Dateiablage

**Ausgaben-Belege:** {{PFAD_AUSGABEN}}  
**Einnahmen-Belege:** {{PFAD_EINNAHMEN}}  
**Kontoauszüge:** {{PFAD_KONTOAUSZUEGE}}

**Dateinamen:** {{DATEIFORMAT}} (Datum = Rechnungsdatum)  
**Ordner-Struktur:** {{ORDNERSTRUKTUR}}  
**PDF-Tool:** {{PDF_TOOL}}

---

## Bankkonten

{{BANKKONTEN_LISTE}}

---

## Private Konten (für Sacheinlagen)

Kontobezeichnungen, die als privat gelten (für `accounts.private` in der Config):

{{PRIVATE_ACCOUNTS_LISTE}}

---

## Kategorie-Zuordnungen wiederkehrender Lieferanten

{{KATEGORIE_MAPPING}}

---

## Besonderheiten

{{BESONDERHEITEN}}

---

## Arbeitshinweise

### Buchungsdatum (EÜR-Prinzip)
**Zufluss-/Abflussprinzip:** Buchungsdatum = **Wertstellungsdatum** aus Kontoauszug (wann Geld tatsächlich floss)

### Beleg-Matching
- EUR-Betrag muss **exakt** übereinstimmen (aus Kontoauszug)
- Bei Fremdwährung: EUR-Abbuchung ist maßgeblich, Original in `--foreign` dokumentieren
- Bei Unsicherheit → **User fragen!**

### Beleg-Ablage
- Dateiname: **Rechnungsdatum** aus dem Beleg verwenden (nicht Wertstellung, nicht Download-Datum)
- Ordner: Gemäß Ordner-Struktur oben ablegen
- Verknüpfung: Belegnamen in Buchung eintragen

### Privatvorgänge
- Betriebsausgabe privat bezahlt: `euer add expense ... --private-paid` (oder privates Konto nutzen)
- Reine Kapitalbewegung: `euer add private-deposit|private-withdrawal ...`
- Jahrescheck: `euer private-summary --year YYYY`

---
