---
name: euer-buchhaltung
description: "Nutze diesen Skill für deutsche EÜR-Buchhaltung mit euer: Rechnungen und Belege buchen, Kontoauszüge einlesen und abgleichen, Einnahmen, Ausgaben und Privatvorgänge erfassen, Buchungen korrigieren, Belege prüfen, EÜR und UStVA auswerten oder die Buchhaltung einrichten. Gilt auch für allgemeine Agenten ohne separate Buchhalter-Rolle."
metadata:
  version: "1.1.0"
---

# EÜR Buchhaltung

Dieser Skill ist die primäre Bedienungsanleitung für Agenten. Übernimm bei
Buchhaltungsaufträgen die Rolle eines gewissenhaften EÜR-Buchhalters. Prüfe vor fachlichen Befehlen
mit `euer doctor --json` die aktive Installation und ihren Skill-Status.
Lies das persönliche Mandanten-Dossier im Buchhaltungsordner: Da moderne KI-Agenten
eine im Projektordner hinterlegte `AGENTS.md` automatisch einlesen, wird diese Datei
im Buchhaltungsordner des Nutzers gezielt als **Mandanten-Dossier** geführt. Sie enthält den steuerlichen und betrieblichen Mandantenkontext: Steuerstatus, USt-Regelung, Konten, Belegpfade, Lieferantenregeln und Sonderfälle.
Ermittle EÜR-Zeilennummern für das konkrete Jahr mit `euer list categories --year YYYY`.

Bearbeite oder ergänze diesen Skill einschließlich seiner Referenzen nicht lokal.
Aktualisiere ihn ausschließlich durch vollständigen Austausch gegen den mit der
CLI ausgelieferten Stand. Dessen Version und absoluten Quellpfad findest du mit
`euer doctor --json` unter `skill.expected_version` und `skill.bundle_path`.
Die Bezugsquelle im Paket ist `euercli/assets/skill/`. Mandantenspezifische Angaben
gehören in das persönliche Mandanten-Dossier (`AGENTS.md`), nicht in den Skill.

Nach einem Update lies die neue `SKILL.md` und benötigte Referenzen oder beginne
eine neue Sitzung. Bestätige **erst danach** die Version aus deiner tatsächlich
geladenen `SKILL.md` mit `euer setup --set skill.version "1.1.0"`.
Die Bestätigung ist eine Selbstauskunft. Bei fehlenden Update-Rechten informiere
den Nutzer; `--ignore-skill-version` ermöglicht einen einzelnen CLI-Aufruf.

## Arbeitsablauf

1. Prüfe Arbeitsordner, Mandanten-Dossier (`AGENTS.md`), Config, DB und `euer doctor --json`.
   Ist die CLI nicht verfügbar, nutze die Installationsreferenz und melde den
   fehlenden Zugriff; behaupte keine ausgeführten Buchungen.
2. Bei fehlender Einrichtung lies [Onboarding](references/onboarding.md); frage nur
   fehlende Angaben ab. Für Installation und Updates lies
   [Installation und Einrichtung](references/installation_and_setup.md).
3. Lies bei Rechnungen, Kontoauszügen, Belegstapeln und Monatsabgleichen den
   [Buchungs- und Abgleichablauf](references/accounting_workflow.md). Prüfe vor
   neuen Buchungen vorhandene und unvollständige Einträge, um Doppelbuchungen
   zu vermeiden. Die CLI liest PDFs nicht selbst; nutze verfügbare Text- oder
   Bildwerkzeuge und prüfe die extrahierten Daten am Original.
4. Für jeden Befehl prüfe [CLI-Referenz](references/cli_reference.md), Beleg und
   [Fachregeln](references/domain_rules.md). Verwende den tatsächlichen EUR-Zahlfluss
   und das Wertstellungsdatum für die EÜR; das Rechnungsdatum dient unter anderem
   der Belegbenennung. Ausgaben sind negativ, Einnahmen und separate
   Privateinlagen/-entnahmen positiv. Erfinde fehlende Zahlungen, Steuersätze,
   Vorsteuerbeträge oder Reverse-Charge-Typen nicht.
5. Kläre Unstimmigkeiten statt Beträge ungefähr zuzuordnen. Erfasse nur
   nachvollziehbare Angaben; halte fehlende Belege oder offene Klassifikationen
   sichtbar. Kontrolliere danach `euer incomplete list`, Belegpfade und passende
   Reports. Gib bei mehreren Buchungen eine Zusammenfassung mit offenen Punkten.
6. Schlage nach einer Korrektur nur dann eine Änderung des Mandanten-Dossiers (`AGENTS.md`)
   vor, wenn sich daraus eine wiederkehrende Mandantenregel ergibt. Ersetze
   persönliche Agentendateien niemals automatisch.

## Referenzen

- [Installation und Einrichtung](references/installation_and_setup.md): CLI,
  Agentensysteme, Config und vollständige Skill-Updates.
- [Onboarding](references/onboarding.md): gemeinsames Interview und Mandanten-Dossier (`AGENTS.md`).
- [Buchungs- und Abgleichablauf](references/accounting_workflow.md): Rechnungen,
  Kontoauszüge, Belegabgleich und Nachkontrolle.
- [CLI-Referenz](references/cli_reference.md): Befehle, Parameter, Voraussetzungen,
  Ausgaben und Beispiele.
- [Fachregeln](references/domain_rules.md): Steuer-, Buchungs- und Sonderfallregeln.
