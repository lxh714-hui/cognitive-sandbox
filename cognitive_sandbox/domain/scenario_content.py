from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.world_document import WorldDocument


@dataclass(frozen=True)
class ScenarioContent:
    """Content-layer bundle kept separate from a runtime Scenario."""

    scenario: Scenario
    world_document: WorldDocument | None = None
    character_cards: tuple[CharacterCard, ...] = ()
    event_cards: tuple[EventCard, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, Scenario):
            raise TypeError("scenario must be a Scenario.")
        if self.world_document is not None and not isinstance(self.world_document, WorldDocument):
            raise TypeError("world_document must be a WorldDocument or None.")
        for field_name, expected_type in (
            ("character_cards", CharacterCard),
            ("event_cards", EventCard),
        ):
            values = getattr(self, field_name)
            if isinstance(values, (str, bytes)):
                raise TypeError(f"{field_name} must be a collection.")
            try:
                items = tuple(values)
            except TypeError as error:
                raise TypeError(f"{field_name} must be a collection.") from error
            if any(not isinstance(item, expected_type) for item in items):
                raise TypeError(f"{field_name} must contain only {expected_type.__name__} values.")
            object.__setattr__(self, field_name, items)
