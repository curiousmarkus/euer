# Spec 024: Versionierter Regelkatalog für Entscheidungsnachweise

## Status

Offen

## Entscheidung

Auf [Spec 023](023-entscheidungsnachweis.md) aufbauend einen versionierten,
offline verfügbaren Regelkatalog einführen. Spec 023 kann bereits ohne
Katalogregeln umgesetzt und genutzt werden: Der Agent erfasst dann
fallbezogene `ad_hoc`-Begründungen. Dieser Spec ergänzt geprüfte
Wenn-Dann-Regeln, deren schrittweise Suche und die gezielte Analyse von
Buchungen, die eine bestimmte Regelversion verwendet haben.

Ein leerer Katalog blockiert die Erfassung nach Spec 023 nicht. Erst wenn
Katalogverweise unterstützt werden, dürfen `EUER-R-...`-IDs in Nachweisen
stehen; vorher sind solche IDs nur Beispiele.

## Abhängigkeit und Integrationsgrenze

- Spec 023 liefert `booking_decisions`, Quellen, Beobachtungen,
  `decision.reasoning`, `decision.ad_hoc_assessments`, `euer explain` und
  die Audit-Verknüpfung.
- Dieser Spec ergänzt Regeldateien, `rules find`/`rules show`,
  `booking_decision_rules`, `applied_rules` im Eingabeformat und
  `catalog_search` als optionalen Suchnachweis.
- Eine Entscheidung kann katalogisierte Regeln und fallbezogene Ad-hoc-
  Beurteilungen für verschiedene Themen kombinieren. `ad_hoc` bleibt eine
  Kennung für den Entscheidungsweg und wird nicht als veröffentlichte Regel
  versioniert.

---

## Regelmodell und Katalog

Eine **Regel** ist eine versionierte, fachlich überprüfbare Wenn-Dann-Anweisung.
Sie besteht aus Voraussetzungen, benötigten Tatsachen, einer vorgesehenen
Einordnung oder Berechnung, Abbruch-/Rückfragebedingungen, Geltungszeitraum und
Quellen. Die Regel-ID allein ist keine Regel und ersetzt ihre Definition nicht.
Ein Entscheidungsnachweis hält fest, **welche Version** auf welche belegten
Angaben angewandt wurde und welches Ergebnis daraus entstand.

### Verbindlicher Regelvertrag

Jede veröffentlichte Regeldefinition enthält mindestens:

| Feld | Bedeutung |
|---|---|
| `id`, `version` | Stabile ID und unveränderliche fachliche Version. |
| `title`, `purpose` | Verständliche Bezeichnung und eine klar abgegrenzte fachliche Entscheidung. |
| `summary`, `topics`, `signals` | Kurze Suchvorschau, fachliche Themen und typische Begriffe/Synonyme aus Beleg oder Sachverhalt. |
| `applies_to`, `related_topics` | Vorab bekannte Filtermerkmale und weitere Themen, die bei diesem Fall geprüft werden sollten. |
| `effective_from`, `effective_until` | Zeitraum des **Sachverhalts**, für den die Regel gilt; `null` bei offenem Ende. |
| `required_facts` | Beobachtungsschlüssel und zulässige Herkunftsstatus; eine `assumed`-Angabe erfüllt keine bestätigungspflichtige Voraussetzung. |
| `conditions` | Gemeinsam zu prüfende Voraussetzungen. |
| `outcome` | Erwartete Behandlung und betroffene Buchungsfelder; bei Berechnungen Formel und Rundung. |
| `stop_conditions` | Fälle, in denen Rückfrage oder Fachprüfung nötig ist statt automatischer Einordnung. |
| `sources` | Fundstellen mit URL/Norm, Abruf- oder Veröffentlichungsstand und Begründungsbezug. |

**Beispiel einer geplanten Regeldefinition** (gekürzt; erst nach fachlicher
Prüfung und Veröffentlichung im Katalog verbindlich):

