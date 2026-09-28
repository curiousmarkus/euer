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
- `list --format csv` gibt die Nummer als letzte Spalte aus. CSV-/XLSX-Export
  setzt sie unmittelbar hinter das Rechnungsdatum.
- Die Nummer wird im Audit-Log für Anlegen und Ändern erfasst.
- Es gibt keine Eindeutigkeitsbedingung: derselbe Beleg kann Teilzahlungen
  und Korrekturen betreffen; Nummern anderer Aussteller können übereinstimmen.
- Bei gleicher Rechnungsnummer, gleicher Gegenpartei und gleichem Betrag wird
  unabhängig vom Datum ein mögliches Duplikat gemeldet. Abweichende Beträge
  (etwa Teilzahlungen) lösen über die Nummer allein keine Meldung aus.
- Beim CSV-/JSONL-Import brechen solche Verdachtsfälle den gesamten Import mit
  Zeilennummer ab; bereits vorbereitete Buchungen werden zurückgerollt. Exakte
  Dubletten werden weiterhin übersprungen.
- Hat nur eine Buchung eine Nummer, können gleiches Rechnungsdatum oder gleicher
  Belegname bei gleicher Gegenpartei und gleichem Betrag auch über entfernte
  Zahlungsdaten hinweg eine Duplikatmeldung auslösen.
- Der technische Hash enthält eine vorhandene Rechnungsnummer. Ohne Nummer
  bleibt die bisherige Hash-Berechnung erhalten; eine neue Nummer umgeht keine
  exakte Duplikatprüfung gegen ältere Buchungen ohne Nummer. Nummerierte Hashes
  verwenden eine eindeutige Feldkodierung, damit `|` in Belegnamen und Nummern
  keine falschen Hash-Gleichheiten erzeugt. Bereits gespeicherte Hashes bleiben
  unverändert und werden bei der Dublettenprüfung berücksichtigt.
- Bestehende Datenbanken erhalten das Feld durch Migration 009. Alte Daten
  bleiben unverändert; Rechnungsnummern werden nicht aus Dateinamen erraten.
