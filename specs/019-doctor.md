# Spec 019: `euer doctor` für Umgebungs- und Pre-Flight-Diagnose

## Status

Implementiert

## Originalfeedback (wörtlich)

> Ein Diagnosebefehl wäre nützlich – etwa ein neu zu entwickelndes euer doctor, nicht ein bereits vorhandenes Kommando. Er könnte Version, ausführbaren Pfad, Installationsquelle, doppelte Entry-Points, DB-Pfad und nötige Migrationen anzeigen. Bei konkurrierenden pipx-/Brew-Installationen sollte er klar sagen, welche Version der normale Aufruf verwendet und wie man das behebt.
>
> Die Installationsdoku sollte außerdem einen einzigen kanonischen Brew-Befehl nennen und den Distributionswechsel von euercli zu euer Schritt für Schritt behandeln. Der Homebrew-Tap hatte zunächst noch 0.9.0, während PyPI schon 0.10.2 hatte; nach deiner Aktualisierung bestätigte brew info dann 0.10.2. Die mögliche Verzögerung des Taps sollte direkt bei den Upgrade-Hinweisen stehen.

## Einordnung & Learning

Das ursprüngliche Feedback entstand während einer Migration aus der privaten Entwicklungsphase
(altes Paket `euercli` via `pipx` hin zu `euer` via Homebrew). Da `euer` erst nach der
Namensfestlegung öffentlich vermarktet wird, existiert `euercli` für reguläre Nutzer nicht.
Spezifische Heuristiken oder Code-Pfade für `euercli` entfallen daher als nicht benötigter
Ballast (YAGNI).

Der eigentliche, dauerhafte Wert von `euer doctor` liegt in einem **Pre-Flight-Healthcheck**
für KI-Agenten und Nutzer:
1. **Verdeckte Entry-Points:** Da `euer` sowohl über Homebrew als auch über `pipx` und `pip`
   installiert werden kann, führen parallele Installationen oder venvs im `$PATH` oft dazu,
   dass nach einem Upgrade weiterhin ein altes `euer`-Binary aufgerufen wird.
2. **Datenbank- & Arbeitsverzeichnis-Klarheit:** Agenten wechseln häufig Verzeichnisse.
   `euer doctor` klärt vorab, welcher DB-Pfad effektiv genutzt wird, ob die Datei physisch
   existiert (Schutz vor stillschweigender Neuanlage) und ob der Schemastand aktuell ist.
3. **Optionale Features & Berechtigungen:** Sofortige Prüfung, ob optionale Abhängigkeiten
   wie `openpyxl` (für XLSX-Export) installiert sind und ob Beleg- sowie Exportpfade schreib-
   und lesbar sind.

## Anforderungen

- **Befehl:** Neuer Subcommand `euer doctor` mit strukturierter deutscher Terminal-Ausgabe
  und `--json` für maschinenlesbare Agenten-Prüfungen vor Beginn von Buchungsaufgaben.
- **Laufzeitumgebung & Entry-Point:**
  - Aktive Version aus `euercli.VERSION`, Interpreter (`sys.executable`), Python-Version.
  - Erkannter Typ der Installationsquelle (Homebrew, pipx, virtuelles Environment / venv,
    oder editierbarer Quellcode-Checkout).
  - Aufgelöster realer Pfad des aktiven `euer`-Binaries.
- **PATH- und Installationskollisionen:**
  - Durchsucht `$PATH` ausschließlich nach weiteren ausführbaren Dateien namens `euer`.
  - Meldet gefundene Duplikate in Suchreihenfolge; fasst Symlinks zusammen.
  - Keine Ausführung fremder Binaries zur Versionsermittlung.
  - Bei konkurrierenden Pfaden (z. B. `~/.local/bin/euer` verdeckt `/opt/homebrew/bin/euer`)
    konkreten Behebungshinweis ausgeben (z. B. `pipx uninstall euer` oder Shell-PATH anpassen).
- **Datenbank- & Schema-Status (Read-Only):**
  - Ermittelt den effektiven DB-Pfad (CLI-Parameter `--db`, Umgebungsvariable oder Default `euer.db`).
  - Physische Existenzprüfung vor Verbindungsaufbau: Verhindert, dass `doctor` selbst eine leere
    SQLite-Datei erzeugt.
  - Prüft Lesbarkeit, Dateigröße, Berechtigungen und offene Migrationen (Abgleich gegen
    die jeweils bekannte Schemaversion).
  - Führt eine schnelle, rein lesende Integritätsprüfung aus (`PRAGMA quick_check`).
- **Konfiguration & Verzeichnispfade:**
  - Prüft Existenz und Gültigkeit der `config.toml`.
  - Validiert konfigurierte Arbeitsordner (`receipts.root`, `exports.directory`): Existenz,
    Lese- und Schreibrechte.
- **Optionale Features:**
  - Prüft Verfügbarkeit von `openpyxl` (`HAS_OPENPYXL`). Falls abwesend, Hinweis auf
    Installationserweiterung (z. B. `pipx inject euer openpyxl` oder `brew`-Hinweis).
- **Sicherheits- und Ausgabegarantien:**
  - Rein diagnostisch: Verändert unter keinen Umständen Datenbank, Config, Dateien oder den PATH.
  - Standardmäßig rein lokal und offlinefähig (keine zwingenden Netzwerkaufrufe).
  - `--json` liefert ein stabiles Schema (Felder: `status`, `version`, `binary`, `path_duplicates`,
    `database`, `config`, `features`, `recommendations`); keine sensiblen Buchungsinhalte oder
    Passwörter.

## Akzeptanzfälle

1. **Standard-Setup (Homebrew):** `euer doctor` meldet Homebrew-Installation, aktuelle Version,
   gefundene DB und Status aller Verzeichnisse ohne Warnungen.
2. **Kollision zweier `euer`-Installationen:** Meldet, dass z. B. `pipx` das Homebrew-Paket verdeckt,
   zeigt beide Pfade und gibt den passenden Deinstallationsbefehl aus.
3. **Fehlende/Uninitialisierte Datenbank:** Meldet klar, dass keine DB am Zielort existiert, und
   empfiehlt `euer init`, statt ungefragt eine neue DB anzulegen.
4. **Fehlendes Excel-Modul:** Meldet Status `Warnung` für Excel-Export mit konkretem Befehl zum Nachinstallieren.
5. **Offene Migrationen:** Meldet Schema-Rückstand und verweist auf `euer init` (bzw. Spec 020).

## Dokumentation nach Implementierung

- `README.md` und `docs/USER_GUIDE.md`: `euer doctor` als erster Schritt bei Problemen oder zur
  Ersteinrichtungsprüfung.
- `docs/skills/euer-buchhaltung/SKILL.md`: Aufnahme von `euer doctor --json` in den Pre-Flight-Check
  des Agenten zu Beginn einer Sitzung.
- `docs/RELEASE_NOTES.md`: Vorstellung des Diagnosebefehls.
