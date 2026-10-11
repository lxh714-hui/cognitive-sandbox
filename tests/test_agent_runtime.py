import pytest

from cognitive_sandbox.application.agent_runtime import AgentRuntime
from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.observation_layer import ObservationRuntime
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.models import Agent
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def _agent(agent_id: str) -> Agent:
    return Agent(
        id=agent_id,
        world_id="harbor",
        name=agent_id,
        role="resident",
        persona="observant",
        sprite_key=agent_id,
    )


def _context(*, can_see=True, can_hear=True, location="kitchen"):
    return PerceptionContext(
        agent_location_id=location,
        event_location_id="kitchen",
        can_see=can_see,
        can_hear=can_hear,
    )


def _runtime(store, agents):
    cognition = CognitiveRuntime(store)
    return AgentRuntime(
        agent_reader=_AgentMap(agents),
        observation_runtime=ObservationRuntime(store),
        cognitive_runtime=cognition,
        decision_runtime=DecisionRuntime(cognition, store),
    )


class _AgentMap:
    def __init__(self, agents):
        self._agents = agents

    def get_agent(self, agent_id):
        return self._agents.get(agent_id)


def _committed_break_event(store):
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


def test_process_event_runs_perception_cognition_and_returns_proposal_without_executing(tmp_path):
    store = SQLiteEventStore(tmp_path / "agent-runtime.sqlite3")
    world, event = _committed_break_event(store)
    runtime = _runtime(store, {"lin-xia": _agent("lin-xia")})

    proposal = runtime.process_event("lin-xia", event, _context())

    assert proposal is not None
    assert proposal.actor_id == "lin-xia"
    assert proposal.action_type == "INSPECT_OBJECT"
    assert proposal.target_id == "cup_001"
    state = CognitiveRuntime(store).get_state("lin-xia")
    assert state.cognitive_revision == 1
    assert state.working_memory[-1].content["source_event_ids"] == (event.event_id,)
    assert store.list_world_events("harbor") == [event]
    assert world.world_revision == 1


def test_no_perception_returns_none_without_cognitive_or_decision_update(tmp_path):
    store = SQLiteEventStore(tmp_path / "no-perception.sqlite3")
    _, event = _committed_break_event(store)
    cognition = CognitiveRuntime(store)

    class DecisionMustNotRun:
        def generate_actions(self, agent_id):
            pytest.fail("Decision should not run without an observation.")

    runtime = AgentRuntime(
        _AgentMap({"lin-xia": _agent("lin-xia")}),
        ObservationRuntime(store),
        cognition,
        DecisionMustNotRun(),
    )

    result = runtime.process_event(
        "lin-xia", event, _context(can_see=False, can_hear=False)
    )

    assert result is None
    assert cognition.get_state("lin-xia").cognitive_revision == 0
    assert cognition.get_state("lin-xia").working_memory == ()


def test_processing_event_updates_only_requested_agents_cognition(tmp_path):
    store = SQLiteEventStore(tmp_path / "agent-isolation.sqlite3")
    _, event = _committed_break_event(store)
    runtime = _runtime(
        store,
        {"lin-xia": _agent("lin-xia"), "other": _agent("other")},
    )

    runtime.process_event("lin-xia", event, _context())

    cognition = CognitiveRuntime(store)
    assert cognition.get_state("lin-xia").cognitive_revision == 1
    assert cognition.get_state("other").cognitive_revision == 0


def test_missing_agent_is_reported(tmp_path):
    store = SQLiteEventStore(tmp_path / "missing-agent.sqlite3")
    _, event = _committed_break_event(store)
    runtime = _runtime(store, {})

    with pytest.raises(LookupError, match="Agent not found"):
        runtime.process_event("unknown", event, _context())
