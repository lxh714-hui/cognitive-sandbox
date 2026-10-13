from types import SimpleNamespace

from cognitive_sandbox.event.event_lifecycle import EventLifecycle, EventLifecyclePolicy


def record(event_type, actor, timestamp, **metadata):
    return SimpleNamespace(event_type=event_type, actor_ids=(actor,), timestamp=timestamp, metadata=metadata)


def test_one_time_event_cannot_be_generated_twice():
    assert not EventLifecyclePolicy.can_generate(
        lifecycle=EventLifecycle.ONE_TIME, event_type="first_meeting", actor_id="a",
        timestamp="2026-10-13T10:00:00+00:00",
        timeline=(record("first_meeting", "a", "2026-10-12T10:00:00+00:00"),),
    )


def test_repeatable_events_respect_cooldown_and_ongoing_events_are_not_restarted():
    history = (record("observe", "a", "2026-10-12T10:00:00+00:00"),)
    assert not EventLifecyclePolicy.can_generate(lifecycle="REPEATABLE", event_type="observe", actor_id="a",
                                                 timestamp="2026-10-13T09:00:00+00:00", timeline=history,
                                                 cooldown_days=2)
    active = (record("investigation", "a", "2026-10-12T10:00:00+00:00", lifecycle_active=True),)
    assert not EventLifecyclePolicy.can_generate(lifecycle="ONGOING", event_type="investigation", actor_id="a",
                                                 timestamp="2026-10-13T09:00:00+00:00", timeline=active)
