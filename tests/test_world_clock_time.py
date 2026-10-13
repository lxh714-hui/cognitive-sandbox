from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.domain.actions import ActionCandidate, ResolvedActionResult
from cognitive_sandbox.event.event_pipeline import EventPipeline
from cognitive_sandbox.history.event_timeline import EventTimeline
from cognitive_sandbox.time.world_clock import WorldClock


def test_pipeline_stamps_untimed_action_from_world_clock():
    clock = WorldClock("2026-10-13T09:00:00+00:00")
    timeline = EventTimeline(clock=lambda: clock.current_time().isoformat())
    pipeline = EventPipeline(event_timeline=timeline)
    action = ActionCandidate(action_id="a1", actor_id="player", intent="help", motivation="test")
    result = ResolvedActionResult("a1", True, "尝试帮助", {})
    event = ActionEventAdapter(world_id="w", branch_id="main", world_revision=0,
                               event_id_factory=lambda: "clock-event").adapt(result, action)
    published = pipeline.publish(event, context=type("Context", (), {"world_clock": clock})())
    assert published[0].timestamp == "2026-10-13T09:00:00+00:00"
    assert timeline.events[0].timestamp == published[0].timestamp
