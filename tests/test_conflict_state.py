from cognitive_sandbox.conflict import (
    ConflictAgencyAdapter,
    ConflictContext,
    ConflictManager,
    ConflictSnapshot,
    ConflictState,
    ConflictStatus,
    ConflictType,
)
from cognitive_sandbox.narrative.opportunity.opportunity_manager import OpportunityManager
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.narrative.opportunity.opportunity_proposal import ProposalContext
from cognitive_sandbox.npc.autonomous.npc_scheduler import NpcScheduler
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def make_conflict(**kwargs):
    defaults = dict(
        id="liang_yiyi_truth",
        conflict_type=ConflictType.INFORMATION_CONFLICT,
        participants=("liangjing", "liuyiyi"),
        related_goals=("find_truth",),
        severity=.7,
        description="双方掌握的信息不同",
        related_beliefs=("different_accounts",),
        created_from="public_information_difference",
    )
    defaults.update(kwargs)
    return ConflictState(**defaults)


def test_conflict_creation_is_immutable_and_does_not_change_world():
    world_state = {"danger_level": .2}
    original = dict(world_state)
    conflict = make_conflict()
    manager = ConflictManager()
    manager.add(conflict)
    assert world_state == original
    assert conflict.type is ConflictType.INFORMATION_CONFLICT
    assert conflict.cause == "双方掌握的信息不同"
    assert conflict.intensity == .7
    assert conflict.pressure == .7
    assert manager.active_conflicts == (conflict,)


def test_conflict_snapshot_restores_lifecycle_and_resolution_metadata():
    manager = ConflictManager()
    manager.add(make_conflict())
    resolved = manager.resolve("liang_yiyi_truth", resolved_by="clarifying_event")
    restored = ConflictManager(manager.snapshot())
    state = restored.conflicts[0]
    assert state == resolved
    assert state.status is ConflictStatus.RESOLVED
    assert state.resolved_by == "clarifying_event"


def test_conflict_state_round_trips_through_world_serializer():
    conflict = make_conflict(cause="公开线索掌握不同", intensity=.65, pressure=.4)
    encoded = WorldSerializer._encode(ConflictSnapshot((conflict,)))
    restored = WorldSerializer._decode(encoded)
    assert restored.conflicts[0] == conflict
    assert restored.conflicts[0].created_from == "public_information_difference"


def test_conflict_context_adds_optional_agency_candidates_without_selecting():
    conflict = make_conflict()
    context = ConflictContext.for_character("liuyiyi", (conflict,))
    candidates = ConflictAgencyAdapter().candidates_for(context)
    assert candidates
    assert {item.action_type for item in candidates} == {"ask", "investigate", "observe"}
    assert all(item.conflict_id == conflict.id for item in candidates)
    # The adapter returns suggestions only; there is no chosen action or executor call.
    assert not hasattr(candidates[0], "selected")


def test_scheduler_receives_conflict_candidates_without_executing_them():
    class Agency:
        def snapshot(self):
            return type("Snapshot", (), {"autonomous_action_history": (), "action_feedback_history": ()})()

    class Evaluator:
        def score_action(self, base, **kwargs):
            return base

    manager = ConflictManager()
    manager.add(make_conflict())
    scheduler = NpcScheduler(conflict_manager=manager, agency_manager=Agency(), agency_evaluator=Evaluator())
    candidates = scheduler._conflict_agency_candidates("liangjing", object(), None)
    assert candidates
    assert all(item.action.parameters["conflict_id"] == "liang_yiyi_truth" for item in candidates)
    assert scheduler.action_executor is None


def test_conflict_pressure_creates_an_opportunity_not_an_event():
    manager = ConflictManager()
    manager.add(make_conflict())
    opportunities = OpportunityManager().refresh(
        world_time="2026-10-13T09:00:00", active_conflicts=manager.active_conflicts,
    )
    assert len(opportunities) == 1
    assert opportunities[0].related_conflict == "liang_yiyi_truth"
    assert opportunities[0].source_type.value == "CONFLICT"


def test_conflict_event_can_change_intensity_and_resolve_conflict():
    manager = ConflictManager()
    manager.add(make_conflict(severity=.7))
    updated = manager.record_event(WorldEvent(
        "clarify_1", event_type="conflict_communication", actor_id="liangjing",
        payload={"conflict_id": "liang_yiyi_truth"}, timestamp="2026-10-13T10:00:00",
    ))[0]
    assert updated.intensity < .7
    state = manager.resolve("liang_yiyi_truth", resolved_by="event_42")
    assert state.status is ConflictStatus.RESOLVED
    assert state.resolved_by == "event_42"


def test_legacy_conflict_fields_remain_available():
    legacy = ConflictState("old", ConflictType.GOAL_CONFLICT, ("a", "b"), severity=.4)
    assert legacy.conflict_type is legacy.type
    assert legacy.severity == legacy.intensity == legacy.pressure
    assert legacy.cause == legacy.description
    renamed = ConflictState(id="new", type=ConflictType.RELATIONSHIP_CONFLICT,
                            participants=("a", "b"), cause="信任出现分歧", intensity=.65, pressure=.4)
    assert renamed.type is ConflictType.RELATIONSHIP_CONFLICT
    assert renamed.severity == .65 and renamed.pressure == .4


def test_proposal_context_accepts_only_explicitly_public_conflict_context():
    context = ProposalContext.from_public_data(
        current_time="Day 2 09:00",
        public_conflicts=(
            {"id": "public-1", "type": "information_conflict", "public_summary": "双方掌握信息不同",
             "participants": ("a", "b"), "intensity": .6, "private_cause": "secret"},
            {"id": "private-1", "type": "value_conflict", "cause": "hidden fact"},
        ),
    )
    assert len(context.public_conflicts) == 1
    assert context.public_conflicts[0]["public_summary"] == "双方掌握信息不同"
    assert "private_cause" not in context.public_conflicts[0]
