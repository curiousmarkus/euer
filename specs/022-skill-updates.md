# Spec 022: Versionierte, sichere Skill-Aktualisierung & Skill-as-a-Package Architektur

## Status

Offen

## Originalfeedback (wörtlich)

> Der Skill sollte neben dem Software-Release eine klar ausgewiesene Version haben. Hilfreich wären eine Installations-/Update-Anleitung pro Agent und ein Diff, bevor lokale Dateien ersetzt werden. Nutzerregeln wie AGENTS.md sollten dabei niemals automatisch überschrieben werden. Ein als Vorschlag zu entwickelnder Skill-Updateweg sollte upstream-Inhalte und lokale Anpassungen getrennt behandeln, statt stillschweigend eine Seite zu ersetzen.
>
> Konkrete Empfehlung für dein Projekt
> Die Zuständigkeiten würde ich so trennen:
>
> AGENTS.md: alles, was für diesen Mandanten gilt: Steuerstatus, Konten, Belegablage, Lieferanten → Kategorie, Reverse-Charge-Fälle, gemischte Nutzung, N26-Cashback und Sonderregeln.
> Buchhaltungsskill: allgemeine Bedienung von euer: Befehle, Buchungs- und Datumslogik, Prüfabläufe, Migrationen und die Regel, zuerst die Projekt-AGENTS.md zu lesen.
> EÜR-Zeilennummern: möglichst nicht dauerhaft in AGENTS.md speichern. Sie hängen vom Formularjahr ab und sind im CLI mit euer list categories --year YYYY abrufbar. In der Lieferantentabelle reicht die fachliche Kategorie; Reverse Charge und Sitz bleiben sinnvoll.
> Eine kurze Toolchain-Angabe wie „Homebrew ist die Installationsquelle; Updates mit brew upgrade euer“ kann in AGENTS.md stehen, falls sie für die Arbeit im Projekt wichtig ist. Einen festen Binärpfad würde ich nur dort festhalten, wenn der PATH nicht zuverlässig ist.

## Learning & Konzept-Evolution

Paket, kopierter Skill und Mandanten-Dossier haben verschiedene Lebenszyklen.
Ein `pipx`- oder Brew-Update aktualisiert keine lokale Skill-Kopie. Das
Mandanten-Dossier ist Nutzerdatenbestand und darf bei Tool-/Skill-Updates nicht
automatisch ersetzt werden.

**Die Erkenntnis zur Dokumentation:** Bisher vermischte das `USER_GUIDE.md` Installationshilfen für den Menschen, Syntax-Referenzen für die KI und Steuerlogik. Da der KI-Agent der eigentliche Anwender der CLI ist, benötigt er direkten, strukturierten Zugriff auf diese Spezifikationen. Es führt zu Problemen, wenn Mensch und KI unterschiedliche Informationsstände haben.

**Die Lösung: "Skill-as-a-Package"**
Um sichere Updates und perfekte KI-Ausführung zu vereinen, wird die Dokumentation vollständig in den Skill integriert. Der Ordner `docs/skills/euer-buchhaltung/` wird zur versionierten, monolithischen "Read-Only Firmware" für den Agenten. 

Wir setzen damit eine absolut strikte Trennung um:
- **Code / Firmware (Darf komplett ersetzt werden):** Der gesamte Skill-Ordner inklusive aller Doku-Referenzen (`SKILL.md` + `references/*.md`).
- **State / Nutzerdaten (Darf NIE überschrieben werden):** Das persönliche `AGENTS.md` (Mandanten-Dossier).

Ein Update des Skills bedeutet durch diese Architektur automatisch ein Update der Dokumentation (Single Source of Truth). Mensch und KI lesen exakt denselben Wissensstand.

## Die Zielarchitektur

*   **Der Einstieg (Für den Menschen)**
    *   `README.md`: Der "Showroom". Fokussiert auf Fähigkeiten und bietet den Handoff-Prompt (Kopier-Vorlage für die KI zur Installation & Doku-Lektüre). Verlinkt für alle Doku-Details direkt in den Skill-Ordner.
    *   `docs/CONCEPTS.md`: Ein konzeptioneller Überblick für den Menschen (Trust-Building, Guardrails, Architektur, Sicherheit), der komplett ohne CLI-Syntax auskommt.

*   **Das Maschinen-Handbuch (Der Skill-Ordner)**
    *   📁 `docs/skills/euer-buchhaltung/`
        *   `SKILL.md`: Der Orchestrator. Definiert Rolle, zentrale Abläufe und dient als Index für die Referenzen. Enthält im Header eine klare Versionsnummer.
        *   📁 `references/`
            *   `installation_and_setup.md`: Anweisungen für den Agenten zur Systemeinrichtung (`pipx`, `brew`, `euer doctor`).
            *   `cli_reference.md`: Harte Befehlsspezifikation (Flags, Exklusiv-Regeln, JSON-Outputs).
            *   `domain_rules.md`: Fachliche Buchhaltungsregeln (Steuersätze, Bewirtungskosten).
            *   `faq.md`: Für Mensch und Maschine bei Troubleshooting.

## Upgrade-Vertrag je Release

Jede Release Note enthält nahe bei den DB-Upgrade-Schritten einen Block
„Agenten-Dateien“ mit vier getrennten Zeilen:

