# Spec 024: Versionierter Regelkatalog für Entscheidungsnachweise

## Status

Offen

## Entscheidung

Auf [Spec 023](023-entscheidungsnachweis.md) aufbauend einen versionierten,
offline verfügbaren Regelkatalog einführen. Spec 023 kann bereits ohne
Katalogregeln umgesetzt und genutzt werden: Der Agent erfasst dann
fallbezogene Begründungen und Annahmen. Dieser Spec ergänzt geprüfte
Wenn-Dann-Regeln, deren schrittweise Suche und die gezielte Analyse von
Buchungen, die eine bestimmte Regelversion verwendet haben.

Ein leerer Katalog blockiert die Erfassung nach Spec 023 nicht. Erst wenn
Katalogverweise unterstützt werden, dürfen `EUER-R-...`-IDs in Nachweisen
stehen; vorher sind solche IDs nur Beispiele.

## Abhängigkeit und Integrationsgrenze

- Spec 023 speichert Begründung, Annahmen und Gültigkeitsstatus direkt in
  `expenses`, `income` und `private_transfers`; deren Historie steht in den
  bestehenden Audit-Feldern `old_data` und `new_data`. Dazu kommen `--reasoning`,
  `--assumption`, `euer explain` und die Vollständigkeitsprüfung über `incomplete`.
  Quellen und Fundstellen stehen im Freitext; separate Nachweis-JSONs entfallen.
- Dieser Spec ergänzt den versionierten Regelkatalog, `rules find`/`rules show`,
  das wiederholbare Flag `--rule ID@VERSION` sowie die Suche nach angewandten
  Regelversionen. Ein Nachweis wird durch die zugehörige `audit_log.id` identifiziert.
- **Ein gültiger Regelverweis ersetzt die Freitextbegründung.** `--reasoning` bleibt
  optional als fallbezogene Ergänzung möglich; Annahmen werden weiterhin über
  `--assumption` dokumentiert. Regeln, Freitext oder beides sind zulässige Grundlagen.
- Es gibt keinen neuen Freigabeprozess. Die Regeln werden vom Agenten ausgewählt;
  die Engine speichert deren Anwendung und erzwingt ihre bestehenden Buchungsregeln.

---

## Regelmodell und Katalog

Eine **Regel** ist eine versionierte, fachlich überprüfbare Wenn-Dann-Anweisung.
Sie besteht aus Voraussetzungen, benötigten Tatsachen, einer vorgesehenen
Einordnung oder Berechnung, Abbruch-/Rückfragebedingungen, Geltungszeitraum und
Quellen. Die Regel-ID allein ist keine Regel und ersetzt ihre Definition nicht.
Ein Entscheidungsnachweis hält fest, **welche Version** der Agent für den
Buchungsvorgang angewandt hat und welches Ergebnis gespeichert wurde. Den
Sachverhalt liefern Beleg, Buchungsdaten, Mandantenkontext und gegebenenfalls
Freitext und Annahmen; die CLI verlangt keine separate strukturierte
Tatsachenerfassung als Voraussetzung für einen Regelverweis.

### Verbindlicher Regelvertrag

Jede veröffentlichte Regeldefinition enthält mindestens:

Die strukturierten Quellenangaben unten gehören zur Regeldefinition im Katalog.
Beim Buchungsaufruf stehen zusätzliche Quellenhinweise im optionalen Freitext.

