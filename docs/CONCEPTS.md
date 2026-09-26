# Konzept und Grenzen

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
