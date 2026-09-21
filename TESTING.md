# Teststrategie

## Ziele

- Sicherstellen, dass alle CLI-Kommandos korrekt funktionieren.
- Verhindern von Regressionen bei Datenbank-Operationen und Audit-Log.
- Reproduzierbare Tests ohne Abhängigkeit von lokaler Konfiguration.

## Testansatz

- **CLI-Integrationstests (Standard-Library `unittest`)**: Die Tests rufen `python -m euercli`
  per Subprocess auf und prüfen Exit-Codes sowie die wichtigsten Ausgaben.
- **Isolierte Umgebung**: Jede Test-Run nutzt ein temporäres `HOME` und eine
  eigene SQLite-DB (`--db`), damit die lokale Konfiguration unberührt bleibt.
- **Datei-Outputs**: Exporte werden in temporäre Ordner geschrieben und geprüft.

## Abdeckung

Die Test-Suite deckt folgende Funktionsbereiche ab:

- `init` und Seed-Kategorien
- `add`, `list`, `update`, `delete` für Ausgaben und Einnahmen
- Duplikat-Erkennung (Hash)
- `summary` inkl. Reverse-Charge-Logik
- `vat-report` inkl. Periodenlogik, KZ-Mapping, Warnungen, CSV-Export und Rundung
- `audit` (INSERT/UPDATE/DELETE)
- `export` (CSV)
- `config show` und `setup` (Onboarding-Wizard)
- `receipt check` und `receipt open` (Fehlerpfade)
- `import` (CSV) und `incomplete list`

## Nicht automatisiert (manuell)

- `receipt open` erfolgreicher Pfad (öffnet GUI/Datei-System)

## Ausführen

```bash
make test
```

Linting, Formatprüfung und Coverage-Bericht:

```bash
make lint
make coverage
```

Die XLSX-Integrationstests werden automatisch ausgeführt, wenn `openpyxl` installiert
ist. `make install` installiert dafür die Extras `dev` und `xlsx`. Ohne `openpyxl`
werden ausschließlich diese optionalen Tests übersprungen.

In GitHub Actions läuft die Suite auf Linux, macOS und Windows mit Python 3.11 sowie
zusätzlich auf Linux mit der aktuellen unterstützten Python-Version.
