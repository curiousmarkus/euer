# Spec 023: Begründungen und Annahmen an Buchungen mit Audit-Historie

## Status

Offen

## Ziel und Produktentscheidung

Agent und Nutzer sollen später nachvollziehen können, **warum** eine Ausgabe,
Einnahme oder ein Privatvorgang so eingeordnet und behandelt wurde und **welche
Annahmen** der Entscheidung zugrunde lagen. Der Agent liefert die Erklärung
direkt bei der Buchung. Begründung, Annahmen und Gültigkeitsstatus stehen an der
Buchung; das bestehende `audit_log` dokumentiert deren Änderungen und frühere Stände.

Der Agent übernimmt die Buchhaltung weiter selbstständig nach dem bestehenden
Skill und den Validierungsregeln der Engine. Dieses Feature führt keinen neuen
Freigabeprozess ein. Eine fallbezogene Begründung genügt; eine Regel-ID oder
zusätzliche Nutzerbestätigung ist nicht erforderlich. Bisherige Rückfragen bei
fehlenden Angaben oder fachlich unklaren Fällen bleiben bestehen.

**Ohne aktuellen Entscheidungsnachweis ist die Buchung unvollständig.** Sie wird
trotzdem angelegt, fließt weiter in Auswertungen ein und erscheint in `euer incomplete list`.
Das gilt bewusst auch für Altdaten und bisherige Importe. Die Liste unterstützt
so auch die nachträgliche Prüfung der bisherigen Buchungen durch den Agenten.
Fehlende Buchungsdaten und fehlende Begründungen lassen sich getrennt filtern.

Die CLI prüft die Struktur der Erklärung, aber nicht Beleginhalte oder deren
fachliche Richtigkeit. Ein vorhandener Text ist kein Qualitätsbeweis. Der Nachweis
ersetzt keinen Beleg und beansprucht keine GoBD-Revisionssicherheit.

[Spec 024](024-regelkatalog.md) ergänzt später `--rule ID@VERSION`. Ein gültiger,
aktueller Regelverweis ersetzt dann die Freitextbegründung für die
Nachweisvollständigkeit; `--reasoning` bleibt ergänzend möglich. Vor Umsetzung
von Spec 024 ist eine Freitextbegründung der einzige Nachweisweg.
[Spec 028](028-tamper-evident-audit-chain.md) behandelt den Integritätsschutz; die
Nachweisfelder und späteren Regelzuordnungen müssen in dessen Prüfung von
Buchungszustand und Audit-Historie einfließen.

## Erfassung über Buchungsparameter

Für die bestehenden `add`- und `update`-Befehle für Ausgaben, Einnahmen und
Privatvorgänge werden folgende Flags ergänzt. Die heutigen Command-Namen bleiben
bestehen (bei `add` etwa `private-deposit` und `private-withdrawal`).

| Flag | Vertrag |
|------|---------|
| `--reasoning TEXT` | Fallbezogene Begründung von Kategorie und Behandlung. Äußere Leerzeichen werden entfernt; explizit leerer Text ist ein Fehler. |
| `--assumption TEXT` | Entscheidungsrelevante Annahme; mehrfach verwendbar. Jede Angabe wird außen getrimmt und muss nicht leer sein. |
| `--clear-assumptions` | Nur bei `update`: bisherige Annahmen ausdrücklich durch `[]` ersetzen. Nicht mit `--assumption` kombinierbar. |

```bash
euer add expense --date 2025-03-16 --vendor "Hosting-Anbieter" \
  --amount -18.50 --category "Laufende EDV-Kosten" \
  --receipt "receipts/2025/hosting.pdf" \
  --reasoning "Laufender Serverbetrieb für die betriebliche Website; daher laufende EDV-Kosten. Im konfigurierten Kleinunternehmermodus ohne Vorsteuerabzug." \
  --assumption "Ausschließlich betriebliche Nutzung."

euer update expense 42 \
  --reasoning "Die betriebliche Nutzung wurde bei der Belegprüfung nachvollzogen." \
  --clear-assumptions
```

- Bei `add` sind die Flags technisch optional. Ohne Begründung wird vor Spec 024
  kein Nachweis erzeugt; die Buchung bleibt wegen `reasoning` unvollständig.
  Nach Spec 024 genügt alternativ ein gültiger Regelverweis. Nicht angegebene
  Annahmen bedeuten bei einem neuen Nachweis `[]`.