```json
{
  "id": "EUER-R-RC-THIRD-COUNTRY-01",
  "version": "1.2.0",
  "title": "Drittland-Dienstleistung an inländischen Kleinunternehmer",
  "purpose": "RC-Einordnung und Vorsteuerstatus eines geklärten B2B-Leistungsbezugs",
  "summary": "Ausländische B2B-Dienstleistung aus dem Drittland: deutsche RC-Steuerschuld und Vorsteuerstatus bei Kleinunternehmern prüfen.",
  "topics": ["reverse_charge", "input_vat"],
  "signals": ["SaaS", "Cloud-Dienst", "Dienstleistung", "USA", "Drittland"],
  "applies_to": {
    "booking_types": ["expense"],
    "tax_modes": ["small_business"],
    "supplier_regions": ["third_country"]
  },
  "related_topics": ["foreign_currency", "reverse_charge_period", "expense_category"],
  "effective_from": "2025-01-01",
  "effective_until": null,
  "required_facts": [
    { "field": "service_type", "statuses": ["observed", "user_provided"] },
    { "field": "business_purpose", "statuses": ["user_provided"] },
    { "field": "vendor_country", "statuses": ["observed", "user_provided"] },
    { "field": "supplier_establishment", "statuses": ["user_provided"] },
    { "field": "payment_amount_eur", "statuses": ["observed"] }
  ],
  "conditions": [
    "sonstige B2B-Leistung mit Leistungsort Inland nach § 3a Abs. 2 UStG",
    "leistender Unternehmer für diese Leistung im Ausland ansässig",
    "keine einschlägige Ausnahme oder Steuerbefreiung festgestellt",
    "Leistungsempfänger nutzt § 19 Abs. 1 UStG und verwendet den Bezug für steuerfreie Umsätze"
  ],
  "outcome": {
    "rc_type": "third_country",
    "vat_code": "reverse_charge_third_country",
    "vat_output": "19 % der geklärten EUR-Bemessungsgrundlage, auf Cent gerundet",
    "vat_input": "0 EUR bei Verwendung für nach § 19 Abs. 1 UStG steuerfreie Umsätze"
  },
  "stop_conditions": [
    "Leistungsart, Leistungsort oder leistende Betriebsstätte ungeklärt",
    "Steuersatz oder Bemessungsgrundlage ungeklärt"
  ],
  "sources": [
    { "reference": "§ 3a Abs. 2 UStG", "url": "https://www.gesetze-im-internet.de/ustg_1980/__3a.html" },
    { "reference": "§ 13b Abs. 2 Nr. 1 und Abs. 5 UStG", "url": "https://www.gesetze-im-internet.de/ustg_1980/__13b.html" },
    { "reference": "§ 19 Abs. 1 UStG", "url": "https://www.gesetze-im-internet.de/ustg_1980/__19.html" },
    { "reference": "§ 15 Abs. 2 Satz 1 Nr. 1 UStG", "url": "https://www.gesetze-im-internet.de/ustg_1980/__15.html" }
  ]
}
```

