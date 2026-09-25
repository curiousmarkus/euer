# Spec 019: `euer doctor` für Installation und Datenbank

## Status

Offen

## Originalfeedback (wörtlich)

> Ein Diagnosebefehl wäre nützlich – etwa ein neu zu entwickelndes euer doctor, nicht ein bereits vorhandenes Kommando. Er könnte Version, ausführbaren Pfad, Installationsquelle, doppelte Entry-Points, DB-Pfad und nötige Migrationen anzeigen. Bei konkurrierenden pipx-/Brew-Installationen sollte er klar sagen, welche Version der normale Aufruf verwendet und wie man das behebt.
>
> Die Installationsdoku sollte außerdem einen einzigen kanonischen Brew-Befehl nennen und den Distributionswechsel von euercli zu euer Schritt für Schritt behandeln. Der Homebrew-Tap hatte zunächst noch 0.9.0, während PyPI schon 0.10.2 hatte; nach deiner Aktualisierung bestätigte brew info dann 0.10.2. Die mögliche Verzögerung des Taps sollte direkt bei den Upgrade-Hinweisen stehen.

## Learning

Ein Paketupdate sagt noch nicht, welches `euer` die aktuelle Shell aufruft.
Ein früheres `pipx`-Paket `euercli` kann den Homebrew-Entry-Point verdecken.
Die Diagnose muss den tatsächlich gestarteten Prozess und die PATH-Reihenfolge
sichtbar machen, ohne Buchhaltungsdaten zu verändern.

## Anforderungen

- Neuer Befehl `euer doctor` mit lesbarer deutscher Ausgabe und `--json` für Agenten.
- Aktive Version aus `euercli.VERSION`, tatsächlicher Entry-Point, Interpreter,
  Python-Version, aufgelöster Pfad und erkannte Installationsquelle ausgeben.
  `sys.executable` allein ist nur der Interpreter und kein Beleg für den
  aufgerufenen CLI-Entry-Point. Bei Unsicherheit „unbekannt“ ausgeben.
- Alle `euer`- und `euercli`-Kandidaten im PATH in Suchreihenfolge melden;
  Symlinks und identische Ziele zusammenführen. Keine fremden Binaries zur
  Versionsbestimmung ungefragt ausführen. Versionen nur dort nennen, wo sie
  sicher aus Metadaten oder vertrauenswürdigem Kontext ermittelbar sind.
- Effektive DB-Auflösung wie bei normalen Commands verwenden. Existenz,
  Lesbarkeit und Schema-/Migrationsstatus read-only prüfen; keine DB durch
  `sqlite3.connect()` versehentlich anlegen. Optional `PRAGMA quick_check`
  explizit anfordern, da eine vollständige Integritätsprüfung dauern kann.
- Konkrete, zur erkannten Lage passende Hinweise ausgeben: PATH-Reihenfolge,
  altes `pipx`-Paket, `brew info euer`, Shell-Command-Cache. Deinstallation
  oder Shell-Änderungen niemals automatisch ausführen.
- Standardmäßig offline. Eine spätere explizite Onlineprüfung ist optional
  und darf eine erfolgreiche lokale Diagnose nicht blockieren.
- `--json` enthält stabile Feldnamen, Status und Exit-Code; keine privaten
  Buchungsinhalte, Zugangsdaten oder vollständige Config ausgeben.

## Akzeptanzfälle

- Nur Homebrew vorhanden; pipx und Brew konkurrieren; alter `euercli`-Entry-Point;
  nicht existente DB; nicht lesbare DB; ausstehende Migrationen.
- Der Befehl selbst verändert weder Datenbank noch Config noch PATH.

## Dokumentation nach Implementierung

`README.md`, `docs/USER_GUIDE.md`, `docs/USER_JOURNEY.md`,
`docs/skills/euer-buchhaltung/SKILL.md` und `docs/RELEASE_NOTES.md`.
