from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB_PATH = PROJECT_ROOT / "euer.db"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "exports"
DEFAULT_USER = "markus"
CONFIG_PATH = Path.home() / ".config" / "euer" / "config.toml"
