# Spec 022: Versionierte, sichere Skill-Aktualisierung

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

## Learning

Paket, kopierter Skill und Mandanten-Dossier haben verschiedene Lebenszyklen.
Ein `pipx`- oder Brew-Update aktualisiert keine lokale Skill-Kopie. Das
Mandanten-Dossier ist Nutzerdatenbestand und darf bei Tool-/Skill-Updates nicht
automatisch ersetzt werden.

Die bisherige Rollen-Vorlage enthielt OpenCode-artiges `mode: primary`-Frontmatter,
obwohl sie auch für andere Agenten beworben wurde. Der Dateiname
`accountant-role.md` bezeichnet künftig die gemeinsame Quelle; die installierte
Agentendatei ist ein eigenes, möglicherweise lokal angepasstes Artefakt.
Hermes' `SOUL.md` ist eine globale Identität und kein sinnvoller Ort für jeden
euer-Buchungsworkflow. Claude Code und OpenCode unterstützen dagegen eigene
Agentendateien und Skills. Ein normales Skill-Update soll deshalb möglichst
keine globale Agentenidentität ändern.

## Upgrade-Vertrag je Release

Jede Release Note enthält nahe bei den DB-Upgrade-Schritten einen Block
„Agenten-Dateien“ mit vier getrennten Zeilen:

| Bereich | Angabe je Release |
|---|---|
| Skill | Version vorher/nachher, geänderte Buchungsregeln, Update nötig: ja/nein |
| Rolle | Version vorher/nachher, Änderung der gemeinsamen Rolle, Update nötig: ja/nein |
| Agenten-Adapter | Betroffene Systeme und Dateien; kompatibel/Update empfohlen/Update erforderlich |
| Mandanten-Dossier | Konkreter Prüfpunkte oder „keine Änderung“; niemals automatisches Ersetzen |

„Update erforderlich“ wird nur verwendet, wenn sonst eine fachlich falsche
oder inkompatible Anleitung aktiv bliebe. Eine rein redaktionelle Änderung
ist „empfohlen“. Der Block nennt die **installierte euer-Version** als Bezug
und verlinkt unveränderliche Quellen des zugehörigen Release-Tags, nicht `main`.
Die CI prüft, dass der Block bei Änderungen an Skill, Rolle, Adaptern oder
Onboarding vorhanden ist. Das bereits publizierte Release wird nicht
nachträglich ergänzt.

## Ablauf beim Nutzer

1. **Bestand feststellen:** Aktive euer-Version und Installationskanal prüfen;
   Agentensystem, Profil/Projekt, lokale Skill- und Rollenpfade sowie deren
   Versionen ermitteln. Nicht gefundene Dateien oder unbekannte Herkunft
   ausdrücklich melden. Keine beliebigen Verzeichnisse oder Profile ändern.
2. **Passende Quelle laden:** Release Notes und Agenten-Dateien vom Tag der
   tatsächlich installierten euer-Version beziehen. Eine Homebrew-Verzögerung
   darf nicht versehentlich neuere Agenten-Dateien mit einer älteren CLI mischen.
3. **Vorschau erstellen:** Upstream-Basis, neue Upstream-Datei und lokale Datei
   vergleichen. Ausgabe: neu/geändert/unverändert, fachliche Änderung, Diff,
   betroffene Agentendatei und vorgeschlagener nächster Schritt.
4. **Anwenden:** Unveränderte, eindeutig von euer verwaltete Skill-Dateien
   dürfen nach Vorschau und Sicherung aktualisiert werden. Lokal bearbeitete
   Dateien, unbekannte Versionen und Konflikte erhalten einen Patch-Vorschlag;
   ohne Entscheidung des Menschen kein Überschreiben. Persönliche
   `AGENTS.md`/`CLAUDE.md`, globale `SOUL.md`, Config und andere
   Nutzerdaten werden nie automatisch ersetzt. Eine explizit beauftragte,
   vom Menschen geprüfte Einzeländerung daran ist möglich.
5. **Nachprüfung:** Agent in einer neuen Sitzung starten, laden des Skills und
   der Rolle prüfen, Versions-/Kompatibilitätsstand melden. Ein ausstehender
   menschlicher Schritt bleibt sichtbar, bis er erledigt oder bewusst
   verworfen wurde; ein CLI-Upgrade allein gilt nicht als Agenten-Upgrade.

Für die erste Umsetzung genügt ein dokumentierter manueller Diff-Ablauf.
Ein späterer Helfer darf Vorschau und Konflikterkennung automatisieren, muss
aber dieselben Grenzen einhalten. Lokale Version/Upstream-Basis kann in
einer kleinen eigenen Installationsmetadatei liegen; sie gehört nicht in die
persönliche `AGENTS.md`.

## Agentenspezifische Einbindung

| Agent | Ziel für euer | Grenze |
|---|---|---|
| Claude Code | Skill plus optionaler eigener Subagent in `.claude/agents/` oder Nutzerverzeichnis | Projekt-`CLAUDE.md` nur für lokale Mandantenregeln, nicht als Kopie der Rolle |
| OpenCode | Skill plus optionaler eigener Agent in `.opencode/agents/` oder Nutzerverzeichnis | Projekt-`AGENTS.md` bleibt Mandanten-Dossier |
| Hermes | Skill und gegebenenfalls projektbezogene Kontextdatei oder eigenes Buchhaltungsprofil | Globale `SOUL.md` ist Identität; Änderungen daran nur als menschlich geprüfter Vorschlag |

