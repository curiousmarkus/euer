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
2. **Die Versionsprüfung (CLI):** Bei jedem CLI-Aufruf prüft `euer`, ob der in der Config hinterlegte Skill-Stand (`~/.config/euer/config.toml` unter `[skill] version`) kompatibel mit der internen `MIN_SKILL_VERSION` ist. 
3. **Die harte Blockade (Zwei Fälle):**
   - **Fall A (Skill veraltet):** Ist die CLI neuer als der Skill, bricht sie ab:
     > `[✗] FEHLER: Dein registrierter Skill (v1.2.0) ist veraltet. Diese CLI erfordert v1.3.0.`
     > `Bitte überschreibe deinen aktiven euer-buchhaltung Skill-Ordner vollständig mit den Inhalten aus: /absoluter/pfad/zu/euercli/assets/skill/`
     > `Bestätige das Update danach mit dem Befehl: euer setup --set skill.version "1.3.0"`
   - **Fall B (CLI veraltet):** Ist der registrierte Skill (z.B. v1.4.0) neuer als die CLI (z.B. v1.3.0), blockiert die CLI ebenfalls, da der Agent neue Flags nutzen könnte, die der Code noch nicht versteht:
     > `[✗] FEHLER: Dein Skill-Package (v1.4.0) ist neuer als diese CLI (v1.3.0).`
     > `Bitte führe 'pipx upgrade euer' oder 'brew upgrade euer' aus, um die CLI zu aktualisieren.`
4. **Die Selbstheilung (Agent im Fall A):** Der Agent liest den Fehler und führt die Anweisungen mittels seiner Terminal-Werkzeuge aus:
   - Er kopiert (`cp -r`) die Dateien aus dem lokalen Installationspfad über seinen eigenen aktiven Skill-Ordner und aktualisiert so sein "Gehirn" (`references/` und `SKILL.md`). Das private `AGENTS.md` bleibt unangetastet.
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
- Das finale Python-Wheel muss den Ordner `docs/skills/euer-buchhaltung/` als Package Data unter `euercli/assets/skill/` physisch enthalten (dies dient als Acceptance Criteria; Implementierungsdetails sind dem Entwickler überlassen).
- Auflösung der traditionellen `USER_GUIDE.md` in die neue Struktur (`CONCEPTS.md` und `references/*.md`).
- Auflösung der bisherigen `FAQ.md` (ersatzlos). Ihre fachlichen Sonderfälle (Prepaid, Cashback etc.) wandern als Wenn-Dann-Regeln (inklusive Begründung) in die `domain_rules.md`. CLI-Probleme und Eigenheiten wandern in die `cli_reference.md` oder werden direkt durch Self-Describing Errors in der CLI (`stderr`) gelöst.
- **Doc-Coverage-Test:** Implementierung eines CI-Tests (`test_docs_coverage.py`), der den `argparse`-Baum ausliest und sicherstellt, dass jeder Befehl und jedes Flag zwingend im Text der `cli_reference.md` erwähnt wird (Verhindert "Wissens-Drift" zwischen Code und Agent).
- Da der Befehl `euer setup --set key value` bereits existiert, ist keine neue CLI-Logik für die Registrierung des Skills nötig.

## Dokumentation nach Implementierung

`README.md`, `docs/CONCEPTS.md`, gebündeltes `euercli/assets/skill/SKILL.md` und der gesamte `euercli/assets/skill/references/` Ordner. Das alte `docs/USER_GUIDE.md` entfällt ersatzlos.
