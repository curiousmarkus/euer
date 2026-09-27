![euer Logo](https://raw.githubusercontent.com/curiousmarkus/euer/main/euer_logo.png)

# EÜR-Buchhaltung für KI-Agenten

> `euer` ist die Lösung für Freelancer und Einzelunternehmer in Deutschland, die ihre Einnahmenüberschussrechnung (EÜR) an ihre KI-Agenten auslagern möchten.

---

## Warum euer?

Wenn du eine EÜR erstellen musst, stehst du vor der Entscheidung: ein Software-Abo bei einer großen Buchhaltugnssoftware (Lexoffice, SevDesk) abschließen oder irgendwas in Excel zu basteln. `euer` geht einen dritten Weg: **Ein CLI-Tool, das deinen KI-Agent befähigt, die Buchführung zu übernehmen.**

### 🤖 Built for AI Agents (Claude Code, Hermes, OpenCode, Codex, etc.)
*   **Agent-First:** KI-Agenten sind die eigentlichen Nutzer der Software. Sie übernehmen die Buchführung; dank euer autonom und so gut wie fehlerfrei.
*   **Basierend auf CLI Commands:** Perfekt für Tool-Calling lokaler Agenten (`euer add expense`, `euer summary`). Klare Anweisungen sowie strikte Validierungen und Sicherheitsprüfungen verhindern Fehlbuchungen.
*   **Mit SQL Superpowers:** Für komplexe Auswertungen kann der Agent direkt auf die lokale SQLite-Datenbank zugreifen.

### 🔒 Lokal und Open Source
* **Deine Daten bleiben bei dir:** Alle Buchungen liegen in einer lokalen SQLite-Datenbank bei dir auf deinem Rechner.
* **Offener Quellcode:** `euer` ist Open Source (AGPLv3) und damit transparent und auditierbar. 
* **Jederzeit zugänglich:** Du kannst deine Daten direkt auswerten und jederzeit als CSV oder Excel exportieren.

### ✅ Passend für die EÜR und UStVA
* **Passend für Freiberufler und Einzelunternehmer:** Buchführung nach dem Zufluss-/Abfluss-Prinzip (§ 11 EStG) inkl. Bericht für die UStVA, ohne unnötige doppelte Buchführung oder festem Kontenrahmen.
* **Steuerlichen Regeln eingebaut:** EÜR-Kategorien, Kleinunternehmerregelung (§19 UStG), Umsatzsteuer und Reverse Charge (§13b UStG) werden direkt unterstützt.
* **Geordnet und nachvollziehbar:** Zugeordnete Belege zu jeder Buchung und ein  Audit-Trail, der jede Änderung durch den Agenten mitschreibt.

---

## Quickstart: In 2 Minuten startklar

### 1. Installation

**macOS und Linux (Homebrew):**

```bash
brew install curiousmarkus/euer/euer
```

**Alle Plattformen (PyPI):**

```bash
# pipx einmalig installieren (falls noch nicht vorhanden)
python3 -m pip install --user pipx
pipx ensurepath

pipx install euer
```

Für den optionalen Excel-Export installierst du direkt das XLSX-Extra:

```powershell
pipx install "euer[xlsx]"
```

Unter Windows kannst du stattdessen `py -m pip install --user pipx` und danach
`pipx ensurepath` verwenden. Die Paketinstallation bleibt identisch.

**GitHub-Fallback:**

Für Entwicklungsversionen oder einen Checkout ohne PyPI kannst du auch direkt aus
dem Repository installieren:

```bash
pipx install git+https://github.com/curiousmarkus/euer.git
```

Danach ist `euer` sofort und dauerhaft in jedem Terminal verfügbar.

**Update auf die neueste Version:**
```bash
pipx upgrade euer
```

Bei einer Homebrew-Installation aktualisierst du mit:

```bash
brew upgrade euer
```

Der Homebrew-Tap übernimmt PyPI-Releases zeitversetzt (geplant spätestens
innerhalb von sechs Stunden). Prüfe mit `brew info euer` und `euer --version`,
welche Version verfügbar ist und welche dein Terminal startet. Für den Wechsel
von einer alten `pipx`-/`euercli`-Installation zu Homebrew siehe den
[Upgrade-Leitfaden](docs/skills/euer-buchhaltung/references/installation_and_setup.md#von-pipx-zu-homebrew-wechseln).

**Entwicklungsinstallation unter Windows (PowerShell):**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,xlsx]"
python -m unittest discover -s tests
```

(Details siehe [Installationsreferenz](docs/skills/euer-buchhaltung/references/installation_and_setup.md#installation))

### 2. Personalisierung

Richte den vollständigen [Skill-Ordner `euer-buchhaltung`](docs/skills/euer-buchhaltung)
**inklusive `references/`** in deiner KI-Anwendung ein. Starte deinen Agenten im
Buchhaltungsordner und sage: **„Richte meine Buchhaltung mit euer ein.“**
Der Agent prüft vorhandene Angaben, führt bei Bedarf das Onboarding durch und
legt dein persönliches Mandanten-Dossier (`AGENTS.md`) sowie die Konfiguration an.
Da moderne KI-Agenten die `AGENTS.md` im Arbeitsverzeichnis automatisch einlesen,
dient sie als Mandanten-Dossier für deine betrieblichen Regeln (ohne Coding-Anweisungen).

Alternativ kannst du den [Onboarding-Prompt](docs/templates/onboarding-prompt.md)
in einem separaten LLM-Chat verwenden.
Der Skill enthält die Buchhalter-Grundregeln und kann auch von einem
allgemeinen Claude-Code- oder Hermes-Agenten genutzt werden. Die
[Buchhalter-Rolle](docs/templates/accountant-role.md) ist nur eine optionale
Vorlage für eigens konfigurierte Agenten. Bei Updates zeigen die
[Release Notes](docs/RELEASE_NOTES.md) getrennt an, ob Skill, Rolle oder
persönliches Mandanten-Dossier geprüft werden müssen. Agentendateien und
`AGENTS.md` werden durch `brew upgrade` oder `pipx upgrade` nicht ersetzt.
Prüfe nach dem Update `euer doctor`, ersetze den Skill vollständig aus
`skill.bundle_path`, lies ihn neu und bestätige dann seine Version mit
`euer setup --set skill.version "1.1.0"`.

### 3. Initialisierung
Falls noch nicht durch den Agenten erledigt: Wechsle in deinen Buchhaltungsordner
und initialisiere Datenbank und Konfiguration:
```bash
euer init --create
euer setup
```

### 4. Erste Buchung (lass es deinen AI-Agent machen!)
```bash
euer add expense --payment-date 2026-02-02 --vendor "Hetzner" --category "Laufende EDV-Kosten" --amount -10.00

# Optional mit Kontenrahmen:
euer add expense --payment-date 2026-02-02 --vendor "Hetzner" --ledger-account hosting --amount -10.00
```

---

## So arbeitet dein AI-Agent mit euer

Du hast einen Stapel PDF Belege?
Gib es an deinen KI-Agenten:
> "Buche diese Belege in euer ein."

1. Der Agent holt sich die korrekten Steuerkategorien mit `euer list categories`
2. Prüft optional den Kontenrahmen mit `euer list ledger-accounts`
3. Fügt die Belege in die EÜR mit `euer add expense --payment-date ... --vendor ...`
4. kontrolliert die Vollständigkeit mit `euer incomplete list`
5. gibt dir eine Übersicht über deine EÜR mit `euer summary --year 2026`
6. erstellt bei Bedarf einen UStVA-Arbeitsbericht mit `euer vat-report --year 2026`

**Ergebnis:** Du kannst dich zurücklehnen — dein Agent übernimmt für dich die Buchhaltung!

---

## Dokumentation & Support

Detaillierte Anleitungen findest du in unseren Guides:

- 🧭 **[User Journey](docs/USER_JOURNEY.md)** – Von Installation und Onboarding über den Monatsabgleich bis zur EÜR, mit Ablaufdiagramm.
- 🧩 **[Konzept und Grenzen](docs/CONCEPTS.md)** – Was euer und der Agent übernehmen.
- 📖 **[CLI-Referenz](docs/skills/euer-buchhaltung/references/cli_reference.md)** – Befehle, Optionen und Workflows.
- ❓ **[Fachregeln und Sonderfälle](docs/skills/euer-buchhaltung/references/domain_rules.md)** – Buchungsregeln und Beispiele.
- 🧾 **[Release Notes](https://github.com/curiousmarkus/euer/blob/main/docs/RELEASE_NOTES.md)** – Upgrade-Hinweise für bestehende lokale Instanzen.
- 🤖 **[SKILL "euer-buchhaltung"](https://github.com/curiousmarkus/euer/blob/main/docs/skills/euer-buchhaltung/SKILL.md)** – Die Anleitung für deinen Agenten
- 🤖 **[Agent Templates](https://github.com/curiousmarkus/euer/tree/main/docs/templates)** – Konfigurationsvorlagen für KI-Buchhalter
- 🤝 **[Mitwirken](https://github.com/curiousmarkus/euer/blob/main/CONTRIBUTING.md)** – Hinweise für Issues, Änderungen und Pull Requests.
- 🛠️ **[Development](https://github.com/curiousmarkus/euer/blob/main/DEVELOPMENT.md)** – Architektur und technische Entwicklungsregeln.

---

## 📄 Lizenz

GNU AGPLv3 License
Copyright (c) 2026 Markus

**Hinweis zur AGPL:**
Diese Software ist frei verfügbar. Wenn du sie jedoch modifizierst und über ein Netzwerk (z.B. als Web-Service oder SaaS) anbietest, bist du verpflichtet, den vollständigen Quellcode deiner Version ebenfalls unter der AGPL offenzulegen.
Dies stellt sicher, dass `euer` ein Gemeinschaftsprojekt bleibt und nicht proprietär vereinnahmt wird.

---

*Entwickelt für AI-Agents, die sich täglich freuen deine Buchhaltung zu übernehmen – CLI basiert, lokal und einfach.*
