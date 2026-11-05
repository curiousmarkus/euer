# Release-Leitfaden für euer

Dieses Dokument beschreibt den verbindlichen Release-Prozess für `euer`. Es richtet sich an Maintainer und automatisierte Agenten, um fehlerfreie, reproduzierbare Veröffentlichungen auf PyPI und GitHub Releases sicherzustellen und typische Fallstricke (z. B. geschützte Tags, Plattformunterschiede, Pfadmaskierung) systematisch zu vermeiden.

---

## 1. Grundprinzipien & Sicherheitsregeln

1. **PyPI ist unveränderlich (Immutable):** Einmal auf PyPI hochgeladene Versionen können weder überschrieben noch mit demselben Versionsbezeichner erneut hochgeladen werden.
2. **GitHub-Release-Tags sind geschützt (`refs/tags/v*`):** 
   - Das Repository erzwingt GitHub Rulesets für Tags.
   - Ein gepushter Tag **kann nicht gelöscht** und **nicht per `git push --force` aktualisiert** werden.
   - Scheitert ein Release nach dem Pushen des Tags in der CI, führt die Behebung **immer** über einen neuen SemVer-Patch-Release (z. B. `0.12.0` → `0.12.1`).
3. **Zuerst `main` pushen, dann den Tag:**
   - Der CI-Job `validate` prüft, ob der Commit des Tags bereits auf `origin/main` liegt (`validate_main_ancestry`).
   - Wird der Tag gepusht, bevor `main` auf GitHub aktualisiert wurde, schlägt der Release-Check sofort fehl.
4. **Keine manuellen PyPI-Uploads:** Releases erfolgen ausschließlich automatisiert über GitHub Actions via OpenID Connect (Trusted Publishing).

---

## 2. Häufige Fallstricke & wie man sie vermeidet

### A. Pfadmaskierung in TOML (Windows)
- **Problem:** Windows-Pfade enthalten Backslashes (`C:\Users\...`). Werden diese in doppelt geschätzten TOML-Strings eingefügt (`root = "{path}"`), interpretiert der TOML-Parser `\U` als Unicode-Escape und bricht mit `Fehler: Invalid hex value` ab.
- **Lösung:** In Konfigurations-Generatoren und Tests Pfade **immer** mit `.as_posix()` und/oder in einfachen Anführungszeichen `'...'` (Literal-Strings) schreiben:
  ```python
  # Richtig:
  f"[receipts]\nroot = '{self.receipts.as_posix()}'\n"
  
  # Falsch:
  f'[receipts]\nroot = "{self.receipts}"\n'
  ```

### B. Dateisystem-Semantik: Case-Sensitivity (Linux vs. macOS/Windows)
- **Problem:** macOS (APFS) und Windows (NTFS) ignorieren bei Datei-Lookups standardmäßig die Groß-/Kleinschreibung. Linux (ext4) unterscheidet strikt zwischen z. B. `.pdf` und `.PDF`.
- **Lösung:** Tests, die case-insensitive Auflösung prüfen, müssen per Dateisystem-Sonde prüfen, ob das aktuelle Dateisystem case-insensitive ist, und andernfalls überspringen:
  ```python
  probe = self.root / ".fs_probe"
  probe.write_text("x")
  is_case_insensitive = (self.root / ".FS_PROBE").exists()
  probe.unlink(missing_ok=True)
  if not is_case_insensitive:
      self.skipTest("Dateisystem unterscheidet Groß-/Kleinschreibung")
  ```

### C. Ungültige Dateinamenzeichen unter Windows (`"`, `<`, `>`, `:`, `\`, `|`, `?`, `*`)
- **Problem:** Unter Linux und macOS sind Zeichen wie `"` in Dateinamen erlaubt (z. B. `a,"b.pdf`). Unter Windows (NTFS) ist `"` streng verboten und führt zu `OSError: [Errno 22] Invalid argument`.
- **Lösung:** In Testfällen (z. B. für CSV-Escaping) unter Windows auf erlaubte Sonderzeichen wie Kommas (`a,b.pdf`) ausweichen oder plattformabhängig verzweigen (`if platform.system() == "Windows"`).