- Bei `update` ohne Nachweisflags wird kein neuer Nachweis erzeugt. Die bestehende
  Begründung bleibt je nach geänderten Buchungsfeldern aktuell oder wird veraltet.
- `update --reasoning` erzeugt einen neuen Nachweis, auch ohne Wertänderung. Ohne
  Annahmenflags werden die Annahmen des bisher wirksamen Nachweises übernommen;
  fehlt ein solcher Nachweis, ist die Liste leer. Der Agent prüft bei Korrekturen,
  ob die bisherigen Annahmen weiterhin zutreffen, und ersetzt oder entfernt sie
  gegebenenfalls ausdrücklich.
- Angegebene `--assumption`-Flags ersetzen beim Update die gesamte Annahmenliste;
  sie hängen nicht automatisch an die alte Liste an.
- Annahmenflags erfordern im selben Aufruf eine nicht leere Begründung oder,
  nach Umsetzung von Spec 024, einen gültigen Regelverweis. Allein Annahmen
  hinzuzufügen oder zu entfernen darf keinen veralteten Nachweis erneuern.
- Eine Begründung erläutert den vollständigen aktuellen Stand einschließlich der
  steuerlichen Behandlung, soweit relevant. Annahmen müssen nicht erfunden werden.
  Keine zusätzlichen Annahmen ist ein zulässiger Zustand.

Quellen, Fundstellen, Dossierbezüge und verbleibende Unsicherheiten stehen bei
Bedarf im Freitext von `--reasoning`; angenommene Voraussetzungen stehen unter
`--assumption`. Dafür gibt es keine separaten Quellenobjekte oder Eingabedateien.

Der Skill verlangt bei neuen Buchungen und fachlichen Korrekturen kurze,
fallbezogene Begründungen. Sobald Spec 024 verfügbar ist, genügt stattdessen ein
passender versionierter Regelverweis; fallbezogener Freitext bleibt optional.
Der Agent trennt entnommene Angaben von angenommenen Voraussetzungen und nutzt
`incomplete` zur Nacharbeit. Allgemeine Platzhalter wie
„Betriebsausgabe“ oder nachträglich erfundene ursprüngliche Gründe erfüllen diese
Agentenanweisung nicht. Nachträgliche Begründungen erläutern die aktuelle Prüfung
und werden mit ihrem tatsächlichen Erfassungszeitpunkt dokumentiert.

## Import

Die Erfassung erfolgt über die Buchungsparameter, ohne separate Nachweis-JSONs,
`--decision` oder `--decision-file`. Gültigkeitsstatus und Audit-Metadaten werden
von der Engine erzeugt und sind keine zusätzlichen Importfelder.

JSONL-Importzeilen dürfen die optionalen Buchungsfelder `reasoning` und
`assumptions` enthalten:

```json
{
  "type": "expense",
  "date": "2025-03-16",
  "party": "Hosting-Anbieter",
  "amount_eur": -18.50,
  "category": "Laufende EDV-Kosten",
  "reasoning": "Laufender Serverbetrieb für die betriebliche Website; daher laufende EDV-Kosten.",
  "assumptions": ["Ausschließlich betriebliche Nutzung."]
}
```

`reasoning` ist eine nicht leere Zeichenkette, `assumptions` eine Liste nicht leerer
Zeichenketten; eine fehlende Liste bedeutet `[]`. Annahmen allein erzeugen keinen
Nachweis und erfordern eine Begründung, beziehungsweise nach Spec 024 einen im
selben Datensatz gelieferten Regelverweis. Texte werden außen getrimmt.
`null`, falsche Typen und explizit leere Texte in gelieferten Nachweisfeldern sind
Fehler. JSON mit doppelten Schlüsseln oder nicht endlichen Zahlen wird abgewiesen.

CSV unterstützt das einfache Feld `reasoning`. Eine leere CSV-Zelle gilt als
fehlende Erklärung. Strukturierte Annahmen werden nicht aus CSV gelesen.
`decision`, `sources`, `observations`, `uncertainties` und andere gesonderte
Nachweisobjekte sind keine Importfelder; sie werden nicht still ignoriert.
Ohne Erklärung bleibt die importierte Buchung wegen `reasoning` unvollständig;
Spec 024 ergänzt entsprechend Regelverweise als alternative Nachweisgrundlage.

