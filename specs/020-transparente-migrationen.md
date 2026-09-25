# Spec 020: Transparente und sichere DB-Migrationen

## Status

Offen

## Originalfeedback (wörtlich)

> Bei euer init auf einer bereits vorhandenen Datenbank wäre mehr Transparenz hilfreich:
>
> verwendeter DB-Pfad und erkannte Schemaversion,
> anstehende Migrationen, bevor sie angewendet werden,
> Zahl und IDs der Bestandsbuchungen, die danach unvollständig oder prüfbedürftig werden,
> ein verständlicher Abschlussbericht mit den nächsten Prüfschritten.
> Zusätzlich sollte euer vor der Migration automatisch eine konsistente Datenbanksicherung erstellen und deren Pfad nennen. Am besten über die SQLite-Backup-Schnittstelle, damit auch ein eventuelles WAL konsistent berücksichtigt wird. Ein Dry-run und eine transaktionale Migration mit Rollback bei Fehlern wären sinnvoll. Für falsche oder nicht existierende DB-Pfade sollte init klar unterscheiden zwischen „bestehende DB migrieren“ und „neue DB anlegen“.
>
> Ich würde alte Bewirtungsfelder nicht stillschweigend fachlich klassifizieren: Dass zwei Datensätze als prüfbedürftig markiert wurden, war sicherer, als Werte zu erraten. Aber init hätte diese Fälle bereits vorher ankündigen sollen.

## Learning

Die Bewirtungsmigration aus Spec 018 markiert unbekannte Alt-Fälle sinnvoll als
`needs_review`. Die bisherige `init`-Ausgabe bereitet Betroffene jedoch nicht
vor. Da die heutige DB keine verlässliche globale Schemaversion speichert und
einzelne Migrationshilfen selbst committen, kann ein Bericht diese Eigenschaften
erst nach Umbau zuverlässig bieten. Eine Paketversion ist keine Schemaversion.

## Anforderungen

1. **Read-only Preflight:** Effektiven absoluten DB-Pfad, Existenz und erkannten
   Schema-/Migrationsstand nennen. Für Legacy-DBs ohne Versionsmarker den Stand
   aus Schema-Merkmalen ermitteln und als „abgeleitet“ kennzeichnen; bei
   mehrdeutigem Stand abbrechen statt eine Version zu erfinden. Anstehende
   Migrationen in Reihenfolge und deren Auswirkung vorab anzeigen.
2. **Betroffene Bestandsdaten:** Jede Datenmigration besitzt eine read-only
   Impact-Abfrage. Für Bewirtungen Anzahl und IDs, die `needs_review` erhalten,
   vorab melden; bei großen Listen vollständige IDs über maschinenlesbare Ausgabe
   oder Datei bereitstellen. Keine Vorsteuer oder fachlichen Status schätzen.
3. **Dry-run:** `euer init --dry-run` erzeugt keine DB, kein Backup und keine
   Config-Änderung. Es liefert denselben Plan und Impact als der echte Lauf;
   `--json` macht dies für Agenten auswertbar. Zwischen Dry-run und Ausführung
   können Daten wechseln; der echte Lauf prüft erneut.
4. **Sicherung und Transaktion:** Vor der ersten Änderung einer bestehenden DB
   konsistentes SQLite-Backup gemäß [Spec 016](016-agent-safety-und-guardrails.md)
   erstellen. Schema- und Datenänderungen eines Migrationslaufs in einer
   SQLite-Transaktion ausführen; interne Commits aus Migrationshilfen entfernen.
   Fehler führen zu Rollback und einem eindeutigen Fehlerbericht. Vorab-Sicherung
   bleibt für manuelle Wiederherstellung erhalten.
5. **Migrationshistorie:** Explizite, monotone Migrationskennungen mit
   Ausführungszeitpunkt transaktional protokollieren. Initiale Registrierung
   bereits vorhandener DBs darf keine früheren Schritte erneut anwenden.
6. **Abschlussbericht:** DB-Pfad, vorheriger und neuer **Schemastand**, Backup-Pfad,
   angewendete Migrationen, betroffene IDs und konkrete Prüfaktionen nennen.
   Bei Bewirtungen auf `euer incomplete list` und Belegprüfung verweisen.
   Kein Erfolgstext, bevor Commit abgeschlossen ist.
7. **Neuanlage:** Expliziter fehlender `--db`-Pfad benötigt `--create`; Verhalten
   des Standardpfads siehe Spec 016. Neuaufbau und Upgrade in Ausgaben und
   Exit-Codes unterscheiden.

## Akzeptanzfälle

- Legacy-DB ohne Marker, aktuelle DB, zwei betroffene Bewirtungen, aktive WAL-DB,
  Dry-run, fehlerhafte Migration mit Rollback, Backup-Fehler, falscher DB-Pfad,
  parallele Änderung zwischen Preflight und Ausführung.

## Dokumentation nach Implementierung

`docs/USER_GUIDE.md`, `docs/USER_JOURNEY.md`, `docs/FAQ.md`,
`docs/skills/euer-buchhaltung/SKILL.md` und `docs/RELEASE_NOTES.md`.
