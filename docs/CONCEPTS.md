# Konzept und Grenzen

## Philosophie: Agent-First Buchhaltung

`euer` ist von Grund auf dafür konzipiert, von **KI-Agenten als primäre Nutzer**
bedient zu werden. Der Mensch hinter dem Agenten führt die CLI-Befehle im Alltag in
der Regel nicht selbst aus, sondern delegiert die Buchhaltung; sein Hauptinteresse
ist, dass der Agent die EÜR autonom, verlässlich und vor allem **möglichst fehlerfrei**
übernimmt.

- **Deterministische Guardrails:** Eindeutige Parameter, verlässliche Ausgaben
  und strikte Validierungen schützen den Agenten vor Fehlinterpretationen.
- **Lückenloser Audit-Trail:** Jede Buchung und Änderung wird in der Historie festgehalten,
  sodass alle Aktionen des Agenten transparent und nachvollziehbar bleiben.
- **Klare Rollenteilung:** Der Mensch trägt die steuerliche Letztverantwortung und Freigabe,
  während der Agent die Belege auswertet, Vorprüfungen durchführt und per CLI bucht.

## Das AGENTS.md-Konzept: Mandanten-Dossier statt Coding-Anweisungen

Da moderne KI-Agenten (Claude Code, Cursor, Codex, OpenCode etc.) standardmäßig eine
im Projektordner liegende `AGENTS.md` einlesen, nutzt `euer` diese Konvention gezielt:

- **Mandanten-`AGENTS.md` (im Buchhaltungsordner):**
  Im Buchhaltungsordner des Nutzers wird eine `AGENTS.md` abgelegt (Vorlage:
  `docs/templates/Agents-Template.md`). Diese enthält **keine Coding- oder Programmierregeln**,
  sondern spiegelt das **Mandanten-Dossier** wider: Steuerstatus, USt-Regelung,
  Bankkonten, Belegpfade, Zuordnungsregeln wiederkehrender Lieferanten und individuelle
  Arbeitsregeln des Mandanten.

## Grundbegriffe

- **Ausgaben** haben immer **negative** Beträge (`--amount -10.00`).
- **Einnahmen** haben immer **positive** Beträge (`--amount 10.00`).
- **Privateinlagen/Privatentnahmen** (`add private-*`) verwenden immer **positive** Beträge; die Richtung ergibt sich aus dem Command.
- **Kategorien** sind vorgegeben und müssen existieren: `euer list categories`.
- **Buchungskonten** (`--ledger-account`) sind optional und werden in der Config als
  `[[ledger_accounts]]` gepflegt. Sie setzen die Kategorie automatisch.
- **Datumsfelder**: `payment_date` (Wertstellung, EÜR-relevant) und `invoice_date` (Rechnungsdatum).
  Mindestens eines der beiden muss gesetzt sein.
- **Belege** können geprüft und geöffnet werden, wenn Pfade konfiguriert sind.
- **Datenbank**: Standard `euer.db` im **aktuellen Verzeichnis**; `.euer/config.toml`
  kann pro Projekt einen anderen Pfad speichern. `--db PFAD` gilt für einen Aufruf.
- **Arbeitsverzeichnis**: Das Tool liest dort die Projekt-Config und verwendet
  ohne gespeicherten Pfad `./euer.db`. Wechsle vor dem Arbeiten in deinen
  Buchhaltungsordner!

## Grenzen

`euer` ist ein lokales CLI für nachvollziehbare EÜR-Buchungen und Arbeitsberichte.
Die CLI liest keine Belege selbst und übermittelt keine Steuererklärung an ELSTER.
Der Agent prüft Belege und offene fachliche Fragen; der Mensch verantwortet die
abschließende Prüfung und Abgabe. Für Befehle und Fachregeln siehe den
[Buchhaltungs-Skill](skills/euer-buchhaltung/SKILL.md).
