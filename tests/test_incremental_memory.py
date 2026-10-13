from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.world_tree_manager import WorldTreeManager
from cognitive_sandbox.conflict import ConflictManager, ConflictState, ConflictType
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.history.world_memory import (
    WorldDelta, WorldHistory, WorldMemory, WorldMemorySnapshot,
)
from cognitive_sandbox.narrative.opportunity import NarrativeOpportunity, OpportunitySourceType
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def _metadata(session):
    return SaveMetadata(
        session.world_instance_id, session.world_state.get("world_id", "world"),
        "scenario", "世界", "简介", "day-1", "day-1",
        player_character_id=session.player_id,
    )


def test_event_produces_delta_and_history_without_changing_world():
    session = GameLauncher().start_scenario("example_world")
    before_state = dict(session.world_state)
    event = WorldEvent(
        "event-memory-1", event_type="help_attempt", actor_id=session.player_id,
        target_id="doctor", timestamp="day-2 10:00",
        payload={"description": "梁景帮助了医生", "before": 0.2, "after": 0.3},
    )

    session.executor.event_pipeline.publish(event)

    assert session.world_state == before_state
    assert session.world_memory.history.event_history[0].source_id == event.event_id
    delta = session.world_memory.event_deltas[0]
    assert (delta.source, delta.change_type, delta.before, delta.after) == (
        event.event_id, "event_applied", None, {"type": "help_attempt"},
    )
    assert session.world_memory.history.event_history[0].summary == "Event applied"
    assert session.world_memory.history.relationship_history


def test_opportunity_lifecycle_is_recorded_and_round_trips():
    session = GameLauncher().start_scenario("example_world")
    opportunity = NarrativeOpportunity(
        "opportunity-1", OpportunitySourceType.WORLD, description="便利店传来争论声",
        created_time="day-1 09:00", possible_actions=("前往便利店",),
    )
    session.opportunity_service.register(opportunity)
    session.opportunity_service.resolve("opportunity-1", timestamp="day-1 10:00", cause="player_action")
    actions = [item.metadata["action"] for item in session.world_memory.history.opportunity_history]
    assert actions == ["created", "resolved"]

    serializer = WorldSerializer()
    restored = serializer.deserialize_world(serializer.serialize_world(_metadata(session), session))
    assert restored["world_memory"].history.opportunity_history == session.world_memory.history.opportunity_history
    restored_session = GameLauncher().restore_saved_world(restored)
    assert restored_session.world_memory.snapshot() == session.world_memory.snapshot()


def test_conflict_changes_are_recorded():
    memory = WorldMemory()
    manager = ConflictManager(world_memory=memory)
    conflict = ConflictState(
        "conflict-1", ConflictType.INFORMATION_CONFLICT, ("liang", "yiyi"),
        severity=.4, intensity=.4, pressure=.4, cause="掌握的信息不同",
    )
    manager.add(conflict)
    changed = manager.escalate("conflict-1", .7)
    manager.resolve("conflict-1", resolved_by="clarification")

    records = memory.history.conflict_history
    assert [item.metadata["action"] for item in records] == ["created", "changed", "changed"]
    assert records[1].metadata["status"] == "escalating"
    assert records[1].metadata["before"]["intensity"] == .4
    assert records[1].metadata["after"]["intensity"] == .7
    assert changed.intensity == .7


def test_decision_recording_does_not_change_execution_state():
    session = GameLauncher().start_scenario("example_world")
    before_state = dict(session.world_state)
    before_contexts = session.agent_contexts
    session.world_memory.record_decision(
        "liuyiyi", "investigate", timestamp="day-2 12:00",
        reason_context="goal:investigate_anomaly", target="neighborhood",
    )
    record = session.world_memory.history.decision_history[0]
    assert record.metadata["actor_id"] == "liuyiyi"
    assert record.metadata["decision"] == "investigate"
    assert session.world_state == before_state
    assert session.agent_contexts == before_contexts


def test_legacy_snapshot_loads_with_empty_incremental_history():
    session = GameLauncher().start_scenario("example_world")
    serializer = WorldSerializer()
    payload = serializer.serialize_world(_metadata(session), session)
    payload.pop("world_memory")

    restored = serializer.deserialize_world(payload)

    memory = restored["world_memory"]
    assert isinstance(memory, WorldMemorySnapshot)
    assert memory.current_snapshot["world_state"] == restored["session"]["world_state"]
    assert memory.history == WorldHistory()


def test_delta_and_history_models_are_immutable_and_mapping_serializable():
    source = {"level": {"before": 1}}
    delta = WorldDelta("d1", "day-1", "event-1", "clinic", "power_changed", source, {"on": True})
    source["level"]["before"] = 99
    assert delta.before["level"]["before"] == 1
    try:
        delta.before["level"]["before"] = 3
        assert False, "nested delta should be immutable"
    except TypeError:
        pass


def test_world_tree_branch_lifecycle_is_recorded():
    memory = WorldMemory()
    tree = WorldTreeManager("world-1", world_memory=memory)
    action = ActionCandidate(
        action_type="inspect", actor_id="player", intent="inspect", target="clock",
    )
    branch = tree.record_action(action)
    assert branch is not None
    assert tree.delete_branch(branch.branch_id)
    tree.record_merge(("branch-a", "branch-b"), "branch-merged", reason="same outcome")

    actions = tuple(record.metadata["action"] for record in memory.history.world_tree_history)
    assert actions == ("branch_expanded", "branch_selected", "branch_closed", "branches_merged")

