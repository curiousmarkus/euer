# Spec 022: Versionierte, sichere Skill-Aktualisierung & Skill-as-a-Package Architektur

## Status

Offen

## Originalfeedback (wörtlich)

> Der Skill sollte neben dem Software-Release eine klar ausgewiesene Version haben. Hilfreich wären eine Installations-/Update-Anleitung pro Agent und ein Diff, bevor lokale Dateien ersetzt werden. Nutzerregeln wie AGENTS.md sollten dabei niemals automatisch überschrieben werden. Ein als Vorschlag zu entwickelnder Skill-Updateweg sollte upstream-Inhalte und lokale Anpassungen getrennt behandeln, statt stillschweigend eine Seite zu ersetzen.

## Learning & Konzept-Evolution

Paket, kopierter Skill und Mandanten-Dossier haben verschiedene Lebenszyklen.
Ein `pipx`- oder Brew-Update aktualisiert keine lokale Skill-Kopie. Das Mandanten-Dossier (`AGENTS.md`) ist Nutzerdatenbestand und darf bei Tool-/Skill-Updates niemals automatisch ersetzt werden.

**Die wichtigste Erkenntnis:** `euer` ist eine reine KI-Anwendung. Menschliche Nutzung der CLI ist "out of scope". Demnach muss die gesamte Architektur, Fehlerausgabe und Dokumentation so gebaut sein, dass eine Maschine sie fehlerfrei ausführen und sich im Fehlerfall selbst reparieren kann. Die traditionelle `USER_GUIDE.md` für Menschen ist obsolet.

**Die Lösung: "Skill-as-a-Package" & Bundling**
Um sichere Updates und perfekte KI-Ausführung zu vereinen, wird die Dokumentation vollständig in den Skill integriert. Der Ordner `docs/skills/euer-buchhaltung/` wird zur versionierten, monolithischen "Read-Only Firmware" für den Agenten. 

Zusätzlich wird das fertige Skill-Paket physisch in das Python-Package (`euercli/assets/skill/`) gebündelt. Wenn der Mensch die CLI aktualisiert, wird der neue Skill automatisch mit auf die Festplatte geladen. Das ermöglicht Offline-Updates ohne externe HTTP-Requests durch die KI.

Wir setzen damit eine absolut strikte Trennung um:
- **Code / Firmware (Darf komplett ersetzt werden):** Der gesamte Skill-Ordner inklusive aller Doku-Referenzen (`SKILL.md` + `references/*.md`).
- **State / Nutzerdaten (Darf NIE überschrieben werden):** Das persönliche `AGENTS.md` (Mandanten-Dossier) liegt außerhalb.

## Die Zielarchitektur

*   **Der Einstieg (Für den Menschen)**
    *   `README.md`: Der "Showroom". Fokussiert auf Fähigkeiten und bietet den Handoff-Prompt (Kopier-Vorlage für die KI zur Installation & Lektüre). 
    *   `docs/CONCEPTS.md`: Ein konzeptioneller Überblick (Trust-Building, Guardrails, Sicherheit, Architektur), komplett ohne CLI-Syntax.

*   **Das Maschinen-Handbuch (Der Skill-Ordner)**
    *   📁 `docs/skills/euer-buchhaltung/`
        *   `SKILL.md`: Der Orchestrator. Definiert Rolle, Abläufe und dient als Index für die Referenzen. Enthält im Header eine klare Versionsnummer.
        *   📁 `references/`
            *   `installation_and_setup.md`: Anweisungen für den Agenten zur Systemeinrichtung.
            *   `cli_reference.md`: Harte Befehlsspezifikation (Flags, JSON-Outputs).
            *   `domain_rules.md`: Fachliche Buchhaltungsregeln (z. B. Prepaid, Cashback, 70/30-Aufteilung). WICHTIG: Zu jeder Regel muss zwingend das "Warum" (Steuergesetz, fachliche Begründung) notiert werden, damit sie wartbar bleibt und der Agent dem Menschen die Buchung auf Nachfrage fundiert erklären kann.

## Der selbstheilende Update-Prozess (The Update Loop)

Da `euer` ausschließlich von KIs bedient wird, blockiert die CLI gnadenlos jeden Befehl, wenn die KI mit einem veralteten Wissensstand (Skill) arbeitet. Die Blockade enthält eine direkte Anweisung zur Selbstheilung.

