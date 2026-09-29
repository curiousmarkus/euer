# Spec 026: Innergemeinschaftlicher Warenerwerb und OSS-Erlöse

## Status

Offen

## Ziel und Umfang

`euer` trennt den innergemeinschaftlichen Erwerb von Gegenständen nach § 1a UStG
von bezogenen Dienstleistungen nach § 13b UStG. Es erfasst außerdem Erlöse, die
über die EU-Regelung des One-Stop-Shop (OSS) nach § 18j UStG erklärt werden,
ohne sie als deutsche Umsatzsteuer in der UStVA auszuweisen.

Die EÜR-Buchung bleibt eine Abbildung des tatsächlichen EUR-Zahlungsflusses.
Umsatzsteuerliche Ereignisse werden mit eigener Bemessungsgrundlage, Periode und
Klassifikation nachvollziehbar erfasst. Dieser Spec ist unabhängig von Spec 024
(Regelkatalog). Die fachliche Einordnung erfolgt anhand von Beleg,
Mandantenstatus und Zeitraum; die CLI prüft Widersprüche und fehlende Angaben.

## Fachliche Grundlagen

### EÜR und Umsatzsteuer verwenden unterschiedliche Zeitpunkte

Für die EÜR gilt grundsätzlich der Abfluss im Jahr der Zahlung (§ 11 Abs. 2 EStG),
vorbehaltlich gesetzlicher Ausnahmen und der Behandlung von Anlagevermögen. Bei
einem innergemeinschaftlichen Erwerb entsteht die Erwerbsteuer dagegen mit
Ausstellung der Rechnung, spätestens mit Ablauf des Kalendermonats nach dem
Erwerb (§ 13 Abs. 1 Nr. 6 UStG). Anzahlungen werden in der UStVA noch nicht als
Erwerb eingetragen; die volle Bemessungsgrundlage folgt nach dem Erwerb. Ein
Zahlungsdatum allein bestimmt die UStVA-Periode daher nicht. Bei Teilzahlungen
werden mehrere EÜR-Zahlungen mit einem steuerlichen Erwerb verknüpft, statt
die Erwerbsteuer mehrfach zu melden.

Das Erwerbsdatum bezeichnet den für den Erwerb maßgeblichen Warenübergang.
`invoice_date` bezeichnet die Rechnungsausstellung, `payment_date` weiterhin
den Geldabfluss. Die umsatzsteuerliche Periode wird aus fachlich belegten Daten
bestimmt und gespeichert. Unklare oder widersprüchliche Angaben erscheinen als
Prüfbedarf und werden nicht stillschweigend der Zahlungsperiode zugeordnet.

### Innergemeinschaftlicher Warenerwerb

Voraussetzungen sind unter anderem die Warenbewegung zwischen Mitgliedstaaten,
ein Erwerb für das Unternehmen und eine Lieferung durch einen entsprechend
handelnden Unternehmer (§ 1a Abs. 1 UStG). USt-IdNrn. und ein Hinweis auf eine
innergemeinschaftliche Lieferung sind wichtige Belege, aber die CLI darf aus
einem einzelnen Merkmal keine automatische Einordnung ableiten. Ausnahmen,
etwa die Erwerbsschwelle, neue Fahrzeuge oder verbrauchsteuerpflichtige Waren,
brauchen eine gesonderte Prüfung.

Der EUR-Zahlungsbetrag einer Ausgabe ist wie bisher negativ. Die
Bemessungsgrundlage des Erwerbs wird separat als positiver Nettobetrag erfasst;
sie kann bei An-, Teil- oder Restzahlungen vom einzelnen Zahlungsbetrag
abweichen. Für unterstützte Fälle sind 19 % und 7 % vorgesehen. Der Steuersatz
muss zum Gegenstand belegt sein und wird nicht allein aus einer EÜR-Kategorie
abgeleitet.

