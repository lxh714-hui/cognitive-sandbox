from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.domain.event_card import EventCard


class EventCardLoader:
    """Load immutable event cards from an in-memory catalog."""

    def __init__(self, cards: Iterable[EventCard] = ()) -> None:
        self._cards: dict[str, EventCard] = {}
        for card in cards:
            self.register(card)

    def register(self, card: EventCard) -> None:
        if not isinstance(card, EventCard):
            raise TypeError("card must be an EventCard.")
        self._cards[card.event_id] = card

    def load(self, event_id: str) -> EventCard | None:
        if not isinstance(event_id, str):
            raise TypeError("event_id must be a string.")
        return self._cards.get(event_id)
