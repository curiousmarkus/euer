# Spec 022: Versionierter Skill als primäre Dokumentation

## Status

Offen

## Ziel

Der Buchhaltungs-Skill ist die primäre Bedienungsdokumentation für Agenten. Er hat
eine eigene Version und wird vollständig mit der CLI ausgeliefert. Die CLI vergleicht
seine Version mit der in der Config bestätigten Version und
weist bei Abweichungen auf das nötige Skill-Update hin.

## 1. Version und Auslieferung

- Kanonische Quelle: `docs/skills/euer-buchhaltung/`. Der Build übernimmt den gesamten
  Ordner nach `euercli/assets/skill/`; diese Kopie wird nicht separat gepflegt.
- `SKILL.md` enthält im YAML-Header unter `metadata` das Feld `version` als
  Zeichenkette `"MAJOR.MINOR.PATCH"`. Dies ist die einzige Quelle der Skill-Version.
  Die CLI liest die erwartete Version aus ihrem gebündelten `SKILL.md`.
- Änderungen an ausgelieferten Skill-Inhalten erhöhen die Skill-Version. Ein
  CLI-Release ohne Skill-Änderung behält die bisherige Skill-Version bei.
  `euercli.VERSION` bleibt die unabhängige Softwareversion.
- Es gibt keinen separaten Skill-Release-Prozess. Wheel und sdist enthalten alle
  Skill-Dateien; das aus der sdist gebaute Wheel enthält denselben Skill.
- Maßgeblich ist der Skill des tatsächlich aufgerufenen CLI-Pakets, nicht ein
  vermeintlich neuester Stand im Internet. Version und Bundle-Pfad sind offline
  abrufbar. Versionsbereiche und Kompatibilitätskataloge sind nicht erforderlich.

## 2. Bestätigung in der Config

Die CLI kann den Skill eines Agenten nicht selbst prüfen. Deshalb bestätigt der
Agent nach Einrichtung oder Update seine Skill-Version in der bestehenden globalen
Config (`~/.config/euer/config.toml`, unter Windows am bestehenden Config-Pfad):

```toml
[skill]
version = "1.2.3"
```

**Annahme:** Im Regelfall arbeitet nur ein Agent mit der Installation. Ein gemeinsamer
Versionswert genügt; Agentenkennungen und zusätzliche Aufrufparameter entfallen.
Bei mehreren Agenten mit unterschiedlichen Skill-Ständen kann die CLI diese nicht
unterscheiden. Diese Einschränkung wird bewusst zugunsten einfacher Bedienung akzeptiert.

Der Agent liest die Version aus seiner tatsächlich verwendeten `SKILL.md` und
speichert sie über den bestehenden Config-Befehl:

```bash
euer setup --set skill.version "1.2.3"
```

`setup --set` validiert für `skill.version` eine dreiteilige Versionsnummer und
erhält die übrige Config. Auch eine von der erwarteten Version abweichende Version
darf wahrheitsgemäß bestätigt werden. Der Eintrag ist eine Selbstauskunft, kein
technischer Nachweis geladener Inhalte. Bei Fachbefehlen liest die CLI diesen Wert
automatisch; der Agent muss weder Identität noch Version pro Aufruf angeben.

## 3. Versionsprüfung und Blockade (mit Escape Hatch)

Bei Fachbefehlen vergleicht die CLI `skill.version` aus der Config exakt mit der
gebündelten Skill-Version. Fehlende oder ungültige Bestätigung sowie eine
Versionsabweichung erzeugen einen Fehler (Exitcode 1) auf stderr.

Die Fehlermeldung enthält bestätigte und erwartete Skill-Version,
den absoluten Bundle-Pfad und folgende Handlungsanweisung:

> [✗] FEHLER: Deine bestätigte Skill-Version weicht von der erwarteten Version ab.
> Ersetze deinen Skill vollständig durch den mitgelieferten Stand über den
> Installationsweg deines Agentensystems. Lies die aktualisierten Anweisungen.
> Bestätige anschließend die verwendete Version mit:
> `euer setup --set skill.version "<VERSION>"`
>
> Falls du das Update aufgrund fehlender Rechte nicht durchführen kannst,
> hänge `--ignore-skill-version` an deinen Befehl an, um die Blockade zu umgehen.

Auch ein neuerer bestätigter Skill ist eine Abweichung; die CLI fordert deshalb
nicht automatisch zu einem Software-Upgrade auf, sondern blockiert ebenfalls
mit dem Verweis auf das lokale Bundle.