Importe behalten ihre Atomarität und Duplikatprüfung. Gelieferte Nachweisfelder
werden auch bei Duplikaten validiert. Übersprungene gültige Duplikate ergänzen
keine Begründung an vorhandenen Buchungen; dafür dient `update`. Bei einem Fehler
in späteren Zeilen wird der gesamte Lauf zurückgerollt; `--dry-run` persistiert
nichts.

## Speicherung an der Buchung und Audit-Historie

Eine versionierte Migration ergänzt **alle drei Buchungstabellen** `expenses`,
`income` und `private_transfers` um dieselben Felder:

| Feld | Inhalt |
|------|--------|
| `reasoning` | Freitext als `TEXT`, optional (`NULL` ohne Freitext). |
| `assumptions` | `TEXT` mit JSON-Liste von Zeichenketten, standardmäßig `[]`. |
| `decision_status` | `current`, `missing`, `stale` oder `source_changed`. |
| `decision_status_reasons` | `TEXT` mit JSON-Liste der Ursachen aus dem unten beschriebenen Statusvertrag. |

Beispiel für `expenses`; die Migration führt die gleichen Erweiterungen auch
für `income` und `private_transfers` aus:

```sql
ALTER TABLE expenses ADD COLUMN reasoning TEXT DEFAULT NULL;
ALTER TABLE expenses ADD COLUMN assumptions TEXT NOT NULL DEFAULT '[]';
ALTER TABLE expenses ADD COLUMN decision_status TEXT NOT NULL DEFAULT 'missing'
    CHECK (decision_status IN ('current', 'missing', 'stale', 'source_changed'));
ALTER TABLE expenses ADD COLUMN decision_status_reasons TEXT NOT NULL
    DEFAULT '["reasoning_missing"]';
```

Die JSON-Listen sind einzelne fachliche Felder, kein umfassendes Nachweisobjekt.
Es gibt weder eine separate `booking_decisions`-Tabelle noch eine zusätzliche
`decision_data`-Spalte im Audit. Aktuelle Begründung, Annahmen und Gültigkeit werden
unmittelbar aus der Buchung gelesen; dafür wird keine Audit-Historie rekonstruiert.
Spec 024 ergänzt die aktuellen Regelzuordnungen als eigene Relation zur Buchung.

Das bestehende Audit protokolliert diese Felder wie andere Buchungswerte in
`old_data` und `new_data`. Die Services müssen dort vollständige Vorher-/Nachher-
Stände einschließlich der Nachweisfelder sichern; bisher manuell zusammengestellte
Audit-Dictionaries werden entsprechend ergänzt. Die historische Begründung
bleibt dadurch mit dem damaligen Buchungsstand verbunden, ohne einen zusätzlichen
vollständigen Buchungssnapshot in einem Nachweisobjekt zu speichern.

Für die historische Einordnung enthält der jeweilige Audit-Stand zusätzlich
Engine-Metadaten unter `_context`: Software-/Skill-Versionen, angewandter
Steuermodus sowie relevante aufgelöste Kategorienbezeichnung und `eur_key`.
Die Belegreferenz `receipt_name` gehört bereits zu den Buchungswerten. Metadaten
werden von der Engine ergänzt und nicht als Buchungsspalten durch Undo restauriert.
`_context.decision_updated` kennzeichnet eine ausdrücklich neu gelieferte
Nachweisgrundlage, auch bei identischem Text. Audit-ID, Zeitstempel und `user`
benennen Ereignis und Erfassung; weitere Nachweis-IDs oder Eingabeparameter entfallen.

- Buchungsservice, Nachweisfelder und Audit werden atomar geschrieben. Das gilt
  auch für Privatvorgänge und Imports; ungültige Angaben erzeugen keine Teilmutation.
- Ein Update nur der Erklärung erzeugt einen neuen Audit-Eintrag. Frühere
  Begründungen und Annahmen werden im Audit nicht nachträglich überschrieben.
- Ein Update ohne Nachweisflags behält `reasoning` und `assumptions`. Fachlich
  relevante Änderungen markieren einen vorhandenen Nachweis als veraltet, statt
  den Text zu löschen. Eine reine Notizänderung behält auch dessen Status.
- Eine neue Nachweisgrundlage setzt `decision_status = current` und leert die
  Statusursachen. Ohne Nachweis bleibt der Status `missing`; Datenänderungen
  erzeugen aus einem fehlenden Nachweis keinen veralteten vorhandenen Nachweis.