| Bereich | Angabe je Release |
|---|---|
| Skill-Package | Version vorher/nachher (inkl. Referenz-Dokus), Update nötig: ja/nein |
| Rolle | Version vorher/nachher, Änderung der gemeinsamen Rolle, Update nötig: ja/nein |
| Agenten-Adapter | Betroffene Systeme und Dateien; kompatibel/Update empfohlen/Update erforderlich |
| Mandanten-Dossier | Konkrete Prüfpunkte oder „keine Änderung“; niemals automatisches Ersetzen |

Die CI prüft, dass der Block bei Änderungen am Skill, den Referenzen, der Rolle oder Adaptern vorhanden ist. Das bereits publizierte Release wird nicht nachträglich ergänzt.

## Ablauf beim Nutzer (Sicheres Skill-Update)

1. **Bestand feststellen:** Aktive euer-Version und Installationskanal prüfen;
   Agentensystem, Profil/Projekt, lokale Skill- und Rollenpfade sowie deren
   Versionen (Header der `SKILL.md`) ermitteln.
2. **Passende Quelle laden:** Das gesamte Skill-Package (`euer-buchhaltung/` inkl. `references/`) vom Release-Tag der tatsächlich installierten euer-Version laden.
3. **Vorschau & Schutz:** 
   - Das persönliche Mandanten-Dossier (`AGENTS.md`) wird identifiziert und in jedem Fall geschützt.
   - Upstream-Basis, neues Upstream-Package und lokale Skill-Dateien
   vergleichen. Ausgabe: fachliche Änderung, Diff, vorgeschlagener Schritt.
4. **Anwenden:** Da der Skill-Ordner "zustandslos" ist, kann er bei fehlenden lokalen Anpassungen komplett ausgetauscht werden. Lokal bearbeitete
   Skill-Dateien erhalten einen Patch-Vorschlag;
   ohne Entscheidung des Menschen kein Überschreiben. Persönliche
   `AGENTS.md`/`CLAUDE.md`, globale `SOUL.md`, Config und andere
   Nutzerdaten werden nie automatisch ersetzt. 
5. **Nachprüfung:** Agent in einer neuen Sitzung starten, Laden des Skills und
   der Rolle prüfen, Versions-/Kompatibilitätsstand melden. Durch den vollständigen Ordner-Austausch hat der Agent nun sofort die aktuellen `references/` (wie die neue `cli_reference.md`) im Kontext.

Ein späterer Helfer darf Vorschau und Konflikterkennung automatisieren, muss
aber dieselben Grenzen einhalten. 

## Agentenspezifische Einbindung

| Agent | Ziel für euer | Grenze |
|---|---|---|
| Claude Code | Skill-Package plus optionaler eigener Subagent in `.claude/agents/` | Projekt-`CLAUDE.md` nur für lokale Mandantenregeln (State), nicht als Kopie der Rolle |
| OpenCode | Skill-Package plus optionaler eigener Agent in `.opencode/agents/` | Projekt-`AGENTS.md` bleibt Mandanten-Dossier (State) |
| Hermes | Skill-Package und gegebenenfalls projektbezogene Kontextdatei | Globale `SOUL.md` ist Identität; Änderungen daran nur als menschlich geprüfter Vorschlag |

**Zielbild:** Ein lokaler Adapter enthält nur dauerhafte Einstiegspunkte:
„Für Buchhaltungsaufträge `euer-buchhaltung` laden, persönliches Dossier lesen,
Release-Stand bei Versionswechsel prüfen.“ Neue CLI- oder Steuerregeln sowie Doku-Updates gehen vollständig in das Skill-Package. Damit erfordert ein normales euer-Release keine Änderung an
`SOUL.md`, `CLAUDE.md` oder einem Agentenprofil. 

## Anforderungen

- Separat sichtbare Skill-Version im `SKILL.md`-Header und dokumentierte Kompatibilität zu euer-Releases.
- Für unterstützte Agenten Installations- und Updatepfade dokumentieren.
- Persönliche `AGENTS.md`, Config und andere Mandantendaten nie automatisch
  überschreiben. 
- Das Skill-Package beinhaltet zwingend das gesamte Dokumentations-Set im `references/`-Ordner. Die traditionelle `USER_GUIDE.md` wird aufgelöst.
- Ein möglicher `euer skill update`-Befehl ist eine Option, keine bereits
  vorhandene Funktion. Vor Implementierung gegen dokumentierte manuelle
  Diff-Schritte abwägen.

## Akzeptanzfälle

- Nur CLI geändert: kein Agenten-Eingriff nötig.
- Skill-Package geändert (z. B. neues CLI-Flag in Doku): korrekter Release-Stand wird übernommen und Agent erhält automatisch das neue Wissen.
- Skill lokal angepasst: Diff und Konflikt sichtbar, keine stille Ersetzung.
- Claude Code/OpenCode mit projektbezogenem Agenten und persönlichem Dossier:
  Adaptervorschlag getrennt von Mandantenregeln (`AGENTS.md` wird ignoriert/geschützt).

## Dokumentation nach Implementierung

`README.md`, `docs/CONCEPTS.md`, `docs/skills/euer-buchhaltung/SKILL.md` und der gesamte `docs/skills/euer-buchhaltung/references/` Ordner. Das alte `docs/USER_GUIDE.md` entfällt ersatzlos in dieser Architektur.
