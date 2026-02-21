# Beleg-Management - Spezifikation

## Status
Implementiert (2026-01-31)

## Zusammenfassung

Konfigurierbare Beleg-Pfade mit Validierung und Hilfsbefehlen.
Belege werden in Jahres-Unterordnern organisiert und mit Transaktionen verlinkt.

**Autor:** Markus Keller  
**Zielgruppe:** Coding Agent / LLM  
**Stand:** 2026-01-31

---

## Kontext

### Ist-Zustand

- Belege liegen in Dropbox: 
  - Ausgaben: `~/Dropbox/Beispielunternehmen/Ausgaben-Belege/`
  - Einnahmen: `~/Dropbox/Beispielunternehmen/Einnahmen-Belege/`
- Struktur: `<base>/<Jahr>/YYYYMMDD_Vendor.pdf`
- DB speichert nur `receipt_name` (Dateiname ohne Pfad)
- Keine Validierung ob Beleg existiert

### Soll-Zustand

- Config-Datei definiert Basis-Pfade
- CLI warnt bei fehlenden Belegen
- Commands zum Prüfen und Öffnen von Belegen

---

## Anforderungen

### Funktional

1. **Config-Datei** (`~/.config/euer/config.toml`)
   - Speichert Basis-Pfade für Ausgaben- und Einnahmen-Belege
   - Wird bei Bedarf automatisch erstellt (mit Defaults)

2. **Pfad-Auflösung**
   - Jahres-Unterordner basierend auf Transaktionsdatum
   - Fallback auf Basis-Ordner wenn nicht im Jahres-Ordner

3. **Validierung bei add/update**
   - Warnung (nicht Fehler) wenn Beleg nicht gefunden
   - Zeigt geprüfte Pfade an

4. **Neue Commands**
   - `euer receipt check` - Prüft alle Transaktionen
   - `euer receipt open <id>` - Öffnet Beleg in Default-App
   - `euer config show` - Zeigt aktuelle Konfiguration

### Nicht-Funktional

- Config optional (CLI funktioniert ohne)
- TOML-Format (Standard-Library `tomllib` ab Python 3.11)
- Keine neuen Dependencies

---

## Config-Datei

### Speicherort

`~/.config/euer/config.toml`

### Format

```toml
[receipts]
expenses = "~/Dropbox/Beispielunternehmen/Ausgaben-Belege"
income = "~/Dropbox/Beispielunternehmen/Einnahmen-Belege"
```

### Defaults (wenn keine Config existiert)

```toml
[receipts]
expenses = ""  # Leer = keine Beleg-Prüfung
income = ""
```

### Laden der Config

```python
import tomllib  # Python 3.11+
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "euer" / "config.toml"

def load_config() -> dict:
    """Lädt Config, gibt leeres Dict zurück wenn nicht vorhanden."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)
```

---

## Pfad-Auflösung

### Algorithmus

```python
def resolve_receipt_path(
    receipt_name: str,
    date: str,  # YYYY-MM-DD
    receipt_type: str,  # 'expenses' oder 'income'
    config: dict
) -> tuple[Path | None, list[Path]]:
    """
    Sucht Beleg-Datei.
    
    Returns:
        (found_path, checked_paths)
        found_path ist None wenn nicht gefunden
    """
    base = config.get("receipts", {}).get(receipt_type, "")
    if not base:
        return (None, [])
    
    base_path = Path(base)
    year = date[:4]  # "2026" aus "2026-01-15"
    
    # Reihenfolge: Erst Jahres-Ordner, dann Basis
    candidates = [
        base_path / year / receipt_name,
        base_path / receipt_name,
    ]
    
    for path in candidates:
        if path.exists():
            return (path, candidates)
    
    return (None, candidates)
```

### Beispiele

