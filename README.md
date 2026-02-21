![euer Logo](euer_logo.png)

# EÜR-Buchhaltung für KI-Agenten

> `euer` ist die Lösung für Freelancer und Kleinunternehmer in Deutschland, die ihre Einnahmenüberschussrechnung (EÜR) an ihre KI-Agenten auslagern möchten.

---

## Warum euer?

Die meisten Tools zwingen dich zu einer Entscheidung: Entweder du nutzt unflexible SaaS-Abos (Lexoffice, SevDesk) oder du bastelst manuell in Excel. `euer` geht einen dritten Weg: **Ein Tool, damit dein Agent die Arbeit übernehmen kann.**

### 🤖 Built for AI Agents, not humans
*   **CLI first:** Perfekt für LLMs – Text Input, strukturierter Text Output. Kein Halluzinieren von GUI-Klicks.
*   **Do one thing well:** Kein Feature-Bloat. Nur EÜR. Agenten lieben Tools mit klarem Scope.
*   **SQL Superpowers:** Für komplexe Abfragen kann der Agent direkt SQL nutzen. Volle Flexibilität für intelligente Automatisierung.

### 🔒 Revisionssicher & Lokal
*   **Local First:** Eine SQLite-Datei. Deine Daten. Dein Backup. Deine Kontrolle.
*   **Audit-Log:** Jede Änderung wird unveränderbar protokolliert. Sicherheit für dich und das Finanzamt.
*   **Leichtgewichtig:** Nur Python 3.11+. Keine schweren Abhängigkeiten. Läuft überall.
*   **Kein Lock-in:** Daten einfach in CSV oder Excel exportieren.

### ✅ Alles, was du steuerlich brauchst
- **EÜR-konforme Kategorien:** Direkt einsatzbereit mit den offiziellen Zeilennummern für die Anlage EÜR.
- **Umsatzsteuer-Logik:** Voller Support für Regelbesteuerung (USt/Vorsteuer) sowie Kleinunternehmerregelung (§19 UStG).
- **Reverse-Charge Support:** Umsatzsteuerliche Behandlung von Dienstleistern aus dem EU/Drittland-Ausland (§13b UStG).
- **Beleg-Management:** Verknüpfe digitale Belege (PDF/Bilder) direkt mit deinen Buchungen.

---

## Quickstart: In 30 Sekunden startklar

### 1. Installation

`pipx` installiert `euer` global, ohne dass du je eine virtuelle Umgebung aktivieren musst:

```bash
# pipx einmalig installieren (falls noch nicht vorhanden)
brew install pipx

# euer installieren
pipx install git+https://github.com/curiousmarkus/euer.git
```

Danach ist `euer` sofort und dauerhaft in jedem Terminal verfügbar.

**Update auf die neueste Version:**
```bash
pipx upgrade euercli
```

### 2. Personalisierung

Kopiere den onboarding-prompt (`docs/templates/onboarding-prompt.md`) in einen LLM-Chat und beantworte die Fragen. 
Du erhältst eine personalisierte `AGENTS.md` mit dem nötigen Kontext für deine KI-Agenten sowie die konkreten nächsten Schritte, um loszulegen.

### 3. Initialisierung
Wechsle (wie beim Onboarding erklärt) in deinen Buchhaltungs-Ordner und erstelle deine Datenbank:
```bash
euer init
euer setup
```

### 4. Erste Buchung (lass es deinen AI-Agent machen!)
```bash
euer add expense --payment-date 2026-02-02 --vendor "Hetzner" --category "Laufende EDV-Kosten" --amount -10.00
```

---

## So arbeitet dein AI-Agent mit euer

Du hast einen Stapel PDF Belege?
Gib es an deinen KI-Agenten:
> "Buche diese Belege in euer ein."

1. Der Agent holt sich die korrekten Steuerkategorien mit `euer list categories`
2. Fügt die Belege in die EÜR mit `euer add expense --payment-date ... --vendor ...`
3. kontrolliert die Vollständigkeit mit `euer incomplete list`
4. gibt dir eine Übersicht über deine EÜR mit `euer summary --year 2026`

**Ergebnis:** Du kannst dich zurücklehnen — dein Agent übernimmt für dich die Buchhaltung!

---

## Dokumentation & Support

Detaillierte Anleitungen findest du in unseren Guides:

- 📖 **[User Guide](docs/USER_GUIDE.md)** – Installation, Workflows und alle Befehle.
- 🤖 **[SKILL "euer-buchhaltung"](docs/skills/euer-buchhaltung/SKILL.md)** – Die Anleitung für deinen Agenten
- 🤖 **[Agent Templates](docs/templates/)** – Konfigurationsvorlagen für KI-Buchhalter
- 🛠️ **[Development](DEVELOPMENT.md)** – Architektur und Mitwirkung.

---

## 📄 Lizenz

GNU AGPLv3 License
Copyright (c) 2026 Markus

**Hinweis zur AGPL:**
Diese Software ist frei verfügbar. Wenn du sie jedoch modifizierst und über ein Netzwerk (z.B. als Web-Service oder SaaS) anbietest, bist du verpflichtet, den vollständigen Quellcode deiner Version ebenfalls unter der AGPL offenzulegen.
Dies stellt sicher, dass `euer` ein Gemeinschaftsprojekt bleibt und nicht proprietär vereinnahmt wird.

---

*Entwickelt für AI-Agents, die sich täglich freuen deine Buchhaltung zu übernehmen – CLI basiert, lokal und einfach.*
