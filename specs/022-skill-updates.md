# Spec 022: Versionierte, sichere Skill-Aktualisierung

## Status

Offen

Review-Entwurf: Die folgenden Funktionen sind geplant, noch nicht implementiert.
Diese Änderung aktualisiert die Spec; Skill, CLI und Agenteninstallationen bleiben
unverändert. Der Entwurf wird vor einem Commit vom Nutzer geprüft.

## Originalfeedback (wörtlich)

> Der Skill sollte neben dem Software-Release eine klar ausgewiesene Version haben. Hilfreich wären eine Installations-/Update-Anleitung pro Agent und ein Diff, bevor lokale Dateien ersetzt werden. Nutzerregeln wie AGENTS.md sollten dabei niemals automatisch überschrieben werden. Ein als Vorschlag zu entwickelnder Skill-Updateweg sollte upstream-Inhalte und lokale Anpassungen getrennt behandeln, statt stillschweigend eine Seite zu ersetzen.

## Ziel und Grenzen

CLI-Paket, verfügbare Skill-Dateien, tatsächlich geladener Agentenkontext und
Mandanten-Dossier haben unterschiedliche Lebenszyklen. Ein CLI-Update liefert einen
passenden Skill mit, aktualisiert aber weder Agenteninstallationen noch laufende
Sitzungen. Hermes, Claude Code und andere Systeme verwalten und laden Skills auf
unterschiedliche Weise.

**Verantwortungsgrenze:** `euer` stellt das zum aktiven CLI-Paket gehörende Skill-Bundle
bereit, prüft die vom Aufrufer angegebene Skill-Version und meldet Updatebedarf.
Installation und erneutes Laden erfolgen über den jeweiligen Agenten beziehungsweise
dessen dokumentierten Installationsweg. `euer` überschreibt keine Agenten-Skills,
registriert keine vermeintlich erfolgreiche Kontextaktualisierung und startet keine
Paketmanager-Upgrades.

Die Prüfung ist ein Kompatibilitätsvertrag mit dem Aufrufer, kein Nachweis seines
internen Wissensstands. Fachliche Validierung bleibt im Service-Layer. `euer` wird
primär durch KI-Agenten bedient; Menschen behalten verständliche Einstiegs-, Kontroll-
und Reparaturanleitungen. „Fehlerfreie KI-Ausführung“ wird nicht zugesichert.

## Entscheidungen und Annahmen

### D1: Nur Mutationen sperren — entschieden

**Annahme:** Unverstandene Schreiboperationen sollen verhindert werden; Einsicht und
Diagnose müssen bei Versionsproblemen möglich bleiben.

- **Gewählt:** Mutationen erfordern einen kompatiblen angegebenen Skill-Stand.
  Lesende Befehle bleiben verfügbar und melden Kompatibilitätsprobleme als Warnung.
- **Pro:** Diagnose, Reparatur und Einsicht bleiben möglich.
- **Contra:** Ein alter Agent kann neue Berichtsfelder falsch interpretieren;
  die Warnung muss ihn zur Lektüre der passenden Referenz auffordern.
- **Verworfen:** Alle Fachbefehle sperren. Dies wäre einheitlicher, würde aber auch
  lesende Arbeit bis zur Aktualisierung verhindern.

### D2: Separate Skill-Version und CLI-Kompatibilitätsbereich — entschieden

**Annahme:** CLI-Patches und Änderungen der Agentenanweisungen können unabhängig
voneinander notwendig sein.

- **Gewählt:** Eigene Skill-Version und expliziter Bereich unterstützter CLI-Versionen.
- **Pro:** Kein Skill-Update allein wegen einer kompatiblen CLI-Änderung.
- **Contra:** Kompatibilitätsmetadaten und zugehörige Tests müssen gepflegt werden.
- **Verworfen:** Exakte Gleichheit von CLI- und Skill-Version. Einfachere Zuordnung,
  aber unnötige Skill-Updates bei jedem Software-Release.

### D3: Agentenübergreifend informieren, nicht installieren — entschieden

**Annahme:** `euer` kennt weder den verbindlichen Installationsort noch das
Reload-Verfahren jedes Agenten.