| Feld | Bedeutung |
|---|---|
| `id`, `version` | Stabile ID und unveränderliche fachliche Version. |
| `title`, `purpose` | Verständliche Bezeichnung und eine klar abgegrenzte fachliche Entscheidung. |
| `summary`, `topics`, `signals` | Kurze Suchvorschau, fachliche Themen und typische Begriffe/Synonyme aus Beleg oder Sachverhalt. |
| `applies_to`, `related_topics` | Vorab bekannte Filtermerkmale und weitere Themen, die bei diesem Fall geprüft werden sollten. |
| `effective_from`, `effective_until` | Zeitraum des **Sachverhalts**, für den die Regel gilt; `null` bei offenem Ende. |
| `required_facts` | Vom Agenten zu prüfende Sachverhaltsmerkmale und zulässige Herkunftsstatus. Die Herkunft wird fachlich vom Agenten beurteilt; eine bloße Annahme erfüllt keine Voraussetzung für eine belegte oder bestätigte Angabe. Keine zusätzlichen Pflichtfelder der Buchungs-CLI. |
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
die registrierte Definition und Version sowie eindeutig aus Buchungsdaten
prüfbare Einschränkungen prüfen, aber nicht alle beschriebenen Tatsachen oder die
rechtliche Subsumtion selbst bestätigen. Rechenregeln der Engine bleiben maßgeblich.
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
für die spätere Prüfung nicht. Dossierhinweise sind **mandantenspezifisch**:
Der Agent beschreibt verwendete Abschnitte und Aussagen bei Bedarf unter
`--reasoning`, angenommene Voraussetzungen unter `--assumption`. `--rule`
referenziert in dieser Version ausschließlich veröffentlichte Katalogregeln.
Eine fallbezogene Entscheidung außerhalb des Katalogs bleibt
unter `reasoning` und `assumptions` dokumentiert, ohne zusätzliche Kennung und
ohne erfundene `EUER-R-...`-ID oder Regelversion.

Für Katalogregeln wird `rule_sha256` aus der kanonischen UTF-8-JSON-Darstellung
der vollständigen Regeldefinition berechnet (sortierte Schlüssel, keine
Formatierungsleerzeichen). Der Fingerabdruck ist ein Identifikator, keine
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
Katalogs. Die Relation `booking_rules` speichert nur die **aktuelle Anwendung**
einer Regel auf eine Buchung samt Version und Fingerabdruck; frühere Zuordnungen
stehen in deren Audit-Historie. Veröffentlichte Regelversionen bleiben als Dateien erhalten,
damit `rules show ID --version VERSION` und alte Nachweise nach Paketupdates
auflösbar bleiben. Der Artefakt-Smoke-Test prüft, dass Wheel und sdist diese
Dateien vollständig enthalten.

Mandantenspezifische Dossierregeln verbleiben in der persönlichen `AGENTS.md`
im Buchhaltungsordner. Der allgemeine `rules find`-Katalog durchsucht sie
nicht stillschweigend; der Agent liest das Dossier beim Start und kann eine
verwendete Passage mit Pfad und Abschnitt im Freitext der Begründung nennen.
Die lokale Buchhaltungs-DB ist ebenfalls kein Speicherort für die allgemeine
Regelsammlung.

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
reinen fallbezogenen Freitextbegründung gibt es keine gespeicherten Regelverweise; bei teilweise geregelten
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
existierende ID/Version und eindeutig aus den vorhandenen Buchungsdaten prüfbare
Einschränkungen, etwa Buchungstyp und Steuermodus. Geltungszeitraum und weitere
Voraussetzungen werden vom Agenten am maßgeblichen Sachverhalt geprüft; die CLI
prüft sie nur, soweit sie daraus eindeutig bestimmbar sind. Sie leitet keine
Tatsachen aus Freitext ab und behauptet nicht, alle einschlägigen Regeln gefunden
oder deren rechtliche Voraussetzungen selbst geprüft zu haben.

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

## Erfassung, Vollständigkeit und Updates

Bei den bestehenden `add`- und `update`-Befehlen für Ausgaben, Einnahmen und
Privatvorgänge ergänzt die CLI:

```text
--rule REGEL-ID@VERSION
```

- Das Flag ist mehrfach verwendbar. ID und fachliche Version sind explizit;
  es gibt keine stillschweigende Auflösung auf die neueste Version.
- Die CLI löst jeden Verweis im aktiven lokalen Katalog auf. Fehlende ID/Version,
  unbekannte Regeln, unlesbare Definitionen und eindeutig widersprüchliche
  Buchungsdaten erzeugen `ValidationError` ohne Teilmutation. Ein unbekannter
  Regelverweis wird nicht als Freitext übernommen.
- Identische wiederholte Verweise werden dedupliziert. Verschiedene Versionen
  derselben Regel im selben Nachweis werden als Konflikt abgewiesen.
- `--rule` erzeugt auch ohne `--reasoning` einen vollständigen Regel-Nachweis.
  Der Agent muss den Regeltext nicht nochmals als Begründung formulieren.
  Zusätzlicher Freitext kann Quellen, Besonderheiten und Abgrenzungen erläutern.