Die Erwerbsteuer wird aus der Bemessungsgrundlage berechnet. Bei
Regelbesteuerung kann sie nach § 15 Abs. 1 Satz 1 Nr. 3 UStG als Vorsteuer
abziehbar sein. Der Agent begründet die Abziehbarkeit und Höhe aus Beleg und
bestätigten Mandantenregeln; bei fehlender Grundlage bleibt Prüfbedarf. Bei
Kleinunternehmern ist keine Vorsteuer nach § 15 UStG abziehbar. `tax.mode`
allein beschreibt die steuerliche Behandlung eines früheren Erwerbs nicht
verlässlich. Eine spätere Config-Änderung darf gespeicherte Buchungen und
Berichte nicht rückwirkend verändern.

Für die Erwerbsschwelle von 12.500 EUR gelten die Voraussetzungen des
§ 1a Abs. 3 UStG. Die Verwendung einer erteilten USt-IdNr. gegenüber dem
Lieferer gilt als Verzicht auf die Schwelle und bindet mindestens zwei
Kalenderjahre (§ 1a Abs. 4 UStG); der bloße Besitz der Nummer reicht nicht.
Die Software entscheidet die Schwelle nicht allein aus möglicherweise
unvollständigen Buchungen.

### UStVA 2026

Das amtliche Formular verwendet **KZ 89** als Bemessungsgrundlage für 19 % und
**KZ 93** als Bemessungsgrundlage für 7 %. **KZ 95/98** betreffen andere
Steuersätze und werden hier nicht verwendet. Der Bericht zeigt die berechnete
Erwerbsteuer nachvollziehbar; KZ 93 ist kein Steuerfeld zum 19-%-Erwerb und
KZ 98 gehört nur zur Zeile für andere Steuersätze. Abziehbare Vorsteuer gehört
in **KZ 61**, nicht KZ 67. Bezogene EU-Dienstleistungen bleiben bei
**KZ 46/47** und gegebenenfalls **KZ 67**. Der UStVA-Bericht wählt Erwerbe
nach ihrer gespeicherten Steuerperiode aus, die EÜR nach Zahlungsfluss.

Die Auswertung unterstützt **2025 und 2026**. Die Kennziffern und
Formularzeilen werden für jedes Jahr anhand seines amtlichen UStVA-Vordrucks
getrennt verifiziert und im Code als jahresbezogene Metadaten hinterlegt.
Die oben genannten Kennziffern sind für 2026 geprüft; sie werden nicht ohne
Abgleich auf 2025 übertragen. Eine Buchung mit einer Steuerperiode außerhalb
der unterstützten Jahre bleibt gespeichert, erscheint aber nicht mit einer
erfundenen Formularzuordnung.

### OSS-Erlöse

Die EU-Regelung nach § 18j UStG unterstützt **beide** vom Mandanten explizit
als OSS-pflichtig eingeordneten Umsatzarten: innergemeinschaftliche
Fernverkäufe von Waren an Privatkunden und im Verbrauchsmitgliedstaat
steuerbare digitale B2C-Leistungen. Die Umsatzart wird pro Steuerereignis
gespeichert. Die EU-weite 10.000-EUR-Regel und ein möglicher Verzicht auf ihre
Anwendung beeinflussen den Leistungsort; Kundenland und Betrag allein reichen
für die Einordnung nicht. Die OSS-Teilnahme muss für den Zeitraum bestätigt
sein.

