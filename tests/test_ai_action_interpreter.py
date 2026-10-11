from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.player_intent import PlayerIntent


class StubAdapter:
    def __init__(self, action=None, error: Exception | None = None) -> None:
        self.action = action
        self.error = error
        self.calls = []

    def parse_player_action(self, player_text, context):
        self.calls.append((player_text, context))
        if self.error is not None:
            raise self.error
        return self.action


@pytest.mark.parametrize(
    ("text", "intent", "target"),
    [
        ("请环顾四周，判断附近是否安全", "observe", None),
        ("扶起受伤的人并帮他包扎", "help", "doctor"),
        ("挡在同伴面前保护他", "protect", "soldier"),
    ],
)
def test_interprets_supported_structured_intents(text, intent, target):
    adapter = StubAdapter(PlayerAction("player-1", text, intent, target))

    result = AIActionInterpreter(ai_adapter=adapter).interpret("player-1", text)

    assert result == PlayerIntent("player-1", text, intent, target)


def test_invalid_or_unsupported_input_returns_none():
    adapter = StubAdapter(None)
    interpreter = AIActionInterpreter(ai_adapter=adapter)

    assert interpreter.interpret("player-1", "") is None
    assert interpreter.interpret("player-1", "我想聊聊天") is None
    assert len(adapter.calls) == 1


def test_ai_failure_falls_back_to_keyword_parser():
    interpreter = AIActionInterpreter(ai_adapter=StubAdapter(error=RuntimeError("offline")))

    result = interpreter.interpret("player-1", "请查看门口")

    assert result == PlayerIntent("player-1", "请查看门口", "observe")


def test_input_is_passed_unchanged_and_world_context_is_not_sent():
    text = "  请看看门外  "
    adapter = StubAdapter(PlayerAction("player-1", text, "observe"))

    result = AIActionInterpreter(ai_adapter=adapter).interpret("player-1", text)

    assert adapter.calls == [(text, {"player_id": "player-1"})]
    assert result.raw_input == text


def test_intent_is_immutable_and_parse_compatibility_is_structured():
    intent = PlayerIntent("player-1", "帮帮他", "help")
    with pytest.raises(FrozenInstanceError):
        intent.intent = "protect"

    parser_compatible = AIActionInterpreter().parse("player-1", "帮助医生")
    assert parser_compatible == PlayerAction("player-1", "帮助医生", "help", "doctor")


def test_interpreter_rejects_invalid_intent_from_ai_then_falls_back():
    adapter = StubAdapter(PlayerAction("player-1", "查看出口", "teleport"))

    result = AIActionInterpreter(ai_adapter=adapter).interpret("player-1", "查看出口")

    assert result == PlayerIntent("player-1", "查看出口", "observe")
