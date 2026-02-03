# EÜR CLI: AI-Ready Accounting Engine

> **Local-First, Revisionssicher, Agent-Native.**
> Die modulare Einnahmenüberschussrechnung (EÜR) für deutsche Freelancer, Entwickler und deren KI-Assistenten.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Status: Beta](https://img.shields.io/badge/Status-Open%20Core-green)

`euer` ist mehr als nur ein CLI-Tool. Es ist eine **Accounting Engine**, entwickelt für das Zeitalter der KI-Agenten. Keine unzuverlässigen Text-Parsings mehr – `euer` bietet eine saubere Service-Layer-Architektur, deterministische Outputs und volle Erweiterbarkeit.

## ⚡ Warum EÜR CLI?

### 🤖 Built for AI Agents
Herkömmliche CLIs sind für Menschen gemacht. `euer` ist für **Agents** optimiert:
*   **Service Layer Pattern:** Logik ist strikt von der Ausgabe getrennt.
*   **Structured Data:** Typisierte Dataclasses und klare Exceptions statt Text-Salat.
*   **Context-Aware:** Agents können via SQL direkt auf die DB zugreifen, um komplexe Fragen ("Wie hoch war mein Gewinn in Q3?") zu beantworten.

### 🏗️ Open Core Architektur
Wir glauben an Modularität. Der Kern ist schlank und robust:
*   **Plugin-System:** Erweitere das Tool einfach via `pip install euer-plugin-name` (z.B. für ELSTER, Bank-Importe).
*   **Zero Dependencies:** Der Core läuft überall, braucht nur Python 3.11+.
*   **UUID-based:** Bereit für Sync und verteiltestes Arbeiten dank global eindeutiger IDs.

### 🔒 Revisionssicher & Lokal
Deine Finanzdaten gehören dir.
*   **SQLite-Backend:** Eine einzige Datei. Einfach zu sichern, einfach zu versionieren.
*   **Audit-Log:** Jede Änderung (Insert, Update, Delete) wird unveränderbar protokolliert.
*   **GoBD-Konformität:** Features wie Festschreibung und Historisierung sind im Kern verankert.

---

## 🚀 Quickstart

### Installation

```bash
# Via pip (Empfohlen)
pip install euer-cli

# Oder direkt aus dem Source
git clone https://github.com/dein-user/euer.git
cd euer
pip install -e .
```

### Erste Schritte

1.  **Datenbank initialisieren:**
    ```bash
    euer init
    ```
    Erstellt `euer.db` im aktuellen Verzeichnis.

2.  **Einnahme buchen:**
    ```bash
    euer add income --amount 1500.00 --source "Projekt A" --date 2023-10-01
    ```

3.  **Ausgabe buchen:**
    ```bash
    euer add expense --amount 29.90 --vendor "GitHub" --category "Software"
    ```

4.  **EÜR-Bericht generieren:**
    ```bash
    euer report year 2023
    ```

---

## 🔌 Erweiterungen (Plugins)

Dank der neuen **Plugin-Architektur** kannst du `euer` an deine Bedürfnisse anpassen.
*(Coming Soon)*

*   `euer-elster`: Übermittlung der EÜR direkt an das Finanzamt.
*   `euer-import`: Import von CSV/CAMT Dateien deiner Bank.

## 🛠️ Für Entwickler & Agents

Du willst `euer` in deinen Agenten integrieren?

```python
# Direkter Zugriff auf den Service Layer (Python-API)
from euercli.services.expenses import create_expense
from euercli.database import get_db_connection

conn = get_db_connection("euer.db")
expense = create_expense(
    conn, 
    amount=50.00, 
    vendor="OpenAI", 
    date="2023-11-01"
)
print(f"Created Expense: {expense.uuid}")
```

## 📄 Lizenz

GNU AGPLv3 License
Copyright (c) 2026 Markus

**Hinweis zur AGPL:**
Diese Software ist frei verfügbar. Wenn du sie jedoch modifizierst und über ein Netzwerk (z.B. als Web-Service oder SaaS) anbietest, bist du verpflichtet, den vollständigen Quellcode deiner Version ebenfalls unter der AGPL offenzulegen.
Dies stellt sicher, dass `euer` ein Gemeinschaftsprojekt bleibt und nicht proprietär vereinnahmt wird.
