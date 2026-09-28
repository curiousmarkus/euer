# Spec 023: Nachvollziehbarer Entscheidungsnachweis für Buchungen (Decision Trace)

## Status

Offen

## Entscheidung

Als eigenständiges, schrittweise umsetzbares Feature einplanen. Das vorhandene
`audit_log` dokumentiert Mutationen (welche Tabellenfelder wurden wann und durch
wen geändert), nicht jedoch das *Warum*: aus welcher Belegstelle Angaben entnommen
wurden, welcher epistemische Status ihnen zukommt (gesehen vs. bestätigt vs.
angenommen) und wie eine Steuer- oder Kategorieentscheidung begründet wurde.

Ein formalisierter Entscheidungsnachweis (*Decision Trace*) schließt diese Lücke.
Er dient der Nachvollziehbarkeit agentischer Entscheidungen bei der menschlichen
Prüfung und macht spätere Korrekturen anhand der dokumentierten Gründe nachvollziehbar.
Ein versionierter Regelkatalog und die Suche nach betroffenen Regelanwendungen
folgen separat in [Spec 024](024-regelkatalog.md).

**Klarstellung und Schutzgrenze:**
Der Entscheidungsnachweis ist eine interne Dokumentation der Subsumtion und
Begründung des Erfassers (Mensch oder Agent). Er ist **kein steuerlicher
Belegersatz** (wie Eigenbeleg oder Bewirtungsnachweis nach § 4 Abs. 5 EStG),
keine behördliche Richtigkeitsgarantie und beansprucht keine technische
GoBD-Revisionssicherheit gegen Manipulation durch Betriebssystem-Nutzer.

## Produktgrenze

`euer` liest Belege nicht selbst. Ein Agent oder Mensch liefert extrahierte Angaben
und deren Herkunft. Die CLI speichert diese Angaben als **behauptete, nicht
automatisch verifizierte Tatsachen (Claims)**. Sie darf daraus keine nicht belegten
Fakten oder rechtlichen Voraussetzungen ableiten. Das bisherige Änderungsprotokoll
(`audit_log`) bleibt für Undo und Mutationshistorie zuständig; der
Entscheidungsnachweis ergänzt es transaktional.

Der Nachweis gliedert sich in vier strikt getrennte Ebenen:

1. **Quelle (Source):** Beleg-, Bank- und/oder Nutzerbestätigungsreferenz,
   optionale Datei-Prüfsumme (SHA-256) und konkrete Fundstelle (Belegzeile,
   Rechnungsbereich oder Kontoauszugsposition). Jede als `observed` markierte
   Angabe verweist auf eine solche Quelle. Eine Prüfsumme identifiziert die
   referenzierte Dateiversion, nicht die inhaltliche Richtigkeit der Extraktion.
2. **Beobachtung (Observation):** Aus der Quelle entnommene oder vom Nutzer
   beigesteuerte Angaben (z. B. ausgewiesene Steuer, Betrag, Lieferant, Leistungsart).
   Jedes Feld hat einen expliziten Herkunftsstatus:
   - `observed`: Direkt aus der angegebenen Quelle abgelesen.
   - `user_provided`: Vom Nutzer explizit bestätigt (z. B. betriebliche Veranlassung),
     mit Verweis auf die dokumentierte Bestätigung.
   - `assumed`: Vom Agenten abgeleitet oder vermutet. Annahmen gelten nicht als Beleg.
3. **Entscheidung (Decision):** Gewählte Kategorie, EÜR-Zeile, Steuer- und
   Vorsteuerbehandlung, ermittelte Beträge, fallbezogene Begründung sowie
   benannte Unsicherheiten und Alternativen. Sie kann mehrere versionierte
   fachliche Regeln referenzieren, sobald Spec 024 umgesetzt ist. Ohne
   Katalogregel hält sie je Thema eine fallbezogene Ad-hoc-Beurteilung fest.
4. **Buchung (Booking & Audit):** Transaktionale Verknüpfung mit der erzeugten
   Buchung (`record_uuid`) und dem auslösenden Eintrag im Änderungsprotokoll
   (`audit_log.id`). Nachträgliche Buchungsänderungen erzeugen neue Nachweise und
   überschreiben ältere nicht.

