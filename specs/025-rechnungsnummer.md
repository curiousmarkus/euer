# Optionale Rechnungsnummer bei Einnahmen und Ausgaben

## Status

Implementiert

## Ziel

Agenten können die auf einem Beleg angegebene Rechnungsnummer getrennt vom
Dateinamen und von Notizen erfassen und beim Abgleich wieder auslesen.

## Verhalten

- `expenses` und `income` speichern `invoice_number` als optionalen Text.
- `add` und `update` akzeptieren `--invoice-number`; bei `update` entfernt ein
  leerer Wert die Nummer. Leerraum am Rand wird entfernt.
- CSV-/JSONL-Import akzeptiert `invoice_number` und `Rechnungsnummer`.
- `list --format csv` sowie CSV-/XLSX-Export geben die Nummer als zusätzliche
  letzte Spalte aus. Bestehende Spalten behalten ihre Reihenfolge.
- Die Nummer wird im Audit-Log für Anlegen und Ändern erfasst.
- Es gibt keine Eindeutigkeitsbedingung: derselbe Beleg kann Teilzahlungen
  und Korrekturen betreffen; Nummern anderer Aussteller können übereinstimmen.
- Bestehende Datenbanken erhalten das Feld durch Migration 009. Alte Daten
  bleiben unverändert; Rechnungsnummern werden nicht aus Dateinamen erraten.
