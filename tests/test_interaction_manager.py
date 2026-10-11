from cognitive_sandbox.application.interaction_manager import InteractionManager
from cognitive_sandbox.application.interaction_resolver import InteractionResolver
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState


def _context(agent_id):
    character = CharacterState(agent_id, agent_id, "普通居民", (), (), (), ())
    return AgentContext(agent_id, character, (), (), {})


def _action(actor_id, target_id, intent, action_id):
    return ActionCandidate(
        action_id=action_id,
        actor_id=actor_id,
        intent=intent,
        target=None,
        motivation="test",
        metadata={"target_agent_id": target_id},
    )


def test_help_action_generates_interaction_from_metadata_target():
    contexts = (_context("agent-a"), _context("agent-b"))
    manager = InteractionManager(InteractionResolver(interaction_id_factory=lambda: "interaction-1"))

    interactions = manager.generate(contexts, (_action("agent-a", "agent-b", "help", "act-1"),))

    assert len(interactions) == 1
    assert interactions[0].interaction_type == "help_other"
    assert interactions[0].source_agent_id == "agent-a"
    assert interactions[0].target_agent_id == "agent-b"


def test_protect_action_generates_protect_interaction():
    contexts = (_context("agent-a"), _context("agent-b"))

    interactions = InteractionManager(InteractionResolver()).generate(
        contexts,
        (_action("agent-a", "agent-b", "protect", "act-1"),),
    )

    assert interactions[0].interaction_type == "protect_other"


def test_missing_or_unknown_target_action_does_not_generate_interaction():
    contexts = (_context("agent-a"), _context("agent-b"))
    actions = (
        ActionCandidate(action_id="no-target", actor_id="agent-a", intent="help", motivation="test"),
        _action("agent-a", "missing-agent", "help", "missing-agent"),
        _action("agent-a", "agent-b", "observe", "observe"),
    )

    assert InteractionManager(InteractionResolver()).generate(contexts, actions) == ()


def test_multiple_interactions_are_returned_in_action_order():
    contexts = (_context("agent-a"), _context("agent-b"), _context("agent-c"))
    actions = (
        _action("agent-a", "agent-b", "help", "act-1"),
        _action("agent-b", "agent-c", "protect", "act-2"),
    )

    interactions = InteractionManager(InteractionResolver()).generate(contexts, actions)

    assert tuple(item.interaction_type for item in interactions) == ("help_other", "protect_other")
    assert tuple(item.source_agent_id for item in interactions) == ("agent-a", "agent-b")


def test_manager_does_not_modify_inputs():
    contexts = (_context("agent-a"), _context("agent-b"))
    actions = (_action("agent-a", "agent-b", "help", "act-1"),)
    original_contexts, original_actions = tuple(contexts), tuple(actions)

    InteractionManager(InteractionResolver()).generate(contexts, actions)

    assert contexts == original_contexts
    assert actions == original_actions
