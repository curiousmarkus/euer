# Spec 021: Versionierte Exportläufe mit Manifest

## Status

Offen

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

`docs/USER_GUIDE.md`, `docs/USER_JOURNEY.md`, `docs/FAQ.md`,
`docs/skills/euer-buchhaltung/SKILL.md` und `docs/RELEASE_NOTES.md`.
