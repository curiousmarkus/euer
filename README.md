# euer: Die CLI-Buchhaltung für das KI-Zeitalter 🚀

**Schluss mit komplizierten Tabellen und teuren Abos.**  
euer ist die schlanke und AI-native Lösung für deutsche Freelancer und Kleinunternehmer zur Pflege der Einnahmenüberschussrechnung (EÜR). So kannst du deine Buchhaltung an deine AI Agents outsourcen. Und das vollständig lokal.

---

## Warum euer?

Jeder Freelancer und Kleinunternehmer in Deutschland kennt es: Alle Ausgaben und Einnahmen müssen sorgfältig für das Finanzamt in einer Einnahmenüberschussrechnung (EÜR) erfasst werden. Zusätzlich muss teilweise auch noch eine Umsatzsteuervoranmeldung (UStVA) ausgefüllt werden. Bisher muss man entweder alles manuell in einer teuren Software erfassen oder aufwändig eine Excel Datei pflegen.

### 🤖 Built for AI Agents
Mit euer, kann ich meine Buchhaltung nun ganz einfach an meinen lokalen AI-Agenten (wie OpenCode oder ClaudeCowork) auslagern. Das CLI-Tool macht es dem Agenten leicht Ausgaben und Einnahmen aus ausgelesenen Belegen und Kontoauszügen zu erfassen. 

### 🔒 Local-First & Privat
Deine Finanzdaten bleiben dabei komplett lokal in einer SQLite-Datenbank auf deinem Rechner. Das bedeutet: Volle Performance, maximale Privatsphäre und kein Vendor Lock-in.

### ⚖️ Revisionssicher & Konform
Das integrierte **Audit-Log** protokolliert jede Änderung (INSERT/UPDATE/DELETE). So bleibst du transparent und erfüllst die Anforderungen an eine nachvollziehbare Buchführung.

---

## Die Highlights auf einen Blick

- **EÜR-konforme Kategorien:** Direkt einsatzbereit mit den offiziellen Zeilennummern für deine Steuererklärung.
- **Reverse-Charge Support:** Automatische Logik für ausländische Dienstleister bei denen du die Umsatzsteuer schuldig bist.
- **Beleg-Management:** Verknüpfe digitale Belege direkt mit deinen Buchungen.
- **Umsatzsteuer-Modi:** Unterstützt sowohl die Kleinunternehmerregelung (§19 UStG) als auch die Regelbesteuerung in der USt.
- **Zero Dependencies:** Läuft mit Python 3.11+ Standard-Bibliotheken (optional `openpyxl` für Excel-Exports).

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

### 3. Erste Buchung (oder lass es deinen AI-Agent machen!)
```bash
euer add expense --date 2026-02-02 --vendor "Test" --category "Laufende EDV-Kosten" --amount -10.00
```

---

## So arbeitet dein AI-Agent mit euer

Stell dir vor, du gibst deinem Agenten einen Stapel PDFs und sagst: *"Buche diese Belege in euer ein."*

Der Agent nutzt Befehle wie:
- `euer list categories` – Um die richtige Steuerkategorie zu finden.
- `euer add expense --date ... --vendor ...` – Um die Daten präzise zu erfassen.
- `euer incomplete list` – Um fehlende Informationen (wie Kategorien oder Belege) zu identifizieren.

**Ergebnis:** Dein Agent übernimmt die nervige Buchhaltung und du kannst dich zurücklehnen! 

---

## Dokumentation & Support

Detaillierte Anleitungen findest du in unseren Guides:

- 📖 **[User Guide](USER_GUIDE.md)** – Installation, Workflows und alle Befehle.
- 🤖 **[SKILL "euer-buchhaltung"](euer-buchhaltung/SKILL.md)** – Die Anleitung für deinen Agent
- 🛠️ **[Development](DEVELOPMENT.md)** – Architektur und Mitwirkung.

---

## Lizenz

Dieses Projekt steht unter der **MIT-Lizenz**. Siehe [LICENSE](LICENSE) für Details.

---

*Entwickelt für AI-Agents, die gerne bei der Buchhaltung unterstützen – CLI basiert, lokal und einfach.*
