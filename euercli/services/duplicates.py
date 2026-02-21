from __future__ import annotations

from enum import Enum


class DuplicateAction(str, Enum):
    """Steuert das Verhalten bei erkanntem Duplikat."""

    RAISE = "raise"
    SKIP = "skip"
