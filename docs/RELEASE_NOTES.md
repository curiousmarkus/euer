# Release Notes

Diese Hinweise richten sich an Nutzer:innen mit bestehenden lokalen Instanzen.
Sie ergänzen die normale Update-Sequenz aus dem User Guide:

```bash
pipx upgrade euercli
euer init
euer incomplete list
euer summary --year 2026
```

Bei Releases mit Agenten-Änderungen müssen lokal kopierte Agenten-Dateien
zusätzlich aktualisiert werden. Das betrifft insbesondere:

- `docs/skills/euer-buchhaltung/SKILL.md`
- `docs/templates/accountant-agent.md`
- die persönliche `AGENTS.md`, falls in der jeweiligen Release Note ausdrücklich genannt

Die persönliche `AGENTS.md` sollte nie blind ersetzt werden, weil sie individuelle
Pfade, Konten, Lieferanten-Mappings und steuerliche Stammdaten enthält.

## 0.7.0

### Warum relevant?

Die Belegablage nutzt jetzt standardmäßig eine jahrzentrierte Struktur:

```text
<Beleg-Root>/<Jahr>/<Typ>/<Belegname>
```

Beispiele:

```text
/Users/max/Dropbox/Buchhaltung/2026/Ausgaben/2026-01-15_Amazon.pdf
/Users/max/Dropbox/Buchhaltung/2026/Einnahmen/2026-01-20_Rechnung_001.pdf
```

Die alten Config-Keys `receipts.expenses` und `receipts.income` werden für die
Belegprüfung nicht mehr verwendet. Belegdateien werden beim Upgrade nicht
automatisch verschoben.

### Nach dem Upgrade

1. Backup der bestehenden `~/.config/euer/config.toml` erstellen.
2. Neue Beleg-Config setzen:

```toml
[receipts]
root = "/Users/max/Dropbox/Buchhaltung"
year_dir = "{year}"
expenses_dir = "Ausgaben"
income_dir = "Einnahmen"
```

3. Alternativ per CLI setzen:

```bash
euer setup --set receipts.root "/Users/max/Dropbox/Buchhaltung"
euer setup --set receipts.year_dir "{year}"
euer setup --set receipts.expenses_dir "Ausgaben"
euer setup --set receipts.income_dir "Einnahmen"
```

4. `exports.directory` bei Bedarf separat prüfen: Es ist ein konkreter Ordner
   und unterstützt keinen `{year}`-Platzhalter. Für jahresweise Exportordner
   `--output` mit einem konkreten Pfad verwenden, z.B.
   `euer export --year 2026 --output "/Users/max/Dropbox/Buchhaltung/2026/Exporte"`.
5. Bestehende Belege bei Bedarf manuell nach `Jahr/Typ` verschieben.
6. Migration prüfen:

```bash
euer receipt check --year 2026
```

7. Lokale Kopien von `SKILL.md`, `accountant-agent.md` und der persönlichen
   `AGENTS.md` auf die neue `Jahr/Typ`-Struktur aktualisieren.

## 0.6.0

### Warum relevant?

`euer` enthält jetzt einen ELSTER-nahen USt-Voranmeldungs-Report:

```bash
euer vat-report --year 2026
euer vat-report --year 2026 --quarter 1
euer vat-report --year 2026 --month 3 --format csv --output exports/
```

Dafür speichern `expenses` und `income` neue UStVA-Klassifikationsfelder:

- `vat_rate`
- `vat_code`

Neue Einnahmen bekommen im Modus `standard` standardmäßig `19 %`, sofern nicht
`--vat-rate 7`, `--vat-rate 0` oder `--tax-free` gesetzt wird. `amount_eur`
bleibt weiterhin der tatsächliche Brutto-Zahlfluss; die USt wird für Einnahmen
aus dem Bruttobetrag herausgerechnet oder über `--vat` manuell gesetzt.

### Nach dem Upgrade

1. Backup der lokalen Datenbank erstellen.
2. `pipx upgrade euercli` ausführen.
3. Im Buchhaltungsordner `euer init` ausführen. Dadurch werden `vat_rate` und
   `vat_code` in bestehenden Datenbanken ergänzt.
4. Mit `euer vat-report --year <JAHR>` Warnungen prüfen.
5. Alte Einnahmen ohne `vat_code` bei Bedarf nachklassifizieren:

```bash
euer update income <ID> --vat-rate 19
euer update income <ID> --vat-rate 7
euer update income <ID> --vat-rate 0
euer update income <ID> --tax-free
```

6. Reverse-Charge-Altbuchungen mit `unclassified` weiter per
   `euer update expense <ID> --rc eu|third-country` nachpflegen.
7. Lokale Kopien von `SKILL.md`, `accountant-agent.md` und ggf. der
   persönlichen `AGENTS.md` um die neuen UStVA-Regeln ergänzen.

### Agenten-Regeln

Für regelbesteuerte Mandate sollen Agenten Einnahmen künftig mit passender
USt-Klassifikation buchen:

```bash
euer add income ... --vat-rate 19
euer add income ... --vat-rate 7
euer add income ... --tax-free
```

Für Ausgaben bleibt `--vat` der manuelle Vorsteuerbetrag; Reverse Charge bleibt
`--rc eu|third-country`.

## 0.5.0

### Warum relevant?

Reverse-Charge-Ausgaben speichern jetzt keinen Boolean mehr, sondern einen
konkreten RC-Typ:

- `none`
- `eu`
- `third_country`
- `unclassified` für migrierte Altbuchungen ohne bekannte Jurisdiktion

Dadurch können spätere UStVA-Auswertungen EU-Leistungen und Drittland-Leistungen
sauber trennen.

### Nach dem Upgrade

1. Backup der lokalen Datenbank erstellen.
2. `pipx upgrade euercli` ausführen.
3. Im Buchhaltungsordner `euer init` ausführen.
4. Mit `euer incomplete list` und `euer summary --year 2026` offene Nacharbeiten prüfen.
5. Lokale Kopien von `SKILL.md` und `accountant-agent.md` durch die Version aus diesem Release ersetzen.
6. Bestehende RC-Buchungen mit `unclassified` prüfen und nachpflegen:

```bash
euer update expense <ID> --rc eu
euer update expense <ID> --rc third-country
```

### AGENTS.md

Die persönliche `AGENTS.md` muss nicht komplett neu erzeugt werden. Prüfe aber,
ob dort Reverse-Charge-Anbieter oder Buchungsregeln stehen. Diese Regeln sollten
jetzt zwischen EU und Drittland unterscheiden und `--rc eu` bzw.
`--rc third-country` nennen.

Wenn du unsicher bist, führe den aktuellen `docs/templates/onboarding-prompt.md`
erneut aus oder bitte deinen Agenten um ein gezieltes Update:

```text
Aktualisiere meine AGENTS.md für euer 0.5.0. Übernimm nur die neuen
Reverse-Charge-Regeln aus docs/RELEASE_NOTES.md und docs/templates/onboarding-prompt.md.
Erhalte alle persönlichen Pfade, Konten, Lieferanten-Mappings und Steuerdaten.
```
