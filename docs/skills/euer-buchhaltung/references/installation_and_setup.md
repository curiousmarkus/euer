# Installation, Einrichtung und Skill-Updates

Diese Referenz beschreibt Installation und vollständigen Austausch des Skills. Die
CLI selbst installiert keine Agentendateien. Die persönliche `AGENTS.md`,
`CLAUDE.md`, `SOUL.md` und andere Dateien außerhalb des Skill-Ordners bleiben erhalten.

## Skill in Agentensystemen installieren und aktualisieren

1. Ermittle mit `euer doctor` den absoluten Bundle-Pfad und die
   erwartete Skill-Version der tatsächlich aufgerufenen CLI.
2. Kopiere den **gesamten** Ordner aus `skill.bundle_path` in den Skill-Ordner deines
   Agentensystems. Ersetze die alte Skill-Kopie vollständig, einschließlich
   `references/`. Ergänze oder bearbeite Dateien im Skill nicht lokal.
3. Lade den Skill neu (neue Sitzung oder Agent neu starten), lies `SKILL.md` und
   die für den Auftrag nötigen Referenzen.
4. Bestätige erst danach die Version aus der tatsächlich verwendeten `SKILL.md`:
   `euer setup --set skill.version "MAJOR.MINOR.PATCH"`.
5. Prüfe `euer doctor`: Der Prüfstatus muss `current` bzw. aktuell sein.

- **Claude Code:** Lege den vollständigen Ordner als Skill unter dem von Claude Code
  verwendeten Skill-Verzeichnis ab; beim Update den Ordner vollständig austauschen
  und eine neue Claude-Sitzung starten.
- **OpenCode:** Lege ihn im OpenCode-Skill-Verzeichnis ab; beim Update den Ordner
  vollständig austauschen und OpenCode beziehungsweise die Sitzung neu starten.
- **Hermes:** Lege ihn im Hermes-Skill-Verzeichnis ab; beim Update den Ordner
  vollständig austauschen und eine neue Hermes-Sitzung beginnen.

Prüfe den konkreten Skill-Pfad deiner Agenteninstallation. Kannst du den Skill wegen
fehlender Rechte nicht ersetzen, informiere den Nutzer. Für einen einzelnen
CLI-Aufruf kann `--ignore-skill-version` die Sperre übergehen; das behebt den
abweichenden Stand nicht.

## CLI-Installation und Konfiguration

Der Ablauf reicht von Installation und Onboarding über die erste Rechnung und
den Monatsabgleich bis zum Jahresabschluss. Die Arbeitsweise des Agenten steht
in `SKILL.md` und den Referenzen dieses Bundles.

## Voraussetzungen

- Python 3.11+
- Optional: `openpyxl` für XLSX‑Export

## Installation

### Empfohlene Installation (pipx)

`pipx` installiert `euer` global in einer isolierten Umgebung, ohne dass du je eine virtuelle
Umgebung aktivieren musst:

```bash
# euer installieren
pipx install euer
```

Danach ist `euer` sofort und dauerhaft in jedem Terminal verfügbar.

Für den optionalen XLSX-Export installierst du das Extra direkt mit:

```bash
pipx install "euer[xlsx]"
```

Für den DATEV-Export installierst du das offizielle Add-on `euer-datev`. Mit pipx
kann es in einer eigenen Umgebung oder gemeinsam mit `euer` installiert werden:

```bash
pipx install euer-datev
# Bei einer bestehenden pipx-Installation alternativ: pipx inject euer euer-datev
```