- **Gewählt:** CLI liefert Status, Bundle und Update-Hinweise. Der Agent übernimmt
  Vergleich, Konfliktklärung, Installation und erneutes Laden.
- **Pro:** Keine fremden Agentenverzeichnisse werden automatisch verändert;
  funktioniert unabhängig vom jeweiligen Skill-Verwaltungssystem.
- **Contra:** Kein universeller selbstheilender Installationsprozess; der Erfolg
  hängt vom Adapter und gegebenenfalls von einer neuen Sitzung ab.
- **Verworfen:** CLI-eigener Installer/Updater für fremde Skill-Ordner. Könnte
  Dateiaustausch standardisieren, kennt aber aktive Installation und Kontext nicht.

### D4: Nur Version und Bundle-Pfad, kein CLI-Diff — entschieden

**Annahme:** Der Agent verfügt über eigene Vergleichswerkzeuge; ein lokaler
Skill-Pfad ist nicht bei jedem System zugänglich.

- **Gewählt:** `euer` meldet Version, Kompatibilität, Bundle-Pfad und nächste Schritte.
  Einen Datei-Diff erstellt der Agent mit seinen vorhandenen Werkzeugen.
- **Pro:** Kleiner agentenunabhängiger Umfang, kein Zugriff auf fremde Skill-Bäume.
- **Contra:** Vergleich und Erkennung lokaler Anpassungen müssen die Agentenanleitungen
  abdecken; `euer` kann deren Durchführung nicht verifizieren.
- **Verworfen:** Optionaler lesender CLI-Diff. Würde konkrete Änderungen einheitlich
  darstellen, benötigt aber zusätzliche Logik und zugängliche lokale Dateien.

## Paket und Dokumentation

Einzige gepflegte Quelle ist `docs/skills/euer-buchhaltung/`. Der Build übernimmt
sie einschließlich Manifest und aller Referenzen nach `euercli/assets/skill/`.
Das Bundle ist ein erzeugtes Artefakt und wird nicht separat redaktionell gepflegt.
Wheel und sdist müssen den vollständigen Skill liefern; ein aus der sdist gebautes
Wheel muss dieselben Skill-Inhalte enthalten. Der Zugriff erfolgt über
Package-Ressourcen, ohne fest codierte pipx-, Homebrew- oder venv-Pfade.

Geplante Struktur:

- `SKILL.md`: kurzer Einstieg, sichtbare Version, Routing und Update-Ablauf.
- `manifest.json`: maschinenlesbare Identität, Kompatibilität und Dateiinventar.
- `references/onboarding.md`: bestehende gemeinsame Quelle für Interview und Dossier.
- `references/installation_and_setup.md`: Installation, Adapter, Update und Recovery;
  verweist für das Interview auf `onboarding.md`, statt es zu duplizieren.
- `references/cli_reference.md`: Syntax, Semantik, Ausgabe- und Fehlerverträge.
- `references/domain_rules.md`: fachliche Regeln mit Voraussetzungen, Begründung,
  Quelle, Geltungszeitraum und Verhalten bei unklaren Angaben.

Referenzen werden aufgabenbezogen geladen. Sämtliche für reguläre Bedienung und
Update benötigten Inhalte sind offline im Paket verfügbar. Externe Quellen
begründen Regeln, sind aber keine Voraussetzung für den lokalen Updateweg.

`README.md` enthält Fähigkeiten und Handoff-Prompt; `docs/CONCEPTS.md` erklärt
Architektur und Grenzen. Inhalte von `USER_GUIDE.md` und `FAQ.md` werden vor ihrer
Migration vollständig zugeordnet. `USER_JOURNEY.md` behält den menschlichen Kontroll- und
Übergabeablauf. Links einschließlich der Paketmetadaten werden angepasst.

## Versions- und Kompatibilitätsvertrag

Das Manifest enthält mindestens:

| Feld | Vertrag |
|---|---|
| `manifest_schema` | Ganzzahlige Formatversion |
| `skill_id` | Stabile Kennung `euer-buchhaltung` |
| `skill_version` | Eigene Version `MAJOR.MINOR.PATCH` |
| `cli_min` | Kleinste unterstützte CLI-Version, einschließlich |
| `cli_max_exclusive` | Erste nicht unterstützte CLI-Version, ausschließlich |
| `files` | Relative Dateipfade und SHA-256-Hashes sämtlicher Nutzdateien |

