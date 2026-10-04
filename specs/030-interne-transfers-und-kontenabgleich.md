# Spec 030: Kontobewegungen, Privatkonten und Kontenabgleich

## Status

Offen

Diese Spec enthält die bisherigen Anforderungen aus Spec 030 und Spec 031.
[Spec 031](031-betriebliche-einnahmen-auf-privatkonten.md) bleibt ausschließlich
als Verweis erhalten und ist keine separat zu implementierende Anforderung.

## Ziel, Zuständigkeiten und gemeinsamer Release

Eine gemeinsame Anforderung umfasst interne Transfers, Provider-Auszahlungen,
betriebliche Einnahmen auf Privatkonten und die dazugehörigen Konten-/Privatübersichten.
Die Funktionsbereiche A und B erhalten getrennte Abnahmefälle; ihre fachlichen
Regeln und ihr Migrations-/Releasevertrag gelten gemeinsam.

Core definiert und implementiert Datenmodell, Erfassung, Validierung, Audit,
Import, Klassifikation und Kontenabgleich. Die
[DATEV Spec 002](../../euer-datev/specs/002-kontobewegungen-und-privatkonten.md)
definiert Reader, Exportmapping, Exportvalidierung, Berichte und Artefaktprüfung.
Der fachliche Vertrag steht einmal in dieser Core-Spec; die DATEV-Spec konkretisiert
seine Umsetzung. Änderungen an gemeinsamen Feldern und Falltabellen werden
in beiden Repositories abgestimmt.

Parallelentwicklung ist möglich, sobald Feldnamen und die neue vollständige
Migrationsfolge in beiden Specs identisch festgehalten sind. Gemeinsame Freigabe
erst nach End-to-End-Abnahme. Versionsnummern werden bei Release-Vorbereitung
festgelegt; eine Implementierungsreihenfolge ersetzt keine Release-Abnahme.

## Gemeinsame Abgrenzung


Interne Transfers bilden Geldbewegungen zwischen zwei betrieblichen Eigenkonten
ab. Sie verändern weder EÜR-Ergebnis noch UStVA. Provider-Erlöse und Gebühren
bleiben eigenständige Einnahmen/Ausgaben; eine Auszahlung ist kein neuer Erlös.
Der Kontenabgleich zeigt tatsächliche Bewegungen und offene Transferseiten.

Für alle Funktionsbereiche gilt dieselbe Abgrenzung:

| Bewegung | Core-Erfassung | Privatwirkung | DATEV-Gegenkonto |
| --- | --- | --- | --- |
| Betrieb → Betrieb | Ein `internal_transfer` mit zwei beobachtbaren Seiten | Keine | Geldtransit, je beobachteter Seite |
| Privat → Betrieb | `private_transfers`, Typ `deposit`, betriebliches Zielkonto | Einlage einmal | Privateinlagen, kein Geldtransit |
| Betrieb → Privat | `private_transfers`, Typ `withdrawal`, betriebliches Quellkonto | Entnahme einmal | Privatentnahmen, kein Geldtransit |
| Kunde → Privat | `income` gemäß Abschnitt B | Abgeleitete Entnahme, kein zusätzlicher Privatvorgang | Privatentnahmen gegen Erlös |
| Privat → Privat | Kein interner betrieblicher Transfer | Keine zusätzliche Wirkung | Kein Export aus dieser Bewegung |

`add transfer` und Transfer-Import weisen Privatkonten an beiden Endpunkten ab
und nennen den passenden Einlagen-/Entnahmebefehl. Physische Salden privater
Bankkonten werden nicht berechnet. Keine automatische Erkennung einer Auszahlung
als Einnahme, keine automatische Gebührenanlage, kein Fremdwährungstransit.

## A: Interne Transfers, Gebühren und Kontenabgleich

### Daten- und Validierungsvertrag

Neue Tabelle `internal_transfers`; die konkrete SQL-Migration ist ein technischer
Vorschlag und erhält erst nach Prüfung der Registry eine freie Nummer.