### Beispiel: Kategorieentscheidung ohne Katalogregel

Ein Beleg über 18,50 EUR beschreibt laufenden Serverbetrieb. Der Agent ordnet
den Betrag der Kategorie „Laufende EDV-Kosten“ zu. Der Nachweis enthält die
Belegstelle, die Beobachtung, die erwogene Alternative „Übrige
Betriebsausgaben“, das `reasoning` und den Status `pending_user_review`.
Dafür muss noch keine allgemeine Regel veröffentlicht sein.

---

## Entscheidung ohne Regelkatalog

Spec 023 setzt **keinen** veröffentlichten Regelkatalog voraus. Fehlt eine
passende Katalogregel oder existiert noch kein Katalog, darf der Agent einen
geklärten Einzelfall selbst beurteilen, sofern die Behandlung von der CLI
darstellbar ist und ungeklärte Voraussetzungen nicht als gesichert ausgegeben
werden. Der Ablauf ist:

1. Beleg- und Banktatsachen, Nutzerangaben und Annahmen trennen. Verfügbare
   Skill-Anweisungen und das Mandanten-Dossier prüfen; falls der Katalog aus
   Spec 024 bereits existiert, dort mit passenden Begriffen und Geltungsjahr
   suchen. Die tatsächlich geprüften Grundlagen dokumentieren.
2. Für eine steuerliche Einordnung maßgebliche Quellen mit Stand und
   Fundstelle dokumentieren. Alternativen, Folgen und offene Punkte benennen.
3. Bei fehlenden oder widersprüchlichen Tatsachen nachfragen. Bei fachlich
   weiterhin unsicherer steuerlicher Behandlung zur fachlichen Prüfung
   eskalieren. Eine Nutzerbestätigung ersetzt weder Belege noch Klärung.
4. Eine neue steuerwirksame Ad-hoc-Entscheidung dem Nutzer mit Behandlung,
   Begründung, Quellen, Alternativen und Auswirkungen vor endgültiger
   Buchung zur Bestätigung vorlegen. Eine einfache Kategoriezuordnung ohne
   neue Steuerwirkung darf der Agent mit sichtbarem Prüfstatus buchen. Ohne
   nötige Bestätigung bleibt eine steuerwirksame Behandlung offen; wenn die
   CLI keinen unvollständigen Zustand unterstützt, wartet die Buchung.
5. Die fallbezogene Entscheidung mit `basis: "ad_hoc"`, Thema, `reasoning`,
   Quellen, Alternativen, offenen Fragen und Bestätigungsstatus speichern.
   `ad_hoc` ist eine Kennung für den Entscheidungsweg, keine erfundene
   veröffentlichte Regel-ID.

Eine spätere Bestätigung oder Korrektur erzeugt über `update` einen neuen
auditierten Entscheidungsnachweis. Der frühere Stand bleibt erhalten.
`euer explain` zeigt offene Ad-hoc-Fälle und den aktuellen Status.

---

## Datenmodell und Schemadefinition

### 1. Datenbankschema (SQLite DDL)

Der Entscheidungsnachweis wird unabhängig vom Regelkatalog gespeichert.
`audit_id` verknüpft ihn mit dem Audit-Ereignis; `record_uuid` bleibt auch
nach einem Purge als Suchschlüssel erhalten:

```sql
CREATE TABLE IF NOT EXISTS booking_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER NOT NULL UNIQUE REFERENCES audit_log(id),
    record_uuid TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    euer_version TEXT NOT NULL,
    bundled_skill_version TEXT NOT NULL,
    decision_data TEXT NOT NULL, -- Strukturiertes JSON (siehe Schema unten)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_decisions_record_uuid
    ON booking_decisions(record_uuid);
```

Die CLI liest `euer_version` und `bundled_skill_version` selbst aus der
laufenden Installation. Da `audit_log` die dauerhafte Historie trägt,
dürfen Audit-Einträge mit verknüpften Nachweisen nicht einzeln gelöscht
werden. `user_confirmed` dokumentiert eine Nutzeräußerung; die CLI
verifiziert weder Identität noch steuerliche Richtigkeit.