**Entscheidung: Blockade mit Notausgang.** Die strikte Blockade (Exitcode 1)
zwingt den Agenten dazu, sein Wissen (Skill) zu aktualisieren, bevor er
potenziell falsche Daten produziert (Selbstheilung). Kann der Agent die
Dateien mangels Dateisystemrechten nicht aktualisieren, bewahrt ihn das Flag
`--ignore-skill-version` davor, in einer Endlosschleife gefangen zu sein,
und ermöglicht die fortgesetzte Nutzbarkeit auf eigenes Risiko.

Hilfe, Versionsanzeige, `doctor`, `config show` und die Bestätigung über
`setup --set skill.version` bleiben ungeblockt nutzbar, damit der Agent
diagnostizieren und den Zustand reparieren kann.
Eine defekte Config oder ein defektes Bundle wird als echter Dateifehler
gemeldet, nicht als Versionsabweichung.

## 4. Skill-Auskunft in `doctor`

`euer doctor` zeigt zusätzlich die bestätigte Skill-Version, die erwartete
Skill-Version, den absoluten Bundle-Pfad und den Prüfstatus. Ein eigener
Skill-Statusbefehl wird nicht eingeführt.

`euer doctor --json` ergänzt das bestehende Ergebnis um ein Objekt `skill` mit
`confirmed_version`, `expected_version`, `bundle_path` und `status`.
Mögliche Skill-Statuswerte: `current`, `unconfirmed`, `invalid`, `mismatch` und
`error` bei nicht lesbarer Config oder defektem Bundle. Fehlende Werte sind `null`.
CLI-Version und übrige Diagnosen bleiben in ihren bisherigen Feldern.

Die Skill-Auskunft wird auch bei fehlender Datenbank oder Config ausgegeben.
Fehlende oder abweichende Bestätigung wird als Warnung in die Gesamtdiagnose
aufgenommen, nicht als Fehler. Lese-/Paketfehler werden als Fehler aufgenommen.
Die bestehende Exitcode-Regel von `doctor` bleibt erhalten: 1 bei Fehlern, sonst 0.
Ein unabhängiger DB-Fehler kann daher trotz aktuellem Skill zu Exitcode 1 führen.

Die CLI bietet keinen Installer und keinen Datei-Diff. Warnungen bei Fachbefehlen
werden im JSON-Modus als strukturierte Hinweise auf stderr ausgegeben. Der gemeinsame
Ausgabevertrag und das bisherige Skill-Reparaturbeispiel in
[Spec 023](023-ai-io.md) müssen bei Umsetzung entsprechend angepasst werden.

## 5. Unveränderter Skill und Update-Hinweis

`SKILL.md` enthält ausdrücklich folgende Anweisung:

> Bearbeite oder ergänze diesen Skill einschließlich seiner Referenzen nicht lokal.
> Aktualisiere ihn ausschließlich durch vollständigen Austausch gegen den mit der
> CLI ausgelieferten Stand. Dessen Version und absoluten Quellpfad findest du mit
> `euer doctor --json` unter `skill.expected_version` und `skill.bundle_path`.
> Mandantenspezifische Angaben gehören in das persönliche Dossier, nicht in den Skill.

Der Paketpfad `euercli/assets/skill/` wird im Skill als Bezugsquelle genannt.
Ein absoluter Pfad wird dort nicht fest eingebaut, weil er von Installationsart
und System abhängt; `doctor` ermittelt ihn für die tatsächlich aktive CLI.

Nach einem Update muss der Agent die neue `SKILL.md` und benötigte Referenzen lesen
beziehungsweise eine neue Sitzung starten. Erst danach bestätigt er die Version
mit `euer setup --set skill.version "<VERSION>"`.

Die Installationsreferenz beschreibt für Claude Code, OpenCode und Hermes jeweils
Installation, vollständigen Austausch und erneutes Laden. Die CLI führt diese
Schritte nicht aus und kann ihre Durchführung nicht kontrollieren. Ein Diff-/Merge-
Verfahren für lokale Skill-Anpassungen gehört nicht zum Funktionsumfang; solche
Anpassungen werden nicht unterstützt. Persönliche `AGENTS.md`, `CLAUDE.md`, `SOUL.md`
und andere Dateien außerhalb des Skills werden beim Austausch nicht automatisch
ersetzt. Fehlen Update-Rechte, informiert der Agent den Nutzer.

## 6. Dokumentationsstruktur und Migration

