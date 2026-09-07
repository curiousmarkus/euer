# Häufig gestellte Fragen (FAQ)

Praktische Antworten und Workflows für Sonderfälle in `euer`.

---

## 1. Prepaid-Guthaben & Vorauszahlungen (z. B. Google AI Studio, OpenAI)

### Frage
Anbieter wie Google AI Studio oder OpenAI stellen auf Vorauszahlung (Prepaid-Guthaben / Credits) um. Ich erhalte bei der Abbuchung sofort einen **Zahlungsbeleg**, die eigentliche **Verbrauchsrechnung** (mit 0,00 € Zahlbetrag) kommt jedoch erst gesammelt im Folgemonat. Wie erfasse ich das sauber in `euer`?

---

### Steuerlicher Hintergrund (EÜR & Reverse Charge)

1. **Abflussprinzip (§ 11 Abs. 2 EStG):**  
   In der Einnahmen-Überschuss-Rechnung (EÜR) gibt es keine Bilanzierung und keine aktiven Rechnungsabgrenzungsposten für Vorleistungen wie Software-Guthaben. Eine Ausgabe ist in voller Höhe in dem Kalenderjahr bzw. Monat steuerlich wirksam, in dem das Geld von deinem Bankkonto oder deiner Kreditkarte abfließt.
2. **Reverse-Charge-Entstehung (§ 13b Abs. 4 Satz 2 UStG):**  
   Bei Dienstleistern aus dem EU-Ausland (z. B. Google Cloud EMEA Ltd. in Irland) entsteht die Steuerschuldnerschaft des Leistungsempfängers bei Vorauszahlungen/Anzahlungen bereits **mit Ablauf des Voranmeldungszeitraums, in dem die Zahlung geleistet wurde**. Auch der Vorsteuerabzug (§ 15 Abs. 1 S. 1 Nr. 4 UStG bei Regelbesteuerung) greift im Monat der Zahlung.
3. **Keine Doppelbuchung der Verbrauchsrechnung:**  
   Die spätere Monatsrechnung weist den Verbrauch aus (z. B. 35,00 € abzüglich 35,00 € verrechnetes Guthaben = 0,00 € Zahlbetrag). Sie darf **nicht** nochmals als Ausgabe erfasst werden, da die Kosten sonst doppelt in der EÜR gezählt würden.

---

### Der empfohlene pragmatische Workflow in `euer`

#### Schritt 1: Aufladung mit dem Zahlungsbeleg buchen

Erfasse die Abbuchung direkt bei Zahlung:

```bash
euer add expense \
  --payment-date 2026-08-15 \
  --invoice-date 2026-08-15 \
  --vendor "Google Cloud" \
  --category "Laufende EDV-Kosten" \
  --amount -50.00 \
  --rc eu \
  --receipt "2026-08-15_google-payment-receipt.pdf" \
  --notes "Google AI Studio Prepaid-Guthaben"
```

* **Datum:** Trage als `--invoice-date` pragmatisch das Datum des Zahlungsbelegs bzw. der Kontoabbuchung ein. Dadurch vermeidest du Meldungen in `euer incomplete list`.
* **Reverse Charge:** Setze `--rc eu` (bei Google Irland) bzw. `--rc third-country` (bei US-Anbietern ohne EU-Sitz). Dadurch stimmt die USt-Voranmeldung (`euer vat-report`) für den Zahlungsmonat automatisch.
* **Datums-Warnung:** Sollte das Wertstellungsdatum vor dem Rechnungsdatum liegen (falls du als Rechnungsdatum ein späteres Datum wählst), gibt `euer` die Meldung aus:
  `Warnung: Wertstellungsdatum liegt vor Rechnungsdatum. Bitte prüfen.`  
  Diese Meldung ist **nur eine Warnung und kein Blocker**. Bei Vorauszahlungen ist dieser Zustand völlig normal und die Warnung kann ignoriert werden.

#### Schritt 2: Verbrauchsrechnung ablegen

Wenn Anfang des Folgemonats die Verbrauchsrechnung (Zahlbetrag 0,00 €) im Google Cloud Portal bereitsteht:

1. **Nicht als neue Ausgabe buchen!**
2. Lege das PDF als Leistungsnachweis für das Finanzamt in deinen Belegordner (oder füge es mit dem Zahlungsbeleg zu einer gemeinsamen PDF-Datei zusammen).
3. Ergänze optional eine Notiz bei der ursprünglichen Ausgabe:
   ```bash
   euer update expense <ID> --notes "Google AI Studio Prepaid; Verbrauchsrechnung 2026-08 (0,00 EUR) im Belegordner"
   ```

---

## 2. Dürfen 0,00-Euro-Rechnungen in `euer` gebucht werden?

### Frage
Kann oder sollte ich Null-Betrags-Rechnungen (z. B. durch Guthabenverrechnung oder Rabatte) in `euer` als Buchung anlegen?

### Antwort
**Nein.** Die EÜR bildet nach § 11 EStG reine Geldflüsse ab. Buchungen ohne Zahlungsfluss (`--amount 0.00`) verfälschen Statistiken und haben steuerlich in der EÜR keinen Platz. Bewahre solche Belege stattdessen im Belegarchiv als Leistungsnachweis auf und verweise bei Bedarf in den Notizen der zugehörigen Zahlungsbuchung darauf.

---

## 3. Was passiert mit unverbrauchtem Restguthaben zum Jahreswechsel?

### Frage
Ich lade im Dezember 100 € Guthaben auf, verbrauche davon aber bis zum 31.12. nur 20 €. Wie wird das Restguthaben steuerlich behandelt?

### Antwort
Nach dem Abflussprinzip (§ 11 Abs. 2 Satz 1 EStG) sind die gesamten 100 € im Jahr der Zahlung als Betriebsausgabe abzugsfähig. Im Folgejahr fallen bei der Nutzung des restlichen Guthabens keine weiteren Betriebsausgaben mehr an. Es ist keine rechnerische Abgrenzung in der EÜR erforderlich.