- Die Migration setzt für alle Altdaten `reasoning = NULL`, `assumptions = []`,
  `decision_status = missing` und `decision_status_reasons = ["reasoning_missing"]`.
  Sie erfindet keine Begründungen und schreibt vorhandene Buchungswerte oder
  Audit-Ereignisse nicht um. Historische Ereignisse ohne diese Felder bleiben lesbar.
- Neue beziehungsweise explizit geänderte Beträge werden vor Hash,
  Steuerberechnung und Audit im Service normalisiert: Ausgaben zu
  `-abs(amount_eur)`, Einnahmen zu `abs(amount_eur)`. Bestehende Beträge werden
  durch Migration, Notizänderung oder Nachweisergänzung nicht umgeschrieben.
- Soft-Delete und Purge behalten die Audit-Historie samt Nachweisfeldern. Diese
  bleiben über `record_uuid` zugeordnet. Eine historische ID-Abfrage nach Purge
  ist kein Versprechen der ersten Version.

## Gültigkeit, Korrekturen und Undo

`euer explain <expense|income|transfer> ID [--json]` zeigt aktuellen Buchungsstand,
Begründung einschließlich darin genannter Quellen, Annahmen, Audit-Bezug und
frühere Nachweise. Mit Spec 024 werden zusätzlich angewandte Regelversionen
aufgelöst, auch bei Nachweisen ohne Freitext.
Die bestehende Audit-Ausgabe zeigt Änderungen an Begründungen, Annahmen und Status.
Bei veralteten Nachweisen zeigt `explain` weiterhin die an der Buchung erhaltene
Erklärung mit Veraltungskennzeichen und den damaligen Stand aus dem Audit.

Die JSON-Ausgabe von `explain` enthält `booking`, `status`, `status_reasons`,
`latest_decision`, `history` und `audit_history`. Jeder Nachweis ist über seine
`audit_id` des Erfassungs- beziehungsweise Erneuerungsereignisses adressiert; eine
separate Nachweis-ID entfällt. Der aktuelle Zustand stammt aus der Buchung,
historische Nachweise und zugehörige Buchungsstände aus dem Audit. Die Historien werden
chronologisch ausgegeben, ohne den aktuellen Nachweis in `history` zu duplizieren.

| Nachweisstatus | Bedeutung | Folge für `incomplete` |
|----------------|-----------|-----------------------|
| `current` | Begründung passt zum aktuellen fachlichen Stand. | Keine Begründungslücke. |
| `missing` | Kein wirksamer Nachweis vorhanden, `latest_decision: null`. | `reasoning` fehlt. |
| `stale` | Fachliche Werte wurden ohne neue Erklärung geändert. | `reasoning` fehlt für den aktuellen Stand; alte Erklärung und Annahmen bleiben an der Buchung sichtbar und im Audit historisch lesbar. |
| `source_changed` | Belegreferenz wurde ohne neue Erklärung geändert. | `reasoning` muss für die geänderte Quelle erneuert werden. |

`status_reasons` nennt die Ursachen `reasoning_missing`, `fields_modified` und/oder
`receipt_modified`. Bei gleichzeitig fachlicher Änderung und Belegwechsel hat
`stale` Vorrang; Textausgabe und JSON nennen trotzdem beide Ursachen. Die Engine
speichert Status und Ursachen gemeinsam an der Buchung. Weitere Änderungen ohne
neuen Nachweis behalten bisherige Veraltungsursachen und ergänzen neue. Zurückändern
auf frühere Werte erneuert den Nachweis nicht automatisch.

Status und Ursachen werden ausschließlich von der Engine gesetzt: `current` hat
`[]`, `missing` hat `["reasoning_missing"]`, `stale` enthält `fields_modified`
und gegebenenfalls `receipt_modified`, `source_changed` hat `["receipt_modified"]`.
Die Ursachenliste enthält keine Duplikate. Ein Notizupdate erneuert auch einen
bereits veralteten Nachweis nicht.

Als fachlich relevant gelten tatsächlich geänderte Werte von Betrag, Kategorie,
Zahlungs-/Rechnungsdatum, Gegenpartei, Rechnungsnummer, Zahlungs-/Buchungskonto,
Fremdwährungsangabe, RC-/USt-/Vorsteuerfeldern, Privatklassifikation und
Bewirtungsfeldern. Für Privatvorgänge zählen Datum, Typ, Betrag, Beschreibung und
Bezug zur Ausgabe. Diese Feldlisten und die Statusübergänge liegen zentral im
Service Layer; `explain` und `incomplete` verwenden denselben gespeicherten Zustand.
Eine reine Notizänderung, Hash- oder Zeitstempeländerung veraltet den Nachweis nicht.