Die spätere Tabelle für angewandte Katalogregeln wird in Spec 024 ergänzt.

### 2. JSON-Eingabeschema und `decision_data` (Version 1.0)

Das versionierte Eingabeformat enthält `sources`, `observations` und
`decision`; diese Felder werden in `booking_decisions.decision_data`
gespeichert. `decision.reasoning` kann die Gesamtentscheidung erläutern.
Für jedes ungeregelte Thema enthält `decision.ad_hoc_assessments` die
Kennung `basis: "ad_hoc"`, Thema, Ergebnis, Quellverweise, Alternativen,
Begründung, offene Fragen und den Status `pending_user_review`,
`user_confirmed` oder `rejected`. Bei `user_confirmed` verweist
`confirmation_source_id` auf eine `user_confirmation` in `sources`;
bei `rejected` wird die ablehnende Nutzeräußerung über `source_ids`
belegt und `confirmation_source_id` bleibt leer.

Ein vollständiger Ad-hoc-Nachweis ohne Katalogregel:

```json
{
  "schema_version": "1.0",
  "sources": [
    {
      "id": "receipt_1",
      "type": "receipt",
      "reference": "receipts/2025/hosting.pdf",
      "locator": "Leistungsbeschreibung und Gesamtbetrag"
    },
    {
      "id": "bank_1",
      "type": "bank_statement",
      "reference": "Kontoauszug_2025_03.csv",
      "locator": "Zeile 142"
    }
  ],
  "observations": {
    "service_type": {
      "value": "Laufender Serverbetrieb",
      "status": "observed",
      "source_id": "receipt_1"
    },
    "payment_amount_eur": {
      "value": -18.50,
      "status": "observed",
      "source_id": "bank_1"
    }
  },
  "decision": {
    "category": "Laufende EDV-Kosten",
    "amount_eur": -18.50,
    "uncertainties": [],
    "open_questions": [],
    "ad_hoc_assessments": [
      {
        "basis": "ad_hoc",
        "topic": "expense_category",
        "result": "Laufende EDV-Kosten",
        "source_ids": ["receipt_1"],
        "alternatives": ["Übrige Betriebsausgaben"],
        "reasoning": "Die Leistung ist laufender Serverbetrieb und keine einmalige Anschaffung.",
        "open_questions": [],
        "review_status": "pending_user_review",
        "confirmation_source_id": null
      }
    ]
  }
}
```

`ad_hoc_assessments[*].reasoning` erklärt den jeweiligen ungeregelten
Teilschritt. `decision.reasoning` ist nur nötig, wenn die einzelnen
Beurteilungen das Gesamtergebnis noch nicht ausreichend erklären. Das
spätere Eingabeformat aus Spec 024 ergänzt optional
`applied_rules` und `catalog_search`; beide sind für Spec 023 nicht nötig.

---

## CLI-Schnittstelle und Interaktionsmodell

### 1. Erfassung bei `add` und `update`

Die CLI unterstützt drei flexible Eingabewege für Nachweise:
- `--decision-file <PFAD>`: Liest das JSON aus einer lokalen Datei.
- `--decision '<JSON>'`: Direkte Inline-Übergabe des JSON-Strings. Da
  Shell-Historie und Prozesslisten die Argumente zeigen können, für sensible
  Angaben Datei oder `stdin` bevorzugen.
- `--decision -`: Liest den JSON-String aus `stdin`.

Beispiel:
```bash
euer add expense \
  --date 2025-03-16 \
  --vendor "Hosting-Anbieter" \
  --amount -18.50 \
  --category "Laufende EDV-Kosten" \
  --receipt "receipts/2025/hosting.pdf" \
  --decision-file /tmp/hosting_decision.json
```

### 2. Diskrepanz- und Validierungsregeln (Konfliktschutz)

