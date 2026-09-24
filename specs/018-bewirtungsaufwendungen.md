# Spec 018: Bewirtungsaufwendungen, Vorsteuer und EÜR-Zuordnung

## Status

Offen

## Ziel

Geschäftliche Bewirtungen werden als **ein Zahlungsvorgang** erfasst. Aus dem
tatsächlichen Zahlbetrag und der belegten, abziehbaren Vorsteuer ermittelt der
Service den abziehbaren und nicht abziehbaren Aufwand je Buchung. `summary`,
`vat-report`, Import und Export verwenden dieselben gespeicherten Grundlagen.
Unvollständige Altbuchungen werden sichtbar, ohne Steuerbeträge zu schätzen.

## Amtliche Grundlage und Formularjahr

- § 4 Abs. 5 Satz 1 Nr. 2 und Abs. 7 EStG: 70 % der angemessenen und
  nachgewiesenen geschäftlichen Bewirtungskosten sind abziehbar; getrennte
  Aufzeichnung ist erforderlich.
- § 15 Abs. 1 und 1a UStG: Die 30-%-Kürzung begrenzt den Vorsteuerabzug für
  angemessene und nachgewiesene Bewirtung nicht. Die übrigen Voraussetzungen
  des Vorsteuerabzugs gelten weiterhin.
- Amtliche Anlage EÜR **2025**: Bewirtung in **Zeile 63**, Vorsteuer in
  **Zeile 57**. Amtliche Anlage EÜR **2026**: Bewirtung in **Zeile 64**,
  Vorsteuer in **Zeile 58**. Die Bewirtungszeile hat jeweils getrennte Felder
  für abziehbare und nicht abziehbare Beträge; 2026 ist Zeile 63 für Geschenke.
- Quellen: https://www.gesetze-im-internet.de/estg/__4.html ;
  https://www.gesetze-im-internet.de/ustg_1980/__15.html ;
  https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Einkommensteuer/2025-08-29-anlage-EUER-2025.pdf?__blob=publicationFile&v=2 ;
  https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Einkommensteuer/2026-09-01-anlage-EUER-2026.pdf?__blob=publicationFile&v=4

Die Zeilennummern sind **Formularjahr-Metadaten**, keine dauerhafte Eigenschaft
einer Kategorie. Für Jahre ohne geprüftes Mapping keine ELSTER-Zeile behaupten.
Die bestehende `categories.eur_line = 63` für Bewirtung darf 2026 nicht direkt
als Formularzeile ausgegeben werden.

### Jährliche Pflege und Mein ELSTER

Das BMF veröffentlicht den amtlichen Vordruck **und** verweist für die
elektronische Abgabe auf den amtlich vorgeschriebenen Datensatz in Mein
ELSTER. Die ELSTER-Online-Hilfe 2025 verwendet für Bewirtung Zeile 63 und
für deren Vorsteuer Zeile 57, also dieselben Positionen wie der BMF-Vordruck.
Für 2026 liegt der BMF-Vordruck vor; eine öffentlich zugängliche
ELSTER-Online-Hilfe bzw. die konkrete Eingabemaske für EÜR 2026 konnte am
24.09.2026 noch nicht unmittelbar gegengeprüft werden. Die 2026-Zeilen
sind deshalb **amtlich bestätigt**, aber nicht als bereits gegen die
veröffentlichte Online-Maske geprüft zu kennzeichnen. Bei Bereitstellung
von Mein ELSTER 2026 folgt diese zweite Prüfung.

Quellen: https://www.elster.de/eportal/formulare-leistungen/alleformulare/euer ;
https://www.elster.de/eportal/helpGlobal?themaGlobal=help_euer_ufa_77_2025 ;
https://www.elster.de/eportal/infoseite/bereitstellungstermine

Implementierungsziel ist eine **lokal mitgelieferte, versionierte
Formularzuordnung** nach Jahr und fachlichem Feldschlüssel, zum Beispiel
`entertainment_deductible` und `entertainment_non_deductible`. Ein Eintrag
enthält Formularjahr, Zeile, Feldbezeichnung, gegebenenfalls amtliche
Kennzahl, Primärquelle und Prüfstatus (`bmf_verified`, `elster_verified`).
Kennzahlen können beim Abgleich helfen, sind aber selbst jahresabhängig
zu prüfen und ersetzen keinen fachlichen Schlüssel. Die Buchungen speichern
keine Zeilennummern; der Report wählt die Zuordnung anhand des
**Berichtsjahrs**. Eine Prüfung der Zuordnung gegen amtliche Quellen sowie
Regressionstests für unterstützte Jahre gehören in den Release-Prozess.

