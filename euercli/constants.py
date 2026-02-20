import os
import platform
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB_PATH = Path.cwd() / "euer.db"
DEFAULT_EXPORT_DIR = Path.cwd() / "exports"
DEFAULT_USER = "default"


def get_config_path() -> Path:
    """Liefert den plattformüblichen Pfad für die Konfigurationsdatei."""
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "euer" / "config.toml"
        return Path.home() / "AppData" / "Roaming" / "euer" / "config.toml"
    return Path.home() / ".config" / "euer" / "config.toml"


CONFIG_PATH = get_config_path()