Werden sowohl CLI-Flags als auch Decision-Daten übergeben, führt die CLI einen
**strengen Konsistenzabgleich** durch:
- Verglichen werden die **normalisierten, tatsächlich zu speichernden Felder**
  mit gleichartigen Feldern in `decision`, nicht Rechnungs- und Zahlungsbeträge
  unterschiedlicher Währung. Für `expense` werden `--amount 18.50` und
  `--amount -18.50` vor dem Speichern beide zu `-18.50` normalisiert und
  gegen das signierte `decision.amount_eur = -18.50` geprüft; 20,00 USD aus
  der Rechnung bleiben eine separate Beobachtung. Diese Normalisierung muss
  im Buchungsservice für `add`, `update` und Import erfolgen, damit Buchung,
  Audit-Eintrag und Nachweis denselben Wert tragen. Der derzeitige
  `create_expense`-Service speichert das Eingabevorzeichen noch unverändert;
  eine Änderung nur in `decisions.py` würde einen falschen Nachweis erlauben.
  Bereits gespeicherte Ausgaben werden durch die Migration nicht stillschweigend
  umgeschrieben.
- Kategorie, RC-Typ, Steuermodus und die vom Service berechneten Steuerbeträge
  werden nach der Service-Berechnung verglichen. CLI-Schreibweise und interne
  Werte (`third-country`/`third_country`) werden zuerst normalisiert;
  Geldbeträge werden centgenau mit Dezimalarithmetik verglichen. Fehlende
  Vergleichsfelder gelten nicht stillschweigend als Bestätigung.
- Bei Abweichung bricht der Befehl mit `ValidationError`
  (`code="decision_payload_mismatch"`) ab und nennt die widersprüchlichen
  Felder und Werte.
- **Keine stillschweigende Vorrangregelung:** Die CLI überschreibt weder Flags noch
  Nachweisdaten heimlich.
- Bei ungültigem JSON oder Schemaverletzungen bricht die Transaktion ab; es wird
  weder eine Buchung noch ein Audit-Eintrag geschrieben.
- Bei einer als `user_confirmed` markierten Ad-hoc-Beurteilung ist eine
  zugehörige `user_confirmation`-Quelle Pflicht. Bei `pending_user_review`
  oder `rejected` darf `confirmation_source_id` nicht gesetzt sein.

### 3. Nachträgliche Prüfung einer Ad-hoc-Entscheidung

Eine spätere Bestätigung oder Ablehnung wird mit `euer update` und
`--decision-file` als neuer vollständiger Entscheidungsnachweis erfasst.
Dabei dürfen alle Buchungswerte gleich bleiben: Die Änderung betrifft dann
nur den Nachweis, erhält aber einen eigenen Audit-Eintrag. Eine Bestätigung
verweist auf eine neue `user_confirmation`-Quelle. Bei Ablehnung hält der
neue Nachweis `review_status: "rejected"` und die offene Korrektur fest;
falls die Buchung falsch ist, werden die Buchungswerte im selben `update`
berichtigt. Der Service validiert die Verweise und schreibt Audit und
Nachweis atomar. Es gibt keine separate Review-Tabelle und keinen
zusätzlichen Review-Befehl.

### 4. Bulk-Import (`import`)

- **JSONL (`--format jsonl`):** Jede Zeile darf ein optionales Objekt `"decision": { ... }`
  enthalten. Beim Import wird der Nachweis in derselben Transaktion mit der Buchung
  und dem Audit-Eintrag persistiert.
- **CSV (`--format csv`):** CSV unterstützt als flaches tabellarisches Format keine
  verschachtelten Nachweise. CSV-Importzeilen erhalten automatisch den Status
  `Nachweis nicht erfasst`.

---

## Verhalten bei Mutationen, Update, Undo und Delete

### 1. Fachlich relevante Änderungen (`update`)

Als **fachlich relevant** gelten Änderungen an folgenden Feldern:
`amount_eur`, `category_id`, `payment_date`, `invoice_date`, `rc_type`,
`vat_input`, `vat_output`, `vat_rate`, `vat_code`, `is_private_paid`.

- Erfolgt ein `update` an einem dieser Felder **ohne** `--decision` / `--decision-file`,
  wird die Änderung in `expenses` und `audit_log` gespeichert. Für diesen neuen
  Audit-Eintrag existiert jedoch kein Eintrag in `booking_decisions`.