Neue Formularjahre brauchen stets eine geprüfte Datenaktualisierung.
Für ein rein offline verteiltes CLI ist dafür grundsätzlich ein Paket-Release
nötig; alternativ kann ein separat versioniertes, lokal installierbares und
verifiziertes Formular-Datenpaket aktualisiert werden. Ein ungeprüfter
Live-Abruf oder das Fortführen der Vorjahresnummern ist ausgeschlossen.
Ist das Jahr noch nicht unterstützt, zeigt die CLI Kategorie-/Feldnamen und
Beträge ohne ELSTER-Zeile und meldet den fehlenden Formularstand. Die
fachliche Buchung und 70/30-Berechnung funktionieren weiterhin offline.

### Inventur aller aktuell hinterlegten Zeilen

Abgleich von `euercli/schema.py:SEED_CATEGORIES` mit den amtlichen
Anlagen EÜR 2025 und 2026. Die Spalte „gespeichert“ ist der aktuelle
Core-Seed, nicht die richtige Zeile für jedes Jahr.

| Ausgabenkategorie | Gespeichert | EÜR 2025 | EÜR 2026 |
|---|---:|---:|---:|
| Waren, Rohstoffe und Hilfsstoffe | 27 | 27 | 29 |
| Bezogene Fremdleistungen | 29 | 29 | 30 |
| Aufwendungen für geringwertige Wirtschaftsgüter (GWG) | 36 | 36 | 37 |
| Telekommunikation | 43 | 43 | 44 |
| Übernachtungs- und Reisenebenkosten | 44 | 44 | 45 |
| Fortbildungskosten | 45 | 45 | 46 |
| Rechts- und Steuerberatung, Buchführung | 46 | 46 | 47 |
| Beiträge, Gebühren, Abgaben und Versicherungen | 49 | 49 | 50 |
| Laufende EDV-Kosten | 50 | 50 | 51 |
| Arbeitsmittel | 51 | 51 | 52 |
| Werbekosten | 54 | 54 | 55 |
| Gezahlte USt (Zahlung ans Finanzamt) | **57** | **58** | **59** |
| Übrige Betriebsausgaben | 60 | 60 | 61 |
| Bewirtungsaufwendungen | 63 | 63 | 64 |
| Verpflegungsmehraufwendungen | 64 | 64 | 65 |
| Fahrtkosten (Nutzungseinlage) | 71 | 71 | 72 |

`Gezahlte USt` ist schon im 2025-Seed um eine Zeile falsch; sie darf nicht
mit der **abziehbaren Vorsteuer** verwechselt werden (2025 Zeile 57,
2026 Zeile 58). 2026 wurde im Ausgabenbereich vor den Waren eine neue
Position eingefügt. Daher wandert „Waren“ von 27 auf 29, die weiteren
hier aufgeführten Ausgabenpositionen überwiegend um eine Zeile.

| Einnahmen-/Privatposition | Gespeichert/CLI | EÜR 2025 | EÜR 2026 |
|---|---:|---:|---:|
| Betriebseinnahmen als Kleinunternehmer | 12 | 12 | 12 |
| Davon nicht steuerbare KU-Umsätze (§ 19 Abs. 2 UStG) | 13 | 13 | 13 |
| Umsatzsteuerpflichtige Betriebseinnahmen | 15 | 15 | 15 |
| Umsatzsteuerfreie/nicht umsatzsteuerbare Betriebseinnahmen | 16 | 16 | 16 |
| Vereinnahmte Umsatzsteuer | 17 | 17 | 17 |
| Vom Finanzamt erstattete Umsatzsteuer | 18 | 18 | 18 |
| Veräußerung oder Entnahme von Anlagevermögen | 19 | 19 | 19 |
| Private Kfz-Nutzung | 20 | 20 | 20 |
| Sonstige Sach-, Nutzungs- und Leistungsentnahmen | 21 | 21 | 21 |
| Privatentnahmen | **121** | **106** | **107** |
| Privateinlagen | **122** | **107** | **108** |

Die Kategorie `Nicht steuerbare Umsätze` ist mit Zeile 13 **zu allgemein
benannt**: Diese Zeile ist ein „davon“-Feld innerhalb der
Kleinunternehmer-Einnahmen, keine eigenständige allgemeine Erlösposition.
Derzeit könnten Agenten denselben Umsatz in Zeile 12 und 13 als zwei
separate `income`-Buchungen erfassen oder nicht steuerbare Umsätze von
Regelbesteuerten falsch dorthin buchen. Die Kategorisierung und die
Summierung dieses Unterfelds müssen fachlich neu gefasst werden.

