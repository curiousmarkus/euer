# AGENTS.md - Coding Agent Guidelines

## Zweck des Projekts

`euer` ermöglicht es deutschen Freelancern und Kleinunternehmern, ihre
Einnahmenüberschussrechnung (EÜR) vollständig an KI-Agenten zu delegieren.
Das Tool ist **CLI-first** und für LLM-gesteuerte Workflows optimiert:
Belege und Kontoauszüge an KI-Agenten übergeben, dieser liest die Daten aus und bucht sie über die CLI. Die Buchhaltungsdaten liegen lokal in
einer einzigen SQLite-Datei — nachvollziehbar mit Audit-Log, ohne Cloud-Abhängigkeit.

Kernfeatures: EÜR-konforme Kategorien (Anlage EÜR Zeilennummern),
Umsatzsteuer-Logik (Regel-/Kleinunternehmer/Reverse-Charge),
Beleg-Management, CSV/Excel-Export.

---

## Vor jeder Code-Änderung

> **PFLICHTLEKTÜRE:** `DEVELOPMENT.md` — Architektur, Service-Layer-Regeln, Checkliste.
> Prüfe auch `specs/` auf offene Change Requests, die dein Feature betreffen.

**Wichtigste Regel:** Alle Schreiboperationen (INSERT/UPDATE/DELETE) auf
`expenses`, `income`, `private_transfers` MÜSSEN über `euercli/services/` laufen.
Commands sind reine View-Controller — keine Business-Logik, kein direktes SQL-Schreiben.

## Tests & Linting

```bash
python -m unittest discover -s tests    # Tests
ruff check euercli && ruff format euercli  # Linting (optional)
```

---

## Code Style

- **Python 3.11+**, moderne Type Hints (`list[str]`, `X | None`)
- **Imports:** Stdlib → Third-party → Local (jeweils alphabetisch, Leerzeile dazwischen)
- **Formatierung:** ~100 Zeichen, 4 Spaces, Double Quotes, Trailing Commas
- **Naming:** `snake_case` (Funktionen/Variablen), `UPPER_SNAKE` (Konstanten), `cmd_<name>` (CLI-Commands)
- **Fehler:** `sys.stderr` + `sys.exit(1)` bei fatalen Fehlern; Warnungen ohne Exit
- **DB:** Immer `get_db_connection()`, `conn.row_factory = sqlite3.Row`, parametrisierte Queries
- **Audit:** Jedes INSERT/UPDATE/DELETE → `log_audit(conn, table, id, action, ...)`
- **Ausgabe:** Deutsch, `format_amount()` für EUR, Fixed-Width-Tabellen

---

## Neues Feature hinzufügen

1. Service-Funktion in `euercli/services/` (Dataclass-Return, Exceptions)
2. `cmd_<name>(args)` in `euercli/commands/` (View-Controller)
3. Parser in `main()` registrieren → `parser.set_defaults(func=cmd_<name>)`

Details und Beispiele: `DEVELOPMENT.md` → „Neue Commands hinzufügen"

---

## Referenzen

| Dokument | Inhalt |
|----------|--------|
| `DEVELOPMENT.md` | Architektur, Service-Layer-Regeln, Checkliste **(Pflichtlektüre)** |
| `specs/` | Offene Change Requests und Backlog |
| `euercli/schema.py` | DB-Schema |
| `docs/USER_GUIDE.md` | Nutzer-Dokumentation |
| `docs/RELEASE_NOTES.md` | Upgrade-Hinweise für bestehende lokale Instanzen |
| `docs/skills/euer-buchhaltung/SKILL.md` | Buchungsregeln für AI-Agenten |
| `docs/templates/` | Agent-Konfigurationsvorlagen |

---

## Pflichten nach Implementierung

**Spec-Status:** Jede Spec in `specs/` hat ein `## Status`-Feld (`Offen` / `Implementiert`).
Bei Änderungen auch die Tabelle in `DEVELOPMENT.md` aktualisieren.

**Doku-Update:** Betroffene Dokumente prüfen und aktualisieren:
`docs/USER_GUIDE.md`, `docs/skills/euer-buchhaltung/SKILL.md`,
`docs/templates/onboarding-prompt.md`, `docs/RELEASE_NOTES.md`, `README.md`,
`DEVELOPMENT.md`

**Versionierung, Release Notes & Veröffentlichung:** Vor Abschluss jeder Änderung
prüfen, ob sie einen Release erfordert. `euercli.VERSION` in
`euercli/__init__.py` ist die einzige Versionsquelle; die Paketmetadaten übernehmen
die Version dynamisch daraus. Bereits veröffentlichte Versionsabschnitte in
`docs/RELEASE_NOTES.md` dürfen nicht um spätere Änderungen ergänzt werden. Änderungen
nach einem Release gehören unter `Unveröffentlicht` oder — bei unmittelbar geplanter
Veröffentlichung — unter die nächste Versionsnummer.

- Nutzerwirksame Bugfixes → PATCH
- Abwärtskompatible Features und Commands → MINOR
- Breaking Changes an Schema oder CLI-API → MAJOR
- Reine CI-, Test-, Refactoring- oder Entwicklerdoku-Änderungen erzwingen keinen
  eigenen Release

Wenn sich Schema, CLI-Verhalten, Import-/Exportformate, Steuerlogik, Agenten-Skill,
Agenten-Template oder Onboarding/`AGENTS.md` ändern, `docs/RELEASE_NOTES.md` mit
konkreten Upgrade- und Migrationsschritten aktualisieren. Vor einem Release muss die
kanonische Version aus `euercli/__init__.py` in den gebauten Metadaten erscheinen.

Vor einer Veröffentlichung müssen Tests, Linting, Build und der
Artefakt-Smoke-Test grün sein. Veröffentlicht wird ausschließlich durch einen
annotierten, geschützten Tag `vMAJOR.MINOR.PATCH` auf `main`. Dieser Tag startet die
Multi-Channel-Pipeline: Sie validiert Tag, Version, `main`-Ancestry und Release Notes,
baut Wheel und sdist genau einmal, prüft dieselben Artefakte und veröffentlicht sie
über PyPI sowie als GitHub-Release. Die Homebrew-Formel wird anschließend aus der
veröffentlichten PyPI-Version durch den geplanten oder manuellen Lauf des separaten
Homebrew-Taps aktualisiert. Bei Fehlern gelten die Wiederholungs- und Recovery-Regeln
aus `DEVELOPMENT.md`.

Details: `DEVELOPMENT.md` → „Versionierung“.