Das Manifest selbst ist nicht in seiner Hashliste enthalten. Eine Paketkennung
ist der SHA-256-Hash seiner deterministisch erzeugten Bytes. Hashes erkennen
Abweichungen; sie beweisen keine vertrauenswürdige Herkunft oder geladenen Kontext.

Jedes CLI-Release enthält einen expliziten Kompatibilitätskatalog der unterstützten
Skill-Versionen und ihrer CLI-Bereiche sowie eine `MIN_SKILL_VERSION`. Dieser Katalog
ermöglicht eine Prüfung ohne Zugriff auf das Dateisystem des Agenten. Akzeptiert
wird eine bekannte Skill-Version, deren Bereich die aktive CLI-Version einschließt
und die mindestens die Mindestversion erfüllt. Unbekannte zukünftige Versionen
werden nicht aufgrund ihrer größeren Nummer als kompatibel angenommen.

Der Katalog ist Release-Metadatum und wird zusammen mit dem Bundle geprüft. Bereits
unterstützte Skill-Versionen bleiben enthalten, solange sie fachlich kompatibel
sind. Eine erhöhte Mindestversion muss in den Release Notes begründet werden.
Das gebündelte Manifest und sein Katalogeintrag müssen übereinstimmen; das Bundle
muss von seiner eigenen CLI akzeptiert werden.

Die erste Fassung unterstützt stabile dreiteilige Versionsnummern; Vergleiche sind
numerisch, keine Stringvergleiche. Fehlende, ungültige, unbekannte und bekannte
inkompatible Versionen werden unterschieden. Bei bekannter kompatibler Version
ist ein neueres Bundle nur ein Updateangebot, keine Sperre.

Die Skill-Version wird im Quellmanifest gepflegt. Sichtbare Angaben in `SKILL.md`
werden daraus erzeugt oder im Build auf Gleichheit geprüft. Eine Änderung der
ausgelieferten Skill-Inhalte erfordert eine neue Skill-Version; eine Version darf
nicht für unterschiedliche Inhalte wiederverwendet werden. Redaktionelle Korrekturen
sind PATCH, kompatible Erweiterungen MINOR, inkompatible Arbeitsabläufe MAJOR.
`euercli.VERSION` bleibt die einzige Quelle der Softwareversion.

## Angabe des tatsächlich verwendeten Skills

Der Agent übergibt die aus seinem geladenen Skill gelesene Version pro Aufruf mit
dem globalen Flag `--skill-version VERSION`, vor dem Subcommand. Alternativ kann
ein Adapter `EUER_SKILL_VERSION` pro Prozess setzen; das Flag hat Vorrang.
Keine dauerhafte globale Shell-Variable als Ersatz für die Sitzungsprüfung verwenden.

Beispiel der geplanten Syntax:

```bash
euer --skill-version 1.2.0 doctor --json
```

Ein globales `[skill].version` in der Config ist kein Nachweis und schaltet keine
Sperre frei. Ein Agent darf niemals einfach die erwartete Version übernehmen, um
einen Fehler zu umgehen. Zwei Agenten mit verschiedenen geladenen Skills geben
unabhängige Versionen an. Die CLI benennt den Wert ausdrücklich als „angegebenen
Skill-Stand“, nicht als technisch nachgewiesenen Kontext.

Nach Aktualisierung der Dateien liest der Agent `SKILL.md` und die für den Auftrag
benötigten Referenzen erneut. Erst danach gibt er die neue Version an. Unterstützt
das Agentensystem kein verlässliches Reload, ist eine neue Sitzung erforderlich.
Kann der Agent seinen Stand nicht ermitteln, bleiben Mutationen gesperrt und die
passenden lokalen Anweisungen werden zum Lesen angeboten.

## CLI-Oberfläche und Fehlervertrag

Folgende neuen Funktionen sind vorgesehen, aber noch nicht implementiert:

