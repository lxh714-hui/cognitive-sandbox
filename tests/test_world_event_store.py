import sqlite3

import pytest

from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def make_proposal(
    proposal_id: str = "proposal_001",
    world_id: str = "world_001",
    object_id: str = "cup_001",
    world_revision: int = 0,
    payload: dict | None = None,
) -> ActionProposal:
    return ActionProposal(
        proposal_id=proposal_id,
        branch_id="main",
        world_id=world_id,
        action_type="BREAK_OBJECT",
        actor_id="liang_jing",
        target_id=object_id,
        payload={"object_id": object_id} if payload is None else payload,
        base_world_revision=world_revision,
    )


def make_runtime(store, world_id="world_001", object_ids=("cup_001",), **kwargs):
    return WorldRuntime(
        store,
        world_id=world_id,
        branch_id="main",
        breakable_object_ids=object_ids,
        **kwargs,
    )


def test_initialization_creates_world_events_table(tmp_path):
    database_path = tmp_path / "events.sqlite3"
    SQLiteEventStore(database_path)

    with sqlite3.connect(database_path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'world_events'"
        ).fetchone()

    assert table == ("world_events",)


def test_world_event_round_trips_all_fields(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    event = make_runtime(store).submit_action(
        make_proposal(
            "proposal_001",
            object_id="cup_001",
            payload={"object_id": "cup_001", "details": {"pieces": 4}},
        )
    )

    [restored] = store.list_world_events("world_001")
    assert restored == event
    assert restored.payload["object_id"] == "cup_001"
    assert restored.payload["details"]["pieces"] == 4


def test_duplicate_world_event_id_is_rejected(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    runtime = make_runtime(
        store,
        object_ids=("cup_001", "cup_002"),
        event_id_factory=lambda: "duplicate-event-id",
    )
    runtime.submit_action(make_proposal("first", object_id="cup_001"))

    with pytest.raises(sqlite3.IntegrityError):
        runtime.submit_action(make_proposal("second", object_id="cup_002", world_revision=1))


def test_world_event_queries_are_scoped_to_world(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    first = make_runtime(store, world_id="world_001").submit_action(
        make_proposal("first", world_id="world_001")
    )
    second = make_runtime(store, world_id="world_002").submit_action(
        make_proposal("second", world_id="world_002")
    )

    assert store.list_world_events("world_001") == [first]
    assert store.list_world_events("world_002") == [second]


def test_world_events_are_returned_in_insertion_order(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    runtime = make_runtime(store, object_ids=("cup_001", "cup_002"))
    first = runtime.submit_action(make_proposal("first", object_id="cup_001"))
    second = runtime.submit_action(
        make_proposal("second", object_id="cup_002", world_revision=1)
    )

    assert store.list_world_events("world_001") == [first, second]


def test_world_revision_database_constraint_rejects_negative_values(tmp_path):
    database_path = tmp_path / "events.sqlite3"
    SQLiteEventStore(database_path)

    with sqlite3.connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO world_events
                   (event_id, branch_id, world_id, event_type, actor_id,
                    payload_json, world_revision, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("event_negative", "main", "world_001", "BREAK_OBJECT", "liang_jing",
                 '{"object_id":"cup_001"}', -1, "2026-10-11T00:00:00+00:00"),
            )
