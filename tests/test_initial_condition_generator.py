from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.initial_condition_generator import InitialConditionGenerator
from cognitive_sandbox.domain.initial_conditions import (
    InitialConditionRequest,
    InitialConditionResult,
)


def test_known_post_apocalyptic_city_prompt_uses_template():
    result = InitialConditionGenerator(world_id_factory=lambda: "world-test").generate(
        InitialConditionRequest("末日城市")
    )

    assert result.world_id == "world-test"
    assert result.summary
    assert dict(result.initial_state) == {
        "setting": "post_apocalypse",
        "danger_level": "medium",
        "resources": "limited",
    }


def test_unknown_prompt_uses_generic_default_world():
    result = InitialConditionGenerator(world_id_factory=lambda: "world-generic").generate(
        InitialConditionRequest("漂浮的玻璃花园")
    )

    assert result.world_id == "world-generic"
    assert result.initial_state["setting"] == "generic"
    assert result.initial_state["description"] == "漂浮的玻璃花园"


@pytest.mark.parametrize("prompt", ["", "  ", None])
def test_empty_prompt_is_rejected(prompt):
    with pytest.raises(ValueError, match="prompt"):
        InitialConditionRequest(prompt)


def test_result_and_nested_initial_state_are_immutable():
    result = InitialConditionResult(
        "world-1",
        "A small test world.",
        {"setting": "test", "details": {"items": ["key"]}},
    )

    with pytest.raises(FrozenInstanceError):
        result.summary = "changed"
    with pytest.raises(TypeError):
        result.initial_state["setting"] = "changed"
    with pytest.raises(TypeError):
        result.initial_state["details"]["items"] = ()
    with pytest.raises(TypeError):
        result.initial_state["details"]["items"][0] = "changed"


def test_generator_requires_request_model():
    with pytest.raises(TypeError, match="InitialConditionRequest"):
        InitialConditionGenerator().generate("末日城市")