| Aufruf | Verhalten |
|---|---|
| `euer skill status [--json]` | CLI-/angegebene Skill-Version, Kompatibilität, Bundle-Version/-Pfad und nächste Schritte melden |
| `euer doctor [--json]` | Skill-Kompatibilität zusätzlich zur bestehenden Diagnose ausweisen |

Die Bundle-Auskunft funktioniert ohne DB, angegebenen Skill oder gültige globale
beziehungsweise Projekt-Config. `doctor` berichtet defekte Config getrennt, statt
deshalb die Skill-Diagnose zu verlieren. Quelle ist das Bundle des tatsächlich
aktiven CLI-Pakets; aktive Softwareversion und Binary-Pfad werden mit ausgegeben.
Es gibt keine CLI-Befehle zur Installation, Aktualisierung oder Registrierung
fremder Agenten-Skills.

Die Mutationssperre greift vor DB-Schreibzugriff, Backups und sonstigen Seiteneffekten:

| Befehlsgruppe | Verhalten bei fehlender oder inkompatibler Skill-Version |
|---|---|
| `add`, `update`, `delete`, `restore`, `undo`, schreibender `import`/`reconcile`, `trash empty` | Sperren |
| Ausführendes `init`, interaktives `setup`, `setup --set`, Änderungen der Projektbindung | Sperren |
| Datei-erzeugende Exporte einschließlich Report-Exporten | Sperren |
| Rein lesende Fachbefehle, `import --schema`, Reportausgabe ohne Dateischreiben | Erlauben, Kompatibilitätswarnung ausgeben |
| Echte seiteneffektfreie `--dry-run`-Aufrufe | Erlauben, warnen; Ergebnis ist keine Freigabe der späteren Mutation |
| Hilfe, Versionsanzeige, `config show`, `doctor`, Skill-Auskunft | Immer für Diagnose erreichbar |

Commands deklarieren ihre Seiteneffekte; neue Commands müssen klassifiziert werden.
Unklassifizierte Plugin-Commands werden konservativ als schreibend behandelt.
Bestehende Validierungen und Berechtigungsprüfungen gelten unverändert.

Stabile Fehler-/Diagnosecodes sind mindestens `skill_version_missing`,
`skill_version_invalid`, `skill_version_unknown`, `skill_incompatible` und
`skill_bundle_invalid`. Normale erfolgreiche Befehle enden mit 0, gesperrte
Mutationen mit 1, Syntaxfehler mit 2. Lesebefehle bleiben bei bloßer Skill-Warnung
erfolgreich. `skill status` liefert bei nicht kompatiblem oder nicht prüfbarem
Stand 1 mit vollständiger Diagnose. Die bestehende Exitcode-Semantik von `doctor`
ist bei der Integration ausdrücklich zu berücksichtigen und zu dokumentieren.

`skill status` liefert mit `--json` genau ein Ergebnisobjekt auf stdout,
auch bei diagnostiziertem Updatebedarf; operative Fehler gehen als Fehlerobjekt
auf stderr. Felder: `status`, `code`, deutsche `message`, `cli_version`, `binary_path`,
`reported_skill_version`, `bundled_skill_version`, `bundle_path`,
`compatible`, `update_available` und geordnete `remediation_steps`.
Nicht ermittelbare Werte sind `null`; keine zusätzliche Prosa auf stdout.
Gesperrte Fachbefehle liefern im JSON-Modus ein Fehlerobjekt auf stderr.
Lesewarnungen dürfen weder Tabellen noch JSON-Ergebnisse auf stdout beschädigen.

Mit [Spec 023](023-ai-io.md) wird der gemeinsame Ausgabe-/Fehlervertrag abgestimmt.
Deren Reparaturbeispiel mit bloßem Setzen von `skill.version` ist bei Umsetzung zu
ersetzen. Bestehende `doctor`-/`init`-JSON-Verträge werden nicht nebenbei gebrochen.
Die neue Skill-Auskunft benötigt strukturierte Ausgaben unabhängig vom gesamten
JSON-Rollout der Spec 023.

## Update-Ablauf im Agenten

1. **Diagnose:** Die CLI meldet angegebenen Stand, konkrete Inkompatibilität,
   aktives Binary und den absoluten Pfad des mitgelieferten Skills. Kein pauschales
   `pipx upgrade`, wenn beispielsweise Homebrew aktiv ist.
