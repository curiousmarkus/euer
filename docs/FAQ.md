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

---

## 7. Wie buche ich Cashback von meinem Geschäftskonto (z. B. bei N26)?

### Frage
Mein Geschäftskonto (z. B. N26 Business oder Finom) vergütet monatlich Cashback auf Kartenzahlungen (z. B. 0,1 % oder 0,5 %). Am Monatsanfang erhalte ich eine gesammelte Gutschrift auf dem Konto (z. B. 1,42 €). Wie erfasse ich das steuerlich sauber in `euer`?

---

### Steuerlicher Hintergrund

1. **Betriebliche Einnahme (§ 4 Abs. 3 EStG):**  
   Cashback auf geschäftliche Kartenausgaben ist betrieblich veranlasst und gehört in die EÜR. Da die Bank (Zahlungsdienstleister) das Cashback als Treue-/Marketing-Incentive aus eigener Marge zahlt und nicht der jeweilige Händler, handelt es sich nicht um einen nachträglichen Lieferantenrabatt, sondern um einen sonstigen betrieblichen Ertrag (SKR03: 2700 / 8605; SKR04: 4830).
2. **Keine Umsatzsteuer / Keine Vorsteuerkorrektur:**  
   Du erbringst für die Bank keine Gegenleistung (§ 1 Abs. 1 UStG); die Gutschrift ist nicht umsatzsteuerbar (0 % USt). Eine Vorsteuerberichtigung nach § 17 UStG entfällt, da die Bank nicht Teil der warenwirtschaftlichen Leistungskette ist (vgl. BFH V R 42/17) und eine cent-genaue Zerlegung eines monatlichen Sammelbetrags auf Vorsteuerklassen (19 %, 7 %, Reverse Charge EU/Drittland, steuerfrei) unverhältnismäßig und unpraktikabel wäre.
3. **Beleg:**  
   Banken stellen für Cashback keine gesonderte Rechnung aus. Als Nachweis für das Finanzamt dient der monatliche PDF-Kontoauszug, auf dem der Betrag und der Buchungstext ausgewiesen sind.

---

### Empfohlener Workflow in `euer`

Buche die Gutschrift mit `euer add income`:

* **Bei Regelbesteuerung:**
  ```bash
  euer add income \
    --payment-date 2026-09-01 \
    --source "N26 Bank AG" \
    --category "Umsatzsteuerfreie, nicht umsatzsteuerbare Betriebseinnahmen" \
    --amount 1.42 \
    --tax-free \
    --receipt "2026-08_n26-kontoauszug.pdf" \
    --notes "N26 Business Cashback August 2026"
  ```
* **Als Kleinunternehmer (§ 19 UStG):**
  ```bash
  euer add income \
    --payment-date 2026-09-01 \
    --source "N26 Bank AG" \
    --category "Betriebseinnahmen als Kleinunternehmer" \
    --amount 1.42 \
    --receipt "2026-08_n26-kontoauszug.pdf" \
    --notes "N26 Business Cashback August 2026"
  ```

* **Privatkonten:** Cashback auf privaten Girokonten oder Kreditkarten (z. B. privates N26-Konto oder Trade Republic Saveback) gehört in die Privatsphäre und wird in `euer` **nicht** erfasst.

---

## 8. Was passiert beim Löschen? Kann ich gelöschte Buchungen wiederherstellen?

### Frage
Ich oder mein KI-Agent hat versehentlich eine Buchung gelöscht oder geändert. Sind die Daten unwiderruflich verloren?

### Antwort
**Nein.**
1. **Papierkorb (Soft-Delete):** `euer delete` löscht Datensätze standardmäßig nicht physisch aus der Datenbank, sondern versieht sie mit einem Löschzeitstempel (`deleted_at`). Sie tauchen in normalen Listen und Auswertungen nicht mehr auf, können aber jederzeit wiederhergestellt werden:
   - `euer trash list` zeigt alle gelöschten Buchungen an.
   - `euer restore <ID>` holt den Datensatz sofort aus dem Papierkorb zurück.
   - Nur mit `euer delete <ID> --purge` oder `euer trash empty` werden Daten physisch entfernt.
2. **Undo-Funktion:** Wurde gerade ein falscher Befehl abgesetzt (z. B. fehlerhaftes `update`, versehentliches `add` oder `delete`), macht `euer undo` die letzte Mutation im Audit-Log rückgängig (mit Vorschau und Bestätigung bzw. per `euer undo --force`).

---

## 9. Warum bricht `euer export` mit einem Fehler ab, dass Dateien bereits existieren?

### Frage
Beim Ausführen von `euer export --year 2026` erhalte ich die Fehlermeldung:  
`Fehler: Exportdateien existieren bereits im Zielordner: [...] Nutze --force zum Überschreiben.`

### Antwort
`euer` verfügt über einen Kollisionsschutz (Guardrail), um zu verhindern, dass fertig geprüfte Jahresabschlüsse oder externe Exportdateien versehentlich überschrieben werden.
- Wenn du die Exporte bewusst neu generieren möchtest, hänge `--force` an den Befehl an: `euer export --year 2026 --force`.
- Alternativ kannst du mit `--output <verzeichnis>` einen separaten Zielordner angeben.
- Exportdateien werden zunächst temporär im Zielordner geschrieben. Bei einem Fehler während des Austauschs setzt `euer` bereits ersetzte Dateien nach Möglichkeit zurück; der gesamte Dateisatz ist nicht atomar.

---

## 10. Was mache ich bei der Fehlermeldung "suspicious_duplicate" (unscharfes Duplikat)?

### Frage
Beim Hinzufügen einer Ausgabe bricht `euer` mit `suspicious_duplicate` ab:  
`Verdächtiges Duplikat erkannt: [...] Nutze --allow-duplicate zum Erzwingen.`

### Antwort
Die CLI prüft Buchungen auf Ähnlichkeit: Liegt innerhalb eines Fensters von $\pm 2$ Tagen bereits eine Buchung mit **exakt demselben Betrag** und einem **ähnlichen Empfänger-/Kundennamen** vor, schlägt die Duplikaterkennung an, um doppelte Erfassungen durch Agenten zu verhindern.
- Handelt es sich um zwei getrennte, berechtigte Transaktionen (z. B. zwei Monatsabos oder separate Einkäufe am selben Wochenende), setze das Flag `--allow-duplicate`:  
  `euer add expense ... --allow-duplicate` (oder `--force`).

---

## 11. Warum verlangt `euer init` das Flag `--create` bei einer neuen Datenbank?

### Frage
Beim Aufruf von `euer init` in einem neuen Verzeichnis erhalte ich den Hinweis,
eine vorhandene DB zu verbinden oder mit `euer init --create` neu anzulegen.

### Antwort
Dies ist eine Schutzmaßnahme gegen Fehlbedienung. Wenn du dich versehentlich im falschen Terminal-Ordner befindest und `euer init` aufrufst, würde ohne dieses Flag stillschweigend eine neue, leere Datenbank an der falschen Stelle initialisiert.
- Um bewusst eine neue `euer.db` im aktuellen Ordner anzulegen, führe `euer init --create` aus.
- Wenn die DB bereits existiert, starte `euer init` in ihrem Projektordner. Es
  trägt `./euer.db` in `.euer/config.toml` ein. Für eine DB an anderem Ort nutze
  `euer --db /pfad/zur/euer.db init --save-db-path`.
- Ist eine bisher konfigurierte DB verschoben worden, stoppt euer mit ihrem
  erwarteten Pfad. Verbinde die vorhandene Datei neu, bevor du weiter buchst.