| Feld | Verbindliches Verhalten |
| --- | --- |
| `id`, `uuid` | Stabile Identität; Update, Wiederimport und zweite Beobachtung erhalten sie |
| `source_account`, `target_account` | Pflicht; trimmen/kleinschreiben wie Spec 029; verschieden; keine Privat-/reservierten Privatkonten; keine stillen Konto-Defaults |
| `amount_eur` | Endlicher EUR-Betrag > 0, Centgenauigkeit; tatsächlich überwiesener Nettobetrag; nicht Bruttoumsatz vor Gebühren |
| `source_date`, `target_date` | ISO-Datum der beobachteten Abbuchung/Gutschrift; mindestens eines gesetzt; fehlend/NULL/leer heißt unbekannt, niemals Datum der anderen Seite übernehmen |
| `reference` | Optional, getrimmt; leer → NULL; exakte externe Transferreferenz, keine Ähnlichkeitssuche |
| `fee_expense_id` | Optionaler Verweis auf eine aktive, bezahlte Gebührenausgabe auf dem Quellkonto; siehe Gebührenvertrag |
| `notes` | Optional; kein Identitäts- oder Zuordnungsschlüssel |
| `created_at`, `deleted_at` | Bestehende Create-/Soft-Delete-Konventionen |

Taggleicher Eingang wird ausdrücklich mit beiden gleichen Daten erfasst.
Die Zielwertstellung darf vor der Quellwertstellung liegen; solche beobachteten
Daten bleiben erhalten und werden zur Prüfung angezeigt, nicht verschoben.
Eine unbekannte Seite ist zulässig und erscheint als `pending`; zwei bekannte
Seiten ergeben `complete`. Diese Zustände werden aus den Daten abgeleitet.
Beträge dürfen nicht durch `abs()` aus widersprüchlichen Angaben repariert werden.

`private_transfers` erhält ein optionales betriebliches `account`, damit direkte
Einlagen/Entnahmen in einem konkreten Kontenabgleich zugeordnet werden können.
Bestehende `add private-deposit`, `add private-withdrawal` und
`update private-transfer` erhalten `--account`; Update zusätzlich
`--clear-account`. Altbestand bleibt NULL. Ein fehlendes Konto wird im
Kontenabgleich als Zuordnungslücke angezeigt, nicht einem Default zugeschlagen.
Die bestehenden Privatübersichten und DATEV-Fallbacks bleiben für Altbestand
kompatibel; ein explizites Konto wird im DATEV-Export regulär aufgelöst.

### Gebühren und Lebenszyklus

Beispiel: +1.000 EUR Einnahme auf Stripe, -29 EUR Gebührenausgabe auf Stripe,
971 EUR Transfer nach Giro. Stripe-Bewegung: `1000 + (-29) - 971 = 0`.
Die Gebühr wird ausschließlich über die Ausgabe erfolgswirksam.

`--fee-expense-id ID` verknüpft eine bereits separat erfasste Gebührenausgabe.
Es gibt kein `--fee`, keine implizite Ausgabe und kein redundantes `fee_eur`.
Eine Ausgabe darf höchstens einem aktiven Transfer zugeordnet sein; bestehende
Betrags-/Steuerregeln der Ausgaben gelten unverändert. Falsches Konto, unbezahlte,
gelöschte oder bereits verknüpfte Ausgabe: Fehler vor Mutation.

Update von Quellkonto oder Gebührenverweis validiert die Zuordnung erneut.
Transfer-Delete löscht die Gebührenausgabe nicht; Restore prüft die Zuordnung
erneut. Löschen oder Ändern einer verknüpften Ausgabe darf keine ungültige aktive
Verknüpfung hinterlassen: abweisen, bis sie explizit gelöst wurde.
Alle Create/Update/Delete/Restore/Purge-/Undo-Wege einschließlich Audit laufen
über Services; Änderungen und Audit sind atomar. Fehler im Import rollen den
vollständigen Batch zurück, Dry-Run verändert weder Daten noch Audit.

