# AGENTS.md - Coding Agent Guidelines

## Zweck des Projekts

`euer` ermöglicht es deutschen Freelancern und Kleinunternehmern, ihre
Einnahmenüberschussrechnung (EÜR) vollständig an KI-Agenten zu delegieren.
Das Tool ist **CLI-first** und für LLM-gesteuerte Workflows optimiert:
Text rein, strukturierter Text raus. Die Buchhaltungsdaten liegen lokal in
einer einzigen SQLite-Datei — revisionssicher mit Audit-Log, ohne Cloud-Abhängigkeit.

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
| `docs/skills/euer-buchhaltung/SKILL.md` | Buchungsregeln für AI-Agenten |
| `docs/templates/` | Agent-Konfigurationsvorlagen |

---

## Pflichten nach Implementierung

**Spec-Status:** Jede Spec in `specs/` hat ein `## Status`-Feld (`Offen` / `Implementiert`).
Bei Änderungen auch die Tabelle in `DEVELOPMENT.md` aktualisieren.

**Doku-Update:** Betroffene Dokumente prüfen und aktualisieren:
`docs/USER_GUIDE.md`, `docs/skills/euer-buchhaltung/SKILL.md`,
`docs/templates/onboarding-prompt.md`, `README.md`, `DEVELOPMENT.md`
