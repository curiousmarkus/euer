# Spec 029: Zahlungskonten für Einnahmen und konsistente Kontovorgaben

## Status

Implementiert

## Ziel und gemeinsamer Release

Einnahmen speichern ihr tatsächliches Zahlungskonto durchgängig von der Erfassung
bis zum DATEV-Export. `account` bezeichnet den Zahlungsweg, `ledger_account` das
Sach-/Erlöskonto; beide bleiben unabhängig. Ein Kontoname ist keine steuerliche
Klassifikation und kein Nachweis des Zuflusszeitpunkts.

Diese Spec und [DATEV Spec 001](../../euer-datev/specs/001-einnahmen-zahlungskonten.md)
bilden einen gemeinsamen Releaseumfang. Core und Add-on werden gemeinsam
abgenommen und im selben Releasefenster veröffentlicht. Die Pakete behalten
eigene Versionsnummern. Kein Teil wird als fertiges Feature angekündigt, bevor
beide Artefakte verfügbar sind. Der genaue Upgrade- und Kompatibilitätsvertrag
steht in DATEV Spec 001; er ist auch für diese Spec verbindlich.

Spec 021 ist ein möglicher separater Releasebaustein, aber keine Abhängigkeit.
Specs 014, 023, 024, 026 und 028 gehören nicht zu diesem Umfang.

## Ausgangslage

- `expenses` besitzt `account`, `income` bislang nicht.
- Der Import normalisiert `account` / `Konto` bereits, reicht es bei Einnahmen
  aber nicht bis zur Persistenz durch.
- Der DATEV-Reader setzt `RawTransaction.account` für Einnahmen auf `None`.
  Das Einnahmen-Mapping kann Zahlungskonten bereits auflösen.
- Ohne gespeichertes Konto verwendet DATEV ein ausdrücklich konfiguriertes
  Bankkonto oder einen gewarnten Bank-Fallback. Ein Kontohinweis in `notes`
  ist keine belastbare Zuordnung und wird nicht automatisch übernommen.

## Umfang und Produktgrenze

Unterstützt werden benannte betriebliche Zahlungswege, etwa Girokonto, Kasse,
PayPal oder Stripe. Der Release ergänzt keine Kontostände, Anfangssalden,
Bankabstimmung oder automatische Zuordnung aus Freitext.

Gebühren sind separate Ausgaben. Eine Auszahlung vom Zahlungsdienstleister auf
ein anderes eigenes betriebliches Konto darf keine zweite Einnahme erzeugen.
Ein Modell für erfolgsneutrale interne Transfers und deren DATEV-Geldtransit
ist nicht Teil dieses Releases. Der Agenten-Skill muss diese Grenze nennen:
Ein vollständiger Zahlungsdienstleister-Kontenabgleich wird nicht zugesagt.
Ein expliziter Transfer-Datensatz darf nicht als Einnahme/Ausgabe umgedeutet
werden; das Importformat unterstützt diesen Vorgangstyp weiterhin nicht.

**Einnahmen auf Privatkonten sind in diesem Release nicht unterstützt.**
Bei neuer oder geänderter Kontozuordnung werden Namen aus `get_private_accounts()`
sowie die reservierten Namen `privat`, `privateinlage` und `privatentnahme` mit
`unsupported_private_income_account` abgewiesen. Ein solches Standardkonto darf für Einnahmen ebenfalls nicht still
verwendet werden. Der Fehler fordert zur Klärung auf, nicht zur falschen Angabe
eines Geschäftskontos. Es entstehen keine automatischen Privattransfers.
Ausgaben behalten ihre bestehende persistierte Privatklassifikation.
Eine spätere Unterstützung benötigt einen eigenen Vertrag für Einnahme,
Privatentnahme, Privatübersicht und Vermeidung doppelter Transfers.