### CLI und Kontenabgleich

Neue Commands (noch nicht implementiert):

```bash
euer add transfer --from stripe --to giro --amount 971.00 \
  --date 2026-03-01 --target-date 2026-03-03 \
  --reference po_12345 --fee-expense-id 42
# Auch nur --target-date ist zulässig, wenn zuerst der Eingang bekannt ist.
euer list transfers --year 2026 --account giro --format csv
euer update transfer 1 --target-date 2026-03-03
euer delete transfer 1
```

`--date` bezeichnet `source_date`. Update unterstützt beide Konten, Betrag,
beide Daten, Referenz, Notiz und Gebührenverweis; optionale Felder erhalten
explizite `--clear-*`-Optionen. Beide Daten zugleich löschen ist unzulässig.
Restore/Undo werden in die vorhandenen Commands integriert; `--purge` verwendet
die bestehenden Schutzregeln und entfernt niemals die Gebührenausgabe.
Jahresfilter bei Transfers: Datensatz anzeigen, wenn mindestens eine bekannte
Seite in das Jahr fällt; Pending-Fälle gesondert zeigen. Nicht auf ein einziges
Ersatzdatum reduzieren. CSV enthält beide Konten/Daten, Betrag, Status und UUID.

```bash
euer reconcile account giro --year 2026 --month 3 \
  --opening-balance 1000.00 --closing-balance 1971.00 --format json
```

`--year` ist erforderlich, `--month` optional (1–12). Salden beziehen sich auf
Beginn/Ende des gewählten Zeitraums. Beide Salden zusammen oder beide weglassen;
endliche, auch negative Werte zulässig. Ohne Salden nur Bewegungsübersicht,
niemals behaupten, das Konto sei abgeglichen.

Verbindliche Berechnung mit gespeicherten Vorzeichen:

```text
Bewegung = SUM(bezahlte income.amount_eur) + SUM(bezahlte expenses.amount_eur)
         + SUM(Transferzugänge) - SUM(Transferabgänge)
         + SUM(direkte Einlagen) - SUM(direkte Entnahmen)
Erwarteter Endsaldo = Anfangssaldo + Bewegung
Abweichung = Tatsächlicher Endsaldo - Erwarteter Endsaldo
```

Nur aktive Datensätze; Einnahmen/Ausgaben nur mit `payment_date` und passendem
Konto. Rückzahlungen und Einnahmekorrekturen behalten ihr Vorzeichen.
Privatwirkungen aus Abschnitt B und privat bezahlte Ausgaben sind keine zusätzliche
Bewegung auf einem Betriebskonto. Direkte Privatvorgänge zählen nur mit passendem
betrieblichem `account`. Jede Transferseite zählt ausschließlich an ihrem Datum.
Gebühren werden nicht zusätzlich aus der Verknüpfung addiert.

Ausgabe (Tabelle/JSON) enthält Zeitraum, Komponenten, bekannte Bewegungen,
Pending-Transfers, Zuordnungslücken und gegebenenfalls Salden/Abweichung.
Status `matched` nur bei Cent-Abweichung 0 und ohne Zuordnungslücken;
`mismatch` bei Abweichung, `needs_review` bei Zuordnungslücken, `movements_only`
ohne Salden. Unzugeordnete bezahlte Datensätze im Zeitraum werden mit IDs genannt;
Pending-Seiten erscheinen auch periodenübergreifend. Keine Mutation.

### Import und Wiederimport

CSV/JSONL akzeptiert explizit `type=transfer` (Alias `Typ=Umbuchung`).
Pflicht: `amount_eur`, Quellkonto (`source_account`, Alias `account`),
`target_account` und mindestens eines von `source_date` (Alias `date`) oder
`target_date`. Beide Konten werden immer in Überweisungsrichtung geliefert;
die empfangende Kontoauszugsseite darf sie nicht vertauschen. Optional:
`reference`, `transfer_id`, `uuid`, `fee_expense_id`, `notes`. Transferimporte brauchen
keine `party`, Kategorie oder USt-Felder; widersprüchliche Erlös-/Steuerfelder
werden abgewiesen. Direkte Privatvorgänge bleiben die bestehenden Commands.