`private-summary` und `summary --include-private` behaupten derzeit
Zeilen 121/122; diese Angaben stimmen weder 2025 noch 2026. Auch die
entsprechende Agenten-Skill-Überschrift ist veraltet. `incomplete.py`
erkennt „Gezahlte USt“ teilweise über eine **feste Zeile 58**: Das ist
2025 die gezahlte USt, aber 2026 die Vorsteuer. Die Belegausnahme muss
an eine stabile Kategorieidentität/Fachklassifikation gebunden werden.

Bei der Umsetzung alle direkten Verbraucher von `categories.eur_line`
einbeziehen: `summary`, `list`, `setup`, `export`, `incomplete`,
`get_category_display` sowie Agenten-Skill und Nutzerdokumentation.
`init` ergänzt Seeds bisher nur und aktualisiert bekannte Altzeilen kaum;
ein bloßer Seed-Edit korrigiert bestehende SQLite-Datenbanken daher nicht.
Ein jahresabhängiges Mapping nach **stabilem fachlichem Kategorie-Schlüssel**
ist vorzuziehen; bestehende Kategorie-IDs, Namen und Buchungsreferenzen
bleiben erhalten. Ausgaben ohne Jahr sollen die Zeile nicht als aktuelle
ELSTER-Anweisung ausgeben. Für den Import von Kategorienlabels mit
historischer `(Zeile)`-Nummer weiterhin den Namen maßgeblich behandeln.

Im Schwester-Repository `euer-website` sind neben dem Bewirtungsratgeber
weitere feste Angaben zu prüfen: `src/app/docs/page.tsx` nennt u. a.
Arbeitsmittel/EDV zusammen als 51, Telekommunikation als 53 und Bewirtung
als 62. Für 2026 sind Arbeitsmittel 52, laufende EDV-Kosten 51,
Telekommunikation 44 und Bewirtung 64. Die Creator-Demo nennt
Arbeitsmittel 51 statt 52. Der Reverse-Charge-Ratgeber nennt für eine
Software-Ausgabe „51 oder 53“; die Zuordnung muss von der tatsächlichen
Kostenart abhängen, während die Einnahmenangabe Zeile 16 für den dort
beschriebenen nicht steuerbaren Umsatz weiterhin passt. Diese Texte bei
der Website-Korrektur getrennt vom Core aktualisieren.

## Rechenregel

Pro Buchung in Cent und mit definiertem Rundungsverfahren:

1. `paid = abs(amount_eur)` ist der gesamte Zahlungsabgang einschließlich
   freiwilligem Trinkgeld.
2. `input_vat` ist nur der **tatsächlich abziehbare und belegte** Vorsteuerbetrag
   aus dem Restaurantentgelt. Er wird nicht aus `paid` und einem pauschalen
   Steuersatz zurückgerechnet.
3. `cost_basis = paid - input_vat`; freiwilliges, belegtes Trinkgeld ohne
   Vorsteuer bleibt darin enthalten.
4. `deductible = round_cent(cost_basis * 0.70)`;
   `non_deductible = cost_basis - deductible`.
5. EÜR: `deductible` und `non_deductible` in getrennte Felder **derselben**
   Bewirtungszeile. Abziehbare Vorsteuer separat in der Vorsteuerzeile.
6. Für die Gewinnrechnung dürfen Zahlungsabgang, Vorsteuer und Kürzung nicht
   doppelt oder gar nicht berücksichtigt werden: der steuerlich wirksame
   Ausgabenbetrag des Beispiels ist `deductible + input_vat`. Die Darstellung
   muss Bewirtungsaufwand und Vorsteuer als eigene Komponenten zeigen.

Beispiel: Zahlung 129,00 €, belegte und abziehbare Vorsteuer 19,00 €,
freiwilliges Trinkgeld 10,00 € → Kostenbasis 110,00 €, Bewirtung abziehbar
77,00 €, nicht abziehbar 33,00 €, Vorsteuer 19,00 €. Für 2026 sind 77,00 €
und 33,00 € die beiden Felder in Zeile 64; 19,00 € gehören in Zeile 58.
Der gewinnwirksame Ausgabenbetrag aus diesem Zahlungsvorgang beträgt 96,00 €.
Ohne Vorsteuerabzug: Kostenbasis 129,00 €, abziehbar 90,30 €,
nicht abziehbar 38,70 €; keine Vorsteuerzeile aus diesem Beleg.

