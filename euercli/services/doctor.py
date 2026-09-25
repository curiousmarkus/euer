"""Diagnosedienst für System, Umgebung, Datenbank und Konfiguration (Spec 019)."""

import os
import shutil
import sqlite3
import sys
from pathlib import Path

from .. import VERSION
from ..config import load_config
from ..constants import CONFIG_PATH, DEFAULT_EXPORT_DIR
from ..migrations import get_migration_plan
from ..project_config import get_project_db_path, project_config_path


def detect_install_source(python_exe: str, active_bin: str | None) -> str:
    """Ermittelt den vermuteten Installationstyp von euer."""
    exe_str = (python_exe or "").lower()
    bin_str = (active_bin or "").lower()

    if "/opt/homebrew" in bin_str or "/usr/local/cellar" in bin_str or "homebrew" in bin_str:
        return "homebrew"
    if "/opt/homebrew" in exe_str or "/usr/local/cellar" in exe_str or "homebrew" in exe_str:
        return "homebrew"

    if "pipx" in exe_str or "pipx" in bin_str:
        return "pipx"

    # Prüfe auf Entwickler-/Editable-Installation
    repo_root = Path(__file__).resolve().parent.parent.parent
    if (repo_root / ".git").is_dir() or (repo_root / "pyproject.toml").is_file():
        # Wenn active_bin oder sys.prefix auf dieses Repo verweist
        if str(repo_root) in exe_str or str(repo_root) in bin_str:
            return "editable"

    # Virtuelle Umgebung (venv / virtualenv)
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return "venv"

    return "system"


def check_path_binaries(active_binary: str | None) -> list[dict]:
    """Findet alle ausführbaren Dateien namens 'euer' im PATH."""
    path_env = os.environ.get("PATH", "")
    target_names = ["euer.exe", "euer.cmd", "euer.bat", "euer"] if sys.platform == "win32" else ["euer"]

    found: list[dict] = []
    seen_real_paths: set[str] = set()

    for folder in path_env.split(os.pathsep):
        folder_clean = folder.strip('"')
        if not folder_clean:
            continue
        folder_path = Path(folder_clean)
        if not folder_path.is_dir():
            continue

        for target in target_names:
            candidate = folder_path / target
            if candidate.is_file() and os.access(candidate, os.X_OK):
                try:
                    real = str(candidate.resolve())
                except OSError:
                    real = str(candidate)

                if real not in seen_real_paths:
                    seen_real_paths.add(real)
                    is_act = (
                        str(candidate) == active_binary
                        or real == active_binary
                        or (active_binary and Path(active_binary).resolve() == Path(real))
                    )
                    found.append(
                        {
                            "path": str(candidate),
                            "real_path": real,
                            "is_active": bool(is_act),
                        }
                    )

    # Falls das aktive Binary noch nicht als active markiert wurde (z.B. erster Eintrag)
    if found and not any(f["is_active"] for f in found):
        found[0]["is_active"] = True

    return found


def diagnose_database(db_path: Path, source: str) -> dict:
    """Führt eine sichere, rein lesende Diagnose der Zieldatenbank durch."""
    resolved_path = str(db_path.resolve())

    if not db_path.is_file():
        return {
            "path": resolved_path,
            "source": source,
            "exists": False,
            "status": "not_found",
            "size_bytes": None,
            "readable": False,
            "writable": False,
            "schema_version": None,
            "target_schema": None,
            "pending_migrations": [],
            "quick_check": None,
            "error": None,
        }

    size_bytes = db_path.stat().st_size
    readable = os.access(db_path, os.R_OK)
    writable = os.access(db_path, os.W_OK)

    if not readable:
        return {
            "path": resolved_path,
            "source": source,
            "exists": True,
            "status": "error",
            "size_bytes": size_bytes,
            "readable": False,
            "writable": writable,
            "schema_version": None,
            "target_schema": None,
            "pending_migrations": [],
            "quick_check": None,
            "error": "Keine Leseberechtigung für die Datenbankdatei.",
        }

    # Nur lesende Verbindung öffnen (kein WAL-Write, keine Dateierzeugung)
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            # Schneller Integritäts-Check
            qc_rows = conn.execute("PRAGMA quick_check").fetchall()
            quick_check_res = qc_rows[0][0] if qc_rows else "unknown"

            # Schema- & Migrationsstand prüfen
            current_schema, target_schema, pending, legacy_stamps = get_migration_plan(conn)
            pending_names = [m.id for m, _ in pending]

            is_ok = quick_check_res == "ok" and not pending_names
            status = "ok" if is_ok else ("error" if quick_check_res != "ok" else "warning")

            return {
                "path": resolved_path,
                "source": source,
                "exists": True,
                "status": status,
                "size_bytes": size_bytes,
                "readable": True,
                "writable": writable,
                "schema_version": current_schema,
                "target_schema": target_schema,
                "pending_migrations": pending_names,
                "quick_check": quick_check_res,
                "error": None,
            }
        finally:
            conn.close()
    except Exception as exc:
        return {
            "path": resolved_path,
            "source": source,
            "exists": True,
            "status": "error",
            "size_bytes": size_bytes,
            "readable": readable,
            "writable": writable,
            "schema_version": None,
            "target_schema": None,
            "pending_migrations": [],
            "quick_check": None,
            "error": str(exc),
        }