Katalogregeln sind deklarative Prüfanweisungen für den Agenten. Die CLI kann
die registrierte Definition, Version und rechnerische Konsistenz prüfen, aber nicht
alle beschriebenen Tatsachen oder die rechtliche Subsumtion selbst bestätigen.
Die **Regeldefinition selbst** ist die Agentenanweisung; sie verweist nicht
zurück auf eine zweite normative Fassung in `domain_rules.md`. CLI-Services
berechnen und validieren Buchungswerte gemäß ihrem Code; sie wählen oder
„führen“ keine Katalogregel aus. Eine Regelreferenz im Nachweis beschreibt
die vom Agenten oder Menschen verwendete fachliche Begründung. Die Regeln
liegen im unten genannten Skill-Bundle und werden gemäß Spec 022 mit dem
Paket ausgeliefert.
Jede zitierte Fundstelle erhält im veröffentlichten Katalog ihren geprüften
Stand. Frühere veröffentlichte Katalogversionen bleiben im Paket als lesbare
Regeldateien verfügbar; ein bloßer Hash ohne Regeltext genügt
für die spätere Prüfung nicht. Dossierregeln sind **mandantenspezifisch**:
Der Nachweis speichert Dossierpfad, Abschnitt, die nötige Regelpassage und
deren SHA-256. Eine fallbezogene Entscheidung außerhalb des Katalogs erhält
im Entscheidungsnachweis die Kennung `basis: "ad_hoc"`, aber **keine**
erfundene `EUER-R-...`-ID oder Regelversion. `ad_hoc` bezeichnet den
Entscheidungsweg, keine fachliche Regel mit eigenen Voraussetzungen.

Für Katalogregeln wird `rule_sha256` aus der kanonischen UTF-8-JSON-Darstellung
der vollständigen Regeldefinition berechnet (sortierte Schlüssel, keine
Formatierungsleerzeichen); bei Dossierregeln aus den UTF-8-Bytes der
gespeicherten Regelpassage. Der Fingerabdruck ist ein Identifikator, keine
Signatur oder Manipulationssperre.

### Speicherort und Auslieferung

**Eine kanonische Quelle für den allgemeinen Regelkatalog:** Im Repository
liegen die Agentenregeln als versionierte JSON-Dateien
unter `docs/skills/euer-buchhaltung/references/rules/`, zum Beispiel
`EUER-R-RC-THIRD-COUNTRY-01/1.2.0.json`. Der CLI-Code bleibt für die
tatsächlich ausgeführten Berechnungen und Validierungen maßgeblich;
Katalogregeln dokumentieren die fachliche Einordnung durch den Agenten.

Der bestehende Build kopiert den **gesamten** Skill-Ordner nach
`euercli/assets/skill/`. `euer rules find` und `euer rules show` lesen die
Regeldateien über denselben `bundle_path()`, den auch `euer doctor` meldet:
im installierten Paket die gebündelte Kopie, im Repository-Checkout die
kanonische Quelle. Die Suche funktioniert offline. Eine eventuell in ein
Agentensystem kopierte Skill-Version ist keine zusätzliche Katalogquelle für
die CLI; deren bestätigte Version wird weiterhin nach Spec 022 geprüft.

Der Suchindex wird aus diesen Dateien beim Lesen abgeleitet. Es gibt keine
zweite manuell gepflegte Indexdatei und keine SQLite-Kopie des allgemeinen
Katalogs. `booking_decisions` und `booking_decision_rules` speichern nur die
**Anwendung** einer Regel auf einen konkreten Vorgang samt Version und
Fingerabdruck. Veröffentlichte Regelversionen bleiben als Dateien erhalten,
damit `rules show ID --version VERSION` und alte Nachweise nach Paketupdates
auflösbar bleiben. Der Artefakt-Smoke-Test prüft, dass Wheel und sdist diese
Dateien vollständig enthalten.

Mandantenspezifische Dossierregeln verbleiben in der persönlichen `AGENTS.md`
im Buchhaltungsordner. Der allgemeine `rules find`-Katalog durchsucht sie
nicht stillschweigend; der Agent liest das Dossier beim Start und kann eine
verwendete Passage im Entscheidungsnachweis mit Quelle und Fingerabdruck
referenzieren. Die lokale Buchhaltungs-DB ist ebenfalls kein Speicherort für
die allgemeine Regelsammlung.

