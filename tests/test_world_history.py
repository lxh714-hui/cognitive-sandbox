import pytest

from cognitive_sandbox.history import EventQuery, EventTimeline, WorldEventRecord
from cognitive_sandbox.domain.world_events import WorldEvent


def _event(event_id, event_type, timestamp, actor="player", target=None, location="harbor", importance=0.5):
    return WorldEvent(
        event_id=event_id, event_type=event_type, actor=actor, target=target,
        location=location, timestamp=timestamp, metadata={"importance": importance},
    )


def test_world_event_is_recorded_with_participants_location_and_importance():
    timeline = EventTimeline()
    record = timeline.record_event(_event("e1", "player_helped_doctor", "day-3", target="doctor", importance="high"))
    assert record == WorldEventRecord(
        "e1", "player_helped_doctor", "day-3", ("player",), ("doctor",), "harbor", 0.8,
        {},
    )
    assert timeline.get_recent_events() == (record,)


def test_timeline_is_time_ordered_and_recent_events_are_newest_first():
    timeline = EventTimeline()
    timeline.record_event(_event("e2", "arrival", "2026-10-02"))
    timeline.record_event(_event("e1", "departure", "2026-10-01"))
    assert [record.event_id for record in timeline.events] == ["e1", "e2"]
    assert [record.event_id for record in timeline.get_recent_events(2)] == ["e2", "e1"]


def test_query_filters_by_time_type_character_location_and_importance():
    timeline = EventTimeline()
    timeline.record_event(_event("e1", "help_attempt", "2026-10-01", target="doctor", importance=0.9))
    timeline.record_event(_event("e2", "weapon_drawn", "2026-10-02", target="soldier", location="market", importance=0.2))
    results = timeline.query_events(EventQuery(
        start_time="2026-10-01", event_types=("help_attempt",), character_ids=("doctor",),
        location="harbor", minimum_importance=0.7,
    ))
    assert [record.event_id for record in results] == ["e1"]


def test_timeline_rejects_conflicting_duplicate_event_ids():
    timeline = EventTimeline()
    timeline.record_event(_event("e1", "help", "2026-10-01"))
    with pytest.raises(ValueError, match="different data"):
        timeline.record_event(_event("e1", "lie", "2026-10-01"))

