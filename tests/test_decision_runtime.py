from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.observation_layer import ObservationLayer
from cognitive_sandbox.application.world_runtime import WorldRuleViolation, WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def build_agent_state(store, *, observer_id="lin-xia"):
    world_runtime = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    event = world_runtime.submit_action(
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
    observation_layer = ObservationLayer(store)
    [task] = observation_layer.create_tasks(
        event.event_id,
        observer_locations={observer_id: "kitchen"},
    )
    CognitiveRuntime(store).process_observation(observation_layer.produce(task))
    return world_runtime


def test_decision_runtime_generates_proposal_from_own_cognitive_state(tmp_path):
    store = SQLiteEventStore(tmp_path / "decision.sqlite3")
    build_agent_state(store)
    decision = DecisionRuntime(CognitiveRuntime(store))

    [proposal] = decision.generate_actions("lin-xia")

    assert proposal.actor_id == "lin-xia"
    assert proposal.action_type == "INSPECT_OBJECT"
    assert proposal.target_id == "cup_001"
    assert proposal.world_id == "harbor"
    assert proposal.branch_id == "main"
    assert proposal.base_world_revision == 1
    assert proposal.payload["source_event_ids"]
    assert proposal.priority == proposal.payload["action_score"]
    assert "supported_by_working_memory" in proposal.payload["score_reasons"]


def test_decision_runtime_returns_no_actions_without_matching_cognition(tmp_path):
    store = SQLiteEventStore(tmp_path / "decision.sqlite3")
    build_agent_state(store)
    decision = DecisionRuntime(CognitiveRuntime(store))

    assert decision.generate_actions("unobservant-agent") == []


def test_decision_runtime_is_repeatable_and_does_not_write_database(tmp_path):
    store = SQLiteEventStore(tmp_path / "decision.sqlite3")
    world_runtime = build_agent_state(store)
    decision = DecisionRuntime(CognitiveRuntime(store))
    before_state = CognitiveRuntime(store).get_state("lin-xia")
    before_events = store.list_world_events("harbor")

    first = decision.generate_actions("lin-xia")
    second = decision.generate_actions("lin-xia")

    assert first == second
    assert CognitiveRuntime(store).get_state("lin-xia") == before_state
    assert store.list_world_events("harbor") == before_events
    assert world_runtime.world_revision == 1


def test_world_runtime_executes_decision_proposal(tmp_path):
    store = SQLiteEventStore(tmp_path / "decision.sqlite3")
    world_runtime = build_agent_state(store)
    [proposal] = DecisionRuntime(CognitiveRuntime(store)).generate_actions("lin-xia")

    event = world_runtime.submit_action(proposal)

    assert event.event_type == "OBJECT_INSPECTED"
    assert event.payload == {"object_id": "cup_001", "inspector": "lin-xia"}
    assert len(store.list_world_events("harbor")) == 2
    assert world_runtime.world_revision == 2
