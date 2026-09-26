"""CLI-Command für 'euer doctor' (Spec 019)."""

import json
import sys
from pathlib import Path

from ..services.doctor import run_doctor


def cmd_doctor(args) -> None:
    """Führt eine Diagnose des Gesamtsystems durch und gibt die Ergebnisse aus."""
    source = (
        "--db"
        if getattr(args, "is_explicit_db", False)
        else "Projekt-Config"
        if getattr(args, "db_from_project_config", False)
        else "Standard"
    )

    project_root = getattr(args, "project_root", Path.cwd())
    db_path = Path(args.db)

    report = run_doctor(project_root=project_root, db_path=db_path, source=source)

    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report["status"] == "error":
            sys.exit(1)
        sys.exit(0)

    # Formatierte Terminal-Ausgabe
    print("=== EÜR Doctor: System- und Umgebungsdiagnose ===")
    print()

    # 1. Laufzeitumgebung
    print("Laufzeitumgebung:")
    print(f"  Version:            {report['version']}")
    py = report["python"]
    print(f"  Python:             {py['version']} ({py['executable']})")
    bin_info = report["binary"]
    print(f"  Aktives Binary:     {bin_info['active']} (Quelle: {bin_info['install_source']})")

    dups = report["path_duplicates"]
    if len(dups) <= 1:
        print("  PATH-Prüfung:       [✓] Keine konkurrierenden euer-Binaries im PATH")
    else:
        print(f"  PATH-Prüfung:       [⚠] {len(dups)} Installationen im PATH gefunden:")
        for idx, d in enumerate(dups, 1):
            mark = " (aktiv)" if d["is_active"] else ""
            print(f"                      {idx}. {d['path']}{mark}")
    print()

    skill = report["skill"]
    print("Buchhaltungs-Skill:")
    print(f"  Bestätigte Version: {skill['confirmed_version'] or '(keine)'}")
    print(f"  Erwartete Version:  {skill['expected_version'] or '(nicht lesbar)'}")
    print(f"  Bundle-Pfad:        {skill['bundle_path']}")
    print(f"  Prüfstatus:         {skill['status']}")
    print()

    # 2. Datenbank
    db = report["database"]
    print("Datenbank:")
    print(f"  Pfad:               {db['path']} (Quelle: {db['source']})")
    if not db["exists"]:
        print("  Status:             [⚠] Nicht gefunden (noch nicht initialisiert)")
    elif db["error"]:
        print(f"  Status:             [✗] Fehler: {db['error']}")
    else:
        size_kb = (db["size_bytes"] or 0) / 1024
        perm = []
        if db["readable"]:
            perm.append("lesbar")
        if db["writable"]:
            perm.append("schreibbar")
        perm_str = ", ".join(perm) if perm else "keine Berechtigungen"
        print(f"  Status:             [✓] Vorhanden ({size_kb:.1f} KB, {perm_str})")

        if db["pending_migrations"]:
            pending_str = ", ".join(db["pending_migrations"])
            print(
                f"  Schemastand:        [⚠] {db['schema_version']} "
                f"({len(db['pending_migrations'])} ausstehend: {pending_str})"
            )
        else:
            print(f"  Schemastand:        [✓] {db['schema_version']} (aktuell)")

        if db["quick_check"] == "ok":
            print("  Integritätsprüfung: [✓] ok (PRAGMA quick_check)")
        else:
            print(f"  Integritätsprüfung: [✗] {db['quick_check']}")
    print()

    # 3. Konfiguration & Pfade
    cfg = report["config"]
    sys_cfg = cfg["system_config"]
    proj_cfg = cfg["project_config"]
    dirs = cfg["directories"]

    print("Konfiguration & Pfade:")
    if not sys_cfg["exists"]:
        print(f"  System-Config:      [⚠] {sys_cfg['path']} (nicht vorhanden)")
    elif not sys_cfg["valid"]:
        print(f"  System-Config:      [✗] {sys_cfg['path']} (Syntaxfehler: {sys_cfg['error']})")
    else:
        print(f"  System-Config:      [✓] {sys_cfg['path']} (vorhanden, gültig)")

    if proj_cfg["exists"]:
        if proj_cfg["valid"]:
            print(
                f"  Projekt-Config:     [✓] {proj_cfg['path']} (db: {proj_cfg['db_path'] or 'keine'})"
            )
        else:
            print(f"  Projekt-Config:     [✗] {proj_cfg['path']} (Fehler: {proj_cfg['error']})")

    rec = dirs["receipts_root"]
    if rec["configured"]:
        if rec["exists"]:
            rec_perm = (
                "schreibbar"
                if rec["writable"]
                else ("lesbar" if rec["readable"] else "eingeschränkt")
            )
            print(f"  Belege-Root:        [✓] {rec['configured']} ({rec_perm})")
        else:
            print(f"  Belege-Root:        [⚠] {rec['configured']} (nicht gefunden)")

    exp = dirs["exports_directory"]
    if exp["exists"]:
        exp_perm = (
            "schreibbar" if exp["writable"] else ("lesbar" if exp["readable"] else "eingeschränkt")
        )
        print(f"  Exporte:            [✓] {exp['configured']} ({exp_perm})")
    else:
        print(f"  Exporte:            [⚠] {exp['configured']} (Ordner wird bei Export erzeugt)")
    print()

    # 4. Optionale Features
    feat = report["features"]
    xl = feat["openpyxl"]
    print("Optionale Features:")
    if xl["available"]:
        print(f"  Excel-Export (XLSX): [✓] Verfügbar (openpyxl {xl['version']})")
    else:
        print("  Excel-Export (XLSX): [⚠] Nicht verfügbar (openpyxl fehlt)")
    print()

    # 5. Empfehlungen
    recs = report["recommendations"]
    if recs:
        print("Empfehlungen & Nächste Schritte:")
        for r in recs:
            print(f"  • {r}")
        print()

    # Gesamtstatus
    st_symbol = {"ok": "[✓] OK", "warning": "[⚠] WARNUNG", "error": "[✗] FEHLER"}
    print(f"Gesamtstatus: {st_symbol.get(report['status'], report['status'].upper())}")

    if report["status"] == "error":
        sys.exit(1)
    sys.exit(0)