Die 30 % sind gesetzlich nicht abziehbar und werden **nicht** automatisch als
Privatentnahme angelegt. Bewirtung ausschließlich eigener Arbeitnehmer fällt
nicht unter diese 70/30-Regel; sie darf nicht als diese Kategorie klassifiziert
werden. Unangemessene, private oder nicht hinreichend nachgewiesene Anteile
erfordern gesonderte Prüfung und dürfen nicht automatisch als voll
vorsteuerabziehbare 70/30-Bewirtung gelten.

## Datenmodell und Service

- `expenses.amount_eur` bleibt der signierte gesamte Zahlbetrag;
  `expenses.vat_input` bleibt der separat gespeicherte abziehbare
  Vorsteuerbetrag und die Grundlage des USt-Reports.
- Additive Felder an `expenses`: optionaler `entertainment_tip_eur` als
  Nachweis- und Plausibilitätsinformation sowie ein expliziter
  `entertainment_vat_status` mit Zuständen `deductible`, `no_deduction`,
  `needs_review`. Letzterer hält die Behandlung **pro Buchung** fest, damit
  ein späterer Wechsel des globalen Steuermodus frühere Jahre nicht ändert.
  Ein fehlender Trinkgeldwert bedeutet „nicht erfasst“, nicht „kein Trinkgeld“.
- Der Service validiert Cent-Beträge, Vorzeichen, `0 <= input_vat <= paid`,
  `0 <= tip <= paid - input_vat` und zulässige Status-/Betragskombinationen.
  Ein Trinkgeldbetrag erhöht `amount_eur` nicht nochmals. Bei gemischten
  Steuersätzen zählt die Summe der **auf dem Beleg ausgewiesenen** abziehbaren
  Vorsteuer; ein einzelner `vat_rate` ist dafür keine verlässliche Grundlage.
- Die 70/30-Logik und die Auflösung der Behandlungszustände liegen in
  `euercli/services/`; Commands bleiben View-Controller. Jede Mutation an
  `expenses` läuft über den Service und wird auditiert. `create`, `update`,
  Import, Export und Duplikatprüfung müssen die neuen Felder konsistent
  behandeln. Der bestehende Hash auf Zahlungsdatum/Lieferant/Betrag/Beleg
  bleibt für Bestandsdaten stabil.
- `init` migriert bestehende Datenbanken additiv und wiederholbar. Keine
  automatischen Änderungen an alten Beträgen oder Vorsteuerwerten.

## CLI und Agenten-Workflow

- Bestehendes `euer add expense --amount ... --category
  "Bewirtungsaufwendungen"` bleibt syntaktisch gültig. Für neue
  Standardmodus-Buchungen wird `--vat` als belegte **abziehbare** Vorsteuer
  verwendet; optionales `--tip` erfasst den enthaltenen Trinkgeldbetrag.
- `--vat 0` bedeutet nach expliziter Belegprüfung „kein Vorsteuerabzug“.
  Ein **weggelassenes** `--vat` bedeutet im Standardmodus „unbekannt“ und
  führt zu `needs_review`, nicht zu einer geschätzten Null. Im
  Kleinunternehmermodus wird `no_deduction` gespeichert; widersprüchliche
  Vorsteuerangaben werden abgewiesen statt still ignoriert.
- `update expense` kann Vorsteuer, Trinkgeld und Behandlungsstatus nachpflegen.
  Für Importe gibt es entsprechende benannte Spalten. CLI-Ausgabe zeigt
  Zahlbetrag, Vorsteuer, Kostenbasis und 70/30-Aufteilung oder einen
  klaren Prüfhinweis. Agenten lesen den Beleg und geben **keinen** aus dem
  Bankbetrag geschätzten Steuersatz ein.
- Wenn `vat_input` nicht auf voller Rechnungsvorsteuer beruht (z. B. nur
  teilweiser Vorsteuerabzug), muss die Rechnung die tatsächlich abziehbare
  Vorsteuer verwenden; die nicht abziehbare Steuer verbleibt in der
  Kostenbasis. Solche Fälle sind vor Freigabe fachlich zu prüfen.

## Bestandsdaten und unvollständige Ergebnisse