Ein OSS-Erlös bleibt mit seinem tatsächlichen EUR-Zufluss Teil der EÜR. Für
die OSS-Auswertung werden mindestens Verbrauchsmitgliedstaat, Umsatzart,
Steuerperiode, Netto-Bemessungsgrundlage, ausländischer Steuersatz, Steuerbetrag
und verwendete Währung beziehungsweise EUR-Umrechnung benötigt. OSS-Steuer
wird nicht als deutsche Umsatzsteuer in `vat-report` oder KZ 83 summiert.
Ein **eigener quartalsweiser OSS-Arbeitsbericht für 2025 und 2026** gruppiert
Bemessungsgrundlage und Steuer nach Verbrauchsmitgliedstaat, Umsatzart und
Steuersatz. Er zeigt
auch Quartale ohne Umsätze als mögliche Nullmeldung und liefert einen
nachvollziehbaren CSV-Export zur manuellen Übergabe. Die Anwendung übermittelt
keine OSS-Erklärung. Korrekturen und Erstattungen verweisen auf das
ursprüngliche Steuerereignis und zeigen im Bericht sowohl das betroffene
Ursprungsquartal als auch das Quartal der Berichtigung. Eine bereits
übermittelte Erklärung wird nicht stillschweigend überschrieben.

Für die EÜR werden vereinnahmter EUR-Zahlungsbetrag und spätere Zahlung der
ausländischen Steuer als getrennte Geldflüsse erfasst. Die OSS-Steuerschuld
allein erzeugt keine zweite EÜR-Ausgabe; ihre Zahlung darf nicht zusätzlich
zur bereits erfassten Bankausgabe als Aufwand gezählt werden. Die
EÜR-Auswertung und der Export weisen diese Trennung aus, damit ausländische
Steuer weder als deutsche USt noch doppelt als Ertrag oder Aufwand erscheint.

## Technische Leitplanken

1. `rc_type` bleibt §-13b-Fällen vorbehalten. Innergemeinschaftliche Erwerbe
   und OSS erhalten eigene Steuerfall-Klassifikationen; `eu_goods` wird nicht
   als Reverse-Charge-Typ gespeichert.
2. Ein steuerlicher Erwerb kann mehreren Ausgaben zugeordnet werden. Seine
   Steuerbasis wird nicht aus einer einzelnen Teilzahlung abgeleitet. Ein
   eigenes, auditierbares Steuerereignis-Modell wird vor Implementierung gegen
   das vorhandene Schema entworfen.
3. Steuerfall, Satz, Basis, Periode, Vorsteuerabzug und Prüfstatus werden
   gespeichert. Der Report berechnet sie nicht aus dem aktuellen `tax.mode` neu.
4. CLI, CSV/JSONL-Import, Listen, Exporte, Audit-Log und `incomplete` bilden
   die Angaben konsistent ab. Keine automatische Umklassifizierung bestehender
   `rc_type = 'eu'`-Buchungen.
5. `vat-report` trennt deutsche UStVA, EU-Warenerwerb und OSS. Ein separater
   OSS-Bericht dient als Übergabehilfe. Ungeklärte Fälle werden gewarnt und
   nicht stillschweigend eingerechnet.
   Zahlungen ausländischer OSS-Steuer erhalten eine eigene Kennzeichnung und
   werden weder als deutsche Umsatzsteuer noch als Vorsteuer klassifiziert.
6. Schema-Änderungen erfolgen versioniert über `euer init` mit Dry-Run.
   Bestehende Buchungen, UUIDs, Audit-Historie, Fremdschlüssel, Indizes und
   Hashes bleiben erhalten. Die Migrationsnummer folgt der dann aktuellen Liste.
7. Amtliche Kennziffern werden je Formularjahr geprüft und nicht ungeprüft
   aus 2026 fortgeschrieben.

## Akzeptanzfälle

1. **Jahreswechsel und Teilzahlungen:** Waren für 1.000 EUR netto gelangen
   im Dezember 2025 nach Deutschland. Eine Anzahlung von 200 EUR fließt im
   Dezember 2025 ab, die Rechnung wird im Januar 2026 ausgestellt und die
   Restzahlung von 800 EUR erfolgt im Februar 2026. Die EÜR zeigt die beiden
   Zahlungen in ihren jeweiligen Jahren. Die UStVA zeigt den Erwerb einmal
   mit 1.000 EUR Bemessungsgrundlage und 190 EUR Erwerbsteuer im Januar 2026.
   Die Anzahlung löst keinen zweiten Erwerb aus.
