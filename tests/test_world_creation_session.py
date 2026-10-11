from __future__ import annotations

import json

import pytest

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.world_creation_session import WorldCreationSession
from cognitive_sandbox.application.world_generator import WorldGenerator
from cognitive_sandbox.domain.ai_gm import AIGMResponse
from cognitive_sandbox.domain.scenario_content import ScenarioContent


def generated_json() -> str:
    return json.dumps(
        {
            "world": {
                "world_id": "test_world",
                "name": "测试世界",
                "description": "一座等待探索的小城。",
                "history": [],
                "rules": [],
            },
            "characters": [
                {
                    "character_id": character_id,
                    "name": name,
                    "identity": {"occupation": occupation},
                    "personality": ["谨慎"],
                    "background": "生活在这座城市。",
                    "goals": ["寻找线索"],
                    "constraints": [],
                }
                for character_id, name, occupation in (
                    ("doctor", "林医生", "医生"),
                    ("soldier", "陈队长", "士兵"),
                    ("survivor", "阿禾", "居民"),
                )
            ],
            "events": [
                {
                    "event_id": "power_outage",
                    "name": "停电",
                    "description": "街区灯光熄灭。",
                    "event_type": "initial",
                    "participants": ["doctor"],
                    "conditions": [],
                    "effects": ["可能影响照明"],
                    "priority": 1,
                }
            ],
        },
        ensure_ascii=False,
    )


class JsonProvider:
    def __init__(self, content: str) -> None:
        self.content = content
        self.prompts: list[str] = []

    def complete(self, request) -> AIGMResponse:
        self.prompts.append(request.context["prompt"])
        return AIGMResponse(self.content)


def test_world_creation_requires_confirmation_before_start() -> None:
    launcher = GameLauncher()
    generator = WorldGenerator(JsonProvider(generated_json()))
    creation = WorldCreationSession(generator, launcher)
    prompt = "一个灾后小城"

    result = creation.generate(prompt)

    assert result.validation_result.valid
    assert creation.state == WorldCreationSession.DRAFT
    assert launcher.current_session is None
    with pytest.raises(RuntimeError, match="confirm"):
        creation.start()

    content = creation.confirm()

    assert isinstance(content, ScenarioContent)
    assert creation.state == WorldCreationSession.CONFIRMED
    assert launcher.current_session is None
    assert prompt == "一个灾后小城"


def test_confirmed_world_starts_roleplay_and_generates_runtime() -> None:
    launcher = GameLauncher()
    creation = WorldCreationSession(WorldGenerator(JsonProvider(generated_json())), launcher)
    creation.generate("一个灾后小城")
    creation.confirm()

    session = creation.start()

    assert creation.state == WorldCreationSession.STARTED
    assert session is launcher.current_session
    assert session.player_id == "doctor"
    assert session.current_turn.status == "waiting_input"
    assert session.world_state["world_id"] == "test_world"


def test_invalid_generation_cannot_be_confirmed_or_started() -> None:
    launcher = GameLauncher()
    creation = WorldCreationSession(WorldGenerator(JsonProvider("not JSON")), launcher)
    result = creation.generate("一个世界")

    assert not result.validation_result.valid
    with pytest.raises(RuntimeError, match="valid generated draft"):
        creation.confirm()
    assert launcher.current_session is None
