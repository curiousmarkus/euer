# Spec 011: Kontenrahmen (Buchungskonten je Kategorie)

## Status

Offen

## Motivation

Die EÜR kennt aktuell nur ELSTER-Kategorien (z.B. „Laufende EDV-Kosten", Zeile 50).
In der Praxis nutzen Buchhalter:innen und Steuerberater:innen jedoch einen
**Kontenrahmen** (SKR 03 / SKR 04), in dem jede ELSTER-Gruppe mehrere
Buchungskonten enthält — z.B.:

| ELSTER-Kategorie (Zeile 50) | Buchungskonto |
|------------------------------|---------------|
| Laufende EDV-Kosten          | 4930 – Software/SaaS |
| Laufende EDV-Kosten          | 4940 – Hosting/Cloud |
| Laufende EDV-Kosten          | 4950 – IT-Support |

Ein solcher Kontenrahmen bietet:

1. **Feinere Auswertung** — „Wie viel gebe ich für SaaS vs. Hosting aus?"
2. **Weniger Fehler bei der Buchung** — Konto impliziert die Kategorie; die
   Kategorie muss nicht separat angegeben werden.
3. **Steuerberater-Kompatibilität** — Übergabe-Dateien können Kontonummern
   enthalten, die der Steuerberater direkt zuordnen kann.
4. **KI-Agent-Unterstützung** — Buchungsagenten können einem Benutzer passende
   Konten vorschlagen und so die Buchungsqualität verbessern.

### Abgrenzung

- Die Konten sind **rein informativ / organisatorisch** und haben keine
  steuerrechtliche Wirkung innerhalb der EÜR-Berechnung.
- Es wird **kein vollständiger SKR** abgebildet, sondern ein frei
  konfigurierbarer, vom Nutzer definierter Kontenrahmen.
- Die Funktion ist **vollständig optional**; bestehende Workflows (Buchung
  nur mit Kategorie) bleiben unverändert.

---

## Anforderungen

### A1: Kontenrahmen-Konfiguration in `config.toml`

Der Kontenrahmen wird in der bestehenden Konfigurationsdatei
(`~/.config/euer/config.toml`) definiert. Jeder Eintrag ordnet ein
Buchungskonto einer ELSTER-Kategorie zu.

**TOML-Struktur:**

```toml
# Kontenrahmen — ordnet Buchungskonten den ELSTER-Kategorien zu.
# Format: Kontonummer + optionaler Anzeigename → Kategorie-Name (muss exakt
# mit einer bestehenden Kategorie übereinstimmen).

[[kontenrahmen]]
konto = "4930"
name = "Software / SaaS-Abos"
kategorie = "Laufende EDV-Kosten"

[[kontenrahmen]]
konto = "4940"
name = "Hosting & Cloud-Dienste"
kategorie = "Laufende EDV-Kosten"

[[kontenrahmen]]
konto = "4950"
name = "IT-Support & Wartung"
kategorie = "Laufende EDV-Kosten"

[[kontenrahmen]]
konto = "4930"
name = "Büromaterial"
kategorie = "Arbeitsmittel"

[[kontenrahmen]]
konto = "6300"
name = "Sonstige betriebliche Aufwendungen"
kategorie = "Übrige Betriebsausgaben"

[[kontenrahmen]]
konto = "4400"
name = "Rechts- und Beratungskosten"
kategorie = "Rechts- und Steuerberatung, Buchführung"

[[kontenrahmen]]
konto = "8400"
name = "Erlöse 19% USt"
kategorie = "Umsatzsteuerpflichtige Betriebseinnahmen"
```

**Felder:**

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `konto` | String | Ja | Kontonummer (frei wählbar, z.B. SKR-03-Nummer) |
| `name` | String | Ja | Anzeigename / Beschreibung des Kontos |
| `kategorie` | String | Ja | Name der ELSTER-Kategorie (exakter Match auf `categories.name`) |

**Regeln:**

- Die Kombination `konto` muss innerhalb der Config eindeutig sein.
- `kategorie` muss einer existierenden Kategorie in der Datenbank
  entsprechen. Ungültige Zuordnungen werden beim Laden validiert und mit
  einer Warnung gemeldet.
- Ein Konto erbt den `type` (expense/income) automatisch von der
  zugeordneten Kategorie.

### A2: Config-Ladefunktion `get_kontenrahmen()`

Neue Funktion in `euercli/config.py`:

```python
@dataclass
class Konto:
    konto: str           # z.B. "4930"
    name: str            # z.B. "Software / SaaS-Abos"
    kategorie: str       # Name der ELSTER-Kategorie

def get_kontenrahmen(config: dict) -> list[Konto]:
    """Lädt den Kontenrahmen aus der Config.
    
    Returns:
        Liste aller konfigurierten Konten. Leere Liste wenn kein 
        Kontenrahmen konfiguriert ist.
    """
```

### A3: Service-Funktion `get_konten_for_category()`

Neue Funktion in `euercli/services/categories.py`:

```python
def get_konten_for_category(
    conn: sqlite3.Connection,
    category_name: str,
    config: dict,
) -> list[Konto]:
    """Gibt alle konfigurierten Buchungskonten für eine Kategorie zurück.
    
    Args:
        conn: DB-Verbindung (zur Validierung der Kategorie)
        category_name: Name der ELSTER-Kategorie
        config: Geladene Config
        
    Returns:
        Liste der zugeordneten Konten. Leere Liste wenn keine Konten
        konfiguriert sind oder die Kategorie nicht existiert.
    """
```

### A4: Service-Funktion `resolve_konto()`

Neue Funktion in `euercli/services/categories.py`:

```python
def resolve_konto(
    conn: sqlite3.Connection,
    konto: str,
    config: dict,
) -> tuple[str, str]:
    """Löst eine Kontonummer in (kategorie_name, konto_name) auf.
    
    Args:
        konto: Kontonummer (z.B. "4930")
        
    Returns:
        Tuple (kategorie_name, konto_display_name)
        
    Raises:
        ValidationError: Wenn das Konto nicht im Kontenrahmen existiert.
    """
```

### A5: Implizite Kategorie bei Buchung über Konto

Wenn bei `euer add expense` oder `euer add income` ein `--account`-Wert
angegeben wird, der einem konfigurierten Buchungskonto entspricht, soll:

1. Die zugehörige Kategorie **automatisch** gesetzt werden.
2. Eine explizit angegebene `--category` wird **nicht** überschrieben, sondern
   gegen die Konto-Kategorie validiert. Bei Widerspruch → Fehler.
3. Wenn `--account` kein konfiguriertes Konto ist, bleibt das Verhalten wie
   bisher (Freitext-Konto, Kategorie muss explizit angegeben werden).

**Konkretes Verhalten in `create_expense()` / `create_income()`:**

```
Eingabe: --account 4930 --category (leer)
→ Konto "4930" erkannt → Kategorie "Laufende EDV-Kosten" automatisch gesetzt.

Eingabe: --account 4930 --category "Laufende EDV-Kosten"
→ OK, Kategorie stimmt mit Konto überein.

Eingabe: --account 4930 --category "Arbeitsmittel"
→ Fehler: Konto 4930 gehört zur Kategorie "Laufende EDV-Kosten", 
  nicht zu "Arbeitsmittel".

Eingabe: --account mein-girokonto --category "Laufende EDV-Kosten"
→ Kein Konto im Kontenrahmen → bisheriges Verhalten, Kategorie wird normal verwendet.
```

### A6: CLI-Befehl `euer list konten`

Neuer Befehl zum Anzeigen der konfigurierten Konten:

```
$ euer list konten

Kontenrahmen (7 Konten konfiguriert):

Laufende EDV-Kosten (Zeile 50, Ausgabe):
  4930  Software / SaaS-Abos
  4940  Hosting & Cloud-Dienste
  4950  IT-Support & Wartung

Arbeitsmittel (Zeile 51, Ausgabe):
  4930  Büromaterial

Rechts- und Steuerberatung, Buchführung (Zeile 46, Ausgabe):
  4400  Rechts- und Beratungskosten

Übrige Betriebsausgaben (Zeile 60, Ausgabe):
  6300  Sonstige betriebliche Aufwendungen

Umsatzsteuerpflichtige Betriebseinnahmen (Zeile 15, Einnahme):
  8400  Erlöse 19% USt
```

Optional mit Filter:

```
$ euer list konten --category "Laufende EDV-Kosten"

Laufende EDV-Kosten (Zeile 50, Ausgabe):
  4930  Software / SaaS-Abos
  4940  Hosting & Cloud-Dienste
  4950  IT-Support & Wartung
```

### A7: Kontenrahmen-Validierung

Beim Laden des Kontenrahmens (und beim Start relevanter Befehle) wird geprüft:

1. **Pflichtfelder** — Jeder Eintrag muss `konto`, `name` und `kategorie`
   enthalten.
2. **Kategorie-Existenz** — Die angegebene `kategorie` muss in der DB
   existieren. Bei ungültiger Kategorie → Warnung auf stderr, Eintrag wird
   übersprungen.
3. **Eindeutigkeit** — `konto` muss innerhalb des Kontenrahmens eindeutig sein.
   Duplikate → Fehler.
4. **Typ-Konsistenz** — Wird bei der Buchung zusätzlich geprüft:
   Expense-Buchung kann nur Konten mit Expense-Kategorie verwenden und
   umgekehrt.

### A8: Kontenrahmen im Import

Der bestehende Import-Befehl (`euer import`) soll Kontonummern im
`account`-Feld erkennen und die Kategorie automatisch auflösen, analog zur
manuellen Buchung (A5). Der Import-Flow nutzt bereits den Service Layer
(Spec 009), so dass die Konten-Auflösung zentral in `create_expense()` /
`create_income()` greift.

### A9: Kontenrahmen-Hilfe bei Fehlern

Wenn eine Buchung ohne Kategorie und ohne erkanntes Konto ausgeführt wird,
soll die Fehlermeldung einen Hinweis geben:

```
Fehler: Kategorie erforderlich.
Verfügbare Kategorien:
  - Laufende EDV-Kosten (Konten: 4930, 4940, 4950)
  - Arbeitsmittel (Konten: 4930)
  - ...
Tipp: Verwende --account <Kontonummer>, um die Kategorie automatisch zu setzen.
```

---

## Implementierungsplan

### Phase 1: Config & Datenhaltung

1. **Dataclass `Konto`** in `euercli/services/models.py` anlegen.
2. **`get_kontenrahmen(config)`** in `euercli/config.py` implementieren.
3. **Unit-Tests** für Config-Parsing (leerer Kontenrahmen, gültige Einträge,
   fehlende Felder, Duplikate).

### Phase 2: Service Layer

4. **`get_konten_for_category()`** in `euercli/services/categories.py`
   implementieren.
5. **`resolve_konto()`** in `euercli/services/categories.py` implementieren.
6. **`create_expense()` / `create_income()` erweitern** — neuer optionaler
   Parameter `config: dict | None = None` für Konten-Auflösung. Wenn ein
   `account`-Wert einem Konto im Kontenrahmen entspricht:
   - Kategorie automatisch setzen
   - Kategorie-Konflikt prüfen
7. **Unit-Tests** für alle Service-Funktionen.

### Phase 3: CLI

8. **`euer list konten`** implementieren (Command + Parser).
9. **`cmd_add_expense` / `cmd_add_income`** — Config an Service-Funktionen
   durchreichen.
10. **Fehlermeldungen verbessern** (A9) — Kontenliste in Kategorie-Fehlern
    einblenden.

### Phase 4: Dokumentation

11. **`docs/USER_GUIDE.md`** — Abschnitt „Kontenrahmen" ergänzen mit
    Konfigurationsbeispiel und Workflow.
12. **`docs/skills/euer-buchhaltung/SKILL.md`** — Konten-Auflösung als
    Buchungsregel dokumentieren.
13. **`DEVELOPMENT.md`** — Spec-Tabelle aktualisieren.

---

## Nicht-Ziele (bewusst ausgeklammert)

- **Schema-Änderung / DB-Tabelle für Konten:** Der Kontenrahmen lebt
  ausschließlich in der Config. Es wird keine neue DB-Tabelle angelegt.
  Begründung: Der Kontenrahmen ist ein Konfigurationsartefakt, kein
  transaktionaler Datensatz. So bleibt die DB portabel und einfach.
- **Automatische SKR-03/04-Vorlagen:** Es wird kein Standard-Kontenrahmen
  ausgeliefert. Falls gewünscht, kann dies als späteres Feature (z.B.
  `euer setup kontenrahmen --template skr03`) ergänzt werden.
- **Kontensalden / Kontoblätter:** Keine Saldenberechnung je Konto.
  Auswertungen pro Konto können als separates Feature (z.B. `euer summary
  --by-konto`) in einer späteren Spec ergänzt werden.
- **Migration bestehender `account`-Werte:** Bestehende Freitext-Werte im
  `account`-Feld werden nicht automatisch auf Kontonummern umgestellt.

---

## Offene Fragen

1. Soll `kontenrahmen` der TOML-Schlüssel sein, oder ist `konten` oder
   `accounts` besser? → Vorschlag: `kontenrahmen` (domänenspezifisch,
   eindeutig, deutsch — konsistent mit der Nutzer-Sprache).
2. Soll das `account`-Feld in der DB bei erkannten Konten die Kontonummer
   oder den Anzeigenamen speichern? → Vorschlag: Die **Kontonummer** (`konto`),
   da diese stabil ist und bei Config-Änderungen nicht bricht.

---

## Beispiel: Vollständiger Workflow

```bash
# 1. Kontenrahmen konfigurieren (in ~/.config/euer/config.toml)
#    → siehe Beispiel oben unter A1

# 2. Konten anzeigen
$ euer list konten
Kontenrahmen (7 Konten konfiguriert):
  Laufende EDV-Kosten:  4930, 4940, 4950
  Arbeitsmittel:        4930
  ...

# 3. Buchung mit Konto (Kategorie wird automatisch aufgelöst)
$ euer add expense --payment-date 2026-02-15 --vendor "Hetzner" \
    --amount 49.90 --account 4940
Ausgabe #42 hinzugefügt: Hetzner 49,90 EUR
  → Konto: 4940 (Hosting & Cloud-Dienste)
  → Kategorie: Laufende EDV-Kosten (Zeile 50)

# 4. Buchung mit Konto + expliziter Kategorie (konsistent → OK)
$ euer add expense --payment-date 2026-02-15 --vendor "GitHub" \
    --amount 3.67 --account 4930 --category "Laufende EDV-Kosten"
Ausgabe #43 hinzugefügt: GitHub 3,67 EUR

# 5. Buchung mit widersprüchlicher Kategorie → Fehler
$ euer add expense --payment-date 2026-02-15 --vendor "GitHub" \
    --amount 3.67 --account 4930 --category "Arbeitsmittel"
Fehler: Konto 4930 gehört zur Kategorie "Laufende EDV-Kosten",
  nicht zu "Arbeitsmittel".

# 6. Buchung ohne Konto → bisheriges Verhalten
$ euer add expense --payment-date 2026-02-15 --vendor "Büro GmbH" \
    --amount 120.00 --category "Arbeitsmittel"
Ausgabe #44 hinzugefügt: Büro GmbH 120,00 EUR

# 7. Konten einer Kategorie abfragen
$ euer list konten --category "Laufende EDV-Kosten"
Laufende EDV-Kosten (Zeile 50, Ausgabe):
  4930  Software / SaaS-Abos
  4940  Hosting & Cloud-Dienste
  4950  IT-Support & Wartung
```
