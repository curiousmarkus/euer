"""Sammel- und Einstiegsmodul für CLI-Integrationstests.

Die Tests wurden modularisiert in themenspezifische Testdateien:
- test_cli_core.py: Core, Setup, Config, Audit-Log, Query
- test_cli_expenses.py: Ausgaben CRUD, Tabellen, Reverse-Charge
- test_cli_income.py: Einnahmen CRUD, Tabellen, USt-Klassifikation
- test_cli_private_transfers.py: Privateinlagen/-entnahmen, Reconcile, Private-Summary
- test_cli_receipts.py: Belegprüfung, Belegpfade, Warnungen
- test_cli_reports.py: EÜR-Summary, UStVA-Report, Bewirtung
- test_cli_import_export.py: CSV-/XLSX-Export, CSV-/JSONL-Import, Migrationen

Dieses Modul ermöglicht weiterhin die Ausführung aller CLI-Tests via:
    python -m unittest tests/test_cli.py
"""

import unittest
from pathlib import Path


def load_tests(
    loader: unittest.TestLoader,
    standard_tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    # Bei 'unittest discover' (pattern is not None) wird eine leere Suite zurückgegeben,
    # da discover bereits alle test_cli_*.py einzeln findet.
    if pattern is not None:
        return unittest.TestSuite()

    # Bei direkter Ausführung (python -m unittest tests/test_cli.py):
    cli_dir = Path(__file__).parent
    return loader.discover(start_dir=str(cli_dir), pattern="test_cli_*.py")


if __name__ == "__main__":
    unittest.main()