- `--assumption` und `--clear-assumptions` aus Spec 023 sind auch zusammen mit
  `--rule` ohne Freitext zulässig. Annahmen allein ersetzen keinen Nachweis.
- Quellen, geprüfte Kandidaten und relevante Sachverhaltsangaben können im
  Freitext stehen. Es gibt keine zusätzlichen Nachweis-JSONs, `sources`-Objekte,
  `observations` oder Pflichtfelder für einen Suchnachweis.

| Aktuelle Nachweisgrundlage | Folge für `incomplete` |
|---------------------------|-----------------------|
| Freitext, kein Regelverweis | Nachweis vorhanden wie in Spec 023. |
| Mindestens ein gültiger Regelverweis, kein Freitext | Nachweis vorhanden; keine Begründungslücke. |
| Freitext und gültige Regelverweise | Nachweis vorhanden; beide Grundlagen sichtbar. |
| Weder Freitext noch Regelverweis | Nachweis fehlt; Buchung wegen `reasoning` unvollständig. |
| Fachlich veralteter Nachweis oder geänderte Belegreferenz | Nachweislücke wie in Spec 023, auch bei einem früheren Regelverweis. |

Andere Datenlücken bleiben bestehen. Die Filter `--missing reasoning` und
`--missing reasoning-only` erfassen weiterhin die Nachweisvollständigkeit; eine
fehlende Freitextbegründung allein ist bei gültigem aktuellem Regelverweis keine
Lücke. Ein Regelverweis bloß im Freitext bleibt lesbar, wird aber nicht automatisch
als strukturierte Regelanwendung für die Regelsuche ausgewertet.

Bei `update` mit `--reasoning` und/oder `--rule` entsteht ein neuer vollständiger
Nachweis zum aktuellen Buchungsstand, auch ohne geänderte Buchungswerte.
Regelverweise müssen dabei ausdrücklich neu angegeben werden; sie werden nicht
stillschweigend aus der Historie übernommen. Ein Update nur mit `--rule` übernimmt
keinen alten Freitext; `reasoning` ist dann intern `null`. Die Annahmen folgen dem
Übernehmen-/Ersetzen-/Leeren-Vertrag aus Spec 023. Ohne Nachweisflags wird kein neuer
Nachweis erzeugt; Änderungen können den bisherigen Stand veralten lassen.

JSONL unterstützt ein optionales Feld `rules` als Liste von `ID@VERSION`-Zeichenketten;
CSV ein optionales Feld `rule` für einen einzelnen Verweis. Fehlende Regeln,
`rules: []` und leere CSV-Zellen bedeuten keinen Verweis; explizit leere Verweise
oder falsche Typen sind Fehler. `reasoning` darf bei gültigen Regelverweisen fehlen;
ein explizit leerer Begründungstext in CLI oder JSONL bleibt ein Eingabefehler.
Validierung, Duplikate, Rollback und Dry-Run folgen Spec 023.

## Persistenz und Anzeige

Begründung, Annahmen und Gültigkeitsstatus bleiben in den Buchungstabellen gemäß
Spec 023. Bei reinen Regel-Nachweisen ist `reasoning = NULL`; die Engine erzeugt
keinen angeblich vom Agenten geschriebenen Erklärungstext. Ein gültiger aktueller
Regelverweis setzt den Nachweisstatus auch ohne Freitext auf `current`.

Die Migration ergänzt eine zunächst leere Relation; bestehende Freitextnachweise
und deren Status werden nicht verändert. Mehrere aktuelle Regelverweise werden
als Relation zur Buchung gespeichert:

```sql
CREATE TABLE IF NOT EXISTS booking_rules (
    table_name TEXT NOT NULL
        CHECK (table_name IN ('expenses', 'income', 'private_transfers')),
    record_uuid TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    rule_sha256 TEXT NOT NULL,
    PRIMARY KEY (table_name, record_uuid, rule_key)
);

CREATE INDEX IF NOT EXISTS idx_booking_rules_lookup
    ON booking_rules(rule_key, rule_version);
```

