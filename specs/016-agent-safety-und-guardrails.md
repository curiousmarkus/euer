# Spec 016: Agent-Safety und Guardrails

## Status

Offen

## Ziel

`euer` soll gezielt gegen typische Fehler, Halluzinationen und versehentlich
destruktive Aktionen von KI-Agenten abgesichert werden. Ziel ist es, dem Agenten
Leitplanken (Guardrails) zu geben, versehentliche Datenverluste unmöglich zu machen
und Buchungsfehler sofort behebbar zu machen.

Das Spec umfasst zwei Kernbereiche:
1. **Schutz vor destruktiven Aktionen & Datenverlust** (Backups, Soft-Delete, Undo).
2. **Plausibilitätsprüfungen & Guardrails** (Konsistenzprüfung von Beträgen/Steuern,
   Datums- und Betragsgrenzen, erweiterte Duplikatserkennung).

---

## Motivation

`euer` wird primär von LLM-Agenten bedient. LLMs arbeiten prinzipiell zuverlässig mit
strukturierten CLI-Tools, weisen jedoch spezifische Fehlermuster auf:
- **Fehlinterpretationen von Belegen:** Falsche Steuersätze (z. B. 19 % statt 7 %),
  Zahlendreher bei Beträgen oder irrtümliche Zuordnung von Rechnungs- statt Zahlungsdatum.
- **Doppelbuchungen durch abweichende Schreibweisen:** Der Kreditor heißt auf dem Beleg
  „Adobe Systems Software Ireland“, auf dem Kontoauszug „ADOBE“. Der bisherige exakte
  SHA-256-Hash greift hier nicht.
- **Versehentlich destruktive Aktionen:** Ein Agent löscht oder überschreibt versehentlich
  Buchungen bei einem fehlgeschlagenen Abgleich.
- **Fehlende Wiederherstellbarkeit:** Bisher führt `euer delete` ein physisches SQL-`DELETE`
  aus. Zwar wird die Zeile im Audit-Log archiviert, eine einfache Wiederherstellung
  erfordert jedoch manuelle SQL-Eingriffe.

---

## 1. Schutz vor destruktiven Aktionen & Datenverlust

### 1.1 Automatisches DB-Snapshot-Backup
- **Verhalten:** Vor jeder schreibenden Operation (`add`, `update`, `delete`, `reconcile`,
  `import`), die die Datenbank verändert, prüft `euer`, ob bereits ein Snapshot der aktuellen
  Session/des aktuellen Tages vorliegt, oder erstellt eine rotierende Sicherung.
- **Speicherort:** `~/.config/euer/backups/euer_YYYY-MM-DD_HHMMSS.db`
- **Rotation:** Standardmäßig werden die letzten 10 Snapshots aufbewahrt; ältere werden
  automatisch bereinigt.
- **Overhead:** SQLite-Datenbanken für EÜR umfassen typischerweise nur wenige hundert Kilobyte
  bis Megabyte. Ein Dateisystem-Snapshot benötigt wenige Millisekunden.

### 1.2 Soft-Delete statt Hard-Delete
- **Schema-Erweiterung:**
  - Tabellen `expenses`, `income` und `private_transfers` erhalten eine Spalte
    `deleted_at TIMESTAMP DEFAULT NULL`.
- **Verhalten bei `delete`:**
  - `euer delete expense <id>` setzt `deleted_at = CURRENT_TIMESTAMP` und schreibt
    einen entsprechenden `DELETE`-Eintrag ins `audit_log`.
  - Physisch bleibt der Datensatz erhalten.
- **Filterung:**
  - Standardabfragen (`list`, `summary`, `vat-report`, `export`) filtern
    `WHERE deleted_at IS NULL`.
- **Wiederherstellung:**
  - Neuer Befehl: `euer restore <id> [--table expenses|income|private_transfers]`
    setzt `deleted_at = NULL` zurück.
  - Option `euer list --trash` zeigt gelöschte Einträge an.
- **Endgültiges Löschen (Purge):**
  - Nur bei explizitem `euer delete <id> --purge` (oder `euer trash empty`) wird ein physisches
    SQL-`DELETE` ausgeführt.

### 1.3 Undo-Befehl (`euer undo`)
- **Konzept:** Nutzung der in `audit_log` bereits gespeicherten Vorher-/Nachher-Zustände (`old_data`).
- **Befehl:** `euer undo [--id <audit_log_id>]`
  - Ohne Parameter: Macht die letzte Änderung rückgängig.
  - Mit `--id`: Macht eine spezifische Mutation aus dem Audit-Log rückgängig.
