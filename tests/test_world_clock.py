from datetime import datetime, timezone

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.time.time_scheduler import TimeScheduler
from cognitive_sandbox.time.world_clock import WorldClock, WorldClockState


def test_clock_advances_and_restores_immutable_snapshot():
    clock = WorldClock("2030-01-01T08:00:00+00:00")
    result = clock.advance(10)
    assert result == datetime(2030, 1, 1, 8, 10, tzinfo=timezone.utc)
    state = clock.state
    assert state == WorldClockState("2030-01-01T08:10:00+00:00")
    clock.advance(5)
    clock.restore(state)
    assert clock.current_time() == result


def test_scheduler_releases_due_event_after_world_tick():
    clock = WorldClock("2030-01-01T08:00:00+00:00")
    scheduler = TimeScheduler()
    scheduled = WorldEvent("scheduled", "main", "w", "supply_arrived", "system", {}, 0)
    scheduler.schedule(scheduled, "2030-01-01T08:05:00+00:00")
    clock.advance(10)
    tick = WorldEvent("tick", "main", "w", "world_tick", "player", {}, 0)
    context = type("Context", (), {"world_clock": clock})()
    assert scheduler.handle_event(tick, context) == (scheduled,)
    assert scheduler.pending_events == ()


def test_clock_rejects_negative_advance():
    import pytest
    with pytest.raises(ValueError):
        WorldClock().advance(-1)


def test_wait_handler_advances_clock_and_emits_world_tick():
    from types import SimpleNamespace
    from cognitive_sandbox.application.actions.wait_handler import WaitHandler
    from cognitive_sandbox.domain.agent_context import AgentContext
    from cognitive_sandbox.domain.character import CharacterState

    clock = WorldClock("2030-01-01T08:00:00+00:00")
    context = SimpleNamespace(
        world_state={}, world_clock=clock, branch_id="main", world_id="w",
        agent_context=AgentContext("player", CharacterState("player", "玩家", "resident", (), (), (), ()), (), (), {}),
        turn=SimpleNamespace(turn_id="turn-1"),
    )
    result = WaitHandler(id_factory=iter(("wait", "tick")).__next__).handle(
        SimpleNamespace(actor_id="player"), context
    )

    assert clock.current_time().isoformat() == "2030-01-01T08:10:00+00:00"
    assert [event.event_type for event in result.simulation_result.events] == ["wait_elapsed", "world_tick"]