Die zweite Kontoauszugsseite ergänzt denselben Transfer über `transfer_id`
oder eine eindeutige Kombination aus normalisiertem Kontopaar und exakter
`reference`. Eine aktive Referenz je Kontopaar bezeichnet genau einen Transfer;
unterschiedlicher Betrag oder widersprüchliches bereits bekanntes Datum erzeugt
einen Konflikt, keine zweite Buchung. Reimport gleicher bekannter Angaben ist
wirkungslos, ergänzt keine Gebühren und erzeugt keinen zusätzlichen Audit-Eintrag.
Gelöschte Treffer werden nicht automatisch restauriert.

Ohne ID/Referenz nur exakte Wiederholung sämtlicher bekannter Identitätsfelder
überspringen. Eine möglicherweise passende Gegenseite mit fehlenden Daten nicht
heuristisch zusammenführen oder als zweiten Transfer buchen: mit Kandidaten-IDs
abbrechen und explizite Zuordnung verlangen. Gleichartige Transfers können
explizit getrennt erfasst werden; kein globales Duplikatflag überschreibt
Referenz-/Betragskonflikte oder fachliche Validierung. Export/Wiederimport
verwendet UUID als stabile Transferidentität und weist widersprüchliche IDs ab.
Numerische IDs sind nur innerhalb derselben Datenbank gültig; ein Export in
eine andere DB muss über UUID zugeordnet werden und darf keine fremde ID binden.

## B: Betriebliche Einnahmen auf Privatkonten

### Ziel und Produktgrenzen

Betriebliche Einnahmen dürfen auf einem Privatkonto erfasst werden. Das tatsächliche
Zahlungsdatum bleibt maßgeblich für die bestehenden Auswertungen; eine spätere
Weiterleitung auf ein Betriebskonto ist keine zweite Einnahme.
Die Sperre aus Spec 029 entfällt erst mit funktionierender Privatklassifikation,
Privatübersicht und passender DATEV-Abbildung in beiden Paketen.

Bestehende EÜR-/UStVA-, Steuerklassen-, Kleinunternehmer- und Korrekturregeln
bleiben unverändert. Diese Spec führt insbesondere keine neue Regel ein, nach der
Umsatzsteuer unabhängig von Steuermodus/Steuerfall immer bei Gutschrift entsteht.
Die Privatwirkung ist eine abgeleitete buchhalterische Größe; der ausgewiesene
Saldo ist kein eigenständiger rechtlicher Erstattungsanspruch.

### Persistierte Klassifikation und Zahlung

`income` behält sein normalisiertes `account`. Es erhält eine persistierte
Privatklassifikation analog zum Ausgabenmodell: Kennzeichen `is_private_received`
und Herkunft `private_classification` (`none` oder `auto`). Konkrete SQL-Namen
werden mit dem Modell abgeglichen; Verhalten und Persistenz sind verbindlich.
Keine zusätzliche Entnahmetabelle, kein manuelles Override in diesem Umfang.

Private Konten werden zentral nach derselben normalisierten Definition wie in
Core und DATEV erkannt, einschließlich reservierter Namen und des bisherigen
`privat`-Fallbacks bei fehlender/leerer Liste. Ungültige Config bleibt ein Fehler.
Create/Import verwendet das explizite Konto oder den bestehenden Default-Vertrag
von Spec 029. Ein fehlendes effektives Konto bleibt unbekannt, nicht privat.