def diagnose_config(project_root: Path) -> dict:
    """Prüft System-Config, Projekt-Config und konfigurierte Arbeitsverzeichnisse."""
    # 1. System Config
    sys_cfg_exists = CONFIG_PATH.is_file()
    sys_cfg_valid = True
    sys_cfg_error = None
    loaded_cfg = {}

    if sys_cfg_exists:
        try:
            loaded_cfg = load_config()
        except Exception as exc:
            sys_cfg_valid = False
            sys_cfg_error = str(exc)

    # 2. Projekt Config
    proj_cfg_file = project_config_path(project_root)
    proj_cfg_exists = proj_cfg_file.is_file()
    proj_cfg_valid = True
    proj_cfg_error = None
    proj_db_val = None

    if proj_cfg_exists:
        try:
            proj_db_val = str(get_project_db_path(project_root)) if get_project_db_path(project_root) else None
        except Exception as exc:
            proj_cfg_valid = False
            proj_cfg_error = str(exc)

    # 3. Verzeichnisse prüfen
    receipts_cfg = loaded_cfg.get("receipts", {}).get("root") if sys_cfg_valid else None
    receipts_info = {
        "configured": receipts_cfg,
        "exists": False,
        "readable": False,
        "writable": False,
    }
    if receipts_cfg:
        r_path = Path(receipts_cfg).expanduser().resolve()
        receipts_info["exists"] = r_path.is_dir()
        receipts_info["readable"] = os.access(r_path, os.R_OK) if r_path.exists() else False
        receipts_info["writable"] = os.access(r_path, os.W_OK) if r_path.exists() else False

    exports_cfg = loaded_cfg.get("exports", {}).get("directory") if sys_cfg_valid else None
    effective_export = exports_cfg or str(DEFAULT_EXPORT_DIR)
    exp_path = Path(effective_export).expanduser().resolve()
    exports_info = {
        "configured": effective_export,
        "exists": exp_path.is_dir(),
        "readable": os.access(exp_path, os.R_OK) if exp_path.exists() else False,
        "writable": os.access(exp_path, os.W_OK) if exp_path.exists() else False,
    }

    return {
        "system_config": {
            "path": str(CONFIG_PATH),
            "exists": sys_cfg_exists,
            "valid": sys_cfg_valid,
            "error": sys_cfg_error,
        },
        "project_config": {
            "path": str(proj_cfg_file),
            "exists": proj_cfg_exists,
            "valid": proj_cfg_valid,
            "db_path": proj_db_val,
            "error": proj_cfg_error,
        },
        "directories": {
            "receipts_root": receipts_info,
            "exports_directory": exports_info,
        },
    }


def diagnose_features() -> dict:
    """Prüft optionale Abhängigkeiten wie openpyxl."""
    try:
        import openpyxl

        version = getattr(openpyxl, "__version__", "vorhanden")
        return {
            "openpyxl": {
                "available": True,
                "version": version,
            }
        }
    except ImportError:
        return {
            "openpyxl": {
                "available": False,
                "version": None,
            }
        }