### D. CSV-Zeilenenden unter Windows (`lineterminator="\n"`)
- **Problem:** Python's `csv.writer` verwendet standardmäßig `\r\n`. Schreibt dieser auf `sys.stdout` unter Windows, übersetzt die Windows-Laufzeitumgebung das `\n` nochmals zu `\r\n`, was zu doppelten Wagenrückläufen (`\r\r\n`) und leeren Zeilen führt.
- **Lösung:** Bei allen CSV-Ausgaben auf die Standardausgabe immer explizit `csv.writer(sys.stdout, lineterminator="\n")` verwenden.

### E. Skill-Versionen synchron halten
- Bei Änderungen am AI-Agent-Skill (`docs/skills/euer-buchhaltung/`) muss die Skill-Version synchron in folgenden Dateien erhöht werden:
  1. `docs/skills/euer-buchhaltung/SKILL.md` (YAML-Frontmatter `version` und Hinweistext)
  2. `docs/skills/euer-buchhaltung/references/cli_reference.md`
  3. `docs/skills/euer-buchhaltung/references/domain_rules.md`
  4. `docs/templates/onboarding-prompt.md`
- Die CLI prüft beim Start über `euercli/skill.py`, ob der installierte Skill zur erwarteten Version passt.

### F. Encoding & Zeichensatz unter Windows (`PYTHONUTF8`, `CP1252`)
- **Problem:** Windows verwendet in Standardkonfigurationen für Datei- und Subprozess-IO `CP1252` statt UTF-8. Umlaute (`EÜR`, `äöü`) in Dateipfaden, CLI-Ausgaben oder Testprüfungen werden fehlerhaft dekodiert (`EÃœR`) oder führen zu Testabbrüchen (`AssertionError`).
- **Lösung:**
  1. Alle `open()`-Aufrufe müssen ein explizites `encoding="utf-8"` enthalten (überwacht durch die Ruff-Linter-Regel `PLW1514`).
  2. Datei-I/O via `Path.read_text()` und `Path.write_text()` muss stets `encoding="utf-8"` übergeben.
  3. CLI-Subprozesse in Tests müssen `encoding="utf-8"` verwenden (`subprocess.run(..., text=True, encoding="utf-8")`).
  4. In CI-Workflows (`ci.yml`, `release.yml`) und in `BaseCLITestCase` ist global `PYTHONUTF8: "1"` gesetzt.

### G. Offene SQLite-Verbindungen & File-Locks unter Windows (`WinError 32`)
- **Problem:** Unter Windows können geöffnete Dateien (insbesondere SQLite-Datenbanken und WAL-Dateien) nicht gelöscht werden. Schließt ein Test Verbindungen nicht explizit vor dem Ende der Methode, wirft `tempfile.TemporaryDirectory.cleanup()` in `tearDown()` einen `PermissionError: [WinError 32]`, da `tearDown()` in Python unittest *vor* den mit `addCleanup()` registrierten Callbacks läuft.
- **Lösung:**
  1. Datenbank- und Reader-/Writer-Verbindungen in Tests immer deterministisch im `finally:`-Block oder über `closing()` schließen und Trace-Callbacks abmelden (`reader.set_trace_callback(None)`).
  2. `BaseCLITestCase` initialisiert `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)` und fängt `PermissionError` im Teardown ab.

### H. C-Extension-Typen niemals monkeypatchen (Python 3.15+)
- **Problem:** Builtin- und C-Extension-Typen (wie `os.DirEntry`) besitzen ab neueren CPython-Versionen keine veränderlichen Attribute mehr. Ein Versuch via `patch("os.DirEntry.is_file")` scheitert mit `TypeError: cannot set 'is_file' attribute of immutable type 'posix.DirEntry'`.
- **Lösung:** Statt interner C-Typen stets die übergeordneten Python-Schnittstellen mocken (z. B. `patch("os.scandir")` mit einem Mock-Kontextmanager).

