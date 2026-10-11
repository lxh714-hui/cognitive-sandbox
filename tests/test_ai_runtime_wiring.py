from __future__ import annotations

import json

from PySide6.QtCore import QSettings

from cognitive_sandbox.application.ai_runtime_wiring import AIRuntimeWiring
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.llm_config import LLMConfig
from cognitive_sandbox.domain.player_action import PlayerAction


class MockTransport:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content or json.dumps({"intent": "observe", "target": None})
        self.error = error
        self.calls = []

    def post(self, url, *, headers, body, timeout):
        self.calls.append((url, headers, body, timeout))
        if self.error is not None:
            raise self.error
        return {"choices": [{"message": {"content": self.content}}]}


def _settings(tmp_path) -> QSettings:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("ai/provider", "local-compatible")
    settings.setValue("ai/model_name", "qwen-test")
    settings.setValue("ai/base_url", "http://localhost:11434/v1")
    settings.sync()
    return settings


def test_runtime_loads_saved_ai_configuration_without_api_key(tmp_path):
    wiring = AIRuntimeWiring(settings=_settings(tmp_path))

    config = wiring.load_config()

    assert config == LLMConfig(
        api_key="",
        base_url="http://localhost:11434/v1",
        model_name="qwen-test",
    )


def test_ai_interpreter_is_wired_into_roleplay_session(tmp_path):
    transport = MockTransport(json.dumps({"intent": "help", "target": "doctor"}))
    wiring = AIRuntimeWiring(
        settings=_settings(tmp_path),
        transport=transport,
        timeout=0.25,
    )
    session = GameLauncher(ai_runtime_wiring=wiring).start_scenario("post_apocalypse_city")
    submitted = "请扶起受伤的医生并帮忙处理伤口"
    session.submit_input(submitted)

    result = session.confirm()

    assert result.action_executed
    assert transport.calls[0][0] == "http://localhost:11434/v1/chat/completions"
    request_data = json.loads(transport.calls[0][2]["messages"][1]["content"])
    assert request_data["request_type"] == "parse_player_action"
    assert request_data["context"]["player_text"] == submitted
    assert "world_state" not in request_data["context"]


def test_runtime_falls_back_to_keyword_parser_when_ai_fails(tmp_path):
    transport = MockTransport(error=ConnectionError("offline"))
    wiring = AIRuntimeWiring(settings=_settings(tmp_path), transport=transport)
    session = GameLauncher(ai_runtime_wiring=wiring).start_scenario("post_apocalypse_city")
    session.submit_input("请查看前方")

    result = session.confirm()

    assert result.action_executed
    assert result.simulation_result.events[0].event_type == "observe_action"


def test_interpretation_does_not_mutate_submitted_input_or_world_snapshot(tmp_path):
    wiring = AIRuntimeWiring(
        settings=_settings(tmp_path),
        transport=MockTransport(json.dumps({"intent": "observe", "target": None})),
    )
    interpreter = wiring.create_action_interpreter()
    submitted = "  请观察入口  "
    world_snapshot = {"danger_level": 0.4, "nested": {"resource": "low"}}
    before = json.dumps(world_snapshot, sort_keys=True)

    action = interpreter.parse("doctor", submitted)

    assert action == PlayerAction("doctor", submitted, "observe")
    assert submitted == "  请观察入口  "
    assert json.dumps(world_snapshot, sort_keys=True) == before