Steuerlicher Zufluss setzt wirtschaftliche Verfügungsmacht voraus. Ein
Provider-Buchungsdatum oder `--account stripe` allein beweist diese nicht.
Der Agent muss `payment_date` aus dem belegten Sachverhalt bestimmen; die CLI
leitet es nicht aus dem Kontonamen ab. Siehe
[BMF, Hinweise zu § 11 EStG](https://amtliche-handbuecher.bundesfinanzministerium.de/esth/2025/A-Einkommensteuergesetz/II-Einkommen-2-24b/6-Vereinnahmung-und-Verausgabung-11-11b/Paragraf-11/h-11.html).

## A1: Schema und Migration

`income` erhält `account TEXT NULL` und den Index `idx_income_account`.
Die nächste Migration ist beim gegenwärtigen Stand `010_income_account`.
Die Nummer wird vor Implementierung gegen die Registry geprüft; kein anderer
Entwurf reserviert parallel dieselbe Nummer. Spec 028 wird getrennt umgesetzt.

- Frisches Schema und Migration ergeben denselben Tabellen- und Indexzustand.
- Preflight prüft Tabelle, Spalte und Index und nennt die Anzahl betroffener
  Altbuchungen. Dry-Run schreibt nichts; Apply folgt dem vorhandenen
  transaktionalen Migrationsmechanismus einschließlich Migrationshistorie.
- Apply berücksichtigt bereits vorhandene Spalten/Indizes; ein inkonsistenter
  oder inkompatibler Zustand wird erklärt und nicht blind überschrieben.
- Altbuchungen bleiben `NULL`; kein Backfill aus aktuellem Default, Notizen
  oder DATEV-Bankmapping. IDs, UUIDs, Beträge, Hashes und Audit-Historie bleiben
  erhalten. Es werden keine historischen Kontozuordnungen erfunden.
- Auch Schemaerkennung für vorhandene Datenbanken ohne vollständige Registry
  und wiederholtes `init` sind zu prüfen.

## A2: Konto- und Defaultvertrag im Service Layer

`Income`, Row-Konvertierung, Create/Get/List/Update und Audit-Payloads führen
`account: str | None`. Alle Mutationen laufen über Services und werden samt
Audit atomar gespeichert. Delete/Restore und Undo erhalten bzw. rekonstruieren
den Kontowert; ältere Audit-Payloads ohne das neue Feld bleiben verwendbar.

Kontonamen werden für Speicherung und Vergleich außen getrimmt und in
Kleinbuchstaben normalisiert. Leere Werte werden zu `None`. Bestehende
Ausgabenkontonamen werden nicht pauschal umgeschrieben; Vergleiche und Filter
verwenden dieselbe Normalisierung. Eine Änderung nur des Kontos verändert
weder Steuerwerte noch Duplikat-Hash.

| Operation | Eingabe | Verhalten |
|---|---|---|
| Create, auch Import | explizites nichtleeres Konto | Dieses Konto speichern; Default ignorieren |
| Create, auch Import | Konto fehlt oder ist leer | Konfigurierten Default speichern, sonst `NULL` |
| Update | Argument fehlt (`None`) | Bisherigen Wert erhalten; keinen Default anwenden |
| Update | nichtleeres Konto | Neuen normalisierten Wert speichern |
| Update | leerer String | Auf `NULL` setzen; keinen Default anwenden |

Die Service-API erhält Konto, optionalen Default und private Kontonamen explizit;
sie liest keine globale Config. Commands laden die Config und übergeben die
Werte. Auflösung und Validierung erfolgen im Service, identisch für CLI und
Import. Das gilt auch für neue Ausgaben: Der Default wird vor deren bestehender
Privatklassifikation aufgelöst. Updates an Ausgaben erhalten keinen neuen Default.

Der Default ist eine ausdrücklich konfigurierte Erfassungsvorgabe. Er wird
beim Anlegen materialisiert und im normalen INSERT-Audit festgehalten.
Eine spätere Config-Änderung ändert weder gespeicherte Konten noch alte `NULL`-Werte.
Es gibt keinen nachträglichen Default beim Lesen, Prüfen oder Exportieren.
Altbuchungen werden bei Bedarf einzeln über `update income --account` korrigiert;
eine Sammelkorrektur oder automatische Wiederimport-Anreicherung ist nicht Teil
dieser Spec.

`compute_hash()` bleibt unverändert. Unterschiedliche Zahlungskonten allein
unterscheiden keine ansonsten identischen Buchungen. Diese bestehende Grenze
ist im Importhinweis zu dokumentieren; die bisherigen expliziten Verfahren
zum Umgang mit bestätigten Duplikaten bleiben maßgeblich.

## A3: Konfiguration

```toml
[accounts]
# Erfassungsvorgabe für neue Einnahmen UND Ausgaben, kein Export-Fallback.
default = "g-n26"
private = ["privat", "p-sparkasse"]

# Beispiel für einen bestätigten SKR03-Kontenplan, keine universellen Vorgaben.
[datev.accounts]
g-n26 = "1200"
paypal = "1210"
stripe = "1220"
kasse = "1000"
```

- `get_default_account(config)` akzeptiert einen nichtleeren Kontonamen oder
  einen fehlenden/leeren Wert (`None`); andere Typen sind Konfigurationsfehler.
- `get_known_accounts(config)` liefert normalisierte, deduplizierte Namen aus
  Default, Privatkonten, `[datev.accounts]`, dem Finanzkontenanteil von
  `[accounts.mapping]` und den unterstützten alten flachen Kontenzuordnungen.
  Reservierte Schlüssel `default`, `private`, `mapping` sind keine Konten.
  Diese Liste dient der Orientierung, nicht als verpflichtende Whitelist:
  Core kann auch ohne DATEV-Konfiguration benannte Zahlungskonten erfassen.
- `[datev.accounts]` bleibt kanonisch; bestehende Mapping-Prioritäten und
  Konfliktwarnungen des Add-ons bleiben erhalten. Kontonamen sind von
  DATEV-Kontonummern zu unterscheiden. Details stehen in DATEV Spec 001.
- Core verwendet weiterhin seine bestehende globale Config. Die projektbezogene
  Core-Config bleibt eine DB-Bindung. Eine allgemeine Angleichung der Config-
  Lader ist nicht Teil dieses Releases. DATEV darf seinen zusammengeführten
  `accounts.default` nicht nachträglich auf gelesene Buchungen anwenden.
- Setup, Config-Anzeige und Agenten-Onboarding erklären Erfassungsvorgabe,
  tatsächliches Zahlungskonto und DATEV-Zuordnung getrennt. Der Agent übernimmt
  einen Default erst nach ausdrücklicher Einrichtung für den Mandanten.

## A4: CLI, Import und Ausgabenparität

- `add income --account NAME` und `update income ID --account NAME` ergänzen;
  `update income ID --account ""` löscht die Zuordnung.
- `list income` zeigt das Konto in Tabellenansicht, `--full` und CSV.
  `full` ist kein neuer Wert für `--format`.
- `list income --account NAME` filtert normalisiert. Derselbe Filter wird für
  `list expenses` ergänzt; er existiert bislang nicht. Service-Listen, Jahres-/
  Monatsfilter und Papierkorbansichten kombinieren Filter konsistent.
- CSV/JSONL-Import reicht `account` / `Konto` bis zum Service durch und verwendet
  dieselbe Default- und Privatkontenvalidierung. Import-Schema und Fehlermeldungen
  dokumentieren den Vertrag, einschließlich Zeilenbezug bei Fehlern.
- Wiederimport überschriebener Kontodaten ist kein Update-Verfahren: Ein
  erkannter bestehender Datensatz wird nicht still verändert.
- Änderungen an Ausgaben beschränken sich auf Create-Default und Kontofilter;
  Steuerberechnung und manuelle Privatklassifikation bleiben maßgeblich.

## A5: Exporte und Vollständigkeit

CSV und XLSX erhalten bei Einnahmen die Spalte `Konto` zwischen `EUR` und
`Buchungskonto`, mit dem tatsächlich gespeicherten Wert. Vorhandene Dateinamen,
Arbeitsmappenstruktur, Überschreibschutz und optionale XLSX-Abhängigkeit bleiben
bestehen. Headerbasierter Reimport erhält die Kontozuordnung; positionsabhängige
Verbraucher müssen die neue Spalte berücksichtigen.

`incomplete` gibt bei Einnahmen den gespeicherten Kontowert aus. Bei einer
bezahlten Einnahme mit `NULL` meldet es `account` als fehlende Angabe, unabhängig
von aktuellem Default oder DATEV-Mapping. Unbezahlte Einnahmen benötigen noch
kein Zahlungskonto. Die neue Diagnose alter bezahlter Einnahmen wird als
Upgrade-Auswirkung dokumentiert; sie ändert keine Beträge und blockiert nicht
pauschal den Core-CSV/XLSX-Export.

DATEV prüft separat die Exportkontierung: Ein ausdrücklich konfiguriertes
`bank` kann eine Einnahme ohne gespeichertes Konto mit INFO übernehmen, ohne
deren Core-Daten zu vervollständigen. Automatische Bank-Fallbacks und unbekannte
Kontennamen bleiben gewarnt und verhindern die normale DATEV-Exportfreigabe.
Core benötigt für seine Vollständigkeitsprüfung keine DATEV-Installation.

## A6: Verbindliche Akzeptanzfälle

1. Frische DB und Migration von 009 liefern dasselbe Schema. Dry-Run,
   wiederholtes Init, fehlender Index und Altbuchungen werden geprüft.
2. Einnahmen auf zwei Geschäftskonten behalten ihr Konto über Create, Get,
   List, Update, Audit, Undo und Delete/Restore. Alte Audit-Einträge bleiben nutzbar.
3. Explizites Konto schlägt Default; Create ohne Konto materialisiert ihn.
   Defaultwechsel ändert weder Bestand noch historische Exporteingaben.
   Update ohne Konto erhält es; leerer String löscht es trotz Default.
4. Neue Ausgaben verwenden denselben Default vor der Privatklassifikation.
   Bestehende und manuell klassifizierte Ausgaben ändern sich nicht von selbst.
5. Private Einnahmenkonten und private Defaults werden bei neuer Zuordnung
   verständlich abgewiesen. Kein Ersatzkonto und kein Privattransfer entsteht.
6. CSV/JSONL mit `account` und `Konto`, CSV-/XLSX-Export sowie Reimport in eine
   frische DB erhalten normalisierte Konten. Ohne Konto gilt der Create-Vertrag;
   der ursprüngliche Nullzustand ist bei konfiguriertem Default nicht garantiert.
7. Bezahlte Altbuchung ohne Konto bleibt `NULL` und erscheint in `incomplete`;
   ein DATEV-Bankmapping oder neuer Default beseitigt diese Diagnose nicht.
8. Duplikat-Hashes ändern sich durch Migration/Kontowechsel nicht. Zwei sonst
   identische Vorgänge auf verschiedenen Konten zeigen die dokumentierte Grenze.
9. Bei belegten 299 EUR Kundenzufluss und 9 EUR separater Gebühr werden 299 EUR
   Einnahme und 9 EUR Ausgabe auf dem Providerkonto erfasst. Eine spätere
   290-EUR-Auszahlung wird nicht nochmals als Einnahme importiert. Der Test
   prüft die unterstützten Buchungen und die Ablehnung eines expliziten
   Transfer-Typs; er behauptet keine automatische Erkennung aus Bankfreitext.
10. Gemeinsame Tests mit dem Add-on decken beide unterstützten Schemastände,
    SKR03/SKR04, unbekannte Konten, Nullkonten und private Konten ab. Die
    Release-Abnahme richtet sich zusätzlich nach DATEV Spec 001.

## Umsetzung und Dokumentation

Betroffen sind `schema.py`, `migrations.py`, `config.py`, Service-Modelle,
Income-/Expense-Services, CLI, Add/Update/List/Import/Export/Incomplete und
gegebenenfalls Undo. Tests prüfen Verhalten und Upgrade, nicht nur Parameter.

Bei Implementierung: CLI-Referenz, User Journey, Domain-Regeln, Agenten-Skill,
Onboarding, Dossier-Vorlage, README und DEVELOPMENT abgleichen. Release Notes
nennen beide Paketversionen, neue CSV-Spalte, fehlende Konten im Altbestand,
Privatkonto-/Transfergrenzen und die gemeinsame Upgrade-Sequenz. Historische
Releaseabschnitte werden nicht ergänzt. Implementierung und Release-Abnahme
werden separat gemäß DEVELOPMENT nachgewiesen.

## Präzisierungen aus der Release-Abnahme

- `accounts.private` ist eine Liste nichtleerer Strings. Ein fehlender Schlüssel
  oder eine leere Liste verwendet in beiden Paketen `privat`; die vorherige
  Core-Kompatibilität bleibt erhalten. String-/Zahlwerte und leere Elemente
  sind Fehler, die Controller ohne Traceback melden.
- Core prüft vor Datenbefehlen lesend die Migrationshistorie. Ausstehende oder
  noch nicht registrierte Migrationen verlangen `init`; unbekannte, lückenhafte
  und nicht lesbare Stände sperren den Befehl vor Mutation und Audit.
- Der gemeinsame Release verwendet einen vollständigen Core-Commit, keinen
  veröffentlichungsabhängigen Core-Tag. DATEV-Test und Build verwenden denselben
  SHA-Wert; die Artefaktprüfung erwartet 010 bei neuer DB und prüft 009 separat.
- Implementierungsstatus und Release-Abnahme sind getrennt. Tests und endgültige
  Commit-/Artefaktstände werden gemäß DEVELOPMENT dokumentiert. Externe DATEV-
  Importabnahme und Veröffentlichung sind gesonderte Schritte.

| Akzeptanzfall | Konkreter Nachweis |
|---------------|-------------------|
| Unbekannte/lückenhafte Core-Historie: keine Buchung und kein Audit | Core `test_cli_core.test_schema_preflight_rejects_unknown_and_incomplete_history` |
| Falsche Privatkonten-Konfiguration: sauberer CLI-Fehler | Core `test_cli_core.test_invalid_private_config_is_reported_by_all_affected_commands` |
| Leere Privatkontenliste bleibt kompatibel | Core `test_config.test_get_private_accounts_validates_list_of_strings`, DATEV `test_config.test_empty_private_list_uses_core_compatible_default` |
| Aktuelles Artefaktpaar in Standalone, externer CLI und Plugin | DATEV `scripts/verify_cli_paths.py`, Originalskript mit beiden gebauten Wheels |
| Schema-009-Rückwärtskompatibilität | DATEV `test_reader.test_schema_and_exclusions_are_read_only` |
