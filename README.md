![euer Logo](https://raw.githubusercontent.com/curiousmarkus/euer/main/euer_logo.png)

# EÜR-Buchhaltung für KI-Agenten

> `euer` ist die Lösung für Freelancer und Einzelunternehmer in Deutschland, die ihre Einnahmenüberschussrechnung (EÜR) an ihre KI-Agenten auslagern möchten.

---

## Warum euer?

Wenn du eine EÜR erstellen musst, stehst du vor der Entscheidung: ein Software-Abo bei einer großen Buchhaltungssoftware (Lexoffice, SevDesk) abschließen oder irgendwas in Excel zu basteln. `euer` geht einen dritten Weg: **Ein CLI-Tool, das deinen KI-Agent befähigt, die Buchführung zu übernehmen.**

### 🤖 Built for AI Agents (Claude Code, Hermes, OpenCode, Codex, etc.)
*   **Agent-First:** Software für die Bedienung durch KI-Agenten. Damit sie dir die manuelle Erfassung deiner Ein- und Ausgaben abnehmen können.
*   **Basierend auf CLI Commands:** Befehle wie `euer add expense` und `euer summary` lassen sich von lokalen Agenten aufrufen. Validierungen und Sicherheitsprüfungen erkennen bestimmte fehlerhafte oder doppelte Eingaben.
*   **Mit SQL Superpowers:** Für zusätzliche Auswertungen kann der Agent SQL-Abfragen durchführen; Änderungen laufen über die CLI.

### 🔒 Lokal und Open Source
* **Lokale Buchungsdaten:** `euer` speichert Buchungen in einer lokalen SQLite-Datenbank direkt bei dir auf dem Rechner.
* **Offener Quellcode:** `euer` ist Open Source (AGPLv3) und damit transparent und auditierbar. 
* **Jederzeit zugänglich:** Du kannst deine Daten direkt auswerten und jederzeit als CSV oder Excel exportieren.

### ✅ Passend für die EÜR und UStVA
* **Passend für Freiberufler und Einzelunternehmer:** Buchführung nach dem Zufluss-/Abfluss-Prinzip (§ 11 EStG) inkl. Bericht für die UStVA, ohne unnötige doppelte Buchführung oder festen Kontenrahmen.
* **Steuerfälle unterstützt:** EÜR-Kategorien, Kleinunternehmerregelung (§ 19 UStG), Umsatzsteuer und Reverse Charge (§ 13b UStG) sind abgebildet.
* **Geordnet und nachvollziehbar:** Belege lassen sich Buchungen zuordnen; Änderungen über die CLI werden im Audit-Log festgehalten.

---

## Quickstart

### 1. Installation

**macOS und Linux mit Homebrew:**

```bash
brew install curiousmarkus/euer/euer
```

**Alle Plattformen mit pipx:**

```bash
pipx install euer
```

Für den Excel-Export installierst du hier zusätzlich das XLSX-Addon:

```bash
pipx install "euer[xlsx]"
```

Prüfe die Installation mit `euer --version`. Die [Installationsreferenz](docs/skills/euer-buchhaltung/references/installation_and_setup.md#installation)
erklärt Updates, Entwicklungsversionen und den Wechsel zwischen pipx und Homebrew.
Die [Entwicklungsinstallation unter Windows](DEVELOPMENT.md#windows-powershell) ist im Developer Guide beschrieben.

### 2. KI-Agenten einrichten

Installiere den vollständigen [Skill-Ordner `euer-buchhaltung`](docs/skills/euer-buchhaltung)
inklusive `references/` in deiner KI-Anwendung.

Starte deinen Agenten im Buchhaltungsordner und sage:
**„Richte meine Buchhaltung mit euer ein.“**
Der Agent fragt die nötigen Angaben ab und legt deine Konfiguration sowie
dein Mandanten-Dossier (als `AGENTS.md`) an.

### 3. Erste Belege buchen lassen

Gib deinem Agenten deine Belege und sage zum Beispiel:

> „Buche diese Belege mit euer“

Der Agent nutzt dafür die CLI:

1. Er liest die gültigen Kategorien mit `euer list categories` und bei Bedarf deine
   Buchungskonten mit `euer list ledger-accounts`.
2. Er bucht Ausgaben mit `euer add expense` und Einnahmen mit `euer add income`;
   den jeweiligen Beleg verknüpft er über `--receipt`.
3. Mit `euer incomplete list` prüft er, welche Angaben noch fehlen, und fragt bei
   Unklarheiten nach.
   `euer receipt unbooked --year 2026 --format json` findet Belegdateien ohne
   Buchungszuordnung; vor einer Neubuchung prüft er bestehende Vorgänge.
4. Mit `euer summary --year 2026` zeigt er dir die Jahresübersicht. Bei Bedarf
   erstellt `euer vat-report --year 2026` einen UStVA-Arbeitsbericht.

### Vor der steuerlichen Abgabe

`euer` unterstützt die laufende Buchhaltung und erstellt Arbeitsberichte. Die
CLI-Prüfungen erkennen nicht jeden fachlichen Fehler; auch ein KI-Agent kann
Belege oder steuerliche Sachverhalte falsch einordnen. Der Agent soll fehlende
Angaben und ungeklärte Fälle sichtbar machen. Prüfe Berichte, Belege und offene
Punkte vor der Übernahme in ELSTER und hole bei steuerlich unklaren Fällen
fachlichen Rat ein. `euer` übermittelt keine Steuererklärung.

---

## Dokumentation & Hilfe

- [User Journey](docs/USER_JOURNEY.md): Der gesamte Ablauf von der Einrichtung bis zum Jahresabschluss.
- [CLI-Referenz](docs/skills/euer-buchhaltung/references/cli_reference.md): Alle Befehle und Optionen für deinen Agenten.
- [Fachregeln und Sonderfälle](docs/skills/euer-buchhaltung/references/domain_rules.md): Buchungsregeln mit Beispielen.
- [Konzept und Grenzen](docs/CONCEPTS.md): Was euer und der Agent übernehmen.
- [Release Notes](docs/RELEASE_NOTES.md): Änderungen und Hinweise für bestehende Installationen.

Fragen oder einen Fehler gefunden? [Erstelle ein GitHub-Issue](https://github.com/curiousmarkus/euer/issues).
Wenn du mitarbeiten möchtest, lies [Mitwirken](CONTRIBUTING.md) und den
[Developer Guide](DEVELOPMENT.md).

---

## 📄 Lizenz

GNU AGPLv3 License
Copyright (c) 2026 Markus

**Hinweis zur AGPL:**
Diese Software ist frei verfügbar. Wenn du sie jedoch modifizierst und über ein Netzwerk (z.B. als Web-Service oder SaaS) anbietest, bist du verpflichtet, den vollständigen Quellcode deiner Version ebenfalls unter der AGPL offenzulegen.
Dies stellt sicher, dass `euer` ein Gemeinschaftsprojekt bleibt und nicht proprietär vereinnahmt wird.

---

*Entwickelt für AI-Agents, die sich täglich freuen deine Buchhaltung zu übernehmen – CLI basiert, lokal und einfach.*
