from __future__ import annotations

from dataclasses import FrozenInstanceError
import logging

import pytest

from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter
from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.player_intent import PlayerIntent
from cognitive_sandbox.domain.action_intent import ActionIntent


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


class ResponseProvider:
    def __init__(self, content: str) -> None:
        self.content = content

    def complete(self, request: AIGMRequest) -> AIGMResponse:
        assert request.request_type == "parse_player_action"
        return AIGMResponse(self.content)


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


@pytest.mark.parametrize(
    ("response", "text", "intent", "target"),
    [
        ('{"action_type":"observe"}', "环顾周围", "observe", None),
        (
            '```json\n{"action_type":"help","target":"医生"}\n```',
            "想办法帮忙",
            "help",
            "doctor",
        ),
        (
            '模型分析结果如下：\n{"action_type":"protect","target":"soldier"}\n请谨慎行动。',
            "保护队友",
            "protect",
            "soldier",
        ),
    ],
)
def test_extracts_supported_action_from_json_variants(response, text, intent, target):
    interpreter = AIActionInterpreter(
        ai_adapter=AIGMAdapter(ResponseProvider(response))
    )

    result = interpreter.interpret("player-1", text)

    assert result == PlayerIntent("player-1", text, intent, target)


def test_recovers_controlled_action_label_from_legacy_prose_response():
    response = "开始观察\n角色开始留意周围环境\ndoctor"
    interpreter = AIActionInterpreter(
        ai_adapter=AIGMAdapter(ResponseProvider(response))
    )

    result = interpreter.interpret("player-1", "环顾四周")

    assert result == PlayerIntent("player-1", "环顾四周", "observe", "doctor")


def test_malformed_json_with_known_action_label_recovers_safely():
    response = '{"action_type": "保护'
    interpreter = AIActionInterpreter(
        ai_adapter=AIGMAdapter(ResponseProvider(response))
    )

    result = interpreter.interpret("player-1", "保护医生")

    assert result == PlayerIntent("player-1", "保护医生", "protect", "doctor")


def test_unsupported_json_action_falls_back_to_keyword_parser():
    interpreter = AIActionInterpreter(
        ai_adapter=AIGMAdapter(ResponseProvider('{"action_type":"teleport"}'))
    )

    result = interpreter.interpret("player-1", "请查看出口")

    assert result == PlayerIntent("player-1", "请查看出口", "observe")


def test_parse_failure_logs_raw_response_and_reason_without_credentials(caplog):
    response = '{"action_type":"teleport"} Bearer abc.def.ghi api_key=private-value'
    interpreter = AIActionInterpreter(
        ai_adapter=AIGMAdapter(ResponseProvider(response))
    )

    with caplog.at_level(logging.DEBUG, logger="cognitive_sandbox.application.ai_action_interpreter"):
        result = interpreter.interpret("player-1", "做一件无法识别的事")

    assert result is None
    assert "unsupported action label" in caplog.text
    assert '{"action_type":"teleport"}' in caplog.text
    assert "[REDACTED]" in caplog.text
    assert "abc.def.ghi" not in caplog.text
    assert "private-value" not in caplog.text


@pytest.mark.parametrize(
    ("text", "intent", "target", "object_ref"),
    [
        ("和小花交谈", "talk", "小花", None),
        ("查看建筑", "inspect", None, "建筑"),
        ("去街角看看", "move", None, "街角"),
    ],
)
def test_open_vocabulary_action_interpretation(text, intent, target, object_ref):
    interpreter = AIActionInterpreter(
        ai_adapter=AIGMAdapter(MockOpenIntentProvider(intent, target, object_ref))
    )

    result = interpreter.interpret_action("player-1", text)

    assert result.actor_id == "player-1"
    assert result.raw_input == text
    assert result.intent == intent
    assert result.target == target
    assert result.object == object_ref


class MockOpenIntentProvider:
    def __init__(self, intent, target=None, object_ref=None):
        self.intent = intent
        self.target = target
        self.object_ref = object_ref

    def complete(self, request):
        import json

        assert request.request_type == "parse_action_intent"
        return AIGMResponse(json.dumps({
            "intent": self.intent,
            "target": self.target,
            "object": self.object_ref,
            "parameters": {},
        }, ensure_ascii=False))
