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
