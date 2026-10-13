from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_dispatcher import ActionDispatcher
from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.domain.action_intent import ActionIntent


@pytest.mark.parametrize(
    ("text", "intent", "target", "object_ref"),
    [
        ("和小花交谈", "talk", "小花", None),
        ("查看建筑", "inspect", None, "建筑"),
        ("去街角看看", "move", None, "街角"),
    ],
)
def test_open_action_phrases_are_parsed(text, intent, target, object_ref):
    result = ActionIntentParser().parse("player", text)

    assert result.actor_id == "player"
    assert result.raw_input == text
    assert result.intent == intent
    assert result.target == target
    assert result.object == object_ref
    if intent == "move":
        assert result.parameters["follow_up_intent"] == "observe"


def test_unknown_action_fails_without_inventing_an_intent():
    assert ActionIntentParser().parse("player", "做一件说不清的事") is None


def test_action_intent_is_immutable_and_parameters_are_deeply_read_only():
    source = {"details": ["quietly"]}
    intent = ActionIntent("player", "交谈", "talk", parameters=source)
    source["details"].append("changed")

    assert intent.parameters["details"] == ("quietly",)
    with pytest.raises(TypeError):
        intent.parameters["new"] = True
    with pytest.raises(FrozenInstanceError):
        intent.intent = "move"


def test_dispatcher_rejects_nonexistent_target_and_unsupported_action_safely():
    dispatcher = ActionDispatcher()
    parsed_target = ActionIntentParser().parse("player", "和小花交谈")
    nonexistent = dispatcher.dispatch(parsed_target, known_entities=("沈医生", "周岚"))
    unsupported = dispatcher.dispatch(ActionIntent("player", "休息", "rest"))

    assert not nonexistent.accepted
    assert not unsupported.accepted
    assert unsupported.simulation_intent is None
