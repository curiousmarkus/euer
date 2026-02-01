# EÜR – Open-Source Buchhaltung (CLI)

SQLite-basierte Einnahmenüberschussrechnung (EÜR) für deutsche Freelancer und Kleinunternehmer.
Das Tool ist schlank, auditierbar und AI‑Agent‑freundlich – ideal für wiederholbare Workflows.

## Features

- **EÜR‑konforme Kategorien** inkl. Zeilennummern
- **Audit‑Log** für jede Änderung (INSERT/UPDATE/DELETE)
- **Beleg‑Verwaltung** mit Pfad‑Konfiguration und Checks
- **Import/Export** (CSV, optional XLSX via `openpyxl`)
- **Reverse‑Charge** Logik für ausländische Anbieter
- **Ohne Abhängigkeiten** (Python 3.11+, `openpyxl` optional)

## Quickstart

```bash
# 1) Repo klonen
git clone <repo-url>
cd euer

# 2) Installieren (lokal, im Repo)
python -m pip install -e .

# 3) Datenbank anlegen
euer init

# 4) Optional: Beleg- und Export-Pfade konfigurieren
euer setup

# 5) Erste Ausgabe erfassen
euer add expense --date 2026-01-15 --vendor "Test" --category "Arbeitsmittel" --amount -10.00
```

Falls die CLI nicht installiert ist:

```bash
python -m euercli <command>
```

## Dokumentation

- `USER_GUIDE.md` – Nutzung, Workflows, Beispiele
- `DEVELOPMENT.md` – Architektur, Datenmodell, Contribution‑Hinweise
- `TESTING.md` – Teststrategie und Ausführung
- `AGENTS.md` – Richtlinien für Coding Agents
- `skills/euer-buchhaltung/SKILL.md` – Skill für AI‑Agents
- `specs/` – Historische Anforderungen + zukünftige Backlog‑Items

## Lizenz

MIT (siehe `LICENSE`).