- `euer explain` weist bei solchen Buchungen deutlich darauf hin:
  `⚠️ Warnung: Fachliche Buchungsdaten wurden nach der letzten Begründung geändert (Audit-Stand #105 != Nachweis-Stand #104). Begründung für aktuellen Stand fehlt.`
- Reine Notizänderungen behalten den fachlichen Nachweis. Eine Änderung der
  Belegreferenz erfordert dagegen die Prüfung der Quellenverweise und meldet
  bis dahin `Quelle des Nachweises geändert`.

### 2. Verhalten bei `delete` (Soft-Delete) und `undo`

- Ein Soft-Delete via `euer delete` belässt historische Nachweise unverändert in
  `booking_decisions`. `euer explain` zeigt den Datensatz mit dem Status
  `Im Papierkorb (gelöscht am ...)`.
- Ein [`undo_mutation()`](../euercli/services/undo.py)
  erzeugt einen regulären Audit-Eintrag (`DELETE` oder `UPDATE`) mit
  `undo_of_audit_id`. `euer explain` zeigt auf Wunsch die gesamte Kette der
  Audit- und Nachweisstände.

---

## Abfragebefehl `euer explain`

Zur menschlichen und maschinellen Prüfung wird der Befehl `euer explain` eingeführt:

```bash
euer explain <expense|income|transfer> <ID> [--json]
```

### 1. Standardausgabe (Terminal, menschenlesbar)

```text
Buchung #42 (Ausgabe): -18,50 € an Hosting-Anbieter (2025-03-16)
Kategorie: Laufende EDV-Kosten
ENTSCHEIDUNGSNACHWEIS (Audit #104, Schema v1.0)
Grundlage: ad_hoc (Thema: expense_category; Prüfung: offen)

1. QUELLEN:
   - Beleg: receipts/2025/hosting.pdf (Leistungsbeschreibung)
   - Konto: Kontoauszug_2025_03.csv (Zeile 142)

2. BEOBACHTUNGEN:
   [observed: receipt_1] Laufender Serverbetrieb
   [observed: bank_1]    Zahlbetrag: -18,50 EUR

3. ENTSCHEIDUNG:
   - Kategorie:  Laufende EDV-Kosten
   - Alternative: Übrige Betriebsausgaben
   - Begründung: Der Beleg beschreibt laufenden Serverbetrieb.
   - Prüfung:  Nutzerbestätigung ausstehend.

Historie: 1 Nachweis vorhanden (erstellt am 2025-03-16 14:22:05)
```

### 2. Maschinenlesbare Ausgabe (`--json`)

Gibt ein JSON-Objekt zurück, das die aktuelle Buchungszeile, den letzten
zugehörigen Nachweis sowie ein Array älterer Nachweisstände für diesen
Datensatz enthält. Für jedes Ad-hoc-Thema zeigt die Ausgabe den aktuellen
Prüfstatus und die früheren Nachweisstände. Offene und abgelehnte Themen
werden in Text- und JSON-Ausgabe ausdrücklich markiert; eine bloße
Nutzerbestätigung wird nicht als fachlich geprüfte Regel dargestellt.

---

## Umfang und Phasenplanung

### Phase 1: Nachweisspeicherung und Abfrage

- Tabelle `booking_decisions` via SQLite-Migration anlegen.
- [`log_audit()`](../euercli/db.py) so erweitern, dass die erzeugte
  `audit_id` zurückgegeben wird.
- Service `euercli/services/decisions.py` zur Schema- und
  Quellenvalidierung sowie zur transaktionalen Persistierung einführen.
- Das Vorzeichen neuer Ausgaben in den Buchungsservices für CLI-Erfassung,
  Updates und Importe vor der Nachweisprüfung einheitlich normalisieren.
- `--decision` und `--decision-file` in `add` und `update` integrieren;
  Entscheidungserneuerung ohne Änderung der Buchungswerte ermöglichen.
- `euer explain` samt JSON-Ausgabe und Markierung offener Ad-hoc-Themen
  implementieren.
- JSONL-Import um das optionale `"decision"`-Feld erweitern.

### Phase 2: Menschliche Prüfansicht (Integration mit Spec 014 und 021)