Soft-Delete und Restore ändern allein den Löschstatus, nicht die fachliche Gültigkeit.
Gelöschte Buchungen erscheinen weiterhin nicht in `incomplete`.
Undo nutzt `old_data` des zurückgesetzten Audit-Ereignisses und stellt Buchungswerte,
Begründung, Annahmen, Status und Ursachen zusammen wieder her. Auch Undo einer reinen
Nachweisänderung stellt den vorherigen Stand wieder her, einschließlich einer
Veraltungsmarkierung oder fehlenden Erklärung. Bei Ereignissen aus der Zeit vor
der Migration werden fehlende Nachweisfelder als `NULL`, `[]`, `missing` und
`["reasoning_missing"]` restauriert. Das neue Audit-Ereignis nennt wie bisher
`undo_of_audit_id`; Kontextmetadaten dienen der Anzeige, nicht als zu restaurierende
Buchungswerte. Es wird weder eine neue Agentenbegründung erfunden noch ein
historischer Nachweis gelöscht. Ein gewöhnliches Rückändern von Buchungswerten
ohne Undo oder neue Erklärung erneuert dagegen keine zwischenzeitlich veraltete
Begründung.

## Vollständigkeit und Filter

`incomplete` wird weiterhin aus dem aktuellen Zustand berechnet. Neu ist
`reasoning` als fehlendes Feld, wenn der Nachweis nicht `current` ist. Fehlende
Annahmen allein sind keine Lücke; eine leere Liste ist gültig. Nach Umsetzung von
Spec 024 ist ein aktueller, gültiger Regelverweis ebenfalls ausreichend. Dann
fehlt `reasoning` nur, wenn weder Freitext noch Regelverweis einen aktuellen
Nachweis liefern. Die vorhandenen Filter behalten ihre Namen und unterscheiden
weiter Buchungsdatenlücken von Nachweislücken.

Bestehende Prüfungen auf Buchungsdaten wie Beleg, Datum, Kategorie, Konto und
Steuerangaben bleiben bestehen. Unvollständige Buchungen werden weder aus
Auswertungen entfernt noch allein wegen fehlender Begründung beim Export gesperrt.
Einträge ohne Erklärung aus Altdaten und Importen werden ohne Stichtagsausnahme
angezeigt. Der Agent prüft und begründet sie nachträglich, ohne die Erklärung als
ursprüngliche historische Entscheidung auszugeben.

Neuer Filter für den bestehenden Befehl:

```bash
euer incomplete list --missing data
euer incomplete list --missing reasoning
euer incomplete list --missing reasoning-only
```

| `--missing` | Bedeutung |
|-------------|-----------|
| `all` (Default) | Alle Buchungen mit fehlenden Daten oder fehlender aktueller Begründung. |
| `data` | Mindestens eine Lücke in den bisherigen Buchungsdaten; eine zusätzliche Begründungslücke ist zulässig. |
| `reasoning` | Fehlende, veraltete oder auf eine geänderte Quelle bezogene Begründung; zusätzliche Datenlücken sind zulässig. |
| `reasoning-only` | Begründungslücke und sonst vollständige Buchungsdaten. |

Die Filter `data` und `reasoning` überschneiden sich bei Buchungen mit beiden
Arten von Lücken. Eine Buchung erscheint pro Ausgabe trotzdem nur einmal.
`--year`, `--type` und Ausgabeformat werden mit dem neuen Filter kombiniert.
Die bisherigen Typen `expense` und `income` bleiben bestehen; `transfer` wird
für die Begründungsprüfung der Privatvorgänge ergänzt. Hier werden keine neuen
fachlichen Vollständigkeitsregeln für Privatvorgänge eingeführt: `data` trifft
auf sie in dieser Version nicht zu, fehlende Erklärung auf `reasoning-only`.

Terminal- und CSV-Ausgabe nennen alle fehlenden Felder des ausgewählten Datensatzes,
auch beim Filtern nur nach einer Lückenart. `reasoning` wird als „Begründung fehlt“
oder mit dem zutreffenden Hinweis auf Veraltung beziehungsweise geänderte Quelle
angezeigt. Nach Spec 024 heißt die fehlende Grundlage bei Bedarf „Begründung
oder Regelverweis fehlt“; die interne Feldkennung bleibt `reasoning`. Der Default
zeigt auch Privatvorgänge ohne gültigen Nachweis.

