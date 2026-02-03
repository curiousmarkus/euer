from __future__ import annotations


class EuerError(Exception):
    """Base error for service layer failures."""

    def __init__(self, message: str, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ValidationError(EuerError):
    """Input or domain validation error."""


class RecordNotFoundError(EuerError):
    """Raised when a database record is missing."""