- Im HTML-Prüfbericht ([Spec 014](014-html-pruefbericht.md)) Quellen,
  Begründung und Unsicherheiten aufklappbar anzeigen. Offene oder abgelehnte
  Ad-hoc-Themen erscheinen in einer Prüfliste.
- Versionierte Exporte ([Spec 021](021-versionierte-exporte.md)) nennen im
  Manifest die Nachweis-Schema-Version und den Anteil der Buchungen mit
  vorhandenem Nachweis.

Der Regelkatalog, seine Veröffentlichung und die Suche nach angewandten
Regelversionen gehören vollständig zu [Spec 024](024-regelkatalog.md).

---

## Unsicherheit und Schutzregeln

- **Keine Scheinbegründungen:** Pflichtangaben dürfen nicht mit erfundenen Werten
  gefüllt werden. Widersprüchliche Angaben zwischen Beleg und Bankauszug müssen
  vom Agenten unter `open_questions` oder `uncertainties` erfasst werden.
- **Keine Scheingenauigkeit:** Ein numerischer Konfidenzwert (z. B. `confidence: 0.95`)
  ersetzt keine nachvollziehbare Begründung.
- **XSS-Schutz:** Begründungstexte, Quellenpfade und Locators sind Benutzereingaben
  und müssen bei der Ausgabe im HTML-Prüfbericht (Spec 014) strikt escaped werden.
- **Datenschutz:** Nachweise enthalten potenziell personenbezogene Daten. Es sind
  nur notwendige Auszüge zu speichern; lokale Dateipfade sind Dateikopien
  vorzuziehen.

---

## Akzeptanzfälle

1. **Atomare Transaktion:** Ein `add expense` mit `--decision-file`
   schreibt Buchung, `audit_log` und `booking_decisions` zusammen. Ein
   ungültiger Nachweis rollt alles zurück.
2. **Konsistenz:** `--amount -18.50` und `decision.amount_eur = -20.00`
   führen zu `ValidationError`; unterschiedliche Rechnungs- und
   Zahlungswährungen werden als eigene Beobachtungen behandelt.
   Sowohl `--amount 18.50` als auch `--amount -18.50` erzeugen bei einer
   Ausgabe `amount_eur = -18.50` in Buchung, Audit und Nachweis. Der gleiche
   Vergleich gilt beim Update und JSONL-Import einer Ausgabe.
3. **Eigenständiger Nutzen ohne Regeln:** Der Hosting-Fall lässt sich mit
   Quellen, Beobachtungen, `basis: "ad_hoc"`, `reasoning` und Status
   `pending_user_review` speichern und mit `euer explain` anzeigen. Es
   existiert weder ein Katalogeintrag noch eine künstliche Regel-ID.
4. **Steuerwirksamer Ad-hoc-Fall:** Der Agent klärt fehlende Tatsachen und
   legt eine tragfähige Behandlung dem Nutzer vor. Ohne erforderliche
   Bestätigung entsteht keine stillschweigend endgültige Steuerbuchung;
   fachliche Unsicherheit wird eskaliert.
5. **Fachliches Update ohne Nachweis:** Wird ein fachliches Buchungsfeld
   ohne neuen Nachweis geändert, meldet `euer explain`, dass die Begründung
   für den aktuellen Stand fehlt.
6. **Spätere Bestätigung oder Ablehnung:** `update --decision-file` erzeugt
   auch bei unveränderten Buchungswerten einen neuen auditierten Nachweis.
   Der alte bleibt lesbar; `explain --json` zeigt den aktuellen Status und
   frühere Nachweisstände.
7. **Altdaten und Import:** Bestehende Datenbanken bleiben nach der
   Migration nutzbar. Ältere Buchungen zeigen „Nachweis nicht erfasst“.
   JSONL-Importe mit `decision` legen den Nachweis konsistent an.

---

## Verwandte Specs

- [Spec 014: HTML-Prüfbericht](014-html-pruefbericht.md)
- [Spec 016: Agent-Safety und Guardrails](016-agent-safety-und-guardrails.md)
- [Spec 021: Versionierte Exporte](021-versionierte-exporte.md)
- [Spec 022: Versionierter Skill](022-skill-updates.md)
- [Spec 024: Versionierter Regelkatalog](024-regelkatalog.md)
