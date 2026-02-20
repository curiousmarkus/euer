# 007 - Windows-Kompatibilität

## Status

Offen

## Kontext

Aktuell nutzen reale Anwender nur macOS. Trotzdem soll `euer` technisch sauber auf Windows laufen,
damit Neuinstallationen auf Windows ohne Sonderwissen funktionieren.

**Wichtige Festlegung:** Keine Migration bestehender Windows-Konfigurationen nötig.
Backward-Kompatibilität zu alten Windows-Config-Pfaden ist explizit **out of scope**.

---

## Ziel

`euer` soll auf Windows (PowerShell + Python 3.11+) ohne Code-Workarounds nutzbar sein:

1. Config wird am plattformüblichen Ort gespeichert.
2. Test-Suite läuft isoliert und berührt keine echte User-Config.
3. Doku enthält einen klaren Windows-Installationspfad.

---

## Nicht-Ziele

1. Migration alter Windows-Config-Dateien.
2. Vollständige `make`-Unterstützung auf Windows.
3. Erweiterung um weitere Plattform-spezifische Features.

---

## Problemstellung

### 1. Config-Pfad ist Unix-zentriert (hoch)

**Ist-Zustand:** `euercli/constants.py` nutzt immer `~/.config/euer/config.toml`.  
Auf Windows ist der übliche Ort `%APPDATA%\euer\config.toml`.

### 2. Tests isolieren Home auf Windows nicht korrekt (hoch)

**Ist-Zustand:** `tests/test_cli.py` setzt nur `HOME`.  
Auf Windows verwendet `Path.home()` primär `USERPROFILE`; zusätzlich ist `APPDATA` relevant.

### 3. Entwickler-Doku ist macOS/Linux-zentriert (mittel)

**Ist-Zustand:** README/Makefile zeigen primär `brew`, `make`, `source .venv/bin/activate`.
Für Windows fehlt ein direkter PowerShell-Weg.

---

## Lösungsansatz

### A. Config-Pfad plattformabhängig bestimmen

`CONFIG_PATH` wird aus einer kleinen Helper-Funktion abgeleitet:

```python
import os
import platform
from pathlib import Path


def get_config_path() -> Path:
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "euer" / "config.toml"
        return Path.home() / "AppData" / "Roaming" / "euer" / "config.toml"
    return Path.home() / ".config" / "euer" / "config.toml"
```

### B. Tests Windows-sicher machen

In `tests/test_cli.py` zusätzlich setzen:

```python
self.env["HOME"] = str(self.home)
self.env["USERPROFILE"] = str(self.home)
self.env["APPDATA"] = str(self.home / "AppData" / "Roaming")
```

Zusätzlich Assertions auf Config-Inhalt robust machen:

1. Nicht nur rohe String-Suche auf Pfaden mit Backslashes.
2. TOML parsen und strukturierte Werte prüfen.

### C. Doku ergänzen

README ergänzt um PowerShell-Pendant:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

---

## `platformdirs`: Vor-/Nachteile und Alternativen

### Option 1: Standard-Library (empfohlen)

**Ansatz:** `platform.system()` + `APPDATA`/`Path.home()` manuell.

**Vorteile**
1. Keine neue Dependency.
2. Passt zur Projektphilosophie (leichtgewichtig).
3. Verhalten vollständig unter eigener Kontrolle.

**Nachteile**
1. Plattformdetails müssen selbst gepflegt werden.
2. Potenzielle Edge-Cases (ungewöhnliche Umgebungen) liegen in eigener Verantwortung.

### Option 2: `platformdirs` als feste Dependency

**Ansatz:** `user_config_path("euer") / "config.toml"`.

**Vorteile**
1. Plattformkonventionen sind gut abgedeckt.
2. Weniger eigener OS-spezifischer Code.

**Nachteile**
1. Zusätzliche Laufzeitabhängigkeit.
2. Mehr Pflegeaufwand im Packaging (Versionierung, Security-Updates).

### Option 3: Optionales `platformdirs` mit Fallback

**Ansatz:** `try/except ImportError` und sonst manuell.

**Vorteile**
1. Kann Komfort bieten, ohne hart zu dependencen.

**Nachteile**
1. Nicht-deterministisches Verhalten je nach Umgebung.
2. Testbarkeit und Reproduzierbarkeit werden schlechter.

**Entscheidung für diese Spec:** Option 1 (Standard-Library), kein `platformdirs`.

---

## Akzeptanzkriterien (Definition of Done)

1. Auf Windows wird Config unter `%APPDATA%\euer\config.toml` erzeugt.
2. Auf macOS/Linux bleibt Pfad `~/.config/euer/config.toml`.
3. Test-Suite läuft lokal weiterhin grün.
4. CI enthält einen Windows-Job (`windows-latest`, Python 3.11), der Tests ausführt.
5. README enthält explizite PowerShell-Schritte für Entwicklerinstallation.

---

## Umsetzungsplan

1. [ ] `euercli/constants.py`: `get_config_path()` einführen und `CONFIG_PATH` daraus ableiten.
2. [ ] `tests/test_cli.py`: `USERPROFILE` und `APPDATA` ergänzen.
3. [ ] `tests/test_cli.py`: Config-Assertions robust auf geparste TOML-Daten umstellen.
4. [ ] `README.md`: Windows-PowerShell-Setup ergänzen.
5. [ ] `.github/workflows/*`: Windows-Testjob hinzufügen.

---

## Testplan

### Automatisiert

1. `python -m unittest discover -s tests` auf macOS/Linux.
2. Derselbe Befehl in CI auf `windows-latest`.

### Manuell auf Windows

1. `euer init`
2. `euer setup`
3. `euer config show`
4. Prüfen, dass Pfad unter `%APPDATA%\euer\config.toml` liegt.
