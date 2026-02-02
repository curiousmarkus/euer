from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB_PATH = Path.cwd() / "euer.db"
DEFAULT_EXPORT_DIR = Path.cwd() / "exports"
DEFAULT_USER = "default"
CONFIG_PATH = Path.home() / ".config" / "euer" / "config.toml"