- **Funktionsweise:**
  - Bei vorherigem `UPDATE`: Stellt die Werte aus `old_data` wieder her.
  - Bei vorherigem `DELETE`: Hebt das Soft-Delete auf (`deleted_at = NULL`) bzw. fügt
    bei Altbeständen den Datensatz aus `old_data` wieder ein.
  - Bei vorherigem `INSERT`: Markiert die erstellte Zeile als gelöscht (`deleted_at`).
  - Jede Undo-Aktion erzeugt ihrerseits einen sauberen Eintrag im `audit_log`.

---

## 2. Plausibilitätsprüfungen & Guardrails (Schutz vor Halluzinationen)

### 2.1 Mathematische Konsistenzprüfung (Brutto / Netto / USt)
- **Problem:** Ein Agent extrahiert Betrag und USt-Satz getrennt und übergibt z. B.
  119,00 € mit 7 % USt, obwohl die Steuer rechnerisch 19,00 € (19 %) betrug.
- **Regel:**
  - Wenn ein USt-Satz (7 %, 19 %) angegeben ist, wird die rechnerische Steuer
    ermittelt:
    $$\text{vat\_calc} = \text{amount} - \frac{\text{amount}}{1 + \text{rate}/100}$$
  - Weicht eine explizit übergebene Steuer um mehr als 0,02 € (Rundungstoleranz) von
    der mathematischen Erwartung ab, wird die Buchung mit einem `ValidationError`
    abgelehnt.

### 2.2 Datums- und Betragsplausibilität
- **Zukunftsdaten:**
  - Buchungs- und Zahlungsdaten in der Zukunft (`> heute`) sind bei EÜR unzulässig.
    Sie werden abgelehnt, es sei denn, ein Rechnungsdatum liegt in der Zukunft und das
    Zahlungsdatum ist noch offen.
- **Vergangene Daten:**
  - Liegt ein Datum mehr als 2 Jahre in der Vergangenheit, wird eine Warnung ausgegeben.
- **Ausreißer-Beträge:**
  - Beträge über einem konfigurierbaren Schwellenwert (Standard: 5.000 €) erfordern
    eine explizite Bestätigung oder das Flag `--force`, um Tipp- oder Kommafehler des
    Agenten (z. B. `12000` statt `120.00`) abzufangen.

### 2.3 Erweiterte Duplikatserkennung (Fuzzy Duplicate Detection)
- **Bestehendes Verhalten:**
  - Exakter SHA-256-Hash über `date|vendor|amount|receipt_name`.
- **Neue Heuristik:**
  - Vor dem Anlegen einer Ausgabe/Einnahme prüft der Service-Layer:
    - Gibt es am selben Tag (oder +/- 2 Tage) eine Buchung mit identischem Betrag?
    - Ähneln sich die Namen von Kreditor/Debitor (z. B. Levenshtein-Distanz oder
      Substring-Match wie „Adobe“ in „Adobe Systems Software“)?
  - **Reaktion:**
    - Wenn ja, bricht die CLI mit Warnung und Verweis auf die existierende Buchungs-ID ab:
      `Mögliches Duplikat: Buchung #42 vom 01.09.2026 über 119,00 € (Adobe) existiert bereits.`
    - Agenten können die Buchung bei berechtigtem Anlass mit `--allow-duplicate` oder
      `--force` erzwingen.

---

## Nicht-Ziele

- Keine Einführung von komplexen distributed locks oder Mehrbenutzer-Rechtesystemen.
- Keine Behinderung des Agenten-Workflows durch interaktive TTY-Prompts (Prompts
  müssen über Flags wie `--force` oder klare Fehlermeldungen für Agenten steuerbar sein).
- Keine externen Cloud-Dienste für Plausibilitätsprüfungen; alle Checks laufen lokal.

---

## Technische Umsetzung

1. **Service-Layer:**
   - Alle Plausibilitätschecks werden in `euercli/services/validation.py` gebündelt und
     in `create_expense()`, `update_expense()`, `create_income()`, etc. aufgerufen.
   - Einheitliche `ValidationError`-Codes (`suspicious_duplicate`, `vat_mismatch`,
     `future_date`, `amount_threshold_exceeded`).
2. **Backup-Service:**
   - Schlanke Hilfsfunktion `create_backup(db_path)` in `euercli/backup.py`.
3. **Migration:**
   - Migration in `euercli/commands/init.py` fügt `deleted_at` zu den Tabellen hinzu.
4. **CLI-Commands:**
   - Neue Commands `undo` und `restore`.
   - Flags `--force` bzw. `--allow-duplicate` bei `add` und `update`.

---

## Betroffene Dokumente nach Umsetzung

- `DEVELOPMENT.md` (Spec-Tabelle aktualisieren)
- `docs/USER_GUIDE.md` (`euer undo`, `euer restore`, Backup-Verhalten dokumentieren)
- `docs/skills/euer-buchhaltung/SKILL.md` (Agenten-Hinweise zu `--force` und Duplikatswarnungen)
- `docs/RELEASE_NOTES.md` (Hinweise zur Migration auf Schema mit `deleted_at`)
