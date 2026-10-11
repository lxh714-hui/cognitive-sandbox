import pytest

from cognitive_sandbox.application.event_card_loader import EventCardLoader
from cognitive_sandbox.domain.event_card import EventCard


def test_event_card_loader_registers_and_queries_in_memory_cards():
    card = EventCard("power", "停电", "医院停电", "initial", ("doctor",))
    loader = EventCardLoader((card,))

    assert loader.load("power") is card
    assert loader.load("missing") is None

    added = EventCard("alarm", "警报", "警报响起", "reactive")
    loader.register(added)
    assert loader.load("alarm") is added


def test_event_card_loader_rejects_wrong_types_without_changing_cards():
    card = EventCard("power", "停电", "医院停电", "initial")
    loader = EventCardLoader((card,))
    with pytest.raises(TypeError, match="EventCard"):
        loader.register(object())
    with pytest.raises(TypeError, match="event_id"):
        loader.load(42)
    assert loader.load("power") is card
