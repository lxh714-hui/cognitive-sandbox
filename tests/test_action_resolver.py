from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.domain.actions import ActionCandidate, ResolvedActionResult


def candidate(intent):
    return ActionCandidate(
        action_id=f"action-{intent}",
        actor_id="agent-1",
        intent=intent,
        target="target-1",
        motivation="test",
    )


@pytest.mark.parametrize(
    ("intent", "description", "impact"),
    [
        ("help", "角色尝试提供帮助", {"social": "positive"}),
        ("protect", "角色尝试保护目标", {"safety": "increased"}),
        ("observe", "角色观察周围环境", {"information": "gained"}),
    ],
)
def test_known_intents_resolve_to_successful_result(intent, description, impact):
    result = ActionResolver().resolve(candidate(intent), {"location": "room"})

    assert result.action_id == f"action-{intent}"
    assert result.success
    assert result.event_description == description
    assert dict(result.impact) == impact


def test_unknown_intent_returns_failed_result():
    result = ActionResolver().resolve(candidate("teleport"), {})

    assert not result.success
    assert result.event_description == "行动无法解析"
    assert result.impact["error"] == "unknown_action"


def test_impact_is_deeply_read_only_and_result_is_immutable():
    result = ResolvedActionResult(
        "action-1",
        True,
        "已解析",
        {"effects": {"tags": ["social"]}},
    )

    with pytest.raises(FrozenInstanceError):
        result.success = False
    with pytest.raises(TypeError):
        result.impact["effects"]["tags"] = ()
    with pytest.raises(TypeError):
        result.impact["effects"]["tags"][0] = "changed"


def test_resolver_validates_action_and_world_state_inputs():
    resolver = ActionResolver()
    with pytest.raises(TypeError, match="ActionCandidate"):
        resolver.resolve("help", {})
    with pytest.raises(TypeError, match="world_state"):
        resolver.resolve(candidate("help"), None)
