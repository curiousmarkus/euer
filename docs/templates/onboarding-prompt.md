# Onboarding: Persönliche Buchhaltung einrichten

Mit einem lokalen KI-Agenten genügt der vollständig installierte Skill
[`euer-buchhaltung`](../skills/euer-buchhaltung/SKILL.md), einschließlich seines
Ordners `references/`. Starte den Agenten im Buchhaltungsordner und sage:

> Richte meine Buchhaltung mit euer ein. Prüfe zuerst, was schon vorhanden ist,
> und frage nur die fehlenden Informationen ab.

Der Skill lädt bei Bedarf den
[Onboarding-Leitfaden](../skills/euer-buchhaltung/references/onboarding.md).
Dieser ist die gemeinsame Quelle für Interview, Mandanten-Dossier und Setup.
Ein separater LLM-Chat ist optional.

## Alternative: Interview in einem normalen LLM-Chat

Kopiere den folgenden Prompt in den Chat. Stelle zusätzlich den vollständigen
Inhalt des oben verlinkten Leitfadens bereit, falls der Chat die URL nicht lesen kann.
Der Chat liefert das Dossier und die Setup-Befehle; dein lokaler Agent oder du
führt anschließend die Einrichtung durch.

```text
Hilf mir, meine persönliche EÜR-Buchhaltung mit euer einzurichten.

Lies zuerst diesen Onboarding-Leitfaden:
https://raw.githubusercontent.com/curiousmarkus/euer/main/docs/skills/euer-buchhaltung/references/onboarding.md

Falls du den Leitfaden nicht abrufen kannst, bitte mich, seinen Inhalt einzufügen.
Übernimm vorhandene Angaben und führe das Interview nur für fehlende Informationen.
Stelle höchstens drei zusammengehörige Fragen auf einmal und warte auf meine Antwort.

Bei Bewirtungen Vorsteuer ausschließlich vom Beleg übernehmen, nie aus dem
Zahlbetrag schätzen. Die Buchungsregeln und nötigen Prüfangaben stehen im
Buchhaltungs-Skill.

Erstelle daraus meine persönliche AGENTS.md und konkrete Setup-Befehle für meine
Umgebung. Speichere Lieferantenregeln mit fachlicher Kategorie, Sitz und
Reverse-Charge-Typ, aber ohne feste EÜR-Zeilennummer; frage diese für das
Formularjahr über `euer list categories --year YYYY` ab. Erhalte eine vorhandene
AGENTS.md vollständig und schlage Änderungen daran gezielt vor. Kennzeichne
offene Punkte. Ohne lokalen Zugriff behaupte nicht, Dateien
oder Einstellungen geprüft oder geändert zu haben.
```
