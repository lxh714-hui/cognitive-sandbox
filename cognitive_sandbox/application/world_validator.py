from __future__ import annotations

from cognitive_sandbox.domain.validation_result import ValidationResult
from cognitive_sandbox.domain.world_document import WorldDocument


class WorldValidator:
    """Validate world-document structure without changing the document."""

    def validate(self, document: WorldDocument) -> ValidationResult:
        if not isinstance(document, WorldDocument):
            raise TypeError("document must be a WorldDocument.")
        errors: list[str] = []
        for field_name in ("world_id", "name", "description"):
            value = getattr(document, field_name, None)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} must not be empty.")
        for field_name in ("history", "rules"):
            values = getattr(document, field_name, None)
            if not isinstance(values, tuple):
                errors.append(f"{field_name} must be a tuple of non-empty strings.")
            elif any(not isinstance(item, str) or not item.strip() for item in values):
                errors.append(f"{field_name} must contain only non-empty strings.")
        return ValidationResult(not errors, tuple(errors), ())