Die Nomenklatur `EUER-R-<DOMÄNE>-<NUMMER>` ist für veröffentlichte Regeln
reserviert. Eine ID bleibt stabil; jede fachliche Änderung an Voraussetzungen,
Ergebnis oder Geltung erzeugt eine neue Version. Veröffentlichte Versionen
werden nicht überschrieben. Katalogeintrag und Dokumentation erscheinen
zusammen im Paket/Skill; bloße Gesetzesänderungen aktualisieren vergangene
Nachweise nicht. Für jeden Nachweis wird die verwendete Definition mit
Version und SHA-256-Fingerabdruck referenziert, damit sie später auch nach
einem Update eindeutig zugeordnet werden kann. Fehlt eine angegebene
gebündelte Regelversion oder passt ihr Fingerabdruck nicht, wird die Angabe
abgewiesen. Die vom Agenten angegebene Anwendung einer Katalogregel wird als
Claim gespeichert, nicht als Beweis, dass er sie tatsächlich befolgt hat.

Eine Buchung kann mehrere Regeln verwenden. Jede angewandte Regel erhält einen
eigenen Verweis im Nachweis; Suche und Fehleranalyse arbeiten über **alle**
Verweise. Regeln, die lediglich geprüft und verworfen wurden, werden in der
Begründung als Alternativen geführt und gelten nicht als angewandt. Bei einer
reinen Ad-hoc-Entscheidung ist `applied_rules` leer; bei teilweise geregelten
Fällen können Regelverweise und Ad-hoc-Beurteilungen nebeneinander stehen.
Die Geltung wird am für die konkrete Regel maßgeblichen Sachverhaltsdatum
geprüft; Zahlungsjahr und umsatzsteuerliche Meldeperiode sind nicht pauschal
gleichzusetzen. Eine offene Meldeperiode bleibt als Prüfbedarf sichtbar.

### Auffinden und Auswählen von Regeln

**Planungsannahme:** Für eine erste praxistaugliche Abdeckung rechnen wir mit
etwa 10–20 Regeln. Nach der
Übertragung weiterer USt-, EÜR- und Sonderfälle sind eher 50–100 Regeln
denkbar. Das sind Größenordnungen für das CLI-Design,
keine zugesagte Anzahl oder Obergrenze. Nicht jede Überschrift in
`domain_rules.md` wird zu genau einer Regel. Der Agent soll selbst bei einem
größeren Katalog nur eine kurze Übersicht und wenige vollständige Regeln
in seinen Kontext laden müssen.

Die Suchvorschau wird **aus den Regeldefinitionen erzeugt**, nicht als zweite
Liste von Hand gepflegt. Pro Treffer enthält sie nur ID,
Titel, `summary`, Themen, Signale, Vorab-Filter, Geltungszeitraum und
`related_topics`; `summary` bleibt auf 240 Zeichen begrenzt. Quellen,
Bedingungen und vollständige Begründung werden erst
beim gezielten Öffnen geladen. Mit `--year` werden auch ältere Versionen gefunden, deren
Geltungszeitraum das Jahr berührt; ohne Jahresfilter erscheint die aktuell
geltende Version pro ID und ein Hinweis auf vorhandene ältere Versionen.

Geplante lokale, maschinenlesbare Schnittstelle:

```bash
euer rules find --text "SaaS USA" --booking-type expense --tax-mode small_business --year 2025 --json
euer rules find --topic reverse_charge_period --year 2025 --json
euer rules show EUER-R-RC-THIRD-COUNTRY-01 --version 1.2.0 --json
```

`rules find` liefert **Kandidaten**, keine steuerliche Entscheidung. Ohne
Filter ist es ein paginierter Index. Die Ausgabe ist stabil sortiert,
standardmäßig auf 20 Kurztreffer pro Seite begrenzt und enthält `total`,
`has_more` und einen Cursor. Volltextsuche über Titel, Zusammenfassung,
Signale und Themen ist lokal und deterministisch; Synonyme werden im Katalog
gepflegt. Ein Treffer nennt außerdem fehlende Tatsachen, soweit sie aus den
übergebenen Filtern erkennbar sind. Ein unbekanntes Merkmal darf eine Regel
nicht als sicher unzutreffend ausblenden. `--year` zeigt Regeln, deren
Geltungszeitraum das Jahr berührt; die konkrete Anwendbarkeit wird erst mit
dem maßgeblichen Sachverhaltsdatum geprüft. `rules show` lädt genau eine
vollständige Regel einschließlich Voraussetzungen, Stoppfällen und Quellen.