2. **Späte Rechnung:** Bei Erwerb im Dezember 2025 und Rechnung nach Ablauf
   des Januar 2026 ist die Erwerbsteuer spätestens der Periode Januar 2026
   zugeordnet. Die spätere Rechnung verschiebt den Erwerb nicht erneut.
3. **Steuerstatus und Vorsteuer:** Derselbe steuerpflichtige Erwerb erzeugt
   bei einem regelbesteuerten Mandanten mit vollem Vorsteuerrecht 190 EUR
   Vorsteuer in KZ 61. Bei fehlendem oder teilweisem Vorsteuerrecht wird nur
   der belegte Betrag ausgewiesen; bei einem Kleinunternehmer 0 EUR.
   Ein späterer Wechsel von `tax.mode` ändert diese gespeicherten Werte nicht.
4. **OSS-Umsatzarten:** Ein Warenfernverkauf und eine digitale B2C-Leistung
   in einem anderen EU-Staat werden mit eigener Umsatzart, Verbrauchsstaat,
   dortigem Steuersatz und Steuerperiode erfasst. Der OSS-Bericht gruppiert
   beide im passenden Quartal; die deutsche UStVA enthält ihre ausländische
   Steuer nicht.
5. **OSS-Zahlungsfluss:** Ein vereinnahmter Bruttobetrag erscheint im
   EÜR-Zahlungsjahr. Die später gezahlte ausländische OSS-Steuer erscheint
   nur einmal als Ausgabe im Zahlungsjahr. Der OSS-Bericht führt den
   steuerlichen Umsatz unabhängig von diesen Zahlungstagen im passenden
   Quartal.
6. **Korrektur und Nullmeldung:** Eine Erstattung verweist auf den
   ursprünglichen OSS-Umsatz; der Bericht zeigt Ursprungs- und
   Korrekturquartal getrennt. Für ein registriertes Quartal ohne Umsatz
   zeigt er ausdrücklich eine mögliche Nullmeldung. Unvollständige Angaben
   führen zu einer konkreten Warnung statt zu stiller Zuordnung.
7. **Bestand und Migration:** Bestehende EU-Dienstleistungen bleiben
   unverändert, Altbuchungen werden nicht automatisch als Warenerwerb oder
   OSS umgedeutet. Nach Migration liefern 2025er und 2026er Erwerbe nur
   die für ihr Formularjahr verifizierten Kennziffern.

## Amtliche Quellen

- [§ 11 Abs. 2 EStG: Abflussprinzip](https://www.gesetze-im-internet.de/estg/__11.html)
- [§ 1a UStG: Erwerb und Erwerbsschwelle](https://www.gesetze-im-internet.de/ustg_1980/__1a.html)
- [§ 13 Abs. 1 Nr. 6 UStG: Erwerbsteuer](https://www.gesetze-im-internet.de/ustg_1980/__13.html)
- [§ 15 UStG: Vorsteuerabzug](https://www.gesetze-im-internet.de/ustg_1980/__15.html)
- [§§ 16 Abs. 1d, 18j UStG: OSS-EU-Regelung](https://www.gesetze-im-internet.de/ustg_1980/__18j.html)
- [BZSt: One-Stop-Shop, EU-Regelung](https://www.bzst.de/DE/Unternehmen/Umsatzsteuer/One-Stop-Shop_EU/one_stop_shop_eu.html)
- [BMF: UStVA-Vordruck und Anleitung 2025](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Umsatzsteuer/2024-12-09-voranmeldungs-vorauszahlungsverf-2025.pdf?__blob=publicationFile&v=4)
- [BMF: UStVA-Vordruck und Anleitung 2026](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Umsatzsteuer/2025-12-29-vordruckmuster-USt-voranmeldung-2026.pdf?__blob=publicationFile&v=7)
