# Spec 027: Separat installiertes DATEV-Subcommand

## Status

Implementiert

## Ziel

`euer datev` ist auch nutzbar, wenn `euer-datev` in einer eigenen Python-Umgebung
installiert wurde und als ausführbares Programm im `PATH` steht.

## Verhalten

- Ein installierter Entry Point `euer.commands:datev` hat Vorrang.
- Ohne Entry Point wird `euer-datev` im `PATH` aufgerufen. Fehlt es, nennt die
  Fehlermeldung die Installationswege.
- DATEV-Argumente einschließlich `--help` gehen unverändert an das Programm.
- `export` und `validate` verwenden die DB-Auflösung des Core. Ein DATEV-eigenes
  `--db` hat Vorrang vor dem globalen `euer --db`.
- Hilfe, `init-skr` und `license` benötigen weder eine Buchhaltungsdatenbank noch
  eine bestätigte Skill-Version. Datenbefehle behalten die Core-Vorprüfungen.