| Zustand | Privatklassifikation / Wirkung |
| --- | --- |
| Konto privat, bezahlt | Privat gespeichert; signierter Bruttobetrag wirkt als Entnahme |
| Konto privat, nur Rechnungsdatum | Privat gespeichert; keine Entnahme/Kontobewegung bis `payment_date` gesetzt ist |
| Konto betrieblich / unbekannt | Keine abgeleitete Entnahme; bestehende Incomplete-Prüfung gilt |
| Positive Einnahme auf Privatkonto | Entnahme `+amount_eur` am Zahlungsdatum |
| Negative Einnahmekorrektur auf Privatkonto | Mindert die abgeleitete Entnahme um den signierten Betrag; keine Anwendung von `abs()` |
| Soft-deleted | Keine Wirkung in Summen oder Export |

Die bestehende Steuerberechnung wird genau einmal für `income` ausgeführt;
Privatwirkung löst keine zweite Erlös-/Umsatzsteuerbuchung aus.

### Create, Update, Reconcile und Historie

Create/Import klassifizieren nach aktueller Config im Service, atomar samt Audit.
Alle anderen fachlichen Prüfungen bleiben erhalten; auch ein als Dublette
übersprungener Import darf ungültige Felder nicht verbergen.

Ein explizites Konto-Update berechnet die Privatklassifikation neu. Reine
Notiz-/Beleg-/Betrags-/Datumsänderungen behalten die gespeicherte Klassifikation;
Betrag/Datum wirken anschließend nach dem obigen Zahlungs-/Vorzeichenvertrag.
Konto löschen setzt sie auf `none`; kein Default auf historische Updates.
Ein späteres Setzen/Löschen des Zahlungsdatums aktiviert/deaktiviert die Wirkung.

Config-Änderungen verändern historische Klassifikationen nicht beim Lesen.
`euer reconcile private [--year JJJJ] [--dry-run]` erweitert die bestehende
Reklassifikation um Einnahmen: zeigt alte/neue Klassifikation und IDs, führt
nur im Schreibmodus auditierte Änderungen aus und ist wiederholt wirkungslos.
Dry-Run verändert weder Buchung noch Audit. Der bestehende Ausgabenvertrag
(einschließlich manueller Ausnahmen) bleibt erhalten.
DATEV verwendet die gespeicherte Klassifikation. Eine Abweichung zur aktuellen
Privatkonten-Config erzeugt Prüfbedarf mit ID und Reconcile-Hinweis; keine stille
Umkontierung. Für alte unterstützte Schemata gilt der bisherige Reader-Vertrag.

Delete/Restore/Undo/Purge verwenden die bestehende Lebenszykluslogik. Restore
stellt die gespeicherte Klassifikation wieder her; Config-Abweichungen bleiben
sichtbar und werden nicht heimlich rekonstruiert. Alle Summen werden aus aktiven
Quelldatensätzen abgeleitet; keine mehrfach erzeugten Entnahmebuchungen.

### Privatübersicht und Schnittstellen

Der tatsächlich bestehende Befehl heißt `euer private-summary --year JJJJ`.
`euer reconcile private` bleibt ein Reklassifikationsbefehl, keine Auszahlung
und keine Saldenausgleichsbuchung. Kein neuer `--settle`-Schalter.

```text
Saldo = direkte Einlagen - direkte Entnahmen
      + signierte Einlagen aus privat bezahlten Ausgaben
      - signierte Entnahmen aus privat vereinnahmten Einnahmen
```

Ausgabenwirkung bei Zahlung: `-expenses.amount_eur`, Einnahmenwirkung:
`income.amount_eur`, jeweils privat klassifiziert, aktiv und mit `payment_date`
im Jahr. Keine unbezahlten Rechnungen und kein Rechnungsdatumsfallback;
Erstattungen/Korrekturen mindern den jeweiligen Bestandteil. Direkte positive
Einlagen/Entnahmen aus `private_transfers` bleiben nach ihrem eigenen Datum
enthalten. Ihre Account-Zuordnung aus Abschnitt A verändert nicht die Privatwirkung.

