from __future__ import annotations

from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.validation_result import ValidationResult


class EventCardValidator:
    """Validate event-card shape without changing the input object."""

    def validate(self, card: EventCard) -> ValidationResult:
        if not isinstance(card, EventCard):
            raise TypeError("card must be an EventCard.")
        errors: list[str] = []
        for field_name in ("event_id", "name", "description", "event_type"):
            value = getattr(card, field_name, None)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} must not be empty.")
        for field_name in ("participants", "conditions", "effects"):
            values = getattr(card, field_name, None)
            if not isinstance(values, tuple):
                errors.append(f"{field_name} must be a tuple of non-empty strings.")
            elif any(not isinstance(value, str) or not value.strip() for value in values):
                errors.append(f"{field_name} must contain only non-empty strings.")
        priority = getattr(card, "priority", None)
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
            errors.append("priority must be a non-negative integer.")
        return ValidationResult(not errors, tuple(errors), ())
