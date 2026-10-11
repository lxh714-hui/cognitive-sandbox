from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.memory_encoder import MemoryEncoder
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


def _context() -> PerceptionContext:
    return PerceptionContext(agent_location_id="kitchen", event_location_id="kitchen")


def _broken_cup_observation(store, *, observer_id="lin-xia"):
    world = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
        event_id_factory=lambda: "event-break-cup",
    )
    event = world.submit_action(
        ActionProposal(
            proposal_id="proposal-break-cup",
            actor_id="liang-jing",
            action_type="BREAK_OBJECT",
            target_id="cup_001",
            payload={"location_id": "kitchen"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=0,
        )
    )
    observation_runtime = ObservationRuntime(
        store,
        id_factory=lambda: "observation-break-cup",
        clock=lambda: "2026-10-11T12:00:00+00:00",
    )
    [observation] = observation_runtime.generate_observation(
        _agent(observer_id), event, context=_context()
    )
    return observation


def test_memory_encoder_persists_observation_with_provenance_not_world_event(tmp_path):
    store = SQLiteEventStore(tmp_path / "memory.sqlite3")
    observation = _broken_cup_observation(store)
    cognition = CognitiveRuntime(store)
    cognition.process_observation(observation)
    encoder = MemoryEncoder(
        cognition,
        store,
        id_factory=lambda: "memory-break-cup",
        clock=lambda: "2026-10-11T12:01:00+00:00",
    )

    [memory] = encoder.encode("lin-xia")
    [restored] = store.list_long_term_memories("lin-xia")

    assert memory == restored
    assert memory.memory_type == "episodic"
    assert memory.agent_id == "lin-xia"
    assert memory.source_refs == (observation.observation_id,)
    assert memory.content["observation_id"] == observation.observation_id
    assert memory.content["text"] == observation.content
    assert "event-break-cup" not in memory.source_refs
    assert "source_event_ids" not in memory.content


def test_memory_encoding_is_idempotent_for_an_observation(tmp_path):
    store = SQLiteEventStore(tmp_path / "memory.sqlite3")
    observation = _broken_cup_observation(store)
    cognition = CognitiveRuntime(store)
    cognition.process_observation(observation)
    encoder = MemoryEncoder(cognition, store)

    assert len(encoder.encode("lin-xia")) == 1
    assert encoder.encode("lin-xia") == []
    assert len(store.list_long_term_memories("lin-xia")) == 1


def test_memory_encoder_reads_only_the_requested_agent_state(tmp_path):
    store = SQLiteEventStore(tmp_path / "memory.sqlite3")
    observation = _broken_cup_observation(store)
    cognition = CognitiveRuntime(store)
    cognition.process_observation(observation)
    encoder = MemoryEncoder(cognition, store)

    assert encoder.encode("another-npc") == []
    assert store.list_long_term_memories("another-npc") == []
    assert len(encoder.encode("lin-xia")) == 1


def test_neutral_low_salience_observation_is_not_encoded(tmp_path):
    store = SQLiteEventStore(tmp_path / "memory.sqlite3")
    world = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
        event_id_factory=iter(("event-break-cup", "event-inspect-cup")).__next__,
    )
    world.submit_action(
        ActionProposal(
            proposal_id="proposal-break-cup",
            actor_id="liang-jing",
            action_type="BREAK_OBJECT",
            target_id="cup_001",
            payload={"location_id": "kitchen"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=0,
        )
    )
    inspected = world.submit_action(
        ActionProposal(
            proposal_id="proposal-inspect-cup",
            actor_id="lin-xia",
            action_type="INSPECT_OBJECT",
            target_id="cup_001",
            payload={"object_id": "cup_001"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=1,
        )
    )
    [observation] = ObservationRuntime(
        store,
        id_factory=lambda: "observation-neutral-inspection",
    ).generate_observation(_agent("another-npc"), inspected, context=_context())
    cognition = CognitiveRuntime(store)
    state = cognition.process_observation(observation)

    assert state.emotion_state.source_refs == ()
    assert MemoryEncoder(cognition, store).encode("another-npc") == []
    assert store.list_long_term_memories("another-npc") == []