**Der Prozess:**
1. **Das CLI-Update (Mensch):** Der Mensch aktualisiert die CLI (`pipx upgrade euer`). Die CLI ist nun z. B. `v1.3.0` und bringt den passenden Skill `v1.3.0` im Installationspfad (z. B. `~/.local/share/pipx/.../euercli/assets/skill/`) mit.
2. **Die Versionsprüfung (CLI):** Bei jedem CLI-Aufruf prüft `euer`, ob der in der Config hinterlegte Skill-Stand (`~/.config/euer/config.toml` unter `[skill] version`) mindestens der internen `MIN_SKILL_VERSION` entspricht.
3. **Die harte Blockade:** Da der Agent noch die alte Config (z. B. `1.2.0`) hat, bricht die CLI den Befehl ab:
   > `[✗] FEHLER: Dein registrierter Skill (v1.2.0) ist veraltet. Diese CLI erfordert mindestens v1.3.0.`
   > `Kopiere das neue Skill-Paket von /absoluter/pfad/zu/euercli/assets/skill/ in deinen lokalen Workspace und überschreibe deinen aktuellen Skill.`
   > `Bestätige das Update danach mit dem Befehl: euer setup --set skill.version "1.3.0"`
4. **Die Selbstheilung (Agent):** Der Agent liest diesen Fehler und führt die Anweisungen mittels seiner Terminal-Werkzeuge aus:
   - Er kopiert (`cp -r`) die Dateien aus dem lokalen Installationspfad in seinen Arbeitsordner und aktualisiert so sein eigenes "Gehirn" (`references/` und `SKILL.md`). Das private `AGENTS.md` bleibt unangetastet.
   - Er führt `euer setup --set skill.version "1.3.0"` aus.
5. **Freigabe:** Die CLI erkennt die aktualisierte Config. Der Agent kann seine ursprüngliche Aufgabe fortsetzen, nun aber mit exakt auf die CLI-Version abgestimmtem Kontext.

## Upgrade-Vertrag je Release

Jede Release Note enthält nahe bei den DB-Upgrade-Schritten einen Block „Agenten-Dateien“ mit vier getrennten Zeilen:

| Bereich | Angabe je Release |
|---|---|
| Skill-Package | Bundled-Version vorher/nachher, Update zwingend: ja/nein |
| Rolle | Version vorher/nachher, Änderung der gemeinsamen Rolle |
| Agenten-Adapter | Betroffene Systeme und Dateien; kompatibel/Update empfohlen |
| Mandanten-Dossier | Niemals automatisches Ersetzen (Strict State Separation) |

Das bereits publizierte Release wird nicht nachträglich ergänzt.

## Agentenspezifische Einbindung

| Agent | Ziel für euer | Grenze |
|---|---|---|
| Claude Code | Skill-Package in Workspace (z. B. `.claude/`) kopieren | Projekt-`CLAUDE.md` / `AGENTS.md` bleibt rein lokaler State |
| OpenCode | Skill-Package plus optionaler eigener Agent in `.opencode/agents/` | Projekt-`AGENTS.md` bleibt Mandanten-Dossier |
| Hermes | Skill-Package und projektbezogene Kontextdatei | Globale `SOUL.md` ist Identität |

**Zielbild:** Ein lokaler Adapter enthält nur dauerhafte Einstiegspunkte:
„Für Buchhaltungsaufträge den lokalen `euer-buchhaltung` Skill nutzen und persönliches Dossier lesen.“ Neue CLI-Regeln gehen vollständig in das versionierte Skill-Package und aktualisieren sich via Copy-Befehl von selbst.

## Anforderungen zur Implementierung

- Einbau der `MIN_SKILL_VERSION` Konstante und Blockade-Logik in die CLI (`cli.py` / Middleware).
- Bundling des `docs/skills/euer-buchhaltung/` Ordners in der `pyproject.toml` (`package_data`), sodass dieser Teil des Python-Wheels wird.
- Auflösung der traditionellen `USER_GUIDE.md` in die neue Struktur (`CONCEPTS.md` und `references/*.md`).
- Auflösung der bisherigen `FAQ.md` (ersatzlos). Ihre fachlichen Sonderfälle (Prepaid, Cashback etc.) wandern als Wenn-Dann-Regeln (inklusive Begründung) in die `domain_rules.md`. CLI-Probleme und Eigenheiten wandern in die `cli_reference.md` oder werden direkt durch Self-Describing Errors in der CLI (`stderr`) gelöst.
- Da der Befehl `euer setup --set key value` bereits existiert, ist keine neue CLI-Logik für die Registrierung des Skills nötig.

## Dokumentation nach Implementierung

`README.md`, `docs/CONCEPTS.md`, gebündeltes `euercli/assets/skill/SKILL.md` und der gesamte `euercli/assets/skill/references/` Ordner. Das alte `docs/USER_GUIDE.md` entfällt ersatzlos.