`table_name` und `record_uuid` ordnen die Referenz stabil einer Ausgabe, Einnahme
oder einem Privatvorgang zu. Die Services validieren, dass die Buchung existiert;
ein einzelner Fremdschlüssel kann nicht auf drei Tabellen verweisen. Der Primärschlüssel
verhindert verschiedene Versionen derselben Regel an derselben Buchung. Jeder Verweis
enthält Katalog-ID, fachliche Version und den von der Engine ermittelten SHA-256-
Fingerabdruck. Die Relation enthält keine Kopie der allgemeinen Regeldefinition.

- Ein neuer Nachweis ersetzt die aktuelle Regelmenge durch die ausdrücklich
  gelieferten Verweise. Ein reines `update --reasoning` entfernt daher bisherige
  Regelzuordnungen aus dem aktuellen Stand; die Historie behält sie.
- Ohne neue Nachweisgrundlage bleiben Regelzuordnungen, Freitext und Annahmen
  erhalten. Eine fachliche Änderung oder ein Belegwechsel markiert den gesamten
  Nachweis nach Spec 023 als veraltet, einschließlich seiner Regelverweise.
- Das Buchungs-Audit sichert die vollständigen Vorher-/Nachher-Stände gemäß
  Spec 023 und zusätzlich jeweils die Regelmenge unter `_rules` in `old_data`
  beziehungsweise `new_data`. `_rules` ist eine Liste aufgelöster Referenzen mit
  `rule_key`, `rule_version` und `rule_sha256`, standardmäßig `[]`. Sie dokumentiert
  den Stand der Relation und ist kein vom Agenten zu lieferndes Nachweisobjekt.
- Buchungswerte, Nachweisfelder, Regelrelation und Audit werden in derselben
  Transaktion geschrieben. Das gilt auch für reine Regeländerungen und Imports;
  frühere Audit-Stände bleiben unverändert. `audit_log.user` benennt wie bisher
  den Erfassereintrag; zusätzliche Actor-Flags entfallen.
- Undo restauriert Nachweisfelder und aktuelle Regelrelation gemeinsam aus dem
  vorherigen Audit-Stand. Fehlendes `_rules` in Ereignissen vor dieser Erweiterung
  bedeutet keine Regelzuordnung. Audit-Metadaten werden nicht als Buchungsspalten
  restauriert. Der wiederhergestellte Status kann weiterhin veraltet sein.
- Soft-Delete behält die aktuelle Relation für Restore; Purge entfernt sie zusammen
  mit der Buchung, ohne historische Regelreferenzen im Audit zu löschen.

`euer explain` liest den aktuellen Nachweis aus der Buchung und `booking_rules`.
Es zeigt IDs, Versionen und Regeldefinitionen beziehungsweise deren verständliche
Zusammenfassung mit Annahmen, optionalem Freitext und Gültigkeitsstatus. Veraltete
Regelzuordnungen bleiben sichtbar, erfüllen aber nicht die Nachweisvollständigkeit.
Die JSON-Ausgabe ergänzt je Nachweis `rules` mit den aufgelösten Metadaten.
Historische Zuordnungen und Buchungsstände kommen aus dem Audit und werden anhand
der damaligen Regelversion aufgelöst. Fehlende historische Regeldateien werden als
Auflösungsfehler sichtbar, nicht durch eine neuere Definition ersetzt.

Die Suche nach aktuellen Anwendungen nutzt die Relation zur Buchung; die historische
Suche liest die Regelmengen aus den UUID-bezogenen Audit-Ständen. Es gibt keine weitere
Tabelle für unveränderliche Nachweisobjekte. Die Integritätsprüfung aus Spec 028
muss sowohl aktuelle Regelzuordnungen als auch deren Audit-Snapshots einschließen.

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


Nach fachlicher Prüfung und Veröffentlichung der Beispielregel könnte der Agent
sie direkt bei der Buchung referenzieren, ohne einen zusätzlichen Nachweistext oder
eine Datei zu erzeugen. Die folgenden Parameter illustrieren nur die Schnittstelle:

```bash
euer add expense --date 2025-03-16 --vendor "Cloud-Anbieter" \
  --amount -18.50 --category "Laufende EDV-Kosten" \
  --receipt "receipts/2025/cloud.pdf" --rc third-country \
  --rule EUER-R-RC-THIRD-COUNTRY-01@1.2.0
```

