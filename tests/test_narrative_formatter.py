from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.narrative_formatter import NarrativeFormatter
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.world_events import WorldEvent


def _event(event_type, payload=None, actor_id="agent-1"):
    return WorldEvent(
        event_id="event-1",
        branch_id="main",
        world_id="world-1",
        event_type=event_type,
        actor_id=actor_id,
        payload=payload or {},
        world_revision=1,
    )


def test_help_event_formats_as_narrative():
    narrative = NarrativeFormatter().format(_event("help_attempt"))

    assert narrative == NarrativeEvent("event-1", "一次帮助", "有人伸出了援手", ("agent-1",))


def test_protect_event_formats_as_narrative():
    narrative = NarrativeFormatter().format(_event("protect_attempt"))

    assert narrative.title == "一次保护"
    assert narrative.description == "有人选择保护另一个人"
    assert narrative.participants == ("agent-1",)


def test_director_environment_event_uses_payload_for_description():
    narrative = NarrativeFormatter().format(
        _event("director_environment_change", {"weather": "rain", "danger_level": 0.8}, "director")
    )

    assert narrative.title == "环境发生变化"
    assert narrative.description == "环境发生了变化：天气：rain，危险程度：0.8"
    assert narrative.participants == ()


def test_director_environment_prefers_payload_description():
    narrative = NarrativeFormatter().format(
        _event("director_environment_change", {"description": "雨势逐渐增强"}, "director")
    )

    assert narrative.description == "雨势逐渐增强"


def test_director_pressure_event_formats_as_narrative():
    narrative = NarrativeFormatter().format(_event("director_pressure", actor_id="director"))

    assert narrative.title == "新的压力"
    assert narrative.description == "世界出现了新的压力"


def test_unknown_event_returns_none():
    assert NarrativeFormatter().format(_event("unknown_event")) is None


def test_narrative_event_is_immutable_and_participants_are_a_tuple():
    narrative = NarrativeFormatter().format(_event("help_attempt"))

    assert isinstance(narrative.participants, tuple)
    with pytest.raises(FrozenInstanceError):
        narrative.title = "changed"
    with pytest.raises(TypeError):
        narrative.participants[0] = "other-agent"


@pytest.mark.parametrize("field", ["source_event_id", "title", "description"])
def test_narrative_event_requires_non_empty_text(field):
    values = {
        "source_event_id": "event-1",
        "title": "标题",
        "description": "描述",
        "participants": (),
    }
    values[field] = " "

    with pytest.raises(ValueError, match=field):
        NarrativeEvent(**values)
