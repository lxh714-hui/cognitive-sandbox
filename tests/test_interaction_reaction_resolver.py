from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.interaction_reaction_resolver import InteractionReactionResolver
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.interaction import AgentInteraction
from cognitive_sandbox.domain.interaction_reaction import InteractionReaction


def _agent(agent_id):
    character = CharacterState(agent_id, agent_id, "普通居民", (), (), (), ())
    return AgentContext(agent_id, character, (), (), {})


def _interaction(kind, target="agent-b"):
    return AgentInteraction("interaction-1", "agent-a", target, kind, "交互描述")


def test_help_interaction_generates_grateful_reaction_for_target():
    reaction = InteractionReactionResolver().resolve(_interaction("help_other"), _agent("agent-b"))

    assert reaction.interaction_id == "interaction-1"
    assert reaction.agent_id == "agent-b"
    assert reaction.reaction_type == "grateful"
    assert reaction.description == "角色感受到帮助并产生感谢"


def test_protect_interaction_generates_protected_reaction():
    reaction = InteractionReactionResolver().resolve(_interaction("protect_other"), _agent("agent-b"))

    assert reaction.reaction_type == "protected"
    assert reaction.agent_id == "agent-b"


def test_unknown_interaction_generates_no_reaction():
    assert InteractionReactionResolver().resolve(_interaction("unknown"), _agent("agent-b")) is None


def test_reaction_model_is_immutable():
    reaction = InteractionReactionResolver().resolve(_interaction("help_other"), _agent("agent-b"))

    with pytest.raises(FrozenInstanceError):
        reaction.reaction_type = "changed"


def test_reaction_resolver_rejects_a_context_for_the_wrong_target():
    with pytest.raises(ValueError, match="target_agent"):
        InteractionReactionResolver().resolve(_interaction("help_other"), _agent("agent-c"))


@pytest.mark.parametrize("field", ["interaction_id", "agent_id", "reaction_type", "description"])
def test_reaction_model_rejects_empty_fields(field):
    values = {
        "interaction_id": "interaction-1",
        "agent_id": "agent-b",
        "reaction_type": "grateful",
        "description": "角色感受到帮助并产生感谢",
    }
    values[field] = " "

    with pytest.raises(ValueError, match=field):
        InteractionReaction(**values)
