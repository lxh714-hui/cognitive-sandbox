from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.world_document import WorldDocument


def test_event_card_creation_and_immutable_collections():
    participants = ["doctor", "player"]
    conditions = ["night"]
    effects = ["hospital_dark"]
    card = EventCard(
        "hospital_power_failure",
        "医院停电",
        "医院备用电源即将耗尽",
        "initial",
        participants,
        conditions,
        effects,
        1,
    )
    participants.append("soldier")
    conditions.clear()
    effects.append("panic")

    assert card.participants == ("doctor", "player")
    assert card.conditions == ("night",)
    assert card.effects == ("hospital_dark",)
    assert card.priority == 1
    with pytest.raises(FrozenInstanceError):
        card.name = "其他事件"


def test_event_card_rejects_invalid_fields_and_collection_formats():
    with pytest.raises(ValueError, match="event_id"):
        EventCard("", "事件", "描述", "initial")
    with pytest.raises(ValueError, match="name"):
        EventCard("event", " ", "描述", "initial")
    with pytest.raises(ValueError, match="event_type"):
        EventCard("event", "事件", "描述", "")
    with pytest.raises(TypeError, match="participants"):
        EventCard("event", "事件", "描述", "initial", participants="doctor")
    with pytest.raises(ValueError, match="conditions"):
        EventCard("event", "事件", "描述", "initial", conditions=("",))
    with pytest.raises(TypeError, match="effects"):
        EventCard("event", "事件", "描述", "initial", effects=None)
    with pytest.raises(ValueError, match="priority"):
        EventCard("event", "事件", "描述", "initial", priority=-1)
    with pytest.raises(ValueError, match="priority"):
        EventCard("event", "事件", "描述", "initial", priority=True)


def test_scenario_content_bundles_event_and_reference_data_without_runtime_changes():
    scenario = Scenario("demo", "Demo", "Description", {"seed": 1}, ())
    document = WorldDocument("world", "World", "Description")
    character = CharacterCard("doctor", "医生")
    event = EventCard("event", "停电", "医院停电", "initial")
    content = ScenarioContent(scenario, document, [character], [event])

    assert content.scenario is scenario
    assert content.world_document is document
    assert content.character_cards == (character,)
    assert content.event_cards == (event,)
    with pytest.raises(FrozenInstanceError):
        content.event_cards = ()
