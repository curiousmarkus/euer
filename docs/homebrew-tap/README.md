# Bootstrap für `curiousmarkus/homebrew-euer`

Der Tap ist absichtlich ein eigenes Repository. Diese Dateien werden einmalig dorthin
übernommen; der laufende Update-Workflow des Taps benötigt danach keinen Token aus dem
`euer`-Repository.

## Einmalige Einrichtung

1. Repository `curiousmarkus/homebrew-euer` mit dem Inhalt dieses Verzeichnisses anlegen.
2. `Formula/euer.rb.template` nach `Formula/euer.rb` kopieren.
3. Nach dem ersten PyPI-Release den mitgelieferten Updater ausführen:

   ```bash
   python3 scripts/update_formula.py Formula/euer.rb
   ```

   Er setzt sdist-URL und SHA256 und ergänzt `openpyxl` sowie transitive Ressourcen
   wie `et-xmlfile` aus den PyPI-Metadaten des `xlsx`-Extras.
4. Den Workflow unter `.github/workflows/update-formula.yml` übernehmen.

Der erste Bootstrap ist ein einmaliger Maintainer-Schritt. Danach fragt der Tap alle
sechs Stunden PyPI ab, aktualisiert URL, SHA256 und Python-Ressourcen, testet auf macOS
und Linux und pusht nur eine erfolgreich geprüfte Formula mit seinem eigenen
`GITHUB_TOKEN`.

Die Platzhalterdatei ist kein veröffentlichungsfähiges Formula-Artefakt; vor dem ersten
Tap-Commit muss daraus `Formula/euer.rb` mit echten PyPI-Daten erzeugt werden.