2. **Vergleich:** Agent nutzt den vorgesehenen Installationsweg seines Systems und
   erstellt vor Ersetzen lokaler Dateien einen Diff einschließlich entfallener
   Dateien. Ist der Skill nicht als Verzeichnis zugänglich, verwendet er die
   Vergleichsfunktion des Agentensystems. Kann er Änderungen nicht ermitteln,
   meldet er diese Grenze und ersetzt keinen unbekannten Bestand stillschweigend.
3. **Lokale Anpassungen:** Vorhandene Änderungen und zusätzliche Dateien erhalten.
   Ohne verlässlichen Ausgangsstand keine Unverändertheit behaupten. Konflikte
   dem Nutzer zur Entscheidung vorlegen; keine automatische Zusammenführung.
4. **Installation:** Nach dem Verfahren und den Freigaberegeln des Agentensystems
   aktualisieren. Bei Dateikopien vorher sichern und einen vollständigen Dateisatz
   herstellen; einfaches `cp -r` über den alten Ordner genügt nicht, weil entfallene
   Dateien zurückbleiben können. Teilweise Updates dürfen nicht als Erfolg gelten.
5. **Prüfen und laden:** Vollständigkeit/Manifest prüfen, neue Anweisungen lesen
   oder Sitzung neu starten. Erst dann die neue Skill-Version übergeben.
6. **Fortsetzen:** Nur einen nachweislich vor Ausführung gesperrten Befehl erneut
   ausführen. Bei unklarem vorherigem Erfolg zuerst Daten/Audit prüfen, um doppelte
   Buchungen zu vermeiden.

Allgemeine Upstream-Anweisungen und lokale Regeln bleiben getrennt. Mandanten-
`AGENTS.md`, `CLAUDE.md`, globale `SOUL.md` und Adapter werden durch diesen Ablauf
nicht automatisch ersetzt. Mandantenangaben gehören ins Dossier; allgemeine lokale
Arbeitsanweisungen in eine getrennte Ergänzung. Widersprüche werden vor Buchungen
geklärt; lokale Regeln umgehen keine CLI-Validierung.

Ein CLI-Downgrade oder Rollback des Skills ist keine automatische Reparaturaktion.
Der wieder verwendete Stand muss ebenfalls kompatibel sein. Fehlt ein geeigneter
Installations-/Reload-Weg, bleibt die Aufgabe mit einem konkreten Hinweis stehen.

## Agentenspezifische Einbindung

Adapter enthalten dauerhafte Einstiegspunkte: Skill laden, dessen Version angeben,
Dossier lesen, Preflight durchführen und nach Update neu laden. CLI-Regeln liegen
im Paket. Für zunächst Claude Code, OpenCode und Hermes sind vor Auslieferung
jeweils verifizierte Anleitungen erforderlich: Installationsweg, Workspace-/globale
Priorität, Versionsübergabe, Vergleich und lokale Anpassungen, Reload/Neustart und
Wiederherstellung nach einem abgebrochenen Update.

Ungeprüfte Beispiele wie „in `.claude/` kopieren“ gelten nicht als Unterstützung.
Einzelne Adapter können nacheinander freigegeben werden; ungeprüfte Systeme werden
als solche gekennzeichnet. `euer` setzt keinen universellen Skill-Pfad voraus.

## Tests und Akzeptanzfälle

- Skill-Auskunft ohne DB, Config oder Versionsangabe; defekte Config verhindert
  keine Bundle-Auskunft und keine aussagekräftige Diagnose.
- Zwei Agenten geben unterschiedliche Versionen an; globale Registrierung eines
  anderen Agenten hat keinen Einfluss. Flag hat Vorrang vor Prozessumgebung.
- Bekannte kompatible ältere/neue Version, Mindestversion unterschritten,
  CLI außerhalb des Bereichs, unbekannte zukünftige und syntaktisch ungültige Version.
- Numerischer Versionsvergleich, Grenzen einschließlich/ausschließlich,
  Katalog-/Manifestkonsistenz und Annahme des mitgelieferten Bundles.
