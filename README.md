# euer
## EÜR-Buchhaltung für KI-Agenten

> `euer` ist die Lösung für Freelancer und Kleinunternehmer in Deutschland, die ihre Einnahmenüberschussrechnung (EÜR) an ihre KI-Agenten auslagern möchten.

Ein CLI-Tool, das speziell für die Nutzung durch KI-Agenten entwickelt wurde und diesen standardisierte und verlässliche Strukturen bietet, um Buchhaltungsaufgaben effizient und fehlerfrei zu erledigen.

---

## Warum euer?

Jeder Freelancer und Kleinunternehmer in Deutschland kennt es: Alle Ausgaben und Einnahmen müssen sorgfältig für das Finanzamt in einer Einnahmenüberschussrechnung (EÜR) erfasst werden. Zusätzlich muss teilweise auch noch eine Umsatzsteuervoranmeldung (UStVA) ausgefüllt werden. Bisher muss man entweder alles manuell in einer teuren Software erfassen oder aufwändig eine Excel Datei pflegen.

### 🤖 Built for AI Agents
Herkömmliche Buchhaltungs-Tools sind für Menschen gemacht. `euer` ist für **Agents** optimiert:
*   **CLI statt GUI:** Einfach für LLMs zu verstehen und zu bedienen.
*   **Simpel:** Leicht zu verstehen und mit klaren Anweisungen. Ein Tool für genau diesen Zweck.
*   **Flexibel:** Agents können die CLI-Befehle mit direktem Queries auf die SQLite-Datenbank kombinieren, um komplexe Fragen zu beantworten.

### 🔒 Revisionssicher & Lokal
Deine Finanzdaten bei dir und nicht irgendwo in der Cloud.
*   **SQLite-Backend:** Eine einzige Datei. Einfach zu sichern, einfach zu versionieren.
*   **Audit-Log:** Jede Änderung (Insert, Update, Delete) wird unveränderbar protokolliert. Erfüllt die Anforderungen an eine nachvollziehbare Buchführung.
*   **Zero Dependencies:** Der Core läuft überall, braucht nur Python 3.11+.
*   **Einfach migrierbar:** Die Daten können jederzeit in andere Systeme exportiert werden. Kein Vendor Lock-in.

### Alles, was du für deine EÜR brauchst

- **EÜR-konforme Kategorien:** Direkt einsatzbereit mit den offiziellen Zeilennummern für deine Steuererklärung.
- **Reverse-Charge Support:** Automatische Logik für ausländische Dienstleister bei denen du die Umsatzsteuer schuldig bist.
- **Beleg-Management:** Verknüpfe digitale Belege direkt mit deinen Buchungen.
- **Umsatzsteuer-Modi:** Unterstützt sowohl die Kleinunternehmerregelung (§19 UStG) als auch die Regelbesteuerung in der USt.

---

## Quickstart: In 30 Sekunden startklar

### 1. Installation
```bash
git clone https://github.com/curiousmarkus/euer.git
cd euer
python -m pip install -e .
```

### 2. Initialisierung
Wechsle in deinen Buchhaltungs-Ordner und erstelle deine Datenbank:
```bash
euer init
euer setup
```

### 3. Erste Buchung (lass es deinen AI-Agent machen!)
```bash
euer add expense --date 2026-02-02 --vendor "Hetzner" --category "Laufende EDV-Kosten" --amount -10.00
```

---

## So arbeitet dein AI-Agent mit euer

Du hast einen Stapel PDF Belege?
Gib es an deinen KI-Agenten:
> "Buche diese Belege in euer ein."

Der Agent:
1. holt sich die korrekten Steuerkategorien mit `euer list categories`
2. Fügt die Belege in die EÜR mit `euer add expense --date ... --vendor ...`
3. kontrolliert die Vollständigkeit mit `euer incomplete list`
4. gibt dir eine Übersicht über deine EÜR mit `euer summary --year 2026`

**Ergebnis:** Du kannst dich zurücklehnen — dein Agent übernimmt für dich die Buchhaltung!

---

## Dokumentation & Support

Detaillierte Anleitungen findest du in unseren Guides:

- 📖 **[User Guide](USER_GUIDE.md)** – Installation, Workflows und alle Befehle.
- 🤖 **[SKILL "euer-buchhaltung"](skills/euer-buchhaltung/SKILL.md)** – Die Anleitung für deinen Agenten
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
