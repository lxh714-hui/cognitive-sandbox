from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.valid, bool):
            raise TypeError("valid must be a boolean.")
        errors = tuple(self.errors)
        warnings = tuple(self.warnings)
        if any(not isinstance(item, str) or not item.strip() for item in (*errors, *warnings)):
            raise ValueError("errors and warnings must contain non-empty strings.")
        if self.valid and errors:
            raise ValueError("a valid result cannot contain errors.")
        if not self.valid and not errors:
            raise ValueError("an invalid result must contain at least one error.")
        object.__setattr__(self, "errors", errors)
        object.__setattr__(self, "warnings", warnings)