Diese Zuordnung muss bei Implementierung gegen die jeweils aktuellen offiziellen
Agenten-Dokumentationen geprüft werden. Die gemeinsame Rolle ist Inhalt für
einen passenden Adapter, keine Datei zum pauschalen Kopieren. Adapter sollen
so dünn wie möglich bleiben und den aktuellen Skill nutzen, damit Änderungen
an Buchungslogik überwiegend nur den Skill betreffen.

**Zielbild:** Ein lokaler Adapter enthält nur dauerhafte Einstiegspunkte:
„Für Buchhaltungsaufträge `euer-buchhaltung` laden, persönliches Dossier lesen,
Release-Stand bei Versionswechsel prüfen.“ Neue CLI- oder Steuerregeln gehen in
den Skill. Damit erfordert nicht jedes euer-Release eine Änderung an
`SOUL.md`, `CLAUDE.md` oder einem Agentenprofil. Änderungen der eigentlichen
Rolle oder eines Adapters bleiben als eigener Release-Posten sichtbar.

## Wo der Hinweis erscheint

- **Verbindlich:** Release Notes direkt bei den Upgrade-Schritten; User Guide
  erklärt die wiederkehrende Prozedur.
- **Im Agenten:** Skill und Rollen-Adapter weisen beim Start eines
  Buchungsauftrags auf eine erkennbare Versions-/Kompatibilitätslücke hin.
  Eine alte lokale Kopie kann neue Releases nicht selbst kennen; deshalb ist
  dieser Hinweis nur Ergänzung, nicht alleiniger Meldeweg.
- **Künftig in der CLI:** `init`-Abschlussbericht und `doctor` können auf
  Agenten-Änderungen des installierten Releases hinweisen. Ohne bekannte
  lokale Agentenpfade dürfen sie keinen erfolgreichen Update-Status behaupten.
  Dafür muss ein kleines Release-/Asset-Manifest im Wheel verfügbar sein;
  derzeit sind die Dokumente nicht Teil des installierten Python-Pakets.
- **Bei nötigem Eingriff:** Konkreter Hinweis mit betroffener Datei, Grund,
  Diff/Patch und Aktion „prüfen und freigeben“; die Buchhaltungsdaten werden
  dadurch nicht stillschweigend verändert.

Quellen für die Agenten-Zuordnung:
[Claude Code Subagents](https://code.claude.com/docs/en/sub-agents),
[Claude Code Skills](https://code.claude.com/docs/en/skills),
[OpenCode Agents](https://opencode.ai/v2/docs/agents),
[OpenCode Instructions](https://opencode.ai/v2/docs/instructions),
[Hermes Dateiscope](https://hermes-agent.nousresearch.com/docs/user-guide/which-file-does-what).

## Anforderungen

- Separat sichtbare Skill-Version und dokumentierte Kompatibilität zu
  euer-Releases; Versionsschema und Quelle werden vor Umsetzung festgelegt.
  Eine Software-PATCH-Version wird nicht automatisch zur Skill-Version.
- Für unterstützte Agenten Installations- und Updatepfade dokumentieren;
  vor Austausch die lokal installierte Version und Dateiänderungen anzeigen.
- Update-Vorschau mit Diff zwischen Upstream-Basis, neuer Upstream-Version
  und lokalen Anpassungen. Konflikte explizit melden; keine stillen Overrides.
- Persönliche `AGENTS.md`, Config und andere Mandantendaten nie automatisch
  überschreiben. Änderungen daran nur als überprüfbare Vorschläge ausgeben.
- Agenten-/Skill-Kopien und Templates eindeutig von Mandantendaten trennen.
  Auf Windows, macOS und Linux ohne vorausgesetzten festen Skill-Pfad
  dokumentieren.
- `docs/templates/accountant-role.md` ist die gemeinsame Rollen-Vorlage;
  `accountant-agent.md` bleibt als Verweis für historische Links. Die Rolle
  darf nicht unverändert als `SOUL.md`, `CLAUDE.md` oder `AGENTS.md` ausgegeben
  werden. Plattformspezifische Adapter werden gesondert entworfen;
  allgemeine Buchungsregeln gehören in den gemeinsamen Skill.
- Ein möglicher `euer skill update`-Befehl ist eine Option, keine bereits
  vorhandene Funktion. Vor Implementierung gegen dokumentierte manuelle
  Diff-Schritte und die unterschiedlichen Agenten-Skillpfade abwägen.

## Akzeptanzfälle

- Nur CLI geändert: kein Agenten-Eingriff nötig.
- Skill geändert, lokale Kopie unverändert: korrekter Release-Stand wird
  übernommen und verifiziert.
- Skill/Agentenrolle lokal angepasst: Diff und Konflikt sichtbar, keine
  stille Ersetzung.
- Hermes mit angepasster globaler `SOUL.md`: kein automatischer Schreibzugriff.
- Claude Code/OpenCode mit projektbezogenem Agenten und persönlichem Dossier:
  Adaptervorschlag getrennt von Mandantenregeln.
- Homebrew meldet noch die ältere Version: keine Agenten-Dateien vom neueren
  PyPI-Release als kompatibel ausgeben.
- Alter `accountant-agent.md`-Pfad und unbekannte lokale Version: Migration
  wird erkannt und zur Prüfung vorgelegt.

## Dokumentation nach Implementierung

`README.md`, `docs/USER_GUIDE.md`, `docs/USER_JOURNEY.md`,
`docs/skills/euer-buchhaltung/SKILL.md`, `docs/templates/onboarding-prompt.md`
und `docs/RELEASE_NOTES.md`.