Bei getrennter Installation müssen `euer` und `euer-datev` im `PATH` liegen.
Mit uv ist `uv tool install --with euer-datev euer` möglich. Danach steht in
allen Varianten `euer datev` zur Verfügung. Weitere Infos:
[euer-buchhaltung.de/datev](https://euer-buchhaltung.de/datev).

Alternativ ist auf macOS und Linux der Homebrew-Tap verfügbar:

```bash
brew install curiousmarkus/euer/euer
brew install curiousmarkus/euer/euer-datev
```

Der GitHub-Checkout bleibt als Fallback für Entwicklungsversionen möglich:

```bash
pipx install git+https://github.com/curiousmarkus/euer.git
```

**Update auf die neueste Version:**

```bash
pipx upgrade euer
```

Bei einer Homebrew-Installation verwendest du `brew upgrade euer`. Die Basisinstallation
enthält kein `openpyxl`; für XLSX muss das Extra installiert sein oder Homebrew verwendet
werden.

Der Homebrew-Tap übernimmt neue PyPI-Releases zeitversetzt, laut Release-Prozess
geplant spätestens innerhalb von sechs Stunden. `brew info euer` zeigt die im
Tap angebotene Version, `euer --version` die tatsächlich gestartete. Ein Update
von `pipx` ändert keine Homebrew-Installation und umgekehrt.

### Von pipx zu Homebrew wechseln

1. Notiere mit `euer --version`, `command -v euer` und `pipx list` die aktive
   Installation. Sichere den Pfad zur bestehenden `euer.db` und die Config.
2. Installiere Homebrew mit dem kanonischen Befehl
   `brew install curiousmarkus/euer/euer`. Prüfe `brew info euer`.
3. Entferne nach erfolgreicher Installation die tatsächlich vorhandenen alten
   `pipx`-Pakete: `pipx uninstall euercli` und/oder `pipx uninstall euer`.
   Ein nicht installiertes Paket braucht keinen Uninstall-Aufruf.
4. Leere gegebenenfalls den Shell-Command-Cache (`rehash` in zsh,
   `hash -r` in bash), öffne ein neues Terminal und prüfe mit
   `command -v euer`, `type -a euer` und `euer --version` den aktiven Aufruf.
5. Wechsle in den richtigen Buchhaltungsordner und führe erst dann den
   unten beschriebenen DB-Upgrade-Ablauf aus.

### Umgebungs- und Pre-Flight-Diagnose (`euer doctor`)

Mit `euer doctor` prüfst du jederzeit den Zustand deiner Installation, deiner
Pfade und deiner Datenbank:

```bash
# Umgebungs- und Skill-Diagnose
euer doctor
```

`euer doctor` diagnostiziert rein lesend (ohne Schreibzugriffe oder Seiteneffekte):
- **Laufzeitumgebung:** Aktive Version, Python-Interpreter und erkannte Installationsquelle (Homebrew, pipx, venv, editable).
- **PATH-Kollisionen:** Sucht nach weiteren `euer`-Dateien im `$PATH` und warnt, falls beispielsweise ein altes pipx-Binary das neue Homebrew-Paket verdeckt.
- **Datenbank & Schemastand:** Prüft den effektiven DB-Pfad (CLI-Flag, Projekt-Config `.euer/config.toml` oder Standard `euer.db`), die Dateiexistenz (ohne eine leere DB anzulegen!), Lesbarkeit, Integrität (`PRAGMA quick_check`) und offene Migrationen.
- **Konfiguration & Verzeichnisse:** Validiert `config.toml`, Projekt-Config sowie Lese-/Schreibrechte für Beleg- und Exportverzeichnisse.
- **Optionale Features:** Prüft, ob `openpyxl` für den Excel-Export installiert ist.

### Bestehende Installation aktualisieren

Wenn du bereits eine lokale `euer.db` nutzt, aktualisiere nicht nur das CLI,
sondern auch die Datenbankstruktur. `euer init` ist dafür bewusst idempotent
und transaktionssicher: Es führt anstehende Schema-Migrationen kontrolliert aus
und ergänzt fehlende Tabellen oder Spalten.

Vor jeder Migration erstellt `euer` automatisch eine konsistente, WAL-sichere
Datenbanksicherung über die SQLite-Online-Backup-API im Verzeichnis
`~/.config/euer/backups/euer_YYYY-MM-DD_HHMMSS.db`.
Vor dem ersten schreibenden CLI-Befehl pro Datenbank und Kalendertag erstellt
`euer` dort zusätzlich einen Snapshot mit Datenbankkennung im Dateinamen.
Die täglichen Sicherungen ersetzen keine regelmäßige externe Sicherung der
Datenbank, der globalen und projektbezogenen Konfiguration sowie der Belege.

Empfohlener Ablauf nach jedem Update:

```bash
cd /pfad/zu/deinem/buchhaltungsordner

# CLI aktualisieren
pipx upgrade euer

# Lokale Datenbank migrieren (zeigt Status, Vorab-Prüfung und Backup-Pfad)
euer init

# Offene Nacharbeiten prüfen
euer incomplete list
euer summary --year 2026
```

#### Transparente Migrationen & Diagnose

`euer init` bietet umfassende Transparenz vor und nach Änderungen:

- **Preflight-Prüfung:** Zeigt den DB-Pfad, die erkannte Schemaversion sowie alle
  anstehenden Migrationen mit Beschreibung an.
- **Auswirkungsanalyse (Preflight Impact):** Berechnet vorab, wie viele und welche
  bestehenden Buchungen durch die Migration unvollständig werden (z. B. neue
  Pflichtfelder oder Prüfbedarfe bei Bewirtungen).
- **Automatisches Rollback:** Schlägt ein Migrationsschritt fehl, wird die gesamte
  Transaktion rückabgewickelt.
- **Abschlussbericht:** Nennt den Sicherungspfad, den neuen Schemastand und
  konkrete nächste Prüfschritte (`euer incomplete list`).

Zusätzliche Flags für `euer init`:

```bash
# Migration nur simulieren (keine Schreibzugriffe, kein Backup)
euer init --dry-run

# Vollständig neue Datenbank anlegen (Pflichtflag zur Vermeidung von Fehlplatzierungen)
euer init --create
```

`euer` speichert den DB-Pfad pro Buchhaltungsordner in `.euer/config.toml`.
Eine vorhandene `./euer.db` wird beim nächsten erfolgreichen `euer init` dort
eingetragen; `euer init --create` legt sie neu an und trägt sie ebenfalls ein.
Die Pfadwahl ist: `--db PFAD` für den einzelnen Aufruf, dann die Projekt-Config,
danach `./euer.db`. Ein relativer Config-Pfad bezieht sich auf den Projektordner.
Für eine DB an einem anderen Ort verbinde sie nach Prüfung dauerhaft mit:

```bash
euer --db /pfad/zu/euer.db init --save-db-path
```

Ohne `--save-db-path` gilt `--db` nur für diesen Aufruf. Ist eine konfigurierte DB
verschoben worden, bricht `euer` mit dem erwarteten Pfad ab. Verbinde die
vorhandene Datei mit dem obigen Befehl neu; `euer init --create` ist nur für eine
bewusst neue, leere Datenbank gedacht. Ein Buchungsbefehl legt niemals selbst
eine fehlende DB an. `euer config show` zeigt gewählten Pfad, Quelle und
Dateiexistenz. `init --dry-run` ändert auch die Projekt-Config nicht.

### Agenten-Dateien aktualisieren

Nach jedem CLI-Update `euer doctor` ausführen und den Skill anhand des
Bundle-Pfads vollständig austauschen, falls die erwartete Version von
der bestätigten Version abweicht. Die Schritte für Claude Code, OpenCode und
Hermes stehen am Anfang dieser Referenz. Die persönliche `AGENTS.md` und andere
Dateien außerhalb des Skill-Ordners bleiben erhalten. Prüfe
`docs/RELEASE_NOTES.md` des zur aktiven CLI-Version passenden Release-Tags auf
gezielte Änderungen an Rolle,
Adapter und Dossier. Ein CLI-Patch ohne Skill-Änderung erfordert keine neue
Bestätigung.

## Konfiguration und Ablage

Die allgemeine Konfiguration gilt für alle Buchhaltungsordner: unter macOS/Linux
`~/.config/euer/config.toml`, unter Windows `%APPDATA%\euer\config.toml`.
Der Datenbankpfad für einen Buchhaltungsordner steht dagegen in dessen
`.euer/config.toml`. Prüfe mit `euer config show` beide Pfade, bevor du Daten
änderst. Ein neuer Mandant darf nicht stillschweigend die globale Konfiguration
eines anderen Mandanten übernehmen.

Setze `tax.mode` nur aus dem bestätigten Steuerstatus des Mandanten. `euer setup`
kann Werte interaktiv einrichten; `euer setup --set <section.key> <value>` ändert
gezielt einen Wert. Belege und Exporte lassen sich beispielsweise so ablegen:

```toml
[receipts]
root = "/pfad/zu/Buchhaltung"
year_dir = "{year}"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"

[exports]
directory = "/pfad/zu/Buchhaltung/Exporte"
```

`receipts.year_dir` muss `{year}` enthalten. Belege liegen unter
`<root>/<Jahr>/<Typ>/<Belegname>`; der Jahresordner folgt dem
`payment_date`. `exports.directory` ist ein konkreter Ordner und unterstützt
keinen `{year}`-Platzhalter. Für einen einzelnen Jahreslauf kann
`euer export --year 2026 --output <Jahresordner>` einen anderen Zielordner
wählen. Ohne Endung im gespeicherten Belegnamen sucht `euer receipt check`
nach `.pdf`, `.jpg`, `.jpeg` und `.png`.

Ein optionales Buchungskonto verknüpft eine frei gewählte Kennung mit einer
vorhandenen EÜR-Kategorie:

```toml
[[ledger_accounts]]
key = "hosting"
name = "Hosting und Cloud"
category = "Laufende EDV-Kosten"
account_number = "4940"
```

`--ledger-account hosting` wählt dieses Buchungskonto und setzt die Kategorie;
`--account` bezeichnet dagegen das tatsächliche Zahlungs- oder Bankkonto.
Prüfe den Kontenrahmen mit `euer list ledger-accounts`. Persönliche
Zuordnungsregeln gehören ins Mandanten-Dossier, nicht in den ausgelieferten Skill.

Die [Dossier-Vorlage](../assets/Agents-Template.md) liegt im Skill-Bundle.
Im Repository liegen unter `docs/templates/` außerdem ein optionaler
`accountant-role.md` für spezialisierte Agenten und ein
`onboarding-prompt.md` für separate Chats. Ein allgemeiner Agent kann mit dem
vollständigen Skill einschließlich Referenzen und Vorlage arbeiten.
