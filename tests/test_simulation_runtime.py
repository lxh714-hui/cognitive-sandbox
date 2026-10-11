from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.agent_runtime import AgentRuntime
from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.observation_layer import ObservationRuntime
from cognitive_sandbox.application.runtime_coordinator import RuntimeCoordinator
from cognitive_sandbox.application.simulation_runtime import SimulationRuntime
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.models import Agent
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.domain.simulation import SimulationStepResult
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


class _AgentMap:
    def __init__(self, agents):
        self._agents = agents

    def get_agent(self, agent_id):
        return self._agents.get(agent_id)


def _agent(agent_id):
    return Agent(agent_id, "harbor", agent_id, "resident", "observant", agent_id)


def _context():
    return PerceptionContext("kitchen", "kitchen")


def _simulation(store, agent_ids):
    cognition = CognitiveRuntime(store)
    agents = {agent_id: _agent(agent_id) for agent_id in agent_ids}
    agent_runtime = AgentRuntime(
        _AgentMap(agents),
        ObservationRuntime(store),
        cognition,
        DecisionRuntime(cognition, store),
    )
    return SimulationRuntime(RuntimeCoordinator(agent_runtime), ActionResolver())


def _committed_event(store):
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


def test_simulation_step_coordinates_agents_and_resolves_without_executing(tmp_path):
    store = SQLiteEventStore(tmp_path / "simulation.sqlite3")
    world, event = _committed_event(store)
    simulation = _simulation(store, ["lin-xia", "mei"])

    result = simulation.process_event(
        event,
        ["lin-xia", "mei"],
        {"lin-xia": _context(), "mei": _context()},
    )

    assert result.world_event_id == event.event_id
    assert len(result.proposals) == 2
    assert len(result.resolved_actions) == 2
    assert all(resolved.accepted for resolved in result.resolved_actions)
    assert [resolved.action for resolved in result.resolved_actions] == list(result.proposals)
    assert store.list_world_events("harbor") == [event]
    assert world.world_revision == event.world_revision


def test_simulation_step_returns_empty_tuples_when_no_agent_is_processed(tmp_path):
    store = SQLiteEventStore(tmp_path / "empty-simulation.sqlite3")
    _, event = _committed_event(store)
    simulation = _simulation(store, [])

    result = simulation.process_event(event, [], {})

    assert result.world_event_id == event.event_id
    assert result.proposals == ()
    assert result.resolved_actions == ()


def test_simulation_step_result_is_immutable_and_checks_resolution_membership():
    proposal = ActionProposal(
        "p1", "agent-a", "INSPECT_OBJECT", "cup_001", {}, "main", "harbor", 1
    )
    resolved = ActionResolver().resolve([proposal], current_world_revision=1)
    result = SimulationStepResult("event-1", (proposal,), tuple(resolved))

    with pytest.raises(FrozenInstanceError):
        result.world_event_id = "changed"
    with pytest.raises(ValueError, match="refer to a proposal"):
        SimulationStepResult("event-1", (), tuple(resolved))
