# Spec 021: Versionierte Exportläufe mit Manifest

## Status

Implementiert

## Originalfeedback (wörtlich)

> Exporte standardmäßig nicht überschreiben
> Ich würde einen neuen, noch zu entwickelnden versionierten Exportmodus begrüßen: etwa eine neue Ausgabemappe pro Release/Datum, mit Manifest zu euer-Version, Formularjahr und erzeugten Dateien. Falls ein Ziel bereits existiert, sollte euer abbrechen oder ausdrücklich um Überschreiben bitten.

## Learning

Ein bestehender Export kann bereits geprüft oder weitergegeben sein. Das
Überschreibverbot für alle Exporte steht in Spec 016. Ein eigener Ordner je Lauf
und ein Manifest erleichtern spätere Vergleiche und zeigen nachträgliche
Dateiänderungen gegenüber den gespeicherten Prüfsummen. `euer` ist auf die
praktische EÜR-Arbeit ausgerichtet und beansprucht keine GoBD-Konformität.
Der Modus ist keine rechtlich revisionssichere Archivierung.

## Anforderungen

- Optionaler Modus `euer export --versioned`. Ein Lauf erhält einen eindeutigen
  Ordner mit Formularjahr, Zeitstempel inklusive Zeitzone und `euer.VERSION`;
  bei Kollision abbrechen, niemals stillschweigend denselben Ordner nutzen.
- Manifest im Ordner: Manifestformat-Version, euer-Version, Erzeugungszeit,
  Berichts-/Formularjahr, angewandter Steuermodus, Parameter und Liste aller
  erzeugten Dateien mit relativen Namen, Bytegrößen und SHA-256-Prüfsummen.
  Zeilenzahlen nur bei Formaten angeben, für die sie eindeutig definiert sind.
- Alle Exportdateien stammen aus demselben konsistenten lesenden DB-Snapshot.
  Für einen belegbaren DB-Bezug den Hash **dieses Snapshots** oder einen
  transaktional ermittelten Inhaltsfingerabdruck speichern, nicht den Hash
  der laufenden SQLite-Hauptdatei bei aktivem WAL.
- Lauf zunächst in einem temporären Verzeichnis erstellen, dann Manifest
  schreiben und den vollständigen Ordner atomar an den Zielort verschieben,
  soweit das Dateisystem dies zulässt. Fehler hinterlassen keinen als
  abgeschlossen ausgewiesenen Lauf.
- Manifestprüfung kann die Dateien nachträglich auf Veränderung prüfen;
  sie belegt keine inhaltliche Steuerprüfung, Vollständigkeit der Buchhaltung
  oder Unveränderbarkeit außerhalb des lokalen Dateisystems. Lokale Dateien
  und das Manifest können gemeinsam geändert oder gelöscht werden.
- In CLI und Doku den Modus „versionierter Export“ oder „Export mit Manifest“
  nennen. Keine Aussagen wie „revisionssicher“, „GoBD-konform“ oder
  „Audit-Archiv“ als Produkteigenschaft verwenden.
- Standardexport ohne `--versioned` erfüllt den Überschreibschutz aus Spec 016.

## Akzeptanzfälle

- Zwei Läufe am selben Tag, vorhandenes Ziel, fehlendes XLSX-Extra, Fehler
  während Erstellung, aktive WAL-DB, nachträglich geänderte Exportdatei.

## Dokumentation nach Implementierung

`docs/skills/euer-buchhaltung/references/cli_reference.md`, `docs/USER_JOURNEY.md`,
`docs/skills/euer-buchhaltung/SKILL.md` und `docs/RELEASE_NOTES.md`.

Die ursprünglich genannten `docs/USER_GUIDE.md` und `docs/FAQ.md` existieren
im Repository nicht; ihre Exportanleitung liegt in der CLI-Referenz.

## Abnahmematrix (Review)

Die Fälle laufen in `tests/test_export_versioned.py` (Klasse
`VersionedExportTestCase`), sofern nicht anders genannt.

| Fall | Nachweis |
|------|----------|
| CSV, Parameter, Größen, Prüfsummen, Zeilenzahlen | `test_versioned_export_creates_folder_and_valid_manifest` |
| Zwei Läufe innerhalb derselben Sekunde mit Zeitzone | `test_two_exports_in_same_second_have_distinct_directories` |
| Vorhandenes Ziel, auch mit `--force` und spätem Konkurrenzzugriff | `test_versioned_export_aborts_on_collision_without_overwriting`, `test_late_collision_preserves_empty_target_and_removes_staging`, `test_dangling_symlink_target_is_not_replaced_even_with_force` |
| Fehlendes XLSX-Extra | `test_missing_xlsx_extra_creates_no_output` |
| Fehler während Erstellung | `test_versioned_export_error_during_creation_leaves_no_folder`, `test_output_file_instead_of_directory_is_a_cli_error` |
| Aktive WAL-Daten und paralleler Writer; Export und Hash desselben Standes | `test_wal_writer_cannot_change_export_snapshot_or_hash` |
| Nachträgliche Änderung / Löschung | `test_versioned_export_verify_detects_tampered_file`, `test_versioned_export_verify_detects_missing_file` |
| Fehlende Prüfdaten, ungültige Pfade, Verzeichnis statt Datei | `test_verify_rejects_invalid_file_metadata_and_unreadable_files` |
| Automatische Auswahl des letzten abgeschlossenen Laufs über Jahresgrenzen | `test_verify_without_path_uses_latest_completed_run_across_years` |
| Prüfung ohne DB, Skill-Bestätigung und gültige Config | `test_verify_works_without_database_skill_or_project_config` |
| XLSX ohne Zeilenzahl, erfolgreiche Prüfung | `test_versioned_export_xlsx` |
| Standardexport: Schutz, explizites Überschreiben und Rollback | `tests/test_export_guardrails.py` |

Diese Regressionstests sind keine plattformübergreifende Release-Abnahme.
