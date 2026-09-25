# Spec 023: AI-Optimierte Ausgaben & Dry-Run (JSON-First)

## Status

Offen

## Kontext
`euer` wird als primäres Werkzeug für KI-Agenten gebaut. Während Menschen gut darin sind, formatierte ASCII-Tabellen oder farbige Konsolentexte zu lesen, sind diese Formate für LLMs fehleranfällig (z. B. durch Zeilenumbrüche, abgeschnittene Tabellenspalten oder unstrukturierte Strings). 
Zudem benötigen autonome Agenten einen sicheren Weg, komplexe Mutationen (wie Buchungen mit Steuerlogik) zu validieren, bevor sie permanent in die Datenbank geschrieben werden.

## 1. JSON-First (Die Sprache der Maschine)

Jeder lesende Befehl (Read-Operation) und jeder Report muss zwingend strukturiertes JSON ausgeben können.

### Anforderungen an `--json`
- Befehle wie `euer list expenses`, `euer summary`, `euer vat-report`, `euer incomplete list` und `euer doctor` müssen das Flag `--json` unterstützen.
- Der Output muss bei erfolgreicher Ausführung valides JSON sein (ohne zusätzliche Prosa-Einleitungen vor oder nach dem JSON-Block auf `stdout`).
- **Strukturierte Fehler:** Im `--json` Modus sollten auch Fehler auf `stderr` als JSON-Objekt ausgegeben werden. Beispiel:
  ```json
  {
    "status": "error",
    "error_code": "outdated_skill",
    "message": "Skill (v1.2.0) ist veraltet.",
    "remediation": "euer setup --set skill.version 1.3.0"
  }
  ```
- Dadurch muss der Agent nicht mit Regex arbeiten, um Tabellen oder Warnungen zu parsen.

## 2. Der Dry-Run Modus (Probebuchungen für KIs)

Agenten machen Fehler bei der Interpretation von Steuerregeln oder Befehlssyntax. Damit sie nicht den Audit-Log mit ständigen `euer undo`-Befehlen zumüllen, brauchen sie eine Sandbox-Funktion.

### Anforderungen an `--dry-run`
- Jeder schreibende Befehl (`add`, `update`, `delete`, `import`) muss ein `--dry-run` Flag unterstützen.
- Wenn `--dry-run` übergeben wird, führt die CLI den kompletten Validierungszyklus durch:
  - Pflichtfeld-Prüfung
  - Plausibilitäts-Checks (z. B. `--vat` passt rechnerisch zum `--amount`)
  - Duplikats-Prüfung (`suspicious_duplicate`)
  - Warnungen (z. B. "Wertstellungsdatum liegt vor Rechnungsdatum")
- **Wichtig:** Es wird kein `COMMIT` auf der SQLite-Datenbank ausgeführt. Die Transaktion wird zwingend gerollt (oder gar nicht erst gestartet).
- **Kombination:** `euer add expense ... --dry-run --json` liefert dem Agenten ein sauberes JSON-Objekt zurück, das entweder den Zustand `success` (Buchung wäre gültig) oder `error` (mit genauen Validierungsfehlern) enthält.

## Akzeptanzkriterien
- Alle Tabellen-Befehle unterstützen `--json`.
- `euer summary` und `euer vat-report` liefern vollständige Kennzahlenbäume als JSON.
- `euer add expense --dry-run` wirft Fehlermeldungen bei fehlenden Pflichtfeldern, ändert aber die `.db` Datei (und deren Modification-Timestamp) nicht.
- Agenten in der `SKILL.md` werden instruiert: "Nutze bei Unklarheiten immer `--dry-run`, bevor du eine Buchung verbindlich ausführst."