- Jede Zeile der Befehlsmatrix: gesperrte Mutationen erzeugen weder DB-Änderung
  noch Backup/Export/Config-Änderung; Lesen und echte Dry-runs bleiben möglich.
- CLI verändert weder Agenten-Skill noch Dossier/Adapter, auch bei Versionskonflikt.
- Offline-Auskunft aus installiertem Wheel und aus sdist gebautem Wheel außerhalb
  des Repositorys; vollständige Referenzen und identische Hashes auf Linux,
  macOS und Windows.
- Adapter-Abnahme: Update während einer Sitzung, erneutes Lesen oder neue Sitzung,
  Erhalt lokaler Änderungen und Fortsetzen ohne doppelte Buchung. Keine behauptete
  technische Garantie über den Modellkontext.
- JSON-Ausgaben, Warnungen, Exitcodes und vollständige Reparaturschritte.

Die Syntaxreferenz wird aus einer ohne Seiteneffekte erzeugbaren Parserdefinition
abgeleitet oder strukturiert dagegen geprüft: vollständige Befehlspfade,
Positionsargumente, Flags, Defaults, Choices und Ausschlussgruppen. Core-Commands
werden unabhängig von zufällig installierten Plugins geprüft; Plugins verantworten
ihre eigene Referenz. Ein Substring-Test allein reicht nicht aus. Ausgewählte
Beispiele werden ausgeführt; Output-Verträge und fachliche Semantik separat getestet.
Alle relativen Links im ausgelieferten Skill müssen innerhalb des Pakets auflösen.

## Umsetzung und Release-Vertrag

1. Spec einschließlich Befehls- und Fehlervertrag reviewen.
2. Kanonischen Skill, Manifest/Katalog und Build-Bundling mit Artefaktprüfungen umsetzen.
3. Versionsübergabe und Status implementieren; Bundle-Validierung und
   Kompatibilitätslogik in Services, Commands als View-Controller.
4. Mutationssperre, `doctor`-Integration und Agentenanleitungen ergänzen.
5. Dokumentationsmigration, Akzeptanztests und Release Notes abschließen.

Diese Spec-Überarbeitung allein benötigt keinen Release oder Versionsbump. Die
spätere verpflichtende Skill-Angabe/Sperre verändert die bisherige CLI-API und ist
nach Projektregel ein Breaking Change. Ein vorgeschaltetes rein additives Bundle-/
Status-Release kann separat als MINOR erscheinen; es darf keine aktive Sperre
suggerieren. Vor Veröffentlichung gelten Tests, Lint, Build und Artefakt-Smoke-Test.

Jeder betroffene Release erhält unter „Agenten-Dateien“ folgende Angaben:

| Bereich | Angabe je Release |
|---|---|
| Skill-Package | Version vorher/nachher, Kompatibilität, Pflicht/Empfehlung, konkreter Update-/Prüfschritt |
| Rolle | Änderung der gemeinsamen Rolle; Release-Bezug, sofern keine eigene Version existiert |
| Agenten-Adapter | Betroffene Systeme/Dateien, nötige Anpassung und Reload/Neustart |
| Mandanten-Dossier | Kein automatischer Ersatz; gegebenenfalls manuell zu klärende neue Angaben |

Upgrade-Schritte unterscheiden Erstinstallation, unveränderte Kopie, lokal angepasste
Altinstallation und parallele Agenten. Bereits veröffentlichte Release Notes bleiben
unverändert. Spec-Status und Entwicklungstabelle wechseln erst nach vollständiger
Umsetzung auf „Implementiert“.

## Dokumentation nach Implementierung

Betroffen sind `README.md`, `DEVELOPMENT.md`, `docs/CONCEPTS.md`, `docs/USER_GUIDE.md`,
`docs/FAQ.md`, `docs/USER_JOURNEY.md`, `docs/RELEASE_NOTES.md`, der kanonische Skill
mit Referenzen, Rollen-/Agenten-Templates und `docs/templates/onboarding-prompt.md`.
Paketmetadaten und Links auf migrierte Inhalte werden geprüft. Spec 023 wird auf den
gemeinsamen Fehlervertrag abgestimmt.