| Transaktion | receipt_name | Geprüfte Pfade |
|-------------|--------------|----------------|
| 2026-01-15 Expense | `2026-01-15_Render.pdf` | 1. `.../Ausgaben-Belege/2026/2026-01-15_Render.pdf` |
| | | 2. `.../Ausgaben-Belege/2026-01-15_Render.pdf` |
| 2025-03-01 Income | `Rechnung.pdf` | 1. `.../Einnahmen-Belege/2025/Rechnung.pdf` |
| | | 2. `.../Einnahmen-Belege/Rechnung.pdf` |

---

## CLI-Erweiterungen

### Änderungen an bestehenden Commands

#### `euer add expense/income`

Nach erfolgreichem Insert, wenn `--receipt` angegeben:

```
Ausgabe #5 hinzugefügt: Render -15.50 EUR
⚠ Beleg '2026-02-01_Render.pdf' nicht gefunden:
  - /path/to/Ausgaben-Belege/2026/2026-02-01_Render.pdf
  - /path/to/Ausgaben-Belege/2026-02-01_Render.pdf
```

- Warnung nur wenn Config vorhanden UND Pfad konfiguriert
- Keine Warnung wenn `receipt_name` leer
- Exit-Code bleibt 0 (Warnung, kein Fehler)

#### `euer update expense/income`

Analog zu add: Warnung bei fehlendem Beleg.

---

### Neue Commands

#### `euer receipt check`

Prüft alle Transaktionen auf fehlende Belege.

```bash
euer receipt check [--year 2026] [--type expense|income]
```

**Output:**

```
Beleg-Prüfung 2026
==================

Fehlende Belege (Ausgaben):
  #12  2026-01-15  Render      2026-01-15_Render.pdf
  #15  2026-01-20  OpenAI      (kein Beleg)

Fehlende Belege (Einnahmen):
  (keine)

Zusammenfassung:
  Ausgaben: 2 von 10 ohne gültigen Beleg
  Einnahmen: 0 von 3 ohne gültigen Beleg
```

**Verhalten:**
- Ohne Config: Fehler mit Hinweis auf `euer config show`
- Mit `--type`: Nur diesen Typ prüfen
- Exit-Code: 0 wenn alle Belege OK, 1 wenn welche fehlen

---

#### `euer receipt open <id>`

Öffnet den Beleg einer Transaktion.

```bash
euer receipt open 12 [--table expenses|income]  # Default: expenses
```

**Verhalten:**
- Sucht Beleg mit `resolve_receipt_path()`
- Öffnet mit `open` (macOS) / `xdg-open` (Linux)
- Fehler wenn Beleg nicht gefunden

**Beispiel:**
```
$ euer receipt open 12
Öffne: /path/to/Ausgaben-Belege/2026/2026-01-15_Render.pdf
```

---

#### `euer config show`

Zeigt aktuelle Konfiguration.

```bash
euer config show
```

**Output:**

```
EÜR Konfiguration
=================

Config-Datei: ~/.config/euer/config.toml

[receipts]
  expenses = ~/Dropbox/Beispielunternehmen/Ausgaben-Belege
  income   = ~/Dropbox/Beispielunternehmen/Einnahmen-Belege
```

Oder wenn keine Config:

```
EÜR Konfiguration
=================

Config-Datei: ~/.config/euer/config.toml (nicht vorhanden)

Erstelle Config mit:

  mkdir -p ~/.config/euer
  cat > ~/.config/euer/config.toml << 'EOF'
  [receipts]
  expenses = "/pfad/zu/ausgaben-belege"
  income = "/pfad/zu/einnahmen-belege"
  EOF
```

---

## Implementierungsreihenfolge

1. [x] Config-Laden implementieren (`load_config()`)
2. [x] Pfad-Auflösung implementieren (`resolve_receipt_path()`)
3. [x] `config show` Command
4. [x] Warnung in `add expense/income` einbauen
5. [x] Warnung in `update expense/income` einbauen
6. [x] `receipt check` Command
7. [x] `receipt open` Command
8. [x] README.md aktualisieren

---

## Referenzen

- Python tomllib: https://docs.python.org/3/library/tomllib.html
- XDG Base Directory: https://specifications.freedesktop.org/basedir-spec/
- Spec 001 (Init): `specs/001-init.md`
