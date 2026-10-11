import pytest

from cognitive_sandbox.application.agent_runtime import AgentRuntime
from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.observation_layer import ObservationRuntime
from cognitive_sandbox.application.runtime_coordinator import RuntimeCoordinator
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.models import Agent
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


class _AgentMap:
    def __init__(self, agents):
        self._agents = agents

    def get_agent(self, agent_id):
        return self._agents.get(agent_id)


def _agent(agent_id):
    return Agent(agent_id, "harbor", agent_id, "resident", "observant", agent_id)


def _context(*, visible=True):
    return PerceptionContext(
        agent_location_id="kitchen",
        event_location_id="kitchen",
        can_see=visible,
        can_hear=visible,
    )


def _event(store):
    world = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    event = world.submit_action(
        ActionProposal(
            proposal_id="break-cup",
            actor_id="liang-jing",
            action_type="BREAK_OBJECT",
            target_id="cup_001",
            payload={"location_id": "kitchen"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=0,
        )
    )
    return world, event


def _coordinator(store, agents):
    cognition = CognitiveRuntime(store)
    agent_runtime = AgentRuntime(
        _AgentMap(agents),
        ObservationRuntime(store),
        cognition,
        DecisionRuntime(cognition, store),
    )
    return RuntimeCoordinator(agent_runtime)


def test_coordinator_collects_proposals_from_multiple_agents_without_world_writes(tmp_path):
    store = SQLiteEventStore(tmp_path / "coordinator.sqlite3")
    world, event = _event(store)
    coordinator = _coordinator(
        store,
        {"lin-xia": _agent("lin-xia"), "mei": _agent("mei")},
    )

    proposals = coordinator.process_event(
        event,
        ["lin-xia", "mei"],
        {"lin-xia": _context(), "mei": _context()},
    )

    assert [proposal.actor_id for proposal in proposals] == ["lin-xia", "mei"]
    assert all(proposal.action_type == "INSPECT_OBJECT" for proposal in proposals)
    assert all(proposal.base_world_revision == event.world_revision for proposal in proposals)
    assert store.list_world_events("harbor") == [event]
    assert world.world_revision == 1
    cognition = CognitiveRuntime(store)
    assert cognition.get_state("lin-xia").cognitive_revision == 1
    assert cognition.get_state("mei").cognitive_revision == 1


def test_coordinator_skips_agents_without_perception_and_keeps_other_proposals(tmp_path):
    store = SQLiteEventStore(tmp_path / "partial-coordinator.sqlite3")
    _, event = _event(store)
    coordinator = _coordinator(
        store,
        {"lin-xia": _agent("lin-xia"), "outside": _agent("outside")},
    )

    proposals = coordinator.process_event(
        event,
        ["lin-xia", "outside"],
        {"lin-xia": _context(), "outside": _context(visible=False)},
    )

    assert [proposal.actor_id for proposal in proposals] == ["lin-xia"]
    assert CognitiveRuntime(store).get_state("outside").cognitive_revision == 0


def test_coordinator_requires_context_for_each_agent(tmp_path):
    store = SQLiteEventStore(tmp_path / "missing-context.sqlite3")
    _, event = _event(store)
    coordinator = _coordinator(store, {"lin-xia": _agent("lin-xia")})

    with pytest.raises(ValueError, match="Missing perception context"):
        coordinator.process_event(event, ["lin-xia"], {})


def test_coordinator_rejects_duplicate_agent_ids(tmp_path):
    store = SQLiteEventStore(tmp_path / "duplicate-agent.sqlite3")
    _, event = _event(store)
    coordinator = _coordinator(store, {"lin-xia": _agent("lin-xia")})

    with pytest.raises(ValueError, match="duplicates"):
        coordinator.process_event(
            event,
            ["lin-xia", "lin-xia"],
            {"lin-xia": _context()},
        )
