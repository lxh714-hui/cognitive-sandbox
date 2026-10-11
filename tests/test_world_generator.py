from __future__ import annotations

import json

import pytest

from cognitive_sandbox.application.world_generator import WorldGenerator
from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.validation_result import ValidationResult


def valid_payload() -> dict:
    return {
        "world": {
            "world_id": "harbor_after_dark",
            "name": "雾港",
            "description": "停电后的海港城镇。",
            "history": ["风暴切断了城市电力。"],
            "rules": ["夜间能见度很低。"],
        },
        "characters": [
            {
                "character_id": character_id,
                "name": name,
                "identity": {"age": 30, "gender": "", "occupation": role},
                "personality": ["谨慎"],
                "background": "熟悉当地街区。",
                "goals": ["寻找安全地点"],
                "constraints": [{"type": "soft", "content": "尽量避免冲突"}],
            }
            for character_id, name, role in (
                ("doctor", "林医生", "医生"),
                ("mechanic", "周师傅", "技工"),
                ("guide", "阿岚", "向导"),
            )
        ],
        "events": [
            {
                "event_id": "generator_noise",
                "name": "发电机异响",
                "description": "诊所后院的发电机传来断续声响。",
                "event_type": "initial",
                "participants": ["doctor"],
                "conditions": ["night"],
                "effects": ["可能影响诊所供电"],
                "priority": 1,
            }
        ],
    }


class FixedProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[AIGMRequest] = []

    def complete(self, request: AIGMRequest) -> AIGMResponse:
        self.requests.append(request)
        return AIGMResponse(self.response)


def test_world_generator_parses_and_validates_draft_content() -> None:
    provider = FixedProvider(json.dumps(valid_payload(), ensure_ascii=False))
    result = WorldGenerator(provider).generate("一个停电后的海港城镇")

    assert result.validation_result.valid
    assert isinstance(result.scenario_content, ScenarioContent)
    assert result.scenario_content.world_document.name == "雾港"
    assert len(result.scenario_content.character_cards) == 3
    assert result.scenario_content.character_cards[0].constraints[0].type == "soft"
    assert result.scenario_content.event_cards[0].event_id == "generator_noise"
    assert provider.requests[0].request_type == "generate_world"
    assert "严格 JSON" in provider.requests[0].context["prompt"]
    assert result.warnings


def test_world_generator_returns_clear_error_for_invalid_json() -> None:
    result = WorldGenerator(FixedProvider("```json\n{}\n``` ")).generate("雾港")

    assert result.scenario_content is None
    assert not result.validation_result.valid
    assert "strict JSON" in result.error
    assert result.validation_result.errors


def test_world_generator_rejects_content_reported_invalid_by_validator() -> None:
    class RejectingWorldValidator:
        def validate(self, _document: object) -> ValidationResult:
            return ValidationResult(False, ("world rejected by test validator",), ())

    result = WorldGenerator(
        FixedProvider(json.dumps(valid_payload(), ensure_ascii=False)),
        world_validator=RejectingWorldValidator(),  # type: ignore[arg-type]
    ).generate("一个停电后的海港城镇")

    assert result.scenario_content is None
    assert not result.validation_result.valid
    assert "world rejected by test validator" in result.error


def test_world_generator_returns_content_only_and_does_not_create_runtime() -> None:
    result = WorldGenerator(FixedProvider(json.dumps(valid_payload(), ensure_ascii=False))).generate(
        "一个停电后的海港城镇"
    )

    assert isinstance(result.scenario_content, ScenarioContent)
    assert not hasattr(result, "runtime")
    assert not hasattr(result.scenario_content, "world_state")


def test_world_generator_does_not_modify_user_input_or_provider_data() -> None:
    source = valid_payload()
    original = json.dumps(source, ensure_ascii=False)
    prompt = "  一个停电后的海港城镇  "
    provider = FixedProvider(json.dumps(source, ensure_ascii=False))

    result = WorldGenerator(provider).generate(prompt)

    assert result.validation_result.valid
    assert json.dumps(source, ensure_ascii=False) == original
    assert prompt == "  一个停电后的海港城镇  "
    assert "一个停电后的海港城镇" in provider.requests[0].context["prompt"]
    with pytest.raises(TypeError):
        provider.requests[0].context["prompt"] = "changed"  # type: ignore[index]


def test_world_generator_rejects_guaranteed_outcomes_and_wrong_counts() -> None:
    payload = valid_payload()
    payload["events"][0]["effects"] = ["玩家一定成功"]
    payload["characters"].pop()
    result = WorldGenerator(FixedProvider(json.dumps(payload, ensure_ascii=False))).generate("测试")

    assert result.scenario_content is None
    assert not result.validation_result.valid
    assert any("between 3 and 5" in error for error in result.validation_result.errors)
    assert any("guaranteed outcome" in error for error in result.validation_result.errors)


def test_world_generator_rejects_empty_prompt_and_provider_failure() -> None:
    empty = WorldGenerator(FixedProvider("{}")).generate("   ")

    class FailingProvider:
        def complete(self, _request: AIGMRequest) -> AIGMResponse:
            raise ConnectionError("offline")

    failed = WorldGenerator(FailingProvider()).generate("雾港")

    assert empty.scenario_content is None
    assert "must not be empty" in empty.error
    assert failed.scenario_content is None
    assert "offline" in failed.error
