from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.interaction_resolver import InteractionResolver
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.interaction import AgentInteraction


def _agent(agent_id, name):
    character = CharacterState(agent_id, name, "普通居民", (), (), (), ())
    return AgentContext(agent_id, character, (), (), {})


def _action(actor_id, intent, target="agent-b"):
    return ActionCandidate(
        action_id="action-1",
        actor_id=actor_id,
        intent=intent,
        target=target,
        motivation="test",
    )


@pytest.fixture
def agents():
    return _agent("agent-a", "甲"), _agent("agent-b", "乙")


def test_help_action_creates_interaction_with_correct_agents(agents):
    source, target = agents
    interaction = InteractionResolver(interaction_id_factory=lambda: "interaction-1").resolve(
        source, target, _action(source.character_id, "help")
    )

    assert interaction == AgentInteraction(
        "interaction-1",
        "agent-a",
        "agent-b",
        "help_other",
        "角色尝试帮助另一个角色",
    )


def test_protect_action_creates_protect_interaction(agents):
    source, target = agents

    interaction = InteractionResolver().resolve(source, target, _action(source.character_id, "protect"))

    assert interaction.interaction_type == "protect_other"
    assert interaction.source_agent_id == source.character_id
    assert interaction.target_agent_id == target.character_id


@pytest.mark.parametrize("intent", ["observe", "unknown-action"])
def test_observe_and_unknown_actions_do_not_create_interactions(agents, intent):
    source, target = agents

    assert InteractionResolver().resolve(source, target, _action(source.character_id, intent)) is None


def test_missing_or_mismatched_target_does_not_create_interaction(agents):
    source, target = agents
    resolver = InteractionResolver()

    assert resolver.resolve(source, None, _action(source.character_id, "help")) is None
    assert resolver.resolve(source, target, _action(source.character_id, "help", "someone-else")) is None


def test_interaction_is_immutable():
    source, target = _agent("agent-a", "甲"), _agent("agent-b", "乙")
    interaction = InteractionResolver().resolve(source, target, _action(source.character_id, "help"))

    with pytest.raises(FrozenInstanceError):
        interaction.interaction_type = "changed"


@pytest.mark.parametrize("field", ["interaction_id", "source_agent_id", "target_agent_id", "interaction_type", "description"])
def test_interaction_rejects_empty_required_fields(field):
    values = {
        "interaction_id": "interaction-1",
        "source_agent_id": "agent-a",
        "target_agent_id": "agent-b",
        "interaction_type": "help_other",
        "description": "角色尝试帮助另一个角色",
    }
    values[field] = " "

    with pytest.raises(ValueError, match=field):
        AgentInteraction(**values)