Die Ausgabe zeigt die vier Bestandteile, zugehörige Anzahl und Gesamtsaldo.
Bestehende ELSTER-Feldzuordnungen werden weiterverwendet; signierte Korrekturen
werden nachvollziehbar ausgewiesen und nicht durch Betragsbildung verdeckt.
Ein positiver Saldo bedeutet netto mehr Einlagen, ein negativer mehr Entnahmen.

Gültige Erfassung mit vorhandenen CLI-Optionen:

```bash
euer add income --source "Kunde Müller" --amount 1190.00 \
  --date 2026-03-15 --vat-rate 19 --account p-giro \
  --notes "Zahlung auf Privatkonto"
# Spätere Weiterleitung; --account ist die Erweiterung aus Abschnitt A:
euer add private-deposit --amount 1190.00 --date 2026-03-20 \
  --account giro --description "Weiterleitung privater Kundeneingang"
euer private-summary --year 2026
```

Create/Import mit bezahlter Privateinnahme nennt die abgeleitete Wirkung.
CSV/JSON-Ausgaben und Incomplete-Prüfung müssen Konto, Zahlungszustand und
Privatklassifikation konsistent darstellen. Beim Wiederimport in dieselbe DB
bleibt die gespeicherte Klassifikation des vorhandenen Datensatzes erhalten;
kein zusätzlicher Privatvorgang oder Erlös. Neue Datensätze, auch in einer anderen
DB, werden anhand der aktuellen geprüften Config klassifiziert. Importierte
Klassifikationsfelder dürfen diese Validierung nicht überschreiben; eine
Abweichung zur exportierten Klassifikation erzeugt einen Konflikt vor Mutation
statt einer stillen Änderung. Der bestehende Dublettenvertrag bleibt maßgeblich;
Klassifikationsfelder sind kein Herkunftsnachweis. Diese Spec führt keine neue
Importherkunft oder allgemeine UUID-Importverwaltung ein.

### Schutz vor erneuter Erlöserfassung

Bei Create/Import einer positiven, bezahlten Einnahme auf einem Betriebskonto
mit gleichem Centbetrag wie eine aktive, bezahlte Privateinnahme innerhalb der
vorherigen sieben Kalendertage entsteht ein möglicher Weiterleitungsfall.
Ein vorhandener passender Kandidat erzeugt Prüfbedarf mit Kandidaten-IDs und
Hinweis auf `private-deposit`; keine automatische Umklassifikation oder Zuordnung.
Ohne ausdrückliches `--allow-duplicate` wird die Buchung abgewiesen (im Import
vollständiger Rollback). Mit Bestätigung bleibt sie eine eigenständige Einnahme
und die Warnung sichtbar. Der Hinweis behauptet keine nachgewiesene Herkunft;
gleiche Beträge können unabhängige Zahlungen sein. `--force` behält die bestehende
Bestätigungssemantik. Update identitätsrelevanter Daten prüft analog ohne Eigen-ID.

Diese begrenzte Heuristik ersetzt keine Importherkunft. Weiterleitungen außerhalb
des Fensters oder mit Teilbeträgen sind nicht zuverlässig erkannt; Skill und
Nutzerreferenz nennen diese Grenze und prüfen den Sachverhalt vor der Buchung.

## C: DATEV-Vertrag, Migration und Upgrade

### Fachliche Exportwirkung

Die technische Umsetzung und Diagnosematrix sind in DATEV Spec 002 verbindlich.
Für interne Transfers gilt:

| Beobachtete Seite | Soll | Haben | Datum |
| --- | --- | --- | --- |
| Quelle | Geldtransit (SKR03 1360 / SKR04 1460) | Quell-Finanzkonto | `source_date` |
| Ziel | Ziel-Finanzkonto | Geldtransit | `target_date` |

Nur bekannte Seiten im Exportzeitraum erzeugen Zeilen. Ein Transitüberhang bei
Monats-/Jahreswechsel ist erlaubt und ausgewiesen; kein künstlicher Ausgleich
und kein Datumsfallback. Pending-Transfers erzeugen einen erklärten INFO-Befund,
keine erfundene zweite Zeile. Fehlendes/konfligierendes Finanzkontenmapping
blockiert den regulären Export. Transfers zählen nicht zum EÜR-/UStVA-Abgleich;
Quellvorgänge und erzeugte DATEV-Zeilen werden getrennt ausgewiesen.