Der Agentenablauf wird im Skill beschrieben:

1. Beleg- und Bankdaten, Mandantenstatus und Zahlungsjahr ermitteln. Zunächst
   nach **bekannten Tatsachen** suchen, nicht nach einer schon vermuteten
   steuerlichen Schlussfolgerung. Zum Beispiel „SaaS“, „USA“, „Ausgabe“ und
   „Kleinunternehmer“ statt nur „Reverse Charge“.
2. Kandidatenübersicht lesen, die passenden Vollregeln mit `rules show`
   öffnen und deren Voraussetzungen gegen Quellen und Nutzerangaben prüfen.
   `related_topics` und die Grundthemen Zahlungszeitpunkt, Kategorie,
   Umsatzsteuer/Vorsteuer sowie gegebenenfalls Privatbezug gezielt nachladen.
3. Anwendbare Regeln und Versionen im Entscheidungsnachweis speichern;
   verworfene Kandidaten nur bei fachlich relevanter Abgrenzung als Alternative
   dokumentieren. Offene Voraussetzungen führen zu Rückfrage oder Prüfbedarf.
4. Bei null oder zu vielen Treffern Suchbegriffe und Themen erweitern bzw.
   präzisieren. Eine leere oder abgeschnittene Trefferliste ist kein Beweis,
   dass keine Regel existiert. Der Agent erfindet keine Katalog-ID.

Die Auswahl bleibt eine fachliche Aufgabe des Agenten. Die CLI validiert
existierende ID/Version, Geltungszeitraum und übergebene Pflichtfelder; sie
behauptet nicht, alle einschlägigen Regeln gefunden oder deren rechtliche
Voraussetzungen selbst geprüft zu haben.

### Verhältnis zu `domain_rules.md`

Der Katalog wird die **einzige gepflegte Fassung formalisierter Wenn-Dann-Regeln**.
Sobald eine bestehende Regel übertragen und geprüft wurde, entfallen ihre
Voraussetzungen, Ergebnisse, Rechtsquellen und Versionsangaben als eigenständige
Regeldefinition aus `domain_rules.md`. Der Skill verweist für diese Entscheidung
direkt auf den Katalogeintrag. Die Datei kann für Arbeitsabläufe, Beispiele,
Begriffserklärungen und Sonderfälle bestehen bleiben, die sich nicht sinnvoll
als einzelne Regel ausdrücken lassen; sie darf keine abweichende Parallelregel
enthalten. Wenn nach der Migration kein solcher Zusatzinhalt übrig bleibt,
entfällt die Datei und ihre Verweise werden angepasst.

Die Umstellung erfolgt pro Themenbereich: Ein noch nicht migrierter Abschnitt
bleibt bis zur Ablösung als bisherige Skill-Anweisung erkennbar. Eine migrierte
Regel hat dagegen nur den Katalog als normative Quelle. Für RC, Vorsteuer,
Bewirtung und weitere Bereiche werden vorhandene Aussagen und Beispiele beim
Übertragen gegen den tatsächlichen CLI-Code und die Rechtsquellen geprüft;
bloßes Umkopieren genügt nicht. `SKILL.md`, CLI-Referenz, User Journey und
Release Notes werden im selben Change auf die neue Quelle umgestellt. Der
ausgelieferte Skill erhält gemäß Spec 022 eine neue Version.

---

## Persistenz und Eingabe-Erweiterung

Die Migration dieses Specs ergänzt zur `booking_decisions`-Tabelle aus
Spec 023 die Tabelle für **angewandte** Regeln:

