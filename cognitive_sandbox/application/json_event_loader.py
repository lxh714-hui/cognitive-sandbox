from __future__ import annotations

from pathlib import Path

from cognitive_sandbox.application.event_card_validator import EventCardValidator
from cognitive_sandbox.application.json_world_loader import _read_json_object, _require_fields
from cognitive_sandbox.domain.event_card import EventCard


class JsonEventLoader:
    REQUIRED_FIELDS = frozenset(
        {
            "event_id", "name", "description", "event_type", "participants",
            "conditions", "effects", "priority",
        }
    )

    def __init__(self, validator: EventCardValidator | None = None) -> None:
        self._validator = validator or EventCardValidator()

    def load(self, path: str | Path) -> EventCard:
        data = _read_json_object(path, "event")
        _require_fields(data, self.REQUIRED_FIELDS, "event")
        try:
            card = EventCard(
                event_id=data["event_id"],
                name=data["name"],
                description=data["description"],
                event_type=data["event_type"],
                participants=data["participants"],
                conditions=data["conditions"],
                effects=data["effects"],
                priority=data["priority"],
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid event card in {path}: {error}") from error
        result = self._validator.validate(card)
        if not result.valid:
            raise ValueError("event card validation failed: " + "; ".join(result.errors))
        return card