### Privatvorgänge


- Bezahlte, privat klassifizierte Einnahme: Privatentnahmen (SKR03 1800 /
  SKR04 2100) gegen reguläres Erlöskonto; Steuerbehandlung unverändert.
- Negative Korrektur: bisherige Umkehrung der Buchungsrichtung auch gegen das
  Privatentnahmekonto; kein zusätzlicher Privatvorgang.
- Unbezahlte Einnahme: keine Zahlungs-/Entnahmezeile, entsprechend bisherigem
  Exportvertrag. Kein Fallback auf ein betriebliches Bankkonto.
- Direkte spätere Einlage: betriebliches Finanzkonto gegen Privateinlagen
  (SKR03 1890 / SKR04 2180), einmal aus `private_transfers` gemäß Spec 030.
- Betriebliche Einnahme: bestehendes Finanzkontenmapping unverändert.

Die neue zentrale Privatklassifikation ersetzt Core- und DATEV-Sperren gemeinsam;
Konflikte, unbekannte Klassifikationswerte und Config-Abweichungen dürfen nicht
als `ready` erscheinen. Direkte und abgeleitete Privatwirkung werden im Bericht
getrennt, Erlös-/EÜR-Abgleich zählt nur den ursprünglichen Einnahmedatensatz.

### Gemeinsame Migration

Neue Tabelle `internal_transfers`, betriebliches `private_transfers.account`
und persistierte Einnahmenklassifikation erfordern Core-Migrationen.
Erst nach Prüfung der Registry nummerieren und die vollständige neue Folge sowie
verbindliche Feldnamen/Typen in beiden Specs und Reader-Fixtures festhalten.
DATEV schreibt niemals in die Core-Datenbank und migriert sie nicht.

Altbestand erhält keine erfundenen Konten, Transfers oder Zahlungsdaten.
Einnahmenklassifikation initial `none`/false; keine Ableitung aus aktueller Config.
Historische Privateinnahmen können per `reconcile private --dry-run` geprüft und
anschließend auditiert klassifiziert werden. Beträge, UUIDs, Hashes und bestehende
Audit-Einträge bleiben erhalten. Unbekannte/lückenhafte Historien bleiben gesperrt.

DATEV unterstützt bisherige vollständige Schemata und die neue vollständige Folge;
keine opportunistische Spaltenerkennung. Neue Buchungen erst nach Installation
beider kompatiblen Paketversionen und Migration nutzen.
Upgrade: Datenbank sichern, beide Pakete aktualisieren, aktive Versionen prüfen,
`init --dry-run`, Migration, `reconcile private --dry-run`, geprüfte Reklassifikation
und DATEV-Validierung. Bei verzögerter Verfügbarkeit eines Pakets mit der Migration
warten. Skill, CLI-/Domain-Referenz, Onboarding, README und Nutzer-Release-Notes
aktualisieren; veröffentlichte historische Abschnitte erhalten.

Core- und DATEV-Release-Nachweis enthalten Versionspaar, vollständige Commit-SHAs,
SHA256 der gebauten/veröffentlichten Artefakte, Plattformtests und Prüfung desselben
Paketpaars. Externe DATEV-Importprüfung separat vor produktiver Übergabe benennen.

## D: Abnahmematrix

### Transfers und Kontenabgleich


Jede Zeile erhält bei Implementierung einen konkreten Testnamen/Nachweis.