```sql
CREATE TABLE IF NOT EXISTS booking_decision_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL REFERENCES booking_decisions(id),
    rule_key TEXT NOT NULL,
    rule_version TEXT,
    rule_source TEXT NOT NULL CHECK(rule_source IN ('catalog', 'dossier')),
    rule_sha256 TEXT NOT NULL,
    applied_by TEXT NOT NULL CHECK(applied_by IN ('agent', 'user')),
    UNIQUE(decision_id, rule_key, rule_sha256)
);

CREATE INDEX IF NOT EXISTS idx_decision_rules_lookup
    ON booking_decision_rules(rule_key, rule_version);
```

`rule_key` ist bei gebündelten Regeln die Regel-ID, bei Dossierregeln eine
lokale Referenz aus Dossierpfad und Abschnitt. `rule_version` ist für
gebündelte Regeln Pflicht. Die Tabelle speichert nur tatsächlich angewandte
Regeln; verworfene Kandidaten stehen als Alternativen im Nachweis.
`rule_sha256` identifiziert die aufgelöste Definition oder Dossierpassage.
`rule_source` unterscheidet die veröffentlichte Katalogdatei von einer
mandantenspezifischen Dossierpassage. `applied_by` benennt, wer die
fachliche Regelanwendung behauptet; die CLI verifiziert diese Subsumtion nicht.
Bei Dossierregeln speichert `decision_data.dossier_rule_snapshots` je
`rule_key` den Dossierpfad, Abschnitt und die tatsächlich verwendete Passage.
Der Service prüft, dass deren SHA-256 zum Regelverweis passt. So bleibt die
Anwendung lesbar, wenn das persönliche Dossier später geändert wird.

Das Eingabeformat aus Spec 023 erhält optional `applied_rules` und
`catalog_search`. Beispiel eines Regelverweises:

```json
{
  "applied_rules": [
    {
      "rule_id": "EUER-R-RC-THIRD-COUNTRY-01",
      "rule_version": "1.2.0",
      "applied_by": "agent"
    }
  ]
}
```

Die CLI löst gebündelte Regeln im aktiven Katalog auf, prüft ID, Version,
Geltungszeitraum und übergebene Pflichtfelder und schreibt die kanonischen
Werte mit Fingerabdruck in `booking_decision_rules`. `applied_rules` wird
nicht zusätzlich in `booking_decisions.decision_data` persistiert.
`catalog_search` speichert Suchbegriffe, Themen und geprüfte Kandidaten im
Entscheidungsnachweis; die CLI ergänzt den aktiven Bundle-/Skill-Stand.
Diese Angaben sind Claims des Erfassers, keine Vollständigkeitsgarantie.

## Beispiel für einen angewandten Katalogverweis

### Drittland-B2B-Rechnung für Kleinunternehmer (fiktiv)

Das **fiktive** Beispiel setzt einen in Deutschland ansässigen Kleinunternehmer
voraus. Ein Beleg über einen SaaS-Dienst weist 20,00 USD und keine ausgewiesene
deutsche USt aus; die Kreditkartenabbuchung beträgt 18,50 EUR. Die Rechnung
bezeichnet den leistenden Unternehmer als in den USA ansässig. Der Nutzer
bestätigt den betrieblichen B2B-Bezug und erklärt, dass an dieser Leistung
keine inländische Betriebsstätte des Anbieters beteiligt war. Diese
Bestätigung bleibt als Nutzerangabe erkennbar; bei ungeklärter Betriebsstätte
oder Leistungsart ist die Behandlung als Prüfbedarf zu markieren.