- Migration setzt alte Bewirtungsbuchungen auf `needs_review`, unabhängig
  vom heute eingestellten globalen Steuermodus. Auch `vat_input = 0` beweist
  historisch weder Kleinunternehmerstatus noch eine geprüfte Null-Vorsteuer.
- Alte Buchungen mit positivem `vat_input` dürfen einen **vorläufigen**
  rechnerischen Wert zeigen, bleiben aber bis zur Belegprüfung markiert.
  Buchungen ohne eindeutige Vorsteuerbehandlung erhalten keine als endgültig
  bezeichneten 70/30-Beträge. Keine stillen Nullannahmen und keine
  pauschale Umrechnung aller Altbuchungen beim Programmstart.
- `summary` nennt IDs und Anzahl prüfbedürftiger Bewirtungen. Bekannte
  Teilbeträge werden klar von unvollständigen Gesamtsummen getrennt; Gewinn
  und ELSTER-Werte werden bei offenen Fällen nicht als vollständig
  ausgegeben. `vat-report` kennzeichnet fehlende Vorsteuerdaten ebenfalls.
- Eine Nachpflege über `update expense` ändert nur die betroffene Buchung,
  mit Audit-Eintrag. Listen und Exporte behalten den ursprünglichen
  Zahlbetrag und ergänzen Status, Vorsteuer, Trinkgeld und berechnete Felder.

## Dokumentation und Release

Bei Implementierung `docs/USER_GUIDE.md`, Agenten-Skill und seine Referenzen,
Onboarding-Template, `README.md`, `DEVELOPMENT.md`, Release Notes und den
Website-Ratgeber abgleichen. Im Ratgeber das Beispielkommando um die belegte
Vorsteuer ergänzen und die tatsächliche CLI-Ausgabe zeigen; für das Beispieljahr
2026 Zeile 64/58 verwenden. Die Website liegt im Schwester-Repository und
benötigt eine eigene Änderung. Keine feste 19-%-Annahme für Speisen im Jahr
2026. Die Release Notes müssen die additive DB-Migration, die Nachpflege
alter Bewirtungen, die veränderte `summary`-Berechnung sowie die Korrektur
aller EÜR-Zeilennummern und des Zeile-13-Unterfelds erklären.

Die Implementierung ist ein nutzerwirksames abwärtskompatibles Feature mit
Steuerlogik-Änderung; vor Veröffentlichung Versionierung nach `DEVELOPMENT.md`
prüfen. Diese Spec allein ist Entwicklerdokumentation und löst keinen Release
aus.

## Akzeptanzkriterien

1. Standardmodus, 129,00 € Zahlung und 19,00 € belegte Vorsteuer:
   77,00 € / 33,00 € Bewirtung, 19,00 € Vorsteuer; keine doppelte
   Gewinnwirkung. `vat-report` behält den vollen Vorsteuerbetrag.
2. Kleinunternehmer mit derselben Zahlung: 90,30 € / 38,70 € und
   0,00 € Vorsteuer. Änderungen am aktuellen Config-Modus verändern diese
   historische Buchung nicht.
3. Gemischte 7-/19-%-Rechnung mit Trinkgeld: Vorsteuer wird aus belegten
   Steuerbeträgen übernommen; der Zahlbetrag lässt sich mit Kostenbasis und
   Vorsteuer centgenau abstimmen.
4. 2025-Auswertung bezeichnet Bewirtung als Zeile 63 und Vorsteuer als
   Zeile 57; 2026-Auswertung bezeichnet Bewirtung als Zeile 64 und Vorsteuer
   als Zeile 58. Abziehbar/nicht abziehbar sind Felder derselben
   Bewirtungszeile. Für ungemappte Jahre wird keine Nummer erfunden.
5. Altbuchungen bleiben betragsmäßig unverändert und sind bis zur Prüfung
   sichtbar. Fehlende Vorsteuer im Standardmodus führt weder zu einer
   geschätzten Vorsteuer noch zu einer endgültig wirkenden EÜR-Summe.
6. `add`, `update`, Import und Export erhalten dieselbe Buchungssemantik;
   wiederholtes `init` ist sicher und Änderungen sind auditiert.
7. Alle oben inventarisierten Kategorien werden für 2025 und 2026 gegen
   das richtige Formularjahr dargestellt; insbesondere werden Zahlungen
   ans Finanzamt nicht als Vorsteuer und private Transfers nicht als
   Zeilen 121/122 bezeichnet. Das Zeile-13-Unterfeld erzeugt keine
   doppelten Betriebseinnahmen.
