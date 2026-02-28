from __future__ import annotations


class EuerError(Exception):
    """Basisfehler für Service-Layer-Fehler."""

    def __init__(self, message: str, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ValidationError(EuerError):
    """Fehler bei Eingabe- oder Domänenvalidierung."""


class RecordNotFoundError(EuerError):
    """Wird ausgelöst, wenn ein Datensatz nicht gefunden wird."""
