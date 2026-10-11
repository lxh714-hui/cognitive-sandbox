import pytest

from cognitive_sandbox.application.observation_layer import (
    ObservationLayer,
    ObservationSourceError,
)
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def committed_cup_event(store):
    runtime = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    proposal = ActionProposal(
        proposal_id="break-cup",
        actor_id="liang-jing",
        action_type="BREAK_OBJECT",
        target_id="cup_001",
        payload={"location_id": "kitchen"},
        branch_id="main",
        world_id="harbor",
        base_world_revision=0,
    )
    return runtime.submit_action(proposal)


def test_only_agents_present_at_event_location_receive_tasks(tmp_path):
    store = SQLiteEventStore(tmp_path / "observations.sqlite3")
    event = committed_cup_event(store)
    layer = ObservationLayer(store, id_factory=iter(["task-lin", "task-actor"]).__next__)

    tasks = layer.create_tasks(
        event.event_id,
        observer_locations={
            "lin-xia": "kitchen",
            "another-npc": "hall",
            "liang-jing": "kitchen",
        },
    )

    assert [task.observer_id for task in tasks] == ["lin-xia", "liang-jing"]
    assert all(task.source_event_id == event.event_id for task in tasks)
    assert all(task.created_revision == event.world_revision for task in tasks)
    assert tasks[0].channel == "visual"
    assert tasks[1].channel == "action"


def test_observation_record_references_event_and_contains_only_observable_fact(tmp_path):
    store = SQLiteEventStore(tmp_path / "observations.sqlite3")
    event = committed_cup_event(store)
    layer = ObservationLayer(
        store,
        id_factory=iter(["task-lin", "observation-lin"]).__next__,
        clock=lambda: "2026-10-11T12:00:00+00:00",
    )
    [task] = layer.create_tasks(event.event_id, observer_locations={"lin-xia": "kitchen"})

    record = layer.produce(task)

    assert record.agent_id == "lin-xia"
    assert record.source_refs == (event.event_id,)
    assert record.content == "liang-jing broke object cup_001."
    assert "angry" not in record.content
    assert record.uncertainty == 0.0
    assert record.observed_at == "2026-10-11T12:00:00+00:00"


def test_events_without_location_are_only_observable_by_actor(tmp_path):
    store = SQLiteEventStore(tmp_path / "observations.sqlite3")
    runtime = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    event = runtime.submit_action(
        ActionProposal(
            "break-cup", "liang-jing", "BREAK_OBJECT", "cup_001", {},
            "main", "harbor", 0,
        )
    )
    layer = ObservationLayer(store)

    tasks = layer.create_tasks(
        event.event_id,
        observer_locations={"lin-xia": "kitchen", "liang-jing": "kitchen"},
    )

    assert [task.observer_id for task in tasks] == ["liang-jing"]


def test_uncommitted_or_mismatched_source_event_is_rejected(tmp_path):
    store = SQLiteEventStore(tmp_path / "observations.sqlite3")
    layer = ObservationLayer(store)
    with pytest.raises(ObservationSourceError, match="No committed"):
        layer.create_tasks("missing-event", observer_locations={"lin-xia": "kitchen"})

