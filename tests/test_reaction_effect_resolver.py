from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.reaction_effect_resolver import ReactionEffectResolver
from cognitive_sandbox.domain.interaction_reaction import InteractionReaction
from cognitive_sandbox.domain.reaction_effect import ReactionEffect


def _reaction(reaction_type="grateful"):
    return InteractionReaction("reaction-1", "agent-target", reaction_type, "reaction")


def test_grateful_reaction_creates_expected_effect_for_target():
    effect = ReactionEffectResolver().resolve(_reaction("grateful"))

    assert effect == ReactionEffect(
        reaction_id="reaction-1",
        target_agent_id="agent-target",
        memory_content="曾经有人帮助过我",
        relationship_delta=0.1,
        confidence_delta=0.05,
        stress_delta=-0.05,
    )


def test_protected_reaction_creates_expected_effect():
    effect = ReactionEffectResolver().resolve(_reaction("protected"))

    assert effect.memory_content == "曾经有人保护过我"
    assert effect.relationship_delta == 0.05
    assert effect.confidence_delta == 0.03
    assert effect.stress_delta == -0.02
    assert effect.target_agent_id == "agent-target"


def test_unknown_reaction_has_no_effect():
    assert ReactionEffectResolver().resolve(_reaction("unknown")) is None


def test_effect_model_is_immutable():
    effect = ReactionEffectResolver().resolve(_reaction())

    with pytest.raises(FrozenInstanceError):
        effect.stress_delta = 0.0


@pytest.mark.parametrize(
    "field",
    ["relationship_delta", "confidence_delta", "stress_delta"],
)
@pytest.mark.parametrize("value", [-1.0, 1.0])
def test_effect_numeric_boundaries_are_valid(field, value):
    values = {
        "reaction_id": "reaction-1",
        "target_agent_id": "agent-target",
        "memory_content": "",
        "relationship_delta": 0,
        "confidence_delta": 0,
        "stress_delta": 0,
    }
    values[field] = value

    assert getattr(ReactionEffect(**values), field) == value


@pytest.mark.parametrize("value", [-1.01, 1.01])
def test_effect_rejects_out_of_range_numeric_values(value):
    with pytest.raises(ValueError, match="between -1 and 1"):
        ReactionEffect("reaction-1", "agent-target", "", value, 0, 0)


def test_empty_memory_content_is_allowed():
    effect = ReactionEffect("reaction-1", "agent-target", "", 0, 0, 0)

    assert effect.memory_content == ""