## Umfang und Abnahme

Die erste Umsetzung umfasst die Migration aller drei Buchungstabellen,
Buchungs- und Audit-Services, direkte Flags, Import,
`explain`, `incomplete` samt Filter, Agenten-Skill,
Nutzerdokumentation und Tests. Das DATEV-Add-on muss den neuen Schemastand weiter
lesen können; Schemaerkennung, Einnahmenkonten und Kompatibilitätstests werden
als Folgeanpassung mit geprüft. Der Filter verändert keine Exportregeln.

| Fall | Erwartetes Verhalten | Prüfebene |
|------|----------------------|-----------|
| Ausgabe, Einnahme, Privatvorgang mit direkten Flags | Nachweisfelder an der Buchung und vollständiger Audit-Stand atomar gespeichert, ohne Datei | Service und CLI |
| Weder Begründung noch verfügbarer Regelverweis | Buchung möglich, in Auswertung enthalten und bei `incomplete` sichtbar | CLI und Bericht/Export |
| Explizit leerer Text, Annahmen ohne neue Nachweisgrundlage, nicht unterstützte Nachweisobjekte oder ungültiger Import | Verständlicher Fehler ohne Teilmutation | Service und CLI |
| Annahmen fehlen, ersetzen, erhalten oder ausdrücklich leeren | Create-/Update-Vertrag eingehalten; keine erfundenen Annahmen | Service und CLI |
| Altdaten und Migration | Daten und Audit-Historie unverändert; Erklärungslücken ohne Ausnahme sichtbar | Migration und CLI |
| Fachliches Update, Notizänderung, Belegwechsel | Text und Annahmen bleiben erhalten; Markierung und Ursachen in Buchung, `explain` und `incomplete` stimmen überein, auch für Privatvorgänge | Service und CLI |
| Neuer Nachweis ohne Wertänderung | Neuer Audit-Eintrag; frühere Erklärung bleibt erhalten | Service und CLI |
| Undo, Soft-Delete, Restore | Nachweisfelder und Status atomar restauriert, einschließlich alter Ereignisse vor der Migration; Historie bleibt erhalten | CLI |
| Nur Datenlücke, nur Begründungslücke, beide Lücken, vollständige Buchung | Filtermatrix, überschneidungsfreie Ausgabe je Lauf, kombinierte Typ-/Jahresfilter und CSV korrekt | CLI |
| JSONL/CSV mit und ohne Begründung, Duplikate, Dry-Run, Fehler in späterer Zeile | Nachweise konsistent; kein unbeabsichtigtes Ergänzen; vollständiger Rollback | CLI |
| Neuer expliziter Betrag mit beiden Vorzeichen | Negatives Vorzeichen bei Ausgaben, positives bei Einnahmen in Buchung und Audit | Service, CLI und Import |
| Nach Umsetzung von Spec 024: Regelverweis ohne Freitext | Gültiger aktueller Verweis genügt als Nachweis; ungültige Verweise erzeugen Fehler ohne Teilmutation | Paketintegration |
| Neuer Core mit DATEV-Add-on | Neuer Schemastand lesbar; Einnahmenkonten erhalten; unbekannte Schemata weiter abgewiesen | Paketintegration |

Konkrete Testdateien und Methoden werden bei Implementierung zugeordnet. Status
bleibt bis zum Abschluss von Code, Tests und Dokumentation `Offen`. Skill-Änderungen
erhalten eine neue Skill-Version. Release Notes nennen Migration, Skill-Update und
die neue Vollständigkeitsprüfung einschließlich Altdaten und Filtern.

Spätere Integrationen:

- [Spec 014](014-html-pruefbericht.md): Begründungen, Annahmen und Vollständigkeit
  in der HTML-Prüfansicht; Texte und Pfade strikt escapen.
- [Spec 021](021-versionierte-exporte.md): Nachweisabdeckung im Exportmanifest.
- [Spec 024](024-regelkatalog.md): Aktuelle Regelzuordnungen an der Buchung;
  frühere Zuordnungen im Audit.
- [Spec 028](028-tamper-evident-audit-chain.md): Nachweisfelder, Kontextmetadaten
  und Regelzuordnungen in Zustands- und Audit-Integritätsprüfung einbeziehen.
