# Häufig gestellte Fragen (FAQ)

Praktische Antworten und Workflows für Sonderfälle in `euer`.

## Installation und Updates

**Warum zeigt `euer --version` nach `brew upgrade euer` noch eine alte Version?**
Prüfe mit `brew info euer`, welche Version der Tap anbietet, und mit
`command -v euer` sowie `type -a euer`, welche Installation dein Terminal
findet. Der Tap folgt PyPI zeitversetzt (geplant spätestens innerhalb von
sechs Stunden). Ein früherer pipx-Entry-Point kann Homebrew im PATH verdecken.
Der [Upgrade-Leitfaden](USER_GUIDE.md#von-pipx-zu-homebrew-wechseln) beschreibt
den Wechsel. `euer doctor` ist erst in [Spec 019](../specs/019-doctor.md)
geplant.

**Darf ich nach einem Update meine `AGENTS.md` durch die neue Vorlage ersetzen?**
Nein. Sie enthält deine persönlichen Steuer-, Konto- und Lieferantenregeln.
Vergleiche neue Skill- und Template-Dateien mit den lokalen Kopien und übernimm
nötige Änderungen gezielt. EÜR-Zeilennummern für ein Formularjahr liefert
`euer list categories --year YYYY`; sie gehören nicht als dauerhafte Regel
ins Lieferanten-Mapping.

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

---

## 4. Wie buche ich einen Bewirtungsbeleg mit Trinkgeld?

Erfasse eine geschäftliche Bewirtung als eine Ausgabe in `Bewirtungsaufwendungen`.
`--amount` enthält den gesamten negativen Zahlbetrag einschließlich Trinkgeld.
`--tip` dokumentiert den darin bereits enthaltenen Trinkgeldanteil; dieser wird
nicht nochmals addiert. `--vat` ist der belegte, tatsächlich abziehbare
Vorsteuerbetrag. Rechnung, Bewirtungsangaben und Trinkgeldnachweis gehören zur
Belegprüfung. Die CLI prüft deren steuerliche Voraussetzungen nicht automatisch.

Einen vollständigen Ablauf mit CLI-Beispiel findest du in der
[User Journey](USER_JOURNEY.md#einen-geschäftlichen-bewirtungsbeleg-übergeben).
Bei unterschiedlichen Steuersätzen auf dem Beleg übernimmt der Agent die
belegten abziehbaren Steuerbeträge; er schätzt keinen einheitlichen Satz.

## 5. Muss ich die 70/30-Aufteilung selbst buchen? Was gilt für Kleinunternehmer?

Nein. Buche den ganzen Zahlungsvorgang; `summary` übernimmt die Aufteilung.
Für angemessene und nachgewiesene geschäftliche Bewirtung gilt die Begrenzung
auf 70 % des Aufwands. Grundlage ist
[§ 4 Abs. 5 Satz 1 Nr. 2 EStG](https://www.gesetze-im-internet.de/estg/__4.html).
Die 30 % sind nicht abziehbarer betrieblicher Aufwand und keine zusätzliche
Privatentnahme.

Die abziehbare Vorsteuer wird bei erfüllten Voraussetzungen nicht auf 70 %
gekürzt; siehe [§ 15 Abs. 1 und 1a UStG](https://www.gesetze-im-internet.de/ustg_1980/__15.html).
Sie wird vor der Aufteilung aus dem Zahlbetrag herausgerechnet. Ohne
Vorsteuerabzug wird dagegen der gesamte Zahlbetrag aufgeteilt.

Beispiel: Zahlung 129,00 EUR einschließlich 10,00 EUR Trinkgeld, bei
Regelbesteuerung 19,00 EUR belegte abziehbare Vorsteuer:

| Ergebnis | Mit Vorsteuerabzug | Kleinunternehmer ohne Vorsteuerabzug |
|---|---:|---:|
| Kostenbasis | 110,00 EUR | 129,00 EUR |
| Abziehbare Bewirtung (70 %) | 77,00 EUR | 90,30 EUR |
| Nicht abziehbarer Anteil (30 %) | 33,00 EUR | 38,70 EUR |
| Separate Vorsteuer-Ausgabe in der EÜR | 19,00 EUR | 0,00 EUR |
| Gesamte Ausgabenwirkung | 96,00 EUR | 90,30 EUR |

Keine zusätzlichen Buchungen für die Teilbeträge oder die bereits in der
Zahlung enthaltene Vorsteuer anlegen. Das Beispiel setzt einen geprüften,
unterstützten Bewirtungsfall voraus; reine Arbeitnehmerbewirtung gehört nicht
in diesen Workflow.

## 6. Was bedeutet `needs_review`? Darf ich fehlende Vorsteuer mit null angeben?

`needs_review` bedeutet, dass die Vorsteuerbehandlung noch am Beleg geprüft
werden muss. Bei Regelbesteuerung lässt du `--vat` weg, wenn diese Angabe fehlt.
`--vat 0` bestätigt dagegen einen geprüften fehlenden Vorsteuerabzug. Null ist
kein Ersatz für eine unbekannte Angabe.

Nach der Prüfung korrigiert der Agent die bestehende Buchung, zum Beispiel mit
`euer update expense <ID> --vat 19.00` oder bei geprüftem fehlendem Abzug mit
`euer update expense <ID> --vat 0`. Die CLI speichert den passenden Status.

Solange Bewirtungen ungeprüft sind, bleibt die EÜR-Auswertung unvollständig.
Bereits vorhandene Vorsteuerwerte können in Berichten vorläufig berücksichtigt
sein; Hinweise und UStVA-Diagnosen müssen vor der Übernahme nach ELSTER geklärt
werden. Ein technisch gesetzter Status ersetzt keine vollständigen Belege.