Unter diesen Annahmen liegt der Leistungsort nach
[§ 3a Abs. 2 UStG](https://www.gesetze-im-internet.de/ustg_1980/__3a.html)
im Inland. Die Steuerschuld geht nach
[§ 13b Abs. 2 Nr. 1 und Abs. 5 UStG](https://www.gesetze-im-internet.de/ustg_1980/__13b.html)
auf den Leistungsempfänger über; dies gilt laut
[USt-Anwendungserlass, Abschnitt 13b.1 Abs. 1](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Umsatzsteuer/Umsatzsteuer-Anwendungserlass/Umsatzsteuer-Anwendungserlass-31-12-2025.pdf?__blob=publicationFile&v=2)
auch für Kleinunternehmer. Bei 18,50 EUR Bemessungsgrundlage ergeben 19 %
**3,52 EUR** Umsatzsteuer. Die nach
[§ 19 Abs. 1 UStG](https://www.gesetze-im-internet.de/ustg_1980/__19.html)
steuerfreien eigenen Umsätze schließen den Vorsteuerabzug für zu ihrer Ausführung
verwendete Leistungen nach
[§ 15 Abs. 2 Satz 1 Nr. 1 UStG](https://www.gesetze-im-internet.de/ustg_1980/__15.html)
aus (`vat_input = 0.00 EUR`). Der Nachweis hält diese Voraussetzungen unter
der unten als Beispiel definierten Regel `EUER-R-RC-THIRD-COUNTRY-01` fest. Die steuerliche Periode der
§-13b-Schuld ist gesondert zu prüfen; das Zahlungsdatum allein bestimmt sie
nicht.


Der folgende vollständige Eingabenachweis zeigt den geplanten Regelverweis.
Die Beispiel-ID ist erst nach fachlicher Prüfung und Veröffentlichung
verwendbar:

```json
{
  "schema_version": "1.0",
  "applied_rules": [
    {
      "rule_id": "EUER-R-RC-THIRD-COUNTRY-01",
      "rule_version": "1.2.0",
      "applied_by": "agent"
    }
  ],
  "sources": [
    {
      "id": "receipt_1",
      "type": "receipt",
      "reference": "receipts/2025/Cloudflare_INV-12345.pdf",
      "locator": "Invoice Total / Vendor Address / Leistungsbeschreibung"
    },
    {
      "id": "bank_1",
      "type": "bank_statement",
      "reference": "Kontoauszug_2025_03.csv",
      "locator": "Zeile 142"
    },
    {
      "id": "user_1",
      "type": "user_confirmation",
      "reference": "Bestätigung des Nutzers vom 2025-03-16",
      "locator": "Betrieblicher Bezug und leistende Betriebsstätte"
    }
  ],
  "observations": {
    "vendor_name": { "value": "Cloudflare, Inc.", "status": "observed", "source_id": "receipt_1" },
    "vendor_country": { "value": "US", "status": "observed", "source_id": "receipt_1" },
    "invoice_amount_usd": { "value": 20.00, "status": "observed", "source_id": "receipt_1" },
    "invoice_german_vat_eur": { "value": 0.00, "status": "observed", "source_id": "receipt_1" },
    "payment_amount_eur": { "value": -18.50, "status": "observed", "source_id": "bank_1" },
    "business_purpose": { "value": "DNS & WAF für Webprojekt", "status": "user_provided", "source_id": "user_1" },
    "service_type": { "value": "SaaS-Dienstleistung für das Unternehmen", "status": "user_provided", "source_id": "user_1" },
    "supplier_establishment": { "value": "Keine inländische Betriebsstätte an dieser Leistung beteiligt (Nutzerangabe)", "status": "user_provided", "source_id": "user_1" }
  },
  "decision": {
    "category": "Laufende EDV-Kosten",
    "eur_line": 50,
    "amount_eur": -18.50,
    "rc_type": "third_country",
    "tax_mode_applied": "small_business",
    "vat_output_eur": 3.52,
    "vat_input_eur": 0.00,
    "reasoning": "Die Rechnung nennt den US-Anbieter und einen SaaS-Dienst ohne deutsche USt. Der Nutzer bestätigt den betrieblichen B2B-Bezug und verneint eine an dieser Leistung beteiligte inländische Betriebsstätte. Die Bankzeile belegt -18,50 EUR; daraus ergeben sich 3,52 EUR bei 19 %. Deshalb wurde die referenzierte Drittland-RC-Regel angewandt. Die USt-Periode bleibt gesondert zu prüfen.",
    "uncertainties": [],
    "open_questions": ["Steuerperiode der §-13b-Schuld anhand Leistungs- und Rechnungsdatum prüfen"]
  }
}
```

## Umfang und Phasenplanung

1. Den Regelvertrag und eine erste fachlich geprüfte Katalogversion mit dem
   Paket ausliefern. Build und Artefakt-Smoke-Test prüfen die Regeldateien.
2. `euer rules find` und `euer rules show` mit JSON-Ausgabe, Pagination und
   historischen Versionen implementieren. Der Agenten-Skill beschreibt die
   schrittweise Auswahl vor dem Buchen.
3. Die Nachweise aus Spec 023 um `applied_rules`, `catalog_search`,
   `booking_decision_rules` und die Anzeige in `euer explain` erweitern.
4. `domain_rules.md` themenweise migrieren und weitere geprüfte Regeln
   ergänzen. Der Katalog muss nicht zu Beginn vollständig sein.
5. Historische Suche ergänzen, z. B.
   `euer decisions find --rule-id <ID> [--rule-version <VER>] [--scope ever|current]`.
   `ever` durchsucht alle historischen Nachweise einschließlich geänderter
   und gelöschter Buchungen. `current` beschränkt sich auf aktive Buchungen,
   deren letzter fachlicher Nachweis die Regel noch verwendet.

## Akzeptanzfälle

1. Ein leerer Katalog hindert die Erfassung und Anzeige von Ad-hoc-
   Entscheidungsnachweisen nach Spec 023 nicht.
2. Eine referenzierte `EUER-R-...`-Regel besitzt eine ausgelieferte Definition
   mit Voraussetzungen, Ergebnis, Stoppfällen, Quellen und Geltungszeitraum.
   Unbekannte ID/Version oder abweichender Fingerabdruck werden abgewiesen;
   eine neue Version überschreibt die alte nicht.
3. Eine Suche nach `SaaS USA` liefert kompakte Kandidaten; `rules show` lädt
   gezielt die vollständige Version. Mehr als 20 Treffer werden mit stabilem
   Cursor paginiert; unbekannte Merkmale blenden mögliche Regeln nicht aus.
4. Wheel und Checkout liefern dieselben Regel-IDs, Versionen und
   Fingerabdrücke aus dem aktiven Skill-Bundle. Historische Versionen bleiben
   abrufbar; die Buchhaltungs-DB enthält keinen zweiten vollständigen Katalog.
5. Ein Nachweis kann mehrere angewandte Regeln tragen. Alle sind über
   `booking_decision_rules` auffindbar; verworfene Alternativen erscheinen
   dort nicht. Ad-hoc-Beurteilungen können daneben bestehen.
6. Die historische Suche findet alle betroffenen Nachweise; `current` und
   `ever` liefern die jeweils dokumentierte Bedeutung.
7. Eine Dossierregel bleibt anhand der gespeicherten Passage verständlich,
   auch wenn der Mandant sein Dossier später ändert.
8. Eine CLI-Steuerberechnung erzeugt keinen Katalogregelverweis allein wegen
   eines ausgeführten Servicepfads. Nur eine ausdrücklich angegebene
   Regelanwendung wird mit `applied_by = agent|user` dokumentiert; die CLI
   prüft die Referenz und die rechnerische Konsistenz, nicht die fachliche
   Subsumtion.

## Verwandte Specs

- [Spec 023: Entscheidungsnachweis](023-entscheidungsnachweis.md)
- [Spec 022: Versionierter Skill](022-skill-updates.md)
- [Spec 016: Agent-Safety und Guardrails](016-agent-safety-und-guardrails.md)
