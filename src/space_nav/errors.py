"""Public errors raised by the navigation foundation."""

from __future__ import annotations


class ScenarioValidationError(ValueError):
    """A scenario value is missing, malformed, or physically invalid."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.message = message
        self.field = field
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.field}: {self.message}" if self.field else self.message


class EphemerisError(Exception):
    """Raised when SPICE initialization, time conversion, or state lookup fails."""


class TransferSearchError(Exception):
    """Raised when a complete impulsive-transfer search cannot be returned."""


class TrajectoryRefinementError(Exception):
    """Raised when physical trajectory refinement cannot return a result."""