Mit optionalem Freitext können beispielsweise Dossier- und Belegbezüge ergänzt
werden. Relevante Annahmen werden separat über `--assumption` mitgegeben.
Der aktuelle Sachverhalt bleibt vom Agenten zu prüfen; der Verweis dokumentiert
seine Regelwahl, statt die Voraussetzungen selbst zu bestätigen.

## Umfang und Phasenplanung

1. Den Regelvertrag und eine erste fachlich geprüfte Katalogversion mit dem
   Paket ausliefern. Build und Artefakt-Smoke-Test prüfen die Regeldateien.
2. `euer rules find` und `euer rules show` mit JSON-Ausgabe, Pagination und
   historischen Versionen implementieren. Der Agenten-Skill beschreibt die
   schrittweise Auswahl vor dem Buchen.
3. `--rule`, Importfelder und `booking_rules` samt Audit-Snapshots ergänzen. Die Anzeige in
   `euer explain` und die Vollständigkeitsprüfung in `incomplete` erweitern:
   gültiger aktueller Regelverweis genügt auch ohne Freitext.
4. `domain_rules.md` themenweise migrieren und weitere geprüfte Regeln
   ergänzen. Der Katalog muss nicht zu Beginn vollständig sein.
5. Historische Suche ergänzen, z. B.
   `euer decisions find --rule-id <ID> [--rule-version <VER>] [--scope ever|current]`.
   `ever` durchsucht alle historischen Nachweise einschließlich geänderter,
   gelöschter und gepurgter Buchungen. Treffer werden pro Audit-Nachweis und
   Regelverweis dedupliziert; wiederholte Snapshots desselben Nachweises zählen
   nicht als neue Anwendung. `current` beschränkt sich auf aktive Buchungen,
   deren gespeicherter Nachweisstatus `current` ist und deren aktuelle Regelrelation
   die Regel verwendet. Veraltete Anwendungen werden nur unter `ever` gefunden.

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
   `booking_rules` aktuell und im Audit historisch auffindbar; verworfene
   Alternativen erscheinen dort nicht. Ad-hoc-Beurteilungen können daneben bestehen.
6. Die historische Suche findet alle betroffenen Nachweise; `current` und
   `ever` liefern die jeweils dokumentierte Bedeutung.
7. Dossier- und Quellenbezüge lassen sich im optionalen Freitext dokumentieren;
   dafür wird weder eine Datei noch ein separates Nachweisobjekt verlangt.
8. Eine CLI-Steuerberechnung erzeugt keinen Katalogregelverweis allein wegen
   eines ausgeführten Servicepfads. Nur eine ausdrücklich angegebene
   Regelanwendung wird über `--rule` beziehungsweise die entsprechenden
   Importfelder dokumentiert. Die CLI prüft die Referenz und eindeutig prüfbare
   Einschränkungen, nicht die fachliche Subsumtion.
9. Ein gültiger aktueller Regelverweis ohne `--reasoning` erzeugt einen Nachweis
   und keine Begründungslücke. Freitext allein und die Kombination bleiben
   möglich; Datenlücken werden durch Regelverweise nicht behoben.
10. Update nur der Regelanwendung, neue Regelversion, fachliche Änderung ohne
    Nachweis, Notizänderung und Undo liefern in `explain`, `incomplete` und der
    Regelsuche denselben aktuellen Stand, für Ausgaben, Einnahmen und Privatvorgänge.
    Veraltete Texte, Annahmen und Regelzuordnungen bleiben sichtbar; der Status wird
    markiert. Historische Anwendungen bleiben nach Ersetzen und Purge lesbar. Undo
    restauriert auch die Relation atomar, einschließlich fehlender früherer `_rules`.
11. Wiederholte identische Verweise werden dedupliziert; verschiedene Versionen
    derselben Regel, unbekannte IDs, fehlende Versionen und fehlerhafte Importfelder
    erzeugen Fehler ohne Teilmutation, auch in späteren Importzeilen und bei
    Duplikaten. Kein Freitext ist bei gültigen Verweisen zulässig, explizit leerer
    Freitext bleibt ein Fehler.

## Verwandte Specs

- [Spec 023: Entscheidungsnachweis](023-entscheidungsnachweis.md)
- [Spec 022: Versionierter Skill](022-skill-updates.md)
- [Spec 016: Agent-Safety und Guardrails](016-agent-safety-und-guardrails.md)
