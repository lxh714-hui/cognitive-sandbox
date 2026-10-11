from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.domain.character_card import CharacterCard


class CharacterCardLoader:
    """Load important character cards from an in-memory catalog."""

    def __init__(self, cards: Iterable[CharacterCard] = ()) -> None:
        self._cards: dict[str, CharacterCard] = {}
        for card in cards:
            self.register(card)

    def register(self, card: CharacterCard) -> None:
        if not isinstance(card, CharacterCard):
            raise TypeError("card must be a CharacterCard.")
        self._cards[card.character_id] = card

    def load(self, character_id: str) -> CharacterCard | None:
        if not isinstance(character_id, str):
            raise TypeError("character_id must be a string.")
        return self._cards.get(character_id)
