# Backlog - Feature-Ideen

Sammlung von Feature-Ideen für zukünftige Entwicklung. Nicht priorisiert oder bewertet.

---

## Buchhaltung & Erfassung

### Wiederkehrende Buchungen
Monatliche Ausgaben (Hosting, Telefon) automatisch vorschlagen oder erstellen.
```bash
euer recurring add --vendor "1und1" --amount -39.99 --day 15 --category "Telekommunikation"
euer recurring generate --month 2026-02
```

### Bulk-Import aus CSV
Kontoauszüge direkt importieren statt manuell buchen.
```bash
euer import csv bank-statement.csv --account "N26" --mapping n26
```

### Split-Buchungen
Eine Rechnung auf mehrere Kategorien aufteilen.
```bash
euer add expense --date 2026-01-15 --vendor "Amazon" --splits "Arbeitsmittel:-50,Werbekosten:-30"
```

### Vorlagen/Templates
Häufige Buchungen als Template speichern.
```bash
euer template add "openai" --vendor "OpenAI" --category "Laufende EDV-Kosten" --rc
euer add expense --template openai --date 2026-01-20 --amount -20.00
```

---

## Belege & Dokumente

### Beleg-Upload mit Rename
Beleg automatisch umbenennen und in richtigen Ordner verschieben.
```bash
euer receipt attach 12 ~/Downloads/invoice.pdf
# -> Kopiert nach <belege>/2026/2026-01-15_Render.pdf
```

### OCR/PDF-Parsing
Beleg-Daten aus PDF extrahieren (Datum, Betrag, Vendor).
```bash
euer receipt scan ~/Downloads/invoice.pdf
# Vorschlag: --date 2026-01-15 --vendor "Render" --amount -22.71
```

### Beleg-Thumbnail-Ansicht
Vorschau aller Belege eines Monats generieren.

---

## Reporting & Export

### USt-Voranmeldung Export
Direkt die Werte für ELSTER generieren.
```bash
euer report ustva --quarter 2026-Q1
# Zeile 81: xxx EUR (Reverse-Charge)
```

### Monatsabschluss
Zusammenfassung mit Vergleich zum Vormonat.
```bash
euer report month --month 2026-01
```

### Jahresvergleich
Ausgaben/Einnahmen Jahr-über-Jahr vergleichen.
```bash
euer report compare --years 2025,2026
```

### Kategorie-Trends
Entwicklung einer Kategorie über Zeit.
```bash
euer report trend --category "Laufende EDV-Kosten" --months 12
```

### PDF-Export
Summary als PDF für Steuerberater.

---

## Validierung & Qualität

### Validierungs-Rules
Konfigurierbare Regeln für Buchungen.
- Ausgaben müssen negativ sein
- Reverse-Charge nur bei bestimmten Kategorien
- Beleg-Pflicht ab bestimmtem Betrag

```bash
euer validate --year 2026
# Warnung: Ausgabe #12 hat positiven Betrag
# Warnung: Ausgabe #15 > 100 EUR ohne Beleg
```

### Duplikat-Finder
Ähnliche Buchungen erkennen (nicht nur exakte Hash-Matches).
```bash
euer check duplicates --year 2026
# Mögliche Duplikate: #12 und #15 (gleiches Datum, ähnlicher Betrag)
```

---

## Integration & Sync

### Bank-API Integration
Direkte Anbindung an Banking-APIs (FinTS/HBCI).

### Dropbox/Cloud Sync
Automatische Beleg-Erkennung wenn neue Dateien erscheinen.

### Steuerberater-Portal
Export in Format für DATEV oder andere Buchhaltungssoftware.

---

## UX & Convenience

### Interaktiver Modus
Guided Workflow für neue Buchungen.
```bash
euer add expense --interactive
# Datum [2026-01-31]: 
# Lieferant: OpenAI
# Kategorie [Laufende EDV-Kosten]: 
# ...
```

### Undo/Redo
Letzte Aktion rückgängig machen.
```bash
euer undo  # Stellt gelöschte Buchung wieder her
```

### Fuzzy-Kategorie-Matching
Tippfehler bei Kategorien tolerieren.
```bash
euer add expense --category "EDV Kosten"  # Findet "Laufende EDV-Kosten"
```

### Shell-Completion
Bash/Zsh-Completion für Commands und Kategorien.
```bash
euer completion bash > /etc/bash_completion.d/euer
```

---

## Technisch

### Web-UI
Einfaches Flask/FastAPI Frontend für Browser-Zugriff.

### REST-API
Headless-Modus für Integration in andere Tools.

### Multi-User Support
Mehrere Benutzer mit Berechtigungen.

### Backup & Restore
Automatische Backups, einfaches Restore.
```bash
euer backup create
euer backup restore euer-backup-2026-01-31.db
```

### Datenbank-Migrationen
Automatische Schema-Updates bei neuen Versionen.

---

## Dokumentation

### Onboarding-Wizard
Interaktive Ersteinrichtung.
```bash
euer setup
# Willkommen! Konfiguriere deine EÜR...
# Beleg-Pfad für Ausgaben: 
# Beleg-Pfad für Einnahmen:
```

### Beispiel-Datenbank
Demo-Daten für neue Nutzer.
```bash
euer init --demo
```

---

## Priorisierungs-Kriterien

Bei der Auswahl von Features berücksichtigen:

1. **Zeitersparnis** - Wie viel manuelle Arbeit wird eingespart?
2. **Fehlerreduktion** - Verhindert das Feature Buchungsfehler?
3. **Komplexität** - Wie aufwändig ist die Implementierung?
4. **Dependencies** - Werden neue Abhängigkeiten benötigt?
5. **Agent-Kompatibilität** - Kann ein AI-Agent das Feature nutzen?
