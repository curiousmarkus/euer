# Zu euer beitragen

Vielen Dank für dein Interesse an `euer`! Beiträge in Form von Fehlerberichten,
Verbesserungsvorschlägen, Dokumentation und Code sind willkommen.

## Fehler melden und Änderungen vorschlagen

- Prüfe zunächst, ob bereits ein passendes Issue oder eine Spezifikation in
  [`specs/`](specs/) existiert.
- Beschreibe bei Fehlern die verwendete Version, das Betriebssystem, die Schritte zur
  Reproduktion sowie das erwartete und tatsächliche Verhalten.
- Lege für nicht triviale Features eine Spec an oder ergänze die bestehende Spec.

## Entwicklungsumgebung einrichten

Benötigt wird Python 3.11 oder neuer. Installiere das Projekt im Repository mit:

```bash
python -m pip install -e .
euer init
```

Ohne Installation kann die CLI über `python -m euercli <command>` aufgerufen werden.
Architektur, Service-Layer-Regeln und Code-Konventionen sind im
[`DEVELOPMENT.md`](DEVELOPMENT.md) dokumentiert und müssen vor einer Codeänderung
gelesen werden.

## Änderungen einreichen

1. Erstelle einen eigenen Branch und halte die Änderung möglichst klein und fokussiert.
2. Ergänze oder aktualisiere Tests und betroffene Dokumentation.
3. Führe die Test-Suite aus:

   ```bash
   python -m unittest discover -s tests
   ```

4. Prüfe optional Formatierung und Linting:

   ```bash
   ruff check euercli
   ruff format --check euercli
   ```

5. Erstelle einen Pull Request und beschreibe Motivation, Umsetzung und durchgeführte
   Tests.

Weitere Informationen zur Teststrategie stehen in [`TESTING.md`](TESTING.md).

## Wichtige Projektregeln

- Schreiboperationen auf `expenses`, `income` und `private_transfers` laufen immer über
  den Service Layer in `euercli/services/`.
- Nutzerseitige Ausgaben sind deutschsprachig; Bezeichner im Code sind englisch.
- Datenbankabfragen sind parametrisiert und jede Änderung wird im Audit-Log erfasst.
- Bei implementierten Specs wird ihr Status aktualisiert, ebenso die Spec-Tabelle in
  `DEVELOPMENT.md`.
- Prüfe bei jeder Änderung die betroffene Nutzer-, Entwickler- und Release-Dokumentation.

Die vollständigen verbindlichen Regeln und die Checkliste stehen in
[`DEVELOPMENT.md`](DEVELOPMENT.md).
