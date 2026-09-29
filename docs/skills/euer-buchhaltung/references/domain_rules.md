# Fachliche Buchungsregeln und Sonderfälle

Prüfe immer Beleg, Zahlungsfluss, Steuerstatus und Geltungsjahr. Diese Referenz
verbindet die aktuelle CLI-Behandlung mit fachlichen Prüffragen. Wenn ein
Sachverhalt oder seine steuerliche Einordnung unklar ist, frage nach und buche
keinen erfundenen Steuersatz, RC-Typ oder Beleg. Die CLI entscheidet die
steuerliche Einordnung nicht selbst.

## Geltung und Quellen der wichtigsten Wenn-Dann-Regeln

Die CLI-Regeln dieser Referenz beschreiben Skill 1.1.4. Bei älteren Buchungen
gelten Beleg, Zahlungsjahr und damaliger Steuerstatus; eine spätere Änderung der
globalen Config ersetzt deren ursprüngliche Behandlung nicht.

| Wenn | Dann und Begründung | Quelle | Geltungszeitraum |
|---|---|---|---|
| Eine betriebliche Vorauszahlung fließt ab | Zahlung und späteren Verbrauch abgleichen; dieselbe Ausgabe nicht zweimal buchen. Jahreswechsel und Ausnahmen vom Abflussprinzip prüfen | [§ 11 Abs. 2 EStG](https://www.gesetze-im-internet.de/estg/__11.html); Details unten bei Prepaid | Zahlungsjahr, vorbehaltlich gesetzlicher Ausnahmen |
| Eine geklärte RC-Vorauszahlung für eine Leistung nach § 13b UStG erfolgt | RC-Typ anhand von Leistung, leistendem Unternehmen und Beleg bestimmen; Steuerperiode und Vorsteuerberechtigung gesondert prüfen | [§ 13b Abs. 4 UStG](https://www.gesetze-im-internet.de/ustg_1980/__13b.html), [§ 15 Abs. 1 Nr. 4 UStG](https://www.gesetze-im-internet.de/ustg_1980/__15.html); Details unten bei Prepaid | Je nach Voraussetzungen der Anzahlung |
| Eine geschäftliche Bewirtung wird bezahlt | Zahlbetrag als eine Ausgabe erfassen, belegte Vorsteuer und Trinkgeld getrennt prüfen; die EÜR-Aufteilung im Report kontrollieren | § 4 Abs. 5 Satz 1 Nr. 2 EStG und § 15 Abs. 1/1a UStG; Details unten bei Bewirtung | Zahlungsjahr und zugehöriger Beleg |
| Eine Cashback-Gutschrift geht ein | Herkunft, Bedingungen und Bezug zu früheren Käufen prüfen, bevor Einnahme oder Entgeltminderung gebucht wird | § 4 Abs. 3 EStG; Details unten bei Cashback | Jahr des tatsächlichen Zuflusses beziehungsweise der Korrektur |

## Wichtige Regeln

### Beträge

Der Betrag (`--amount`) entspricht dem tatsächlichen **EUR-Zahlfluss** auf dem
Geschäfts- oder Privatkonto beziehungsweise in bar. Eine privat bezahlte
Betriebsausgabe wird zusätzlich als solche gekennzeichnet.

- **Ausgaben**: Immer NEGATIV (z.B. `--amount -119.00`).
    - Standard-Fall: Das ist der Brutto-Preis inkl. USt.
    - Reverse-Charge: Das ist der Netto-Preis (da keine USt überwiesen wurde).
- **Einnahmen**: Immer POSITIV (z.B. `--amount 119.00`).
    - Standard-Fall: Brutto-Rechnungsbetrag, den der Kunde überwiesen hat.
- **Privateinlagen/Privatentnahmen**: Immer POSITIV (`add private-deposit`, `add private-withdrawal`), Richtung ergibt sich aus dem Typ.

### Plausibilitätsprüfungen

Die CLI lehnt künftige Zahlungsdaten und bezahlte Buchungen mit künftigem
Rechnungsdatum ab. Bei Daten, die mehr als zwei Jahre zurückliegen, warnt sie.
Liegt ein Betrag über dem konfigurierten `[safety].amount_threshold`
(Standard: 5.000 EUR), fordert sie `--force`. Ein gleicher Betrag bei ähnlicher
Gegenpartei innerhalb von zwei Tagen vor oder nach einer bestehenden Buchung
gilt als mögliches Duplikat; `--allow-duplicate` kann diese Prüfung übergehen.
Bei vorhandener Rechnungsnummer meldet die CLI auch über größere Datumsabstände
ein mögliches Duplikat, wenn Nummer, Gegenpartei und Betrag übereinstimmen.
Teilzahlungen mit abweichendem Betrag werden dadurch nicht allein wegen der
Rechnungsnummer abgewiesen.
Hat nur eine der Buchungen eine Nummer, prüft `euer` bei gleichem Aussteller
und Betrag auch Rechnungsdatum und Belegname über größere Abstände zwischen
den Zahlungsdaten hinweg.
Beim CSV-/JSONL-Import führt ein solcher Verdachtsfall zum Abbruch des gesamten
Laufs mit Zeilennummer; exakte Dubletten werden weiterhin übersprungen.
Bei gemeinsam übergebenem Steuersatz und Steuerbetrag prüft sie deren
rechnerische Übereinstimmung mit 0,02 EUR Toleranz.

Prüfe vor jeder Ausnahme Beleg, Zahlung, vorhandene Buchung und Mandantenregel.
`--force` übergeht mehrere Schutzprüfungen und ersetzt keine fachliche Klärung.
Verwende `--allow-duplicate` nur für belegte, getrennte Vorgänge und dokumentiere
den Grund. Eine Warnung allein rechtfertigt keinen erfundenen Wert.

### Steuermodus (Config)

Das Verhalten hängt von der Konfiguration ab (`~/.config/euer/config.toml`):

```toml
[tax]
mode = "small_business"  # oder "standard"
```

1.  **Kleinunternehmer (`mode = "small_business"`)**:
    *   Ausgaben werden brutto als Kosten erfasst.
    *   Einnahmen werden ohne ausgewiesene USt mit dem tatsächlichen Zahlungseingang erfasst.
    *   Reverse-Charge: Erzeugt eine Umsatzsteuerschuld (`vat_output`), die nicht als Vorsteuer abgezogen werden kann.

2.  **Regelbesteuerung (`mode = "standard"`)**:
    *   Ausgaben: Vorsteuer (`vat_input`) wird erfasst (automatisch bei RC oder manuell via `--vat`).
    *   Einnahmen: Umsatzsteuer (`vat_output`) wird erfasst; `vat_rate`/`vat_code`
        müssen für den UStVA-Report stimmen.
    *   Standard-Einnahmen ohne Sonderfall mit `--vat-rate 19` buchen; für 7 %
        `--vat-rate 7`, für 0 % `--vat-rate 0`, für steuerfrei `--tax-free`.
    *   Reverse-Charge: Die CLI erfasst Umsatzsteuer und Vorsteuer gleichzeitig.
        Ob der volle Vorsteuerabzug fachlich zulässig ist, muss geklärt sein.

### USt-Voranmeldung (`vat-report`)

```bash
euer vat-report --year YYYY
euer vat-report --year YYYY --quarter 1
euer vat-report --year YYYY --month 3
euer vat-report --year YYYY --quarter 1 --format csv --output exports/
```

Der Report ist kein Ersatz für Steuerberatung oder ELSTER-Übermittlung. Er ist
ein Arbeitsbericht mit Kennzahlen, Warnungen und Diagnose. Er nutzt nur
`payment_date`; Buchungen ohne Wertstellungsdatum werden gewarnt und nicht
eingerechnet. Prüfe die rechtlich maßgebliche USt-Periode vor der Übernahme nach
ELSTER gesondert, insbesondere bei Anzahlungen und RC.

### Reverse-Charge (--rc eu|third-country)

Prüfe bei Auslandsleistungen anhand der konkreten Rechnung, des leistenden
Unternehmens und des Steuerstatus, ob Reverse Charge anzuwenden ist. Bei
geklärtem Sachverhalt verwende `--rc eu` oder `--rc third-country`. Ein
Markenname allein belegt weder Sitz noch RC-Typ.

Die CLI berechnet für unterstützte RC-Buchungen automatisch 19 % USt. Prüfe,
ob dieser Satz und die RC-Behandlung zum konkreten Vorgang passen.
- **Kleinunternehmer**: Erhöht die Zahllast.
- **Regelbesteuerung**: Bucht USt und VorSt gleichzeitig (Zahllast-neutral).
Hinweis: Bei `small_business` setzt RC automatisch `vat_output`, `vat_input` bleibt `0.0`.
Die Anwendung leitet `eu`/`third-country` nicht automatisch aus Anbieter oder Land ab.
Bestehende RC-Buchungen ohne EU-/Drittland-Typ per `euer update expense <ID> --rc ...`
nachpflegen.

### Privatvorgänge

- Eine privat bezahlte Betriebsausgabe bleibt eine Ausgabe mit Beleg und
  fachlicher Kategorie. Verwende das als privat konfigurierte `--account`
  oder bei bestätigtem Sachverhalt `--private-paid`.
- Eine reine Kapitalbewegung ist eine Privateinlage oder Privatentnahme mit
  positivem Betrag; sie ist keine zweite Betriebsausgabe.
- Bei einer Ausgleichsüberweisung für eine privat bezahlte Ausgabe verknüpfe
  die Entnahme mit `--related-expense-id <ID>`. Prüfe zuvor, ob die Ausgabe
  bereits als privat bezahlt erfasst wurde, damit Kosten und Einlage nicht
  doppelt zählen.
- Bei Unklarheit kläre, ob Betriebsausgabe, Ausgleich oder reine
  Kapitalbewegung vorliegt. Kontrolliere `euer private-summary --year YYYY`.
- Für bestehende Buchungen zeigt `euer reconcile private --year YYYY --dry-run`
  Änderungen nach den aktuellen Privatkonto-Regeln. Prüfe die betroffenen
  Buchungen; erst danach `euer reconcile private --year YYYY` anwenden.
  Manuelle Markierungen bleiben erhalten. Eine einzelne bestätigte Ausgabe
  kannst du mit `euer update expense <ID> --private-paid` kennzeichnen.
  Direkte SQL-Änderungen umgehen Validierung und Audit-Log.

### Fremdwährungen

Für die EÜR gilt der tatsächliche EUR-Zahlbetrag aus dem Kontoauszug. Halte
Originalbetrag und Währung zusätzlich mit `--foreign` fest. Bei der Zuordnung
von Rechnung und Zahlung zählt der EUR-Abfluss oder Zufluss; Wechselkurs- und
Gebührenabweichungen müssen geklärt werden, statt Beträge ungefähr zu matchen.

### Prepaid-Guthaben & Vorauszahlungen (z. B. Google AI Studio, OpenAI)

Bei Anbietern mit Guthabenaufladung (Prepaid):
1. **Zahlung prüfen:** Die Guthabenaufladung anhand von Zahlungsbeleg und Kontoauszug erfassen, wenn sie als Betriebsausgabe geklärt ist. `--rc` nur bei belegter RC-Pflicht und geklärtem Typ setzen. `--invoice-date` nur mit dem tatsächlichen Belegdatum füllen; ein fehlendes Rechnungsdatum sichtbar lassen.
2. **Monatliche Verbrauchsrechnung:** Weist die spätere Monatsrechnung einen Zahlbetrag von 0,00 EUR auf (da mit Guthaben verrechnet), wird sie **nicht** als neue Ausgabe gebucht (Vermeidung von Doppelzählung). Sie wird im Belegordner abgelegt und optional in den `--notes` der Zahlungsbuchung vermerkt. (Details: siehe [Sonderfälle](#häufige-sonderfälle-und-fehlerbehebung)).

### Bewirtungsaufwendungen

Bewirtung mit Reverse Charge und positive Erstattungen sind derzeit nicht
unterstützt. Nicht durch Vorzeichenwechsel oder eine andere Kategorie umgehen.
Altbestände separat prüfen; der Bericht bleibt dafür unvollständig.

Eine geschäftliche Bewirtung wird als ein Zahlungsvorgang in
`Bewirtungsaufwendungen` erfasst. Bei 129,00 € Zahlbetrag und 19,00 € belegter
Vorsteuer ergibt sich eine Kostenbasis von 110,00 €, davon 77,00 € abziehbar und
33,00 € nicht abziehbar. Die 19,00 € Vorsteuer bleiben vollständig erhalten.
Freiwilliges Trinkgeld ist bereits Teil des Zahlbetrags und wird nur als
Plausibilitätsangabe erfasst.

```bash
euer add expense --payment-date YYYY-MM-DD --vendor "Restaurant" \
    --category "Bewirtungsaufwendungen" --amount -129.00 --vat 19.00 --tip 10.00
```

Prüfe die Rechnung und den Nachweis statt einen Steuersatz zu schätzen. Alte
Bewirtungsbuchungen werden bei `euer init` als `needs_review` markiert. Positive
alte Vorsteuer kann nur als vorläufige Aufteilung erscheinen; fehlende oder
ungeprüfte Daten machen die EÜR-Summe und den Gewinn unvollständig. Der
nicht abziehbare 30-%-Anteil ist keine Privatentnahme. Bewirtung ausschließlich
eigener Arbeitnehmer gehört nicht in diese Kategorie.
Im Standardmodus bleibt die Vorsteuerbehandlung ohne geprüften Wert offen;
bestätigte Null-Vorsteuer wird ausdrücklich mit `--vat 0` erfasst. Im
Kleinunternehmermodus gibt es keinen Vorsteuerabzug. `--tip` dokumentiert
bereits im Zahlbetrag enthaltenes Trinkgeld und addiert es nicht erneut.

### Kategorien

EÜR-Zeilen sind Formularjahr-Metadaten. Für 2025 und 2026 mitgelieferte
Zuordnungen werden mit `euer list categories --year YYYY` angezeigt; ohne
geprüfte Zuordnung wird keine Zeilennummer behauptet. Ein Teil der Zeilen hat
sich zum Formularjahr 2026 verschoben. Verlasse dich nicht auf eine feste
Jahresliste aus dem Gedächtnis.

`Nicht steuerbare Umsätze` ist fachlich das Unterfeld „Davon nicht steuerbare
Kleinunternehmerumsätze (§ 19 Abs. 2 UStG)“ in Zeile 13. Es wird nur für
Kleinunternehmer verwendet. Eine Buchung zählt genau einmal zu den Einnahmen;
`summary` zeigt den Betrag zusätzlich als „davon“-Wert unter Zeile 12.
`Gezahlte USt` ist die Zahlung ans Finanzamt; sie ist nicht die abziehbare
Vorsteuer (2025 Zeile 57, 2026 Zeile 58). Privatentnahmen und Privateinlagen
haben ebenfalls jahresabhängige Zeilen; `private-summary` zeigt die geprüfte
Jahreszuordnung.

### Datenmodell (Interpretation der Spalten)

#### Ausgaben (expenses)
| Spalte | Bedeutung | Format / Hinweis |
|--------|-----------|------------------|
| `id` | Eindeutige ID | Automatisch vergeben |
| `payment_date` | Wertstellungsdatum (EÜR) | `YYYY-MM-DD`, kann leer sein |
| `invoice_date` | Rechnungsdatum | `YYYY-MM-DD`, kann leer sein |
| `vendor` | Lieferant | Name des Anbieters |
| `category` | Kategorie | Name der Ausgabenkategorie |
| `amount_eur`| Bruttobetrag | **Immer negativ** (z.B. -10.00) |
| `rc_type` | Gespeicherter Reverse-Charge-Typ | `none`, `eu`, `third_country` oder `unclassified`; die CLI-Option heißt `--rc third-country` |
| `vat_input` | Vorsteuer | Forderung an FA (positiv), nur bei Regelbest. |
| `vat_output`| RC Umsatzsteuer | Schuld an FA (positiv), bei RC |
| `vat_rate` | USt-Satz | `19`, `7`, `0` oder leer |
| `vat_code` | UStVA-Klasse | z.B. `input_invoice`, `reverse_charge_eu` |
| `account` | Konto | Verwendetes Bankkonto/Zahlart |
| `receipt_name`| Belegdatei | Name der PDF/JPG Datei |
| `notes` | Notizen | Optionale Bemerkungen |

#### Einnahmen (income)
| Spalte | Bedeutung | Format / Hinweis |
|--------|-----------|------------------|
| `id` | Eindeutige ID | Automatisch vergeben |
| `payment_date` | Wertstellungsdatum (EÜR) | `YYYY-MM-DD`, kann leer sein |
| `invoice_date` | Rechnungsdatum | `YYYY-MM-DD`, kann leer sein |
| `source` | Kunde/Quelle | Wer hat gezahlt? |
| `category` | Kategorie | Name der Einnahmenkategorie |
| `amount_eur`| Bruttobetrag | **Immer positiv** (z.B. 1500.00) |
| `vat_output`| Umsatzsteuer | Schuld an FA (positiv), nur bei Regelbest. |
| `vat_rate` | USt-Satz | `19`, `7`, `0` |
| `vat_code` | UStVA-Klasse | `output_standard_19`, `output_reduced_7`, `output_zero_0`, `output_tax_free_no_vorsteuer` |
| `receipt_name`| Belegdatei | Name der Rechnungsdatei |
| `notes` | Notizen | Optionale Bemerkungen |

#### Privatvorgänge (private_transfers)
| Spalte | Bedeutung | Format / Hinweis |
|--------|-----------|------------------|
| `id` | Eindeutige ID | Automatisch vergeben |
| `date` | Buchungsdatum | `YYYY-MM-DD` |
| `type` | Richtung | `deposit` oder `withdrawal` |
| `amount_eur` | Betrag | **Immer positiv** |
| `description` | Beschreibung | Pflichtfeld |
| `related_expense_id` | Referenz | Optional, z.B. Ausgleich |

### Belegnamen

Empfohlenes Dateinamenformat: `YYYY-MM-DD_Anbieter.pdf` oder
`YYYYMMDD_Anbieter.pdf`. Die CLI erzwingt dieses Namensschema nicht.

Beispiele:
- `2026-01-15_Render.pdf`
- `20260115_OpenAI.pdf`

Belege werden unter einem gemeinsamen Root jahrzentriert erwartet:
```
<root>/<Jahr>/<Typ>/<Belegname>
```

Standard:
- Ausgaben: `<root>/<Jahr>/Ausgaben/<Belegname>`
- Einnahmen: `<root>/<Jahr>/Einnahmen/<Belegname>`

Das Jahr des Belegordners folgt dem `payment_date` der Buchung
(Zufluss-/Abflussprinzip). Ohne `payment_date` kann `euer` beim Buchen keinen
Jahresordner sicher ableiten.

Hinweis: Fehlt die Dateiendung, prüft `euer receipt check` automatisch
`.pdf`, `.jpg`, `.jpeg` und `.png`.
`euer receipt unbooked --year YYYY --format json` prüft die Gegenrichtung:
Welche Dateien im Zahlungsjahresordner haben keine auflösbare Referenz in einer
aktiven Buchung? Vor einer Neubuchung zuerst vorhandene Buchungen und eine
falsche Jahresablage prüfen. Ohne Zahlungsdatum ist eine Zuordnung zum
gewählten Scan-Jahr vorläufig und wird als Warnung ausgegeben.

## Häufige Sonderfälle und Fehlerbehebung

### Prepaid-Guthaben und Vorauszahlungen

#### Aufladung und spätere Verbrauchsrechnung

Eine Zahlung lädt ein Software-Guthaben auf; die Verbrauchsrechnung kommt
später mit 0,00 € Zahlbetrag.

Prüfe zuerst, ob die Aufladung eine Zahlung an den Anbieter für eine bestimmte
betriebliche Leistung ist oder nur eine Umbuchung auf ein eigenes Zahlungsmittel.
Gleiche Zahlungsbeleg, Kontoauszug und spätere Verbrauchsrechnung ab. Eine
bereits erfasste Zahlung darf durch die 0-Euro-Rechnung nicht nochmals als
Ausgabe in die EÜR gelangen.

Bei einer geklärten betrieblichen Vorauszahlung kann die Ausgabe im Zahlungsjahr
liegen. [§ 11 Abs. 2 EStG](https://www.gesetze-im-internet.de/estg/__11.html)
kennt jedoch Ausnahmen für regelmäßig wiederkehrende Ausgaben und langfristige
Nutzungsüberlassung. Prüfe sie besonders am Jahreswechsel; entscheide nicht
allein anhand des Datums der Kontoabbuchung.

**CLI-Ablauf:**

1. Erfasse nur den belegten EUR-Abfluss mit `--payment-date`, `--amount` und
   passender Kategorie. Übernimm `--invoice-date` ausschließlich aus einem
   tatsächlich vorliegenden Rechnungs- oder Zahlungsbeleg. Wenn kein solches
   Datum belegt ist, lasse das Feld offen und kläre den Eintrag in
   `euer incomplete list` später; fülle es nicht bloß zur Warnungsfreiheit.
2. Bestimme `--rc` aus der konkreten Leistung und dem leistenden Unternehmen,
   nicht aus dem Markennamen. Bei einer echten RC-Anzahlung können
   [§ 13b Abs. 4 UStG](https://www.gesetze-im-internet.de/ustg_1980/__13b.html)
   und [§ 15 Abs. 1 Nr. 4 UStG](https://www.gesetze-im-internet.de/ustg_1980/__15.html)
   relevant sein. Die CLI nutzt für `vat-report` das `payment_date`; prüfe die
   rechtlich maßgebliche USt-Periode und den Vorsteuerabzug gesondert.
3. Lege die spätere 0-Euro-Verbrauchsrechnung als Nachweis zur vorhandenen
   Zahlung ab. Füge bei Bedarf mit `euer update expense <ID> --notes ...` einen
   Verweis hinzu. Buche nur dann erneut, wenn ein weiterer tatsächlicher
   Zahlfluss oder ein gesonderter, geklärter Vorgang vorliegt.

#### Rechnung über 0,00 EUR

Eine Rechnung mit 0,00 € Zahlbetrag ist für sich keine zusätzliche
Zahlungsbuchung. Bewahre sie als Nachweis auf und ordne sie der zugehörigen
Zahlung zu. Prüfe bei Gutschriften, Erstattungen oder Verrechnungen, ob ein
weiterer Geschäftsvorfall vorliegt; unterdrücke ihn nicht allein wegen des
Nullbetrags auf einer Einzelrechnung.

#### Restguthaben zum Jahreswechsel

Gleiche Aufladungen, Verbrauch und Rückzahlungen ab. Eine geklärte
Betriebsausgabe wird nicht ein zweites Mal beim Verbrauch gebucht. Ob eine
Dezember-Aufladung vollständig dem Zahlungsjahr zuzuordnen ist, hängt vom
Sachverhalt und den Ausnahmen in § 11 Abs. 2 EStG ab. Bei unklarem
Guthabentyp, längerer Nutzungsüberlassung oder fehlenden Belegen fachlich
klären, bevor der Jahresabschluss übernommen wird.

### Bewirtung

#### Beleg mit Trinkgeld buchen

Erfasse eine geschäftliche Bewirtung als eine Ausgabe in `Bewirtungsaufwendungen`.
`--amount` enthält den gesamten negativen Zahlbetrag einschließlich Trinkgeld.
`--tip` dokumentiert den darin bereits enthaltenen Trinkgeldanteil; dieser wird
nicht nochmals addiert. `--vat` ist der belegte, tatsächlich abziehbare
Vorsteuerbetrag. Rechnung, Bewirtungsangaben und Trinkgeldnachweis gehören zur
Belegprüfung. Die CLI prüft deren steuerliche Voraussetzungen nicht automatisch.

Die verfügbaren Flags stehen unter
[`euer add expense`](cli_reference.md#euer-add-expense).
Bei unterschiedlichen Steuersätzen auf dem Beleg übernimmt der Agent die
belegten abziehbaren Steuerbeträge; er schätzt keinen einheitlichen Satz.

#### 70/30-Aufteilung und Kleinunternehmer

Buche den ganzen Zahlungsvorgang; `summary` übernimmt die Aufteilung.
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

#### Ungeprüfte Vorsteuer (`needs_review`)

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

### Cashback vom Geschäftskonto

Wenn eine Bank oder ein Kartenanbieter Cashback für Kartenzahlungen gutschreibt,
prüfe Programmbedingungen, Zahler und zugehörige Käufe. Gleiche den Betrag mit
dem Kontoauszug ab. Der Programmname allein bestimmt weder EÜR-Kategorie noch
Umsatzsteuerbehandlung.

- Wenn die Gutschrift privaten Käufen zuzuordnen ist, erfasse sie nicht als
  Betriebseinnahme.
- Wenn sie betrieblich veranlasst und ein eigenständiger Zufluss ist, erfasse
  sie nach Klärung einmalig mit `euer add income` und dem tatsächlichen
  Wertstellungsdatum. Bewahre Kontoauszug und Programmbedingungen als Nachweis
  auf.
- Wenn sie den Preis eines früheren Einkaufs mindert, prüfe die Zuordnung zu
  diesem Einkauf und eine mögliche Vorsteuerberichtigung nach
  [§ 17 UStG](https://www.gesetze-im-internet.de/ustg_1980/__17.html).
- Wenn sie Entgelt für eine Leistung ist, kläre die Umsatzsteuerbehandlung,
  bevor du Kategorie oder `--tax-free` setzt.

Die Einordnung hängt vom konkreten Verhältnis zwischen Händler, Anbieter und
Karteninhaber ab. Der
[BFH zu Boni eines Zentralregulierers](https://www.bundesfinanzhof.de/de/entscheidung/entscheidungen-online/detail/STRE202520084/)
zeigt, dass die Stellung des Zahlenden in der Leistungskette entscheidend sein
kann; daraus folgt keine pauschale Einstufung für Bank-Cashback. Wenn die
Bedingungen unklar bleiben, kläre den Sachverhalt vor der Buchung.

### CLI-Schutzprüfungen und Korrekturen

#### Versehentlich geänderte oder gelöschte Buchung

Für versehentliche Änderungen und Löschungen stehen je nach Fall Papierkorb
und Undo zur Verfügung:

1. **Papierkorb (Soft-Delete):** `euer delete` löscht Datensätze standardmäßig nicht physisch aus der Datenbank, sondern versieht sie mit einem Löschzeitstempel (`deleted_at`). Sie tauchen in normalen Listen und Auswertungen nicht mehr auf, können aber jederzeit wiederhergestellt werden:
   - `euer trash list` zeigt alle gelöschten Buchungen an.
   - `euer restore <ID> --table expenses` holt eine gelöschte Ausgabe zurück; für andere Typen `income` oder `private_transfers` angeben.
   - `euer delete expense <ID> --purge` (entsprechend `income` oder `private-transfer`) und `euer trash empty` entfernen Daten physisch. Vorher Ziel und Sicherung prüfen.
2. **Undo-Funktion:** Wurde gerade ein falscher Befehl abgesetzt (z. B. fehlerhaftes `update`, versehentliches `add` oder `delete`), macht `euer undo` die letzte Mutation im Audit-Log rückgängig (mit Vorschau und Bestätigung bzw. per `euer undo --force`).

#### Exportdateien existieren bereits

Bei `euer export --year 2026` kann diese Fehlermeldung erscheinen:

`Fehler: Exportdateien existieren bereits im Zielordner: [...] Nutze --force zum Überschreiben.`

`euer` schützt vorhandene Dateien vor versehentlichem Überschreiben.

- Wenn du die Exporte bewusst neu generieren möchtest, hänge `--force` an den Befehl an: `euer export --year 2026 --force`.
- Alternativ kannst du mit `--output <verzeichnis>` einen separaten Zielordner angeben.
- Exportdateien werden zunächst temporär im Zielordner geschrieben. Bei einem Fehler während des Austauschs setzt `euer` bereits ersetzte Dateien nach Möglichkeit zurück; der gesamte Dateisatz ist nicht atomar.

#### Verdächtiges Duplikat (`suspicious_duplicate`)

Beim Hinzufügen einer Ausgabe kann `euer` mit `suspicious_duplicate` abbrechen:

`Verdächtiges Duplikat erkannt: [...] Nutze --allow-duplicate zum Erzwingen.`

Die CLI prüft Buchungen auf Ähnlichkeit: Liegt innerhalb eines Fensters von
$\pm 2$ Tagen bereits eine Buchung mit **exakt demselben Betrag** und einem
**ähnlichen Empfänger-/Kundennamen** vor, schlägt die Duplikaterkennung an.

- Vergleiche zuerst Belege, Zahlungsdaten und vorhandene Buchungen. Nur bei zwei
  belegten, getrennten Transaktionen `--allow-duplicate` setzen und den Grund
  festhalten. `--force` übergeht zusätzlich andere Schutzprüfungen und ist dafür
  keine Standardlösung.

#### Neue Datenbank mit `euer init --create` anlegen

Beim Aufruf von `euer init` in einem neuen Verzeichnis erscheint der Hinweis,
eine vorhandene DB zu verbinden oder mit `euer init --create` neu anzulegen.

Dieses Flag schützt vor einer neuen, leeren Datenbank im falschen Verzeichnis.

- Um bewusst eine neue `euer.db` im aktuellen Ordner anzulegen, führe `euer init --create` aus.
- Wenn die DB bereits existiert, starte `euer init` in ihrem Projektordner. Es
  trägt `./euer.db` in `.euer/config.toml` ein. Für eine DB an anderem Ort nutze
  `euer --db /pfad/zur/euer.db init --save-db-path`.
- Ist eine bisher konfigurierte DB verschoben worden, stoppt euer mit ihrem
  erwarteten Pfad. Verbinde die vorhandene Datei neu, bevor du weiter buchst.