---

## 3. Pre-Flight Checkliste (Vor dem Release)

Vor dem Erstellen eines Release-Tags müssen folgende Schritte vollständig durchlaufen werden:

- [ ] **Git-Arbeitsbereich sauber:**
  ```bash
  git status -s
  ```
  Es dürfen keine ungesicherten Änderungen oder ungetrackten Dateien vorhanden sein.
- [ ] **Tests und Linting erfolgreich:**
  ```bash
  make lint
  make test
  ```
- [ ] **Skill-Konsistenz geprüft (falls Skill geändert wurde):**
  ```bash
  python -m unittest tests/test_skill_version.py
  ```
- [ ] **Version hochzählen (SemVer):**
  Ausschließlich über Make/Skript oder in `euercli/__init__.py`:
  ```bash
  make bump-patch   # oder bump-minor / bump-major
  ```
- [ ] **Release Notes pflegen:**
  In `docs/RELEASE_NOTES.md` einen neuen Abschnitt `## X.Y.Z` anlegen:
  - Nutzerrelevante Neuerungen und Fixes beschreiben.
  - Upgrade- und Migrationsschritte dokumentieren (oder explizit festhalten, dass keine nötig sind).
  - Eventuelle Agenten-/Skill-Anpassungen aufführen.
  - *Wichtig:* Niemals bereits veröffentlichte Versionsabschnitte nachträglich bearbeiten!
- [ ] **Artefakte lokal bauen und prüfen:**
  ```bash
  make build
  .venv/bin/python -m scripts.verify_artifacts dist
  ```
- [ ] **Release-Check ausführen:**
  ```bash
  .venv/bin/python -m scripts.release_check --tag "v$(sed -nE 's/^VERSION = \"([0-9]+\.[0-9]+\.[0-9]+)\"$/\1/p' euercli/__init__.py)" --main-ref HEAD
  ```

> [!TIP]
> `make release-verify` führt vor dem Tag Linting, Tests, Build, Artefaktprüfung
> sowie Versionsformat- und Release-Notes-Prüfung aus. Nach Anlegen des annotierten
> Tags prüft `make release-check` zusätzlich dessen Existenz, Typ und Main-Ancestry.

---

## 4. Release durchführen (Schritt-für-Schritt: 2-Phasen-Release)

> [!CAUTION]
> **Das 2-Phasen-Release-Prinzip ist zwingend einzuhalten!**  
> GitHub-Tags (`refs/tags/v*`) sind durch Repository-Rulesets geschützt und können weder gelöscht noch force-gepusht werden. Ein Fehler in der Release-CI (z. B. auf einem Windows-Matrix-Runner) blockiert die Version dauerhaft. Daher wird das Tag erst erstellt und gepusht, wenn `main` auf GitHub Actions nachweislich grün ist!

### Schritt 1: Release-Commit erstellen
```bash
release_version=$(.venv/bin/python -c 'from euercli import VERSION; print(VERSION)')
git commit -am "chore(release): prepare v${release_version}"
```

### Schritt 2: Branch `main` zu GitHub pushen
```bash
git push origin main
```
> [!IMPORTANT]
> **Dieser Schritt muss VOR dem Tagging erfolgen!** Der Release-Commit muss sich auf `origin/main` befinden.

### Schritt 3: CI-Lauf auf `main` abwarten und verifizieren (Pre-Flight Gate)
```bash
# Warten bis die vollständige CI-Matrix auf main (Ubuntu, macOS, Windows) erfolgreich grün ist:
gh run list --branch main --limit 1 --workflow CI
gh run watch $(gh run list --branch main --limit 1 --workflow CI --json databaseId --jq '.[0].databaseId')
```
> [!IMPORTANT]
> Erst fortfahren, wenn alle Matrix-Jobs des CI-Workflows auf `main` den Status `success` haben!

