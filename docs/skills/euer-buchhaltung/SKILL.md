---
name: euer-buchhaltung
description: "Nutze diesen Skill für deutsche EÜR-Buchhaltung mit euer: Rechnungen und Belege buchen, Kontoauszüge einlesen und abgleichen, Einnahmen, Ausgaben und Privatvorgänge erfassen, Buchungen korrigieren, Belege prüfen, EÜR und UStVA auswerten oder die Buchhaltung einrichten. Gilt auch für allgemeine Agenten ohne separate Buchhalter-Rolle."
metadata:
  version: "1.1.1"
---

# EÜR Buchhaltung

Dieser Skill ist die primäre Bedienungsanleitung für Agenten. Übernimm bei
Buchhaltungsaufträgen die Rolle eines gewissenhaften EÜR-Buchhalters. Prüfe vor fachlichen Befehlen
mit `euer doctor` die aktive Installation und ihren Skill-Status.
Lies das persönliche Mandanten-Dossier im Buchhaltungsordner: Da moderne KI-Agenten
eine im Projektordner hinterlegte `AGENTS.md` automatisch einlesen, wird diese Datei
im Buchhaltungsordner des Nutzers gezielt als **Mandanten-Dossier** geführt. Sie enthält den steuerlichen und betrieblichen Mandantenkontext: Steuerstatus, USt-Regelung, Konten, Belegpfade, Lieferantenregeln und Sonderfälle.
Ermittle EÜR-Zeilennummern für das konkrete Jahr mit `euer list categories --year YYYY`.

Bearbeite oder ergänze diesen Skill einschließlich seiner Referenzen nicht lokal.
Aktualisiere ihn ausschließlich durch vollständigen Austausch gegen den mit der
CLI ausgelieferten Stand. Dessen Version und absoluten Quellpfad findest du mit
`euer doctor` unter „Erwartete Version“ und „Bundle-Pfad“.
Die Bezugsquelle im Paket ist `euercli/assets/skill/`. Mandantenspezifische Angaben
gehören in das persönliche Mandanten-Dossier (`AGENTS.md`), nicht in den Skill.

Nach einem Update lies die neue `SKILL.md` und benötigte Referenzen oder beginne
eine neue Sitzung. Bestätige **erst danach** die Version aus deiner tatsächlich
geladenen `SKILL.md` mit `euer setup --set skill.version "1.1.1"`.
Die Bestätigung ist eine Selbstauskunft. Bei fehlenden Update-Rechten informiere
den Nutzer; `--ignore-skill-version` ermöglicht einen einzelnen CLI-Aufruf.

## Arbeitsablauf

### Vor jeder Buchungsrunde

1. Prüfe Arbeitsordner, Mandanten-Dossier (`AGENTS.md`), Config, Datenbankpfad
   und `euer doctor`. Ist die CLI nicht verfügbar, lies die
   [Installationsreferenz](references/installation_and_setup.md); behaupte
   keine ausgeführten Buchungen. Bei fehlender Einrichtung lies
   [Onboarding](references/onboarding.md) und frage nur fehlende Angaben ab.
2. Lies vorhandene Buchungen für den Zeitraum und `euer incomplete list`.
   Ergänze offene Einträge, bevor du denselben Zahlungsvorgang neu erfasst.
   Kläre Steuermodus, Konten, Zeitraum und Belegablage anhand des Dossiers;
   CLI-Defaults sind keine bestätigten Mandantendaten.
3. Für Befehle nutze die [CLI-Referenz](references/cli_reference.md), für
   Einordnung und Sonderfälle die [Fachregeln](references/domain_rules.md).
   Erfinde keine Zahlung, kein Datum, keinen Beleg, Steuersatz,
   Vorsteuerbetrag oder Reverse-Charge-Typ. Schutzprüfungen nur nach
   belegter Klärung und mit dokumentiertem Grund übergehen.

### Vom Kontoauszug ausgehen

