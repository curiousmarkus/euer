# 015 - Veröffentlichung auf PyPI

## Status

Offen

## Kontext

`euer` wird derzeit direkt aus dem GitHub-Repository mit `pipx` installiert. Eine
Veröffentlichung auf PyPI könnte Installation, Versionsauswahl und Updates vereinfachen.
Ob und wann dieser zusätzliche Distributionsweg angeboten wird, ist noch nicht entschieden.

Die Standardinstallation soll weiterhin ohne Laufzeitabhängigkeiten auskommen. Die optionale
XLSX-Unterstützung bleibt über das Extra `xlsx` verfügbar.

## Ziel

Bewerten und gegebenenfalls umsetzen, wie reproduzierbare Releases von `euercli` auf PyPI
bereitgestellt werden können.

## Zu klärende Punkte

1. Verfügbarkeit und endgültige Wahl des Distributionsnamens auf PyPI.
2. Manueller Release-Prozess oder GitHub Trusted Publishing.
3. Verwendung von TestPyPI für einen Probelauf.
4. Zuordnung zwischen Git-Tags, Paketversion und Release Notes.
5. Signierung beziehungsweise Provenance der veröffentlichten Artefakte.
6. Dokumentation der Installation mit und ohne das optionale Extra `xlsx`.
7. PyPI-kompatible Darstellung des README, insbesondere des relativen Logo-Pfads.

## Nicht-Ziele

- Diese Spec aktiviert noch keine Veröffentlichung.
- Es werden keine PyPI-Tokens oder anderen Secrets im Repository hinterlegt.
- Die Installation direkt aus GitHub bleibt bis zu einer bewussten Entscheidung der
  dokumentierte Standardweg.

## Akzeptanzkriterien für eine spätere Umsetzung

1. Wheel und Source Distribution werden in CI gebaut und geprüft.
2. Die Paketversion stimmt mit dem Git-Tag und `euercli.VERSION` überein.
3. Ein Test-Release wurde erfolgreich installiert und die CLI per Smoke-Test ausgeführt.
4. Der Release-Prozess benötigt keine langlebigen Zugangsdaten im Repository.
5. README, User Guide und Release Notes dokumentieren den neuen Installationsweg.