| Fall | Erwartung | Nachweis |
| --- | --- | --- |
| Stripe 1000 / Gebühr -29 / Transfer 971 | Stripe 0, Giro +971; Erlös/Gebühr einmal | Service + CLI + DATEV |
| Privatendpunkt, gleiche Konten, ungültiges Datum/Betrag | Verständlicher Fehler, keine Mutation/Audit | Service + CLI/Import |
| Nur Quellseite / nur Zielseite | Genau eine Kontobewegung und DATEV-Zeile, Pending sichtbar | CLI + Reader/Export |
| 31.12. → 02.01.; taggleicher bestätigter Transfer | Eigene Perioden je Seite; kein Ersatzdatum | Kontenabgleich + DATEV |
| Beide Auszugsseiten in beliebiger Reihenfolge, Wiederimport | Ein Transfer, UUID erhalten; keine doppelte Gebühr | Import + Roundtrip |
| Referenzkonflikt / uneindeutige Gegenseite | Abbruch mit IDs, vollständiger Rollback | CLI/Import |
| Gebühr schon gebucht, doppelte/ungültige Verknüpfung | Keine automatische Anlage; Konflikt abweisen | Service + CLI |
| Update/Delete/Restore/Undo, Gebührenänderung | Keine verwaisten aktiven Links; atomarer Audit | Service + CLI |
| Negative Ausgabe, Erstattung, Korrektur, direkte Privatvorgänge | Richtige Kontobewegungen mit Vorzeichen | Kontenabgleich |
| Fehlender Anfangs-/Endsaldo, NULL-Konten, Pending | Kein unbegründetes `matched`; IDs/Status sichtbar | CLI/JSON |
| Altbestand/aktuelle Config, neue Migration, unbekanntes Schema | Keine Rückfüllung; neue und alte Reader-Verträge | Migration + installierte Wheels |
| Dry-Run / Fehler im gemischten Import | DB und Audit unverändert | CLI/Artefakttest |

### Private Einnahmen und Privatübersicht


Jede Zeile erhält bei Implementierung einen konkreten Testnamen/Nachweis.

| Fall | Erwartung | Nachweis |
| --- | --- | --- |
| Privateinnahme 1190 inkl. 19 % | Ein Erlös, eine Steuerwirkung, abgeleitete Entnahme 1190 | Service + CLI + DATEV |
| Kleinunternehmer/steuerfrei/negative Korrektur | Bestehende Steuervarianten; Vorzeichen korrekt | Service + Berichte + DATEV |
| Nur Rechnungsdatum; Zahlung später oder entfernt | Vor Zahlung keine Wirkung; Zahlung aktiviert sie im richtigen Jahr | Update + Privatübersicht + DATEV |
| Privat → Giro nach Kundeneingang | Einlage einmal, kein neuer Erlös/Geldtransit | Core-/DATEV-Integration |
| Direkte Einlagen/Entnahmen + private Ausgaben/Erstattungen + Einnahmen | Vier Komponenten erhalten, signierter Gesamtsaldo korrekt | Privatübersicht + EÜR |
| Betrieb/Privat/NULL-Konto-Updates | Klassifikation/Wirkung konsistent; kein historischer Default | Service + CLI/Import |
| Config geändert; Reconcile Dry-Run/Write wiederholt | Keine Änderung beim Lesen; auditierte, idempotente Reklassifikation | CLI + DATEV-Validierung |
| Delete/Restore/Undo/Import-Roundtrip | Keine zweite Entnahme; Identität und gespeicherte Klassifikation erhalten | CLI + Audit |
| Gleicher Betrag im Zeitfenster / unabhängige Zahlung / explizite Bestätigung | Kandidaten-IDs, Rollback ohne Bestätigung, keine automatische Zuordnung | CLI/Import/Update |
| Teilbetrag/außerhalb Fenster | Keine Herkunftszusage; Grenze dokumentiert | CLI + Skill-Review |
| Altbestand / neue Migration / unbekanntes Schema | Keine stille Klassifikation, keine Konten-/Datumsänderung | Migration + Reader |
| Gebaute Core-/DATEV-Pakete und externe Übergabe | End-to-End-Vertrag getestet; externe Prüfung separat benannt | Installierte Wheels + manueller Nachweis |