| Datei im Skill | Inhalt |
|---|---|
| `SKILL.md` | Version, Rolle, Arbeitsablauf, Änderungsverbot, Bundle-Bezugsquelle, Versionsbestätigung und Referenzindex |
| `references/installation_and_setup.md` | Installation, Agenteneinbindung, Config und Updates |
| `references/onboarding.md` | Bestehendes Interview und Mandanten-Dossier; keine zweite Interview-Anleitung |
| `references/cli_reference.md` | Alle CLI-Befehle mit Syntax, Bedeutung, Voraussetzungen, Ausgabe und Beispielen |
| `references/domain_rules.md` | Fachliche Wenn-Dann-Regeln mit Begründung, Quelle und Geltungszeitraum |

Inhalte aus `docs/USER_GUIDE.md` und `docs/FAQ.md` werden in diese Dateien migriert;
anschließend werden beide alten Dateien entfernt. Fachliche Sonderfälle wie Prepaid
und Cashback gehören in `domain_rules.md`, Bedienungsfragen in die CLI-Referenz.
Alle Links und Paketmetadaten werden auf die neuen Ziele umgestellt. Relative
Referenzen im Skill müssen auch im installierten Bundle funktionieren.

Die Dokumentation für menschliche Anwender beschränkt sich auf `README.md`
(Fähigkeiten und Handoff-Prompt), `docs/CONCEPTS.md` (Konzept und Grenzen) und
`docs/USER_JOURNEY.md` (Ablauf der Arbeit des Agenten und Beteiligung des Menschen).
Entwicklerdokumentation und Release Notes bleiben bestehen.

## 7. Vollständigkeit und Abnahme

Ein CI-Test gleicht den `argparse`-Baum mit den Befehlsabschnitten in
`cli_reference.md` ab. Jeder vollständige Core-Befehlspfad, jedes Positionsargument
und jedes Flag muss dem richtigen Befehlsabschnitt zugeordnet sein. Ein irgendwo
im Dokument erwähntes Flag genügt nicht. Plugin-Befehle gehören in die jeweilige
Plugin-Dokumentation.

Der Test sichert die strukturelle Abdeckung, nicht die fachliche Vollständigkeit.
Das Review prüft zusätzlich Bedeutung, Voraussetzungen, Wechselwirkungen,
Fehlerfälle und brauchbare Beispiele. Ausgewählte Beispiele werden gegen die CLI
getestet. Eine reine generierte Befehlsliste erfüllt die Anforderung nicht.

Abnahmekriterien:

- Skill samt Referenzen und Version ist aus installiertem Wheel und aus sdist
  gebautem Wheel ohne Repository und ohne Netzwerk nutzbar.
- `setup --set skill.version` speichert die Bestätigung und erhält die übrige
  Config. Fachbefehle prüfen diesen Wert ohne zusätzliche Aufrufparameter.
- Fehlende, ungültige, ältere und neuere Bestätigungen blockieren Fachbefehle mit Exitcode 1 und liefern die beschriebenen Fehlerhinweise inklusive Escape Hatch. Passende Bestätigungen erzeugen keine Fehler.
- Das Flag `--ignore-skill-version` umgeht die Blockade und lässt den Fachbefehl regulär durchlaufen (Exitcode 0 bei sonstigem Erfolg).
- Skill-Auskunft in `doctor` und Bestätigung funktionieren ungeblockt, auch ohne DB und bei
  der Erstinstallation; unabhängige Diagnosefehler bleiben sichtbar.
- CLI-Patch ohne Skill-Änderung erfordert keine neue Bestätigung. Änderungen am
  Skill werden mit neuer Skill-Version und Release-Hinweisen ausgeliefert.
- `doctor --json` ergänzt `skill`, ohne bestehende Felder zu verändern, und meldet
  den Bundle-Pfad der aktiven CLI. Die Skill-Anweisung verweist auf dieses Feld und
  verbietet lokale Änderungen einschließlich Ergänzungen der Referenzen.
- CLI verändert keine Agenten-Skills oder Dossiers. Dokumentationsmigration,
  Referenzlinks und strukturierter Coverage-Test sind vollständig geprüft.

## Release und betroffene Dateien

Die Umsetzung aktualisiert Skill, Referenzen, Agenten-/Onboarding-Templates,
`README.md`, `docs/CONCEPTS.md`, `docs/USER_JOURNEY.md`, `DEVELOPMENT.md` und die
Paketmetadaten; `USER_GUIDE.md` und `FAQ.md` entfallen nach Migration.
Release Notes nennen unter „Agenten-Dateien“ die Skill-Version vorher/nachher,
Bestätigung über `skill.version`, nötige Adapteränderungen und den Schutz des Dossiers.
Bereits veröffentlichte Release Notes bleiben unverändert.

Die Spec bleibt bis zur Umsetzung offen. Diese reine Spec-Änderung benötigt keinen
Versionsbump; die Implementierung erhält einen Release gemäß `DEVELOPMENT.md`.