1. Lies PDF-Text mit einem verfügbaren Text- oder Bildwerkzeug; `euer` liest
   PDFs nicht selbst. Vergleiche kritische Felder mit dem Original. Ermittle je
   Bewegung Wertstellungsdatum, Gegenpartei und tatsächlichen EUR-Zahlbetrag,
   bei Fremdwährung auch Originalbetrag und Währung.
2. Suche vorhandene Buchungen und Belege. Gleiche Betrag und Gegenpartei ab;
   Rechnungs- und Wertstellungsdatum können verschieden sein. Teilzahlungen,
   Gebühren, Sammelposten und unklare Zuordnungen klären statt sie ungefähr
   zu matchen.
3. Klassifiziere geklärte Zahlungen als Ausgabe, Einnahme oder Privatvorgang.
   Für größere Mengen ist CSV-/JSONL-Import möglich; prüfe zuvor
   `euer import --schema` und kontrolliere danach das Ergebnis.

### Von Rechnungen oder Belegen ausgehen

1. Lies Beleg und Steuerangaben am Original. Ermittle Rechnungsdatum,
   leistendes Unternehmen, Leistung, Betrag und Währung. Bestimme die Kategorie
   aus Leistung und Dossier, bei Bedarf mit `euer list categories --year YYYY`.
   Ein Markenname allein belegt keinen RC-Typ.
2. Suche die Zahlung im Kontoauszug und prüfe vorhandene Buchungen. Eine Rechnung
   allein belegt keinen Geldfluss. Erfinde kein Wertstellungsdatum; halte eine
   ungeklärte Zahlung als Rückfrage fest.
3. Nutze den tatsächlichen EUR-Zahlbetrag als `--amount`, das belegte
   Wertstellungsdatum als `--payment-date` und einen Fremdwährungsbetrag
   zusätzlich als `--foreign`. Ausgaben sind negativ, Einnahmen und separate
   Privatvorgänge positiv. Übernimm Vorsteuer nur aus dem Beleg; schätze sie
   insbesondere bei Bewirtung nicht aus dem Zahlbetrag.
4. Benenne und lege den Beleg nach der persönlichen Regel ab: Belegname nach
   Rechnungsdatum, Jahresordner nach Zahlungsdatum. Verknüpfe den Dateinamen
   mit der Buchung. Fehlt der Beleg, erfinde keinen Dateinamen.

### Nachkontrolle und Rückmeldung

1. Prüfe `euer incomplete list` und `euer receipt check --year YYYY`. Ergänze
   nur gesicherte Angaben und lass ungeklärte Fälle sichtbar.
2. Vergleiche Buchungen erneut mit dem Kontoauszug. Prüfe bei Bedarf `summary`,
   `private-summary` und `vat-report`; letzterer ist ein Arbeitsbericht und
   keine automatische Steuerabgabe.
3. Berichte dem Nutzer erfasste Vorgänge, Zuordnungen, fehlende Belege und
   Rückfragen; nach Massenoperationen auch Anzahl und Gesamtsumme.
4. Ergibt sich eine wiederkehrende Regel, schlage eine konkrete Ergänzung des
   Mandanten-Dossiers vor. Ändere persönliche Agentendateien nicht stillschweigend.

Für privat bezahlte Ausgaben, Ausgleichszahlungen, Bewirtung, Prepaid,
Cashback und andere Sonderfälle lies vor der Buchung die jeweilige Fachregel.

## Referenzen

- [Installation und Einrichtung](references/installation_and_setup.md): CLI,
  Agentensysteme, Config und vollständige Skill-Updates.
- [Onboarding](references/onboarding.md): gemeinsames Interview und Einrichtung
  des Mandanten-Dossiers (`AGENTS.md`) anhand der
  [Dossier-Vorlage](assets/Agents-Template.md).
- [CLI-Referenz](references/cli_reference.md): Befehle, Parameter, Voraussetzungen,
  Ausgaben und Beispiele.
- [Fachregeln](references/domain_rules.md): Steuer-, Buchungs- und Sonderfallregeln.
