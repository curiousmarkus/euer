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

### Installation (einmalig im Projektordner)

```bash
# 1) Repo klonen
git clone https://github.com/curiousmarkus/euer.git
cd euer

# 2) Installieren (macht 'euer' systemweit verfügbar)
python -m pip install -e .
```

**Wichtig:** Die Installation erfolgt einmalig im Projektordner und macht das `euer`-Kommando 
systemweit verfügbar. Deine Buchhaltungsdaten liegen dann in einem **separaten Arbeitsordner**.

### Nutzung (in deinem Buchhaltungsordner)

```bash
# In deinen Buchhaltungsordner wechseln (nicht das Repo!)
mkdir -p ~/Documents/Buchhaltung_2026
cd ~/Documents/Buchhaltung_2026

# 3) Datenbank anlegen (hier in deinem Buchhaltungsordner)
euer init

# 4) Beleg- und Export-Pfade konfigurieren
euer setup

# 5) Erste Ausgabe erfassen
euer add expense --date 2026-01-15 --vendor "Test" --category "Arbeitsmittel" --amount -10.00
```

**Ohne Installation:**

```bash
cd /pfad/zum/euer-repo
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