### Schritt 4: Annotierten Tag erstellen
```bash
git tag -a "v${release_version}" -m "Release v${release_version}"
```

### Schritt 5: Tag zu GitHub pushen
```bash
git push origin "v${release_version}"
```

---

## 5. Workflow-Ablauf & Monitoring

Sobald der Tag `v*` gepusht wird, startet GitHub Actions automatisch den Workflow `.github/workflows/release.yml`:

```
┌─────────────────────────────────┐
│  validate (release_check.py)    │  Prüft Tag-Format, Version, origin/main, Release Notes
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│  test (Matrix-Lauf)             │  Ubuntu (3.11, 3.14), macOS (3.11), Windows (3.11)
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│  build                          │  Erstellt sdist (.tar.gz) und wheel (.whl)
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│  verify-artifacts               │  Raucht-Test in isolierten virtuellen Umgebungen
└──────┬──────────────────┬───────┘
       │                  │
┌──────▼───────┐   ┌──────▼───────┐
│ publish-pypi │   │ publish-     │  PyPI Trusted Publishing (OIDC) & GitHub Release
└──────────────┘   │ github       │
                   └──────────────┘
```

### Release-Status in der CLI überwachen
```bash
# Aktuelle Release-Läufe anzeigen
gh run list --workflow=Release --repo curiousmarkus/euer

# Live-Log verfolgen
gh run watch <RUN_ID> --repo curiousmarkus/euer
```

---

## 6. Recovery-Runbook (Was tun bei Fehlern?)

| Fehlerphase | Betroffener Job | Status bei PyPI | Vorgehen |
|---|---|---|---|
| **Vor dem Build** | `validate` oder `test` | Noch kein Upload erfolgt. | Ursache auf `main` beheben. Da der Tag geschützt ist, kann er nicht gelöscht werden: Version auf nächsten Patch erhöhen (`X.Y.Z+1`), `docs/RELEASE_NOTES.md` anpassen, neuen Tag pushen. |
| **Artefakt-Build** | `build` oder `verify-artifacts` | Noch kein Upload erfolgt. | Gleiches Vorgehen wie oben: Patch-Version erhöhen und neu veröffentlichen. |
| **GitHub-Draft** | `github-draft` | Noch kein Release publiziert. | Job im selben GitHub-Actions-Lauf erneut starten (`gh run rerun <RUN_ID> --job <JOB_ID>`). Ein existierender Draft wird überschrieben. |
| **PyPI-Upload** | `publish-pypi` | Fehlgeschlagen. | Prüfen, ob PyPI OIDC / Trusted Publishing konfiguriert ist (`pypi` Environment in GitHub Settings). Fehler beheben, Release-Lauf wiederholen. |
| **GitHub-Release nach PyPI** | `publish-github` | **PyPI-Paket ist bereits live!** | **Niemals dieselbe Version erneut nach PyPI pushen!** Ausschließlich den Job `publish-github` im selben Workflow wiederholen, um den GitHub-Release-Draft zu veröffentlichen. |
| **Homebrew-Tap** | Externe Tap-Action | PyPI und GitHub sind live. | Das Tap-Repository aktualisiert sich automatisch alle 6 Stunden. Bei Bedarf kann der Workflow `update-formula.yml` im Tap-Repo manuell ausgelöst werden. |

Nach dem Tap-Lauf die tatsächlich veröffentlichten Formula-Versionen und
Quellarchiv-SHA256 prüfen. Ein erfolgreicher Workflow allein bestätigt keine
neue Version: Der allgemeine PyPI-Endpunkt kann kurz nach dem Upload noch die
vorherige Version liefern, während der versionsbezogene Endpunkt bereits die
neuen Dateien ausliefert. In diesem Fall nach Aktualisierung der Metadaten den
Tap-Workflow erneut starten. Bei gemeinsamen Releases beide Formeln prüfen.