def run_doctor(project_root: Path, db_path: Path, source: str) -> dict:
    """Führt die vollständige System- und Pre-Flight-Diagnose aus."""
    py_executable = sys.executable
    py_version = sys.version.split()[0]
    active_binary = shutil.which("euer") or sys.argv[0]

    try:
        active_bin_real = str(Path(active_binary).resolve())
    except OSError:
        active_bin_real = active_binary

    install_source = detect_install_source(py_executable, active_bin_real)
    path_duplicates = check_path_binaries(active_bin_real)

    db_diag = diagnose_database(db_path, source)
    cfg_diag = diagnose_config(project_root)
    features_diag = diagnose_features()

    recommendations: list[str] = []

    # 1. Empfehlungen zu PATH-Kollisionen
    if len(path_duplicates) > 1:
        first = path_duplicates[0]["path"]
        others = [p["path"] for p in path_duplicates[1:]]
        other_str = ", ".join(others)

        if "pipx" in first and any("homebrew" in o or "cellar" in o for o in others):
            hint = "Nutze 'pipx uninstall euer', um stattdessen die Homebrew-Installation zu aktivieren."
        elif "homebrew" in first and any("pipx" in o for o in others):
            hint = "Die ältere pipx-Installation kann mit 'pipx uninstall euer' entfernt werden."
        else:
            hint = "Prüfe die Reihenfolge der Verzeichnisse in deiner $PATH-Umgebungsvariablen."

        recommendations.append(
            f"Kollidierende Installationen im PATH gefunden: '{first}' verdeckt {other_str}. {hint}"
        )

    # 2. Empfehlungen zur Datenbank
    if not db_diag["exists"]:
        recommendations.append(
            f"Keine Datenbank gefunden unter '{db_diag['path']}'. "
            "Führe 'euer init --create' aus, um eine neue Datenbank anzulegen, "
            "oder verbinde eine vorhandene DB mit 'euer --db PFAD init --save-db-path'."
        )
    elif db_diag["error"]:
        recommendations.append(
            f"Datenbank-Fehler aufgetreten: {db_diag['error']}. Bitte Datenbank und Berechtigungen prüfen!"
        )
    elif db_diag["quick_check"] != "ok":
        recommendations.append(
            f"Datenbank-Integritätsprüfung meldet Auffälligkeiten: {db_diag['quick_check']}. Bitte Backup prüfen!"
        )
    elif db_diag["pending_migrations"]:
        pending_list = ", ".join(db_diag["pending_migrations"])
        recommendations.append(
            f"Die Datenbank hat {len(db_diag['pending_migrations'])} ausstehende Migration(en): {pending_list}. "
            "Führe 'euer init' aus, um das Schema zu aktualisieren."
        )

    # 3. Empfehlungen zur Konfiguration
    if not cfg_diag["system_config"]["valid"]:
        recommendations.append(
            f"Syntaxfehler in System-Config '{cfg_diag['system_config']['path']}': "
            f"{cfg_diag['system_config']['error']}. Bitte Datei manuell korrigieren."
        )
    if not cfg_diag["project_config"]["valid"]:
        recommendations.append(
            f"Fehler in Projekt-Config '{cfg_diag['project_config']['path']}': "
            f"{cfg_diag['project_config']['error']}. Bitte Datei überprüfen."
        )

    # 4. Empfehlungen zu Verzeichnissen
    exp_info = cfg_diag["directories"]["exports_directory"]
    if exp_info["exists"] and not exp_info["writable"]:
        recommendations.append(
            f"Export-Verzeichnis '{exp_info['configured']}' ist nicht beschreibbar."
        )

    rec_info = cfg_diag["directories"]["receipts_root"]
    if rec_info["configured"] and rec_info["exists"] and not rec_info["readable"]:
        recommendations.append(
            f"Belege-Verzeichnis '{rec_info['configured']}' ist nicht lesbar."
        )

    # 5. Empfehlungen zu Features (openpyxl)
    if not features_diag["openpyxl"]["available"]:
        if install_source == "pipx":
            cmd_hint = "pipx inject euer openpyxl"
        elif install_source == "homebrew":
            cmd_hint = "pipx install 'euer[xlsx]' oder in einem virtuellen Python-Environment ausführen"
        else:
            cmd_hint = "pip install openpyxl"
        recommendations.append(
            f"XLSX-Export ist nicht verfügbar (openpyxl fehlt). Nachinstallieren mit: {cmd_hint}"
        )

    # Status-Ermittlung
    if (
        (db_diag["exists"] and (db_diag["error"] or db_diag["quick_check"] != "ok"))
        or not cfg_diag["system_config"]["valid"]
        or not cfg_diag["project_config"]["valid"]
    ):
        overall_status = "error"
    elif (
        not db_diag["exists"]
        or bool(db_diag["pending_migrations"])
        or len(path_duplicates) > 1
        or not features_diag["openpyxl"]["available"]
        or not cfg_diag["system_config"]["exists"]
        or (exp_info["exists"] and not exp_info["writable"])
        or (rec_info["configured"] and rec_info["exists"] and not rec_info["readable"])
    ):
        overall_status = "warning"
    else:
        overall_status = "ok"

    return {
        "status": overall_status,
        "version": VERSION,
        "python": {
            "version": py_version,
            "executable": py_executable,
            "platform": sys.platform,
        },
        "binary": {
            "active": active_binary,
            "real_path": active_bin_real,
            "install_source": install_source,
        },
        "path_duplicates": path_duplicates,
        "database": db_diag,
        "config": cfg_diag,
        "features": features_diag,
        "recommendations": recommendations,
    }